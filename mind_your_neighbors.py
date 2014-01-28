#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import logging
from configparser import ConfigParser
from subprocess import Popen, PIPE


config = ConfigParser(defaults={
        'logfile': '/var/log/neighbors.log',
        'loglevel': 'INFO',
        'error_on_stderr': 'true',
        'cache_file': '/run/mind_your_neighbors.cache',
})
config.read(['/etc/mind_your_neighbors.conf',
    os.path.expanduser('~/.config/mind_your_neighbors.conf')])
MAIN_SEC = config.default_section

logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler(config.get(MAIN_SEC, 'logfile')))
logger.setLevel(getattr(logging, config.get(MAIN_SEC, 'loglevel')))


def ip_neigh_match(regex):
    stdout = Popen(['ip', 'neigh'], stdout=PIPE, stderr=PIPE).communicate()[0]
    stdout = stdout.decode('utf8')

    regex = re.compile(regex)
    for neighbor in stdout.splitlines():
        if regex.match(neighbor):
            return True
    return False


def is_in_cache(key, value):
    path = config.get(MAIN_SEC, 'cache_file')
    if not os.path.exists(path):
        return False
    with open(path, 'r') as fp:
        cache = json.load(fp)
    logger.debug('got value %r from cache, comparing to %r'
            % (cache.get(key), value))
    return cache.get(key) == value


def write_cache(key, value):
    path = config.get(MAIN_SEC, 'cache_file')
    logger.info(path)
    if os.path.exists(path):
        with open(path, 'r') as fp:
            cache = json.load(fp)
    else:
        cache = {}
    cache[key] = value
    with open(config.get(MAIN_SEC, 'cache_file'), 'w') as fp:
        json.dump(cache, fp)


def main():
    for section in config.sections():
        if section == config.default_section:
            continue
        if ip_neigh_match(config.get(section, 'regex')):
            cmd = config.get(section, 'command_match')
        else:
            cmd = config.get(section, 'command_no_match')
        if is_in_cache(section, cmd):
            logger.debug('already in state : not launching %r' % cmd)
            continue
        logger.info('launching %r' % cmd)
        process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        results = process.communicate()
        if config.getboolean(section, 'error_on_stderr') and results[1]:
            logger.error(results[1])
        write_cache(section, cmd)


if __name__ == '__main__':
    main()
