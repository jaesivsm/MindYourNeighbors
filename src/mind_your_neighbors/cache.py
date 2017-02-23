import json
import logging
from os import path


class Cache:
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
        if self.section_name not in self.__cache_dict:
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
