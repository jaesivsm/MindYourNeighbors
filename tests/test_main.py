import unittest

from mind_your_neighbors.main import _split, check_neighborhood


NEIGHS = [
        ('192.168.0.1 dev eth0 lladdr mac1 STALE', '192.168.0.1', 'mac1'),
        ('192.168.0.2 dev eth0 lladdr mac2 REACHABLE', '192.168.0.2', 'mac2'),
        ('10.0.0.1 dev eth1 lladdr mac3 STALE', '10.0.0.1', 'mac3'),
        ('10.0.0.2 dev eth1 lladdr mac4 REACHABLE', '10.0.0.2', 'mac4')]


class MainTest(unittest.TestCase):

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
        known_machines = {'machine1': 'mac1', 'machine2': 'mac2',
                          'machine3': 'mac3', 'machine4': 'mac4'}
        self.assertTrue(  # no known machines passed, filter ignored
                check_neighborhood(NEIGHS, filter_on_machines='Mac1, MAC3 '))
        self.assertFalse(check_neighborhood(NEIGHS,
                filter_on_machines='Machine1, MACHINE3 ',
                known_machines=known_machines))
        self.assertTrue(check_neighborhood(NEIGHS,
                filter_on_machines='Machine2, MAChine4 ',
                known_machines=known_machines))
        self.assertTrue(check_neighborhood(NEIGHS,
                filter_out_machines='Machine1, MAChine3 ',
                known_machines=known_machines))
        self.assertFalse(check_neighborhood(NEIGHS,
                filter_out_machines='Machine2, MACHINE4 ',
                known_machines=known_machines))
