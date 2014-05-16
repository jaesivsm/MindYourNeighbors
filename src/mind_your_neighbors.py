#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import json
import logging
from os import path
from functools import lru_cache
from logging.handlers import SysLogHandler
from configparser import ConfigParser
from subprocess import Popen, PIPE


class Cache(object):
    __cache_dict = {}

    def __init__(self, section, cache_file):
        self.section_name = section.name
        if not self.__cache_dict and path.exists(cache_file):
            with open(cache_file, 'r') as fp:
                self.__cache_dict.update(json.load(fp))

    @classmethod
    def dump(cls, cache_file):
        if cls.__cache_dict is not None:
            with open(cache_file, 'w') as fp:
                json.dump(cls.__cache_dict, fp)

    @property
    def section(self):
        """Returns the stored dictionnary for the instance's section."""
        if not self.section_name in self.__cache_dict:
            self.__cache_dict[self.section_name] = {
                    'results': [], 'last_command': None}
        return self.__cache_dict[self.section_name]

    def cache_result(self, result, threshold):
        """Store a result into cache and maintain the cache coherent."""
        count = self.get_result_count(result)
        self.section['results'].append(result)
        self.section['results'] = self.section['results'][-threshold:]
        if count != threshold:
            logger = logging.getLogger('MindYourNeighbors')
            logger.debug('cache/%s/%s %d => %d', self.section_name, result,
                        count, self.get_result_count(result))

    def get_result_count(self, result):
        return self.section['results'].count(result)

    def cache_command(self, command):
        """Store *command* as the last command launched."""
        self.section['last_command'] = command

    @property
    def last_command(self):
        return self.section['last_command']


@lru_cache(maxsize=None)
def ip_neigh():
    return Popen(['ip', 'neigh'], stdout=PIPE, stderr=PIPE
                ).communicate()[0].decode('utf8').splitlines()


def check_neighborhood(neighbor_ip4=None, neighbor_ip6=None, exclude=None):
    """Will execute *ip neigh* unless the result of the command has been
    cached. Will then compile a specific regex for the given parameters and
    return True if matching result means there is someone in the local network.
    """
    assert neighbor_ip4 or neighbor_ip6
    logger = logging.getLogger('MindYourNeighbors')

    regex = re.compile('%s.*(REACHABLE|STALE)' % (
                       (neighbor_ip4 or neighbor_ip6)
                       if not (neighbor_ip4 and neighbor_ip6)
                       else '(%s|%s)' % (neighbor_ip4, neighbor_ip6)))

    if exclude:
        exclude = re.compile(".*(%s).*" % '|'.join(exclude.split(',')))
    result = False
    for neighbor in ip_neigh():
        if exclude and exclude.match(neighbor):
            logger.debug("EXCLUDED - %r" % neighbor)
            continue
        if regex.match(neighbor):
            logger.debug("MATCH    - %r" % neighbor)
            result = True
        else:
            logger.debug("NO MATCH - %r" % neighbor)
    return result


def browse_config(config):
    """Will browse all section of the config,
    fill cache and launch command when needed.
    """
    processes = {}
    logger = logging.getLogger('MindYourNeighbors')
    cache_file = config.get(config.default_section, 'cache_file')
    for section in config.values():
        if section.name == config.default_section:
            continue

        if not section.getboolean('enabled', fallback=False):
            logger.debug('section %r not enabled', section)
            continue

        cache = Cache(section, cache_file)

        threshold = section.getint('threshold')

        if check_neighborhood(section.get('neighbor_ip4'),
                              section.get('neighbor_ip6'),
                              section.get('exclude', fallback=None)):
            cmd = section.get('command_neighbor')
            result = 'neighbor'
        else:
            cmd = section.get('command_no_neighbor')
            result = 'no_neighbor'

        cache.cache_result(result, threshold)
        if cache.get_result_count(result) != threshold:
            logger.debug("cache count hasn't reached threshold (%r)", threshold)
            continue
        if cache.last_command == cmd:  # command has already been run
            continue

        if logger.isEnabledFor(logging.INFO):
            logger.info('cache content is :')
            for line in ip_neigh():
                logger.info(line)
        cache.cache_command(cmd)
        logger.warn('LAUNCHING - %r' % cmd)
        processes[section.name] = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)

    Cache.dump(cache_file)
    for section in processes:
        if config.getboolean(section, 'error_on_stderr', fallback=False):
            stdout, stderr = processes[section].communicate()
            logger.debug(stdout)
            if stderr:
                logger.error(stderr)


def set_logger(loglevel, logfile=None):
    logger = logging.getLogger('MindYourNeighbors')
    log_level = getattr(logging, loglevel.upper())
    if logfile:
        handler = logging.FileHandler(path.expanduser(logfile))
        formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    else:
        handler = SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(name)s: %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    logger.setLevel(log_level)


def main():
    config = ConfigParser(defaults={
            'loglevel': 'INFO',
            'error_on_stderr': 'true',
            'cache_file': '/run/shm/mind_your_neighbors.cache',
            'threshold': '3',
    })
    config.read(['/etc/mind_your_neighbors.conf',
                path.expanduser('~/.config/mind_your_neighbors.conf')])
    set_logger(config.get(config.default_section, 'loglevel'),
               config.get(config.default_section, 'logfile', fallback=None))
    browse_config(config)


if __name__ == '__main__':
    main()
