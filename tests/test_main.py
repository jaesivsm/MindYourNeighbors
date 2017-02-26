from unittest import TestCase, mock
from datetime import datetime

from mind_your_neighbors.const import KNOWN_MACHINES_SECTION
from mind_your_neighbors.utils import _get_default_config
from mind_your_neighbors.main import _split, check_neighborhood, browse_config


NEIGHS = [
        ('192.168.0.1 dev eth0 lladdr mac1 STALE', '192.168.0.1', 'mac1'),
        ('192.168.0.2 dev eth0 lladdr mac2 REACHABLE', '192.168.0.2', 'mac2'),
        ('10.0.0.1 dev eth1 lladdr mac3 STALE', '10.0.0.1', 'mac3'),
        ('10.0.0.2 dev eth1 lladdr mac4 REACHABLE', '10.0.0.2', 'mac4')]

KNOWN_MACHINES = {'machine1': 'mac1', 'machine2': 'mac2',
                  'machine3': 'mac3', 'machine4': 'mac4'}


class MainTest(TestCase):

    def test_split(self):
        self.assertEqual(['a', 'b c', 'd'], _split('A, B c, D '))
        self.assertEqual(['A', 'B c', 'D'], _split('A, B c, D ', lower=False))

    def test_check_neighborhood(self):
        self.assertTrue(check_neighborhood(NEIGHS))

    def test_check_neighborhood_regex(self):
        mac3, mac4 = '.*mac3.*', '.*mac4.*'
        self.assertFalse(check_neighborhood(NEIGHS, filter_on_regex=mac3))
        self.assertTrue(check_neighborhood(NEIGHS, filter_on_regex=mac4))
        self.assertTrue(check_neighborhood(NEIGHS, filter_out_regex=mac3))
        self.assertFalse(check_neighborhood(NEIGHS, filter_on_regex='10.0.0',
                                            filter_out_regex=mac4))

    def test_check_neighborhood_machine(self):
        self.assertTrue(  # no known machines passed, filter ignored
                check_neighborhood(NEIGHS, filter_on_machines='Mac1, MAC3 '))
        self.assertFalse(check_neighborhood(NEIGHS,
                filter_on_machines='Machine1, MACHINE3 ',
                known_machines=KNOWN_MACHINES))
        self.assertTrue(check_neighborhood(NEIGHS,
                filter_on_machines='Machine2, MAChine4 ',
                known_machines=KNOWN_MACHINES))
        self.assertTrue(check_neighborhood(NEIGHS,
                filter_out_machines='Machine1, MAChine3 ',
                known_machines=KNOWN_MACHINES))
        self.assertFalse(check_neighborhood(NEIGHS,
                filter_out_machines='Machine2, MACHINE4 ',
                known_machines=KNOWN_MACHINES))

    @mock.patch('mind_your_neighbors.cache._read_cache')
    @mock.patch('mind_your_neighbors.cache._write_cache')
    @mock.patch('mind_your_neighbors.main.commands.ip_neigh')
    @mock.patch('mind_your_neighbors.main.commands.execute')
    @mock.patch('mind_your_neighbors.main.commands.nslookup')
    def test_browse_config(self, mock_nslookup, mock_exec,
                           mock_neigh, mock_write, mock_read):
        mock_neigh.return_value = NEIGHS
        mock_read.return_value = {}
        mock_exec.return_value.communicate.return_value = (None, None)
        config = _get_default_config()
        cache_file = config[config.default_section].get('cache_file')

        config[KNOWN_MACHINES_SECTION] = KNOWN_MACHINES
        # disabled
        config['test1'] = {'enabled': 'false', 'command_neighbor': 'garbage'}
        # disabled because not in cron
        now = datetime.now()
        config['test2'] = {'cron': '%d %d * * * *' % (
                (1, 1) if (1, 1) == (now.minute, now.hour) else (2, 2)),
                'command_neighbor': 'garbage'}
        # should match
        cmd = 'command to run'
        config['test3'] = {'command_neighbor': cmd,
                           'filter_on_machines': 'machine2,machine4'}

        # running until reaching threshold
        threshold = config[config.default_section].getint('threshold')
        for i in range(1, threshold + 1):
            browse_config(config)
            cache = {'test3': {'last_command': None if i != threshold else cmd,
                               'results': i * ['neighbor']}}
            mock_write.assert_called_with(cache_file, cache)
            mock_write.reset_mock()
            mock_read.return_value = cache
            if i != threshold:
                mock_exec.assert_not_called()

        mock_exec.assert_called_with(cmd.split())
        mock_exec.reset_mock()

        # re-matching: nothing happens
        browse_config(config)
        mock_write.assert_called_with(cache_file, cache)
        mock_write.reset_mock()
        mock_exec.assert_not_called()

        # changing to not matching
        config['test3']['filter_on_machines'] = 'machine1'

        for i in range(1, threshold + 1):
            browse_config(config)
            cache = {'test3': {'last_command': cmd if i != threshold else None,
                               'results': (threshold - i) * ['neighbor']
                                           + i * ['no_neighbor']}}
            mock_write.assert_called_with(cache_file, cache)
            mock_write.reset_mock()
            mock_read.return_value = cache
            mock_exec.assert_not_called()

        # changing command, exec passing from None to something
        cmd = config['test3']['command_no_neighbor'] = 'command no neighbor'
        browse_config(config)
        cache = {'test3': {'last_command': cmd,
                            'results': 3 * ['no_neighbor']}}
        mock_write.assert_called_with(cache_file, cache)
        mock_write.reset_mock()
        mock_exec.assert_called_with(cmd.split())
