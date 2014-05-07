#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import logging
from configparser import ConfigParser
from subprocess import Popen, PIPE


DEFAULT_CACHE_FILE = '/run/shm/mind_your_neighbors.cache'

config = ConfigParser(defaults={
        'logfile': '/home/jaes/neighbors.log',
        'loglevel': 'INFO',
        'error_on_stderr': 'true',
        'cache_file': DEFAULT_CACHE_FILE,
        'trigger': '3',
})
config.read(['/etc/mind_your_neighbors.conf',
    os.path.expanduser('~/.config/mind_your_neighbors.conf')])
MAIN_SEC = config.default_section
DEFAULT_CACHE_FILE = config.get(MAIN_SEC, 'cache_file')

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
log_level = getattr(logging, config.get(MAIN_SEC, 'loglevel').upper())
handler = logging.FileHandler(config.get(MAIN_SEC, 'logfile'))
handler.setFormatter(formatter)
handler.setLevel(log_level)
logger.addHandler(handler)
logger.setLevel(log_level)


class Cache(object):
    __cache_dict = {}
    _cache_file = DEFAULT_CACHE_FILE

    def __init__(self, section_name):
        self.section_name = section_name
        if not self.__cache_dict and os.path.exists(self._cache_file):
            with open(self._cache_file, 'r') as fp:
                self.__cache_dict.update(json.load(fp))

    @classmethod
    def dump(cls):
        if cls.__cache_dict is not None:
            with open(cls._cache_file, 'w') as fp:
                json.dump(cls.__cache_dict, fp)

    @property
    def section(self):
        if not self.section_name in self.__cache_dict:
            self.__cache_dict[self.section_name] = {
                    'results': [], 'last_command': None}
        return self.__cache_dict[self.section_name]

    def cache_result(self, result, trigger):
        self.section['results'].append(result)
        self.section['results'] = self.section['results'][-trigger:]
        if self.get_result_count(result) not in (0, 3):
            logger.info('cache: %r => %r' % (self.section_name,
                                             self.section['results']))

    def get_result_count(self, result):
        return self.section['results'].count(result)

    def cache_command(self, command):
        self.section['last_command'] = command

    @property
    def last_command(self):
        return self.section['last_command']


__neighborhood_cache = None

def check_neighborhood(neighbor_ip4=None, neighbor_ip6=None, exclude=None):
    assert neighbor_ip4 or neighbor_ip6
    global __neighborhood_cache
    if __neighborhood_cache:
        stdout = __neighborhood_cache
    else:
        stdout = __neighborhood_cache = Popen(['ip', 'neigh'], stdout=PIPE,
                 stderr=PIPE).communicate()[0].decode('utf8')

    regex = re.compile('%s.*(REACHABLE|STALE)' % (
                       (neighbor_ip4 or neighbor_ip6)
                       if not (neighbor_ip4 and neighbor_ip6)
                       else '(%s|%s)' % (neighbor_ip4, neighbor_ip6)))

    if exclude:
        exclude = re.compile(exclude)
    for neighbor in stdout.splitlines():
        if exclude and exclude.match(neighbor):
            logger.debug("line %r is excluded" % neighbor)
            continue
        if regex.match(neighbor):
            logger.debug("line %r is a match" % neighbor)
            return True
        logger.debug("line %r is no match" % neighbor)
    return False


def main():
    cache_file = config.get(config.default_section, 'cache_file')
    for section in config.sections():
        if section == config.default_section:
            continue

        if not config.getint(section, 'enabled', fallback=False):
            logger.debug('section %r not enabled', section)
            continue

        cache = Cache(section)

        trigger = config.getint(section, 'trigger')

        if check_neighborhood(
                config.get(section, 'neighbor_ip4'),
                config.get(section, 'neighbor_ip6'),
                config.get(section, 'exclude', fallback=None)):
            cmd = config.get(section, 'command_neighbor')
            result = 'neighbor'
        else:
            cmd = config.get(section, 'command_no_neighbor')
            result = 'no_neighbor'

        cache.cache_result(result, trigger)
        if cache.get_result_count(result) != trigger:
            logger.debug("cache count hasn't reached trigger (%r)", trigger)
            continue
        if cache.last_command == cmd:
            logger.debug("command %r already launched", cmd)
            continue

        logger.warn('launching %r' % cmd)

        process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stderr = process.communicate()[1]
        if stderr and config.getboolean(section, 'error_on_stderr'):
            logger.error(stderr)

        cache.cache_command(cmd)


if __name__ == '__main__':
    main()
    Cache.dump()
