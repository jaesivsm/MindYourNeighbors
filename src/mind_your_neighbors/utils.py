import logging
from os import path
from configparser import ConfigParser
from logging.handlers import SysLogHandler


def set_logger(loglevel, logfile=None):
    logger = logging.getLogger('MindYourNeighbors')
    log_level = getattr(logging, loglevel.upper())
    base_format = '%(levelname)s - %(message)s'
    if logfile:
        handler = logging.FileHandler(path.expanduser(logfile))
        formatter = logging.Formatter('%(asctime)s ' + base_format)
    else:
        handler = SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(name)s: ' + base_format)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def get_config(config=None):
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
    set_logger(config.get(config.default_section, 'loglevel'),
               config.get(config.default_section, 'logfile', fallback=None))
    return config
