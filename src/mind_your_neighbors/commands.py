from subprocess import Popen, PIPE


def get_output_from_cmd(cmd):
    return Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()[0].decode('utf8')


def ip_neigh(device=None):
    command = ['ip', 'neigh', 'show']
    if device is not None:
        command += ['dev', device]
    for line in get_output_from_cmd(command).splitlines():
        if device is None:
            addr, _, _, _, mac, _ = line.split()
        else:
            addr, _, mac, _ = line.split()
        yield line, addr, mac


def nslookup(addr):
    for line in get_output_from_cmd(['nslookup', addr]).splitlines():
        if 'name = ' in line:
            return line.rsplit('name = ')[-1]
    return None
