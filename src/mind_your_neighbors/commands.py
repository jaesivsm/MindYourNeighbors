from functools import lru_cache
from subprocess import Popen, PIPE


def execute(cmd):
    return Popen(cmd, stdout=PIPE, stderr=PIPE)


def get_output_from_cmd(cmd):
    return execute(cmd).communicate()[0].decode('utf8')


@lru_cache()
def ip_neigh(device=None):
    lines, command = [], ['ip', 'neigh', 'show']
    if device is not None:
        command += ['dev', device]
    for line in get_output_from_cmd(command).splitlines():
        if 'lladdr' not in line:
            addr, mac = '', ''
        elif device is None:
            addr, _, _, _, mac, _ = line.split()
        else:
            addr, _, mac, _ = line.split()
        lines.append((line, addr, mac))
    return lines
