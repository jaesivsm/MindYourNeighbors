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
        'trigger': '3',
})
config.read(['/etc/mind_your_neighbors.conf',
    os.path.expanduser('~/.config/mind_your_neighbors.conf')])
MAIN_SEC = config.default_section

logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler(config.get(MAIN_SEC, 'logfile')))
logger.setLevel(getattr(logging, config.get(MAIN_SEC, 'loglevel')))


def ip_neigh_match(regex, exclude=None):
    stdout = Popen(['ip', 'neigh'], stdout=PIPE, stderr=PIPE).communicate()[0]
    stdout = stdout.decode('utf8')

    regex = re.compile(regex)
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


def is_in_cache(key, value):
    path = config.get(MAIN_SEC, 'cache_file')
    if not os.path.exists(path):
        return False
    with open(path, 'r') as fp:
        cache = json.load(fp)
    if cache.get(key, []).count(value) == config.getint(MAIN_SEC, 'trigger'):
        return cache[key][-1] == value
    return None


def write_cache(key, value):
    path = config.get(MAIN_SEC, 'cache_file')
    if os.path.exists(path):
        with open(path, 'r') as fp:
            cache = json.load(fp)
    else:
        cache = {}
    if key in cache:
        cache[key].append(value)
    else:
        cache[key] = [value]
    cache[key] = cache[key][-config.getint(MAIN_SEC, 'trigger'):]
    logger.debug('write_cache: %r => %r' % (key, cache[key]))
    with open(config.get(MAIN_SEC, 'cache_file'), 'w') as fp:
        json.dump(cache, fp)


def main():
    for section in config.sections():
        if section == config.default_section:
            continue

        if ip_neigh_match(
                config.get(section, 'regex'),
                config.get(section, 'exclude', fallback=None)):
            cmd = config.get(section, 'command_match')
            result = 'match'
        else:
            cmd = config.get(section, 'command_no_match')
            result = 'no_match'

        in_cache = is_in_cache(section, result)
        if in_cache is True:
            continue
        if in_cache is None:
            write_cache(section, result)
            continue

        logger.warn('launching %r' % cmd)
        process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stderr = process.communicate()[1]
        if stderr and config.getboolean(section, 'error_on_stderr'):
            logger.error(stderr)
        write_cache(section, result)


if __name__ == '__main__':
    main()
