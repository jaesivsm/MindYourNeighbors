import re
import logging
from datetime import datetime
from subprocess import Popen, PIPE
from collections import defaultdict

from cronex import CronExpression

from mind_your_neighbors.cache import Cache
from mind_your_neighbors.commands import ip_neigh, nslookup

logger = logging.getLogger('MindYourNeighbors')


def check_neighborhood(filter_on, exclude=None,
                       lookup_addr=False, device=None):
    """Will execute *ip neigh* unless the result of the command has been
    cached. Will then compile a specific regex for the given parameters and
    return True if matching result means there is someone in the local network.
    """
    regex = re.compile('.*%s.*REACHABLE' % filter_on)

    if exclude:
        exclude = re.compile(".*(%s).*" % '|'.join(exclude.split(',')))
    result = defaultdict(list)
    addr_by_mac = defaultdict(lambda: defaultdict(list))
    for neighbor in ip_neigh(device=device):
        if exclude and exclude.match(neighbor):
            key = 'excluded'
        elif regex.match(neighbor):
            key = 'matched'
        else:
            key = 'no match'
        result[key] = neighbor
        try:  # debugging informations gathering
            if device is None:
                addr, _, _, _, mac, _ = neighbor.split()
            else:
                addr, _, mac, _ = neighbor.split()
            addr_by_mac[key][mac].append(addr)
        except Exception:
            pass

    # printing debug informations on results
    for loglevel, key in ((logging.DEBUG, 'excluded'),
                          (logging.INFO, 'matched'),
                          (logging.DEBUG, 'no match')):
        if logger.isEnabledFor(loglevel):
            for mac, addrs in addr_by_mac[key].items():
                message = '%s - %s' % (key.upper(), mac)
                if lookup_addr:
                    fqdns = set()
                    for addr in addrs:
                        fqdn = nslookup(addr)
                        if fqdn is not None:
                            fqdns.add(fqdn)
                    if fqdns:
                        message += ' - FQDNS: ' + ' '.join(fqdns)
                if addrs:
                    message += ' - ADDRS: ' + ' '.join(addrs)
                logger.log(loglevel, message)

    return bool(result['matched'])


@Cache
def browse_config(config, cache):
    """Will browse all section of the config,
    fill cache and launch command when needed.
    """
    processes = {}
    now = datetime.now()
    now = (now.year, now.month, now.day, now.hour, now.minute)
    for section in config.values():
        if section.name == config.default_section:
            continue

        if not section.getboolean('enabled'):
            logger.debug('section %r not enabled', section)
            continue

        cron = section.get('cron')
        if cron and not CronExpression(cron).check_trigger(now):
            logger.debug('section %r disabled for now', section)
            continue

        logger.debug('%r - processing section', section.name)
        cache.section_name = section.name

        threshold = section.getint('threshold')
        filter_on = section.get('filter_on')
        exclude = section.get('exclude')
        nslookup = section.get('nslookup')
        device = section.get('device')

        if check_neighborhood(filter_on, exclude, nslookup, device):
            cmd = section.get('command_neighbor')
            result = 'neighbor'
        else:
            cmd = section.get('command_no_neighbor')
            result = 'no_neighbor'

        cache.cache_result(result, threshold)
        logger.info('%r - cache state: %r', section.name, cache.section)
        count = cache.get_result_count(result)
        if count != threshold:
            logger.info("%r - cache count hasn't reached threshold yet "
                        "(%d/%d)", section.name, count, threshold)
            continue
        if cache.last_command == cmd:
            logger.info('%r - command has already been run', section.name)
            continue

        cache.cache_command(cmd)
        if cmd:
            logger.warn('%r - launching: %r', section.name, cmd)
            processes[section.name] = Popen(cmd.split(),
                                            stdout=PIPE, stderr=PIPE)
        else:
            logger.info('%r - no command to launch', section.name)

    for section in processes:
        if not config.getboolean(section, 'error_on_stderr', fallback=False):
            continue
        stdout, stderr = processes[section].communicate()
        logger.debug(stdout)
        if not stderr:
            continue
        logger.error('%r - an error occured, removing stored command',
                     section.name)
        cache.section_name = section.name
        cache.cache_command(None)
        logger.error('%r - command stderr was: %r', section.name, stderr)
