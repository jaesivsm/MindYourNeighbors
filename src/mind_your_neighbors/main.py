import re
import logging
from datetime import datetime
from collections import defaultdict

from cronex import CronExpression

from mind_your_neighbors import utils, const, commands, cache

logger = logging.getLogger('MindYourNeighbors')


def _split(string, lower=True):
    return [split.strip().lower() if lower else split.strip()
            for split in string.split(',')]


def _to_filter_on_mac(list_, mapping):
    return {mapping[str_] for str_ in _split(list_) if str_ in mapping}


def logging_results(addr_by_mac, known_machines):
    """Will fire several logging message with levels depending on matching
    status"""
    rev_machine = {mac: name for name, mac in known_machines.items()} \
            if known_machines else {}

    for loglevel, key in const.LOG_TO_MATCH_RES_MAPPING:
        if logger.isEnabledFor(loglevel):
            for mac, addrs in addr_by_mac[key].items():
                message = '%s - %s' % (key.name, mac)
                written = False
                if mac in rev_machine:
                    written = True
                    message += ' - MACHINE: %s' % rev_machine[mac]
                if not written and addrs:
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
                       exclude=None, known_machines=None):
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

    logging_results(addr_by_mac, known_machines)
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


@cache.wrap
def browse_config(config, cache):
    """Will browse all section of the config,
    fill cache and launch command when needed.
    """
    commands.ip_neigh.cache_clear()
    processes = {}
    now = datetime.now()
    now = (now.year, now.month, now.day, now.hour, now.minute)
    excluded_sections = {config.default_section, const.KNOWN_MACHINES_SECTION}
    known_machines = utils.get_known_machines(config)
    for section in config.values():
        if section.name in excluded_sections:
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
        neighbors = commands.ip_neigh(device=device)

        threshold = section.getint('threshold')

        if check_neighborhood(neighbors,
                              section.get('filter_on_regex'),
                              section.get('filter_out_regex'),
                              section.get('filter_on_machines'),
                              section.get('filter_out_machines'),
                              section.get('exclude'),
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
            logger.warning('%r - launching: %r', section.name, cmd)
            processes[section.name] = commands.execute(cmd.split())
        else:
            logger.info('%r - no command to launch', section.name)

    handle_processes(processes, config, cache)
