import json
import logging
from os import path
from functools import wraps

logger = logging.getLogger('MindYourNeighbors')


def _read_cache(file_path):
    if path.exists(file_path):
        with open(file_path, 'r') as fp:
            return json.load(fp)
    return {}


def _write_cache(file_path, cache):
    with open(file_path, 'w') as fp:
        json.dump(cache, fp)


class Cache:

    def __init__(self, cache_file):
        self.section_name = None
        self.cache_file = cache_file
        self._cache_dict = {}

    def __enter__(self):
        self._cache_dict = _read_cache(self.cache_file)
        return self

    def __exit__(self, rtype, rvalue, traceback):
        if not isinstance(rvalue, Exception):
            _write_cache(self.cache_file, self._cache_dict)

    @property
    def section(self):
        """Returns the stored dictionnary for the instance's section."""
        assert self.section_name is not None, "you must set section_name"
        if self.section_name not in self._cache_dict:
            self._cache_dict[self.section_name] = {
                    'results': [], 'last_command': None}
        return self._cache_dict[self.section_name]

    def cache_result(self, result, threshold):
        """Store a result into cache and maintain the cache coherent."""
        count = self.get_result_count(result)
        self.section['results'].append(result)
        self.section['results'] = self.section['results'][-threshold:]
        if count != threshold:
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


def wrap(func):
    "Will wrap func between cache constructing and cache dumping."
    @wraps(func)
    def wrapper(config, *args, **kwargs):
        cache_file = config.get(config.default_section, 'cache_file')
        with Cache(cache_file) as cache:
            return func(config, cache, *args, **kwargs)
    return wrapper
