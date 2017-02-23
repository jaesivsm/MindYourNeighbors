import logging
from os import path
from configparser import ConfigParser
from logging.handlers import SysLogHandler


def set_logger(loglevel, logfile=None, write_to_term=False):
    logger = logging.getLogger('MindYourNeighbors')
    # cleaning existing handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)

    base_format = '%(levelname)s - %(message)s'
    if write_to_term:
        logger.addHandler(logging.StreamHandler())
    if logfile:
        logger.addHandler(logging.FileHandler(path.expanduser(logfile)))
        formatter = logging.Formatter('%(asctime)s ' + base_format)
    else:
        logger.addHandler(SysLogHandler(address='/dev/log'))
        formatter = logging.Formatter('%(name)s: ' + base_format)
    for handler in logger.handlers:
        handler.setFormatter(formatter)
        handler.setLevel(loglevel)
    logger.addHandler(handler)
    logger.setLevel(loglevel)
    return logger


def get_config(config=None, force_verbose=False, write_to_term=False):
    if not config:
        config = ConfigParser(defaults={
                'enabled': 'true',
                'nslookup': 'false',
                'loglevel': 'INFO',
                'error_on_stderr': 'true',
                'cache_file': '/run/shm/mind_your_neighbors.cache',
                'threshold': '3',
                'loop_time_sec': '120',
        })

    config.read(['/etc/mind_your_neighbors.conf',
                path.expanduser('~/.config/mind_your_neighbors.conf')])
    if force_verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = config.get(config.default_section, 'loglevel')
        loglevel = getattr(logging, loglevel.upper())

    logfile = config.get(config.default_section, 'logfile', fallback=None)

    set_logger(loglevel, logfile, write_to_term)
    return config
