import re
import logging
from datetime import datetime
from subprocess import Popen, PIPE
from collections import defaultdict

from cronex import CronExpression

from mind_your_neighbors import utils, const
from mind_your_neighbors.cache import Cache
from mind_your_neighbors.commands import ip_neigh, nslookup

logger = logging.getLogger('MindYourNeighbors')


def _split(string, lower=True):
    return [split.strip().lower() if lower else split.strip()
            for split in string.split(',')]


def _to_filter_on_mac(list_, mapping):
    return {mapping[str_] for str_ in _split(list_) if str_ in mapping}


def logging_results(addr_by_mac, lookup_addr):
    """Will fire several logging message with levels depending on matching
    status"""
    for loglevel, key in const.LOG_TO_MATCH_RES_MAPPING:
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


def process_filters(filter_on_regex, filter_out_regex, exclude,
                    filter_on_machines, filter_out_machines, known_machines):
    filter_on, filter_out = [const.REACHABLE.match], []
    filter_on_mac, filter_out_mac = set(), set()

    if filter_on_regex:
        filter_on.append(re.compile(filter_on_regex).match)
    if filter_out_regex:
        filter_out.append(re.compile(filter_out_regex).match)
    if known_machines and filter_on_machines:
        filter_on_mac = _to_filter_on_mac(filter_on_machines, known_machines)
    if known_machines and filter_out_machines:
        filter_out_mac = _to_filter_on_mac(filter_out_machines, known_machines)
    if exclude:
        filter_out.append(lambda string: any(value in string
                            for value in _split(exclude, lower=False)))

    return filter_on, filter_out, filter_on_mac, filter_out_mac


def check_neighborhood(neighbors, filter_on_regex=None, filter_out_regex=None,
                       filter_on_machines=None, filter_out_machines=None,
                       exclude=None, lookup_addr=False, known_machines=None):
    """Will execute *ip neigh* unless the result of the command has been
    cached. Will then compile a specific regex for the given parameters and
    return True if matching result means there is someone in the local network.
    """
    filter_on, filter_out, filter_on_mac, filter_out_mac = process_filters(
            filter_on_regex, filter_out_regex, exclude, filter_on_machines,
            filter_out_machines, known_machines)
    result = defaultdict(list)
    addr_by_mac = defaultdict(lambda: defaultdict(list))
    for line, addr, mac in neighbors:
        if any(match(line) for match in filter_out) or mac in filter_out_mac:
            key = const.MatchResult.EXCLUDED
        elif all(match(line) for match in filter_on) \
                and (not filter_on_mac or mac in filter_on_mac):
            key = const.MatchResult.MATCHED
        else:
            key = const.MatchResult.NO_MATCH
        result[key].append(line)
        addr_by_mac[key][mac].append(addr)

    logging_results(addr_by_mac, lookup_addr)
    return bool(result[const.MatchResult.MATCHED])


def handle_processes(processes, config, cache):
    """Will check on processes launched during config browsing and log result
    """
    for section, process in processes.items():
        if not config.getboolean(section, 'error_on_stderr', fallback=False):
            continue
        stdout, stderr = process.communicate()
        logger.debug(stdout)
        if not stderr:
            continue
        logger.error('%r - an error occured, removing stored command',
                     section.name)
        cache.section_name = section.name
        cache.cache_command(None)
        logger.error('%r - command stderr was: %r', section.name, stderr)


@Cache
def browse_config(config, cache):
    """Will browse all section of the config,
    fill cache and launch command when needed.
    """
    processes = {}
    now = datetime.now()
    now = (now.year, now.month, now.day, now.hour, now.minute)
    neighbors_by_device = {}
    excluded_sections = {config.default_section, const.KNOWN_MACHINES_SECTION}
    known_machines = utils.get_known_machines(config)
    for section in config.values():
        if section.name not in excluded_sections:
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
        device = section.get('device')
        if device not in neighbors_by_device:
            neighbors_by_device[device] = list(ip_neigh(device=device))

        threshold = section.getint('threshold')

        if check_neighborhood(neighbors_by_device[device],
                              section.get('filter_on_regex'),
                              section.get('filter_out_regex'),
                              section.get('filter_on_machines'),
                              section.get('filter_out_machines'),
                              section.get('exclude'),
                              section.get('nslookup'),
                              known_machines=known_machines):
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

    handle_processes(processes, config, cache)
