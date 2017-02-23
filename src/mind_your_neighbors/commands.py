from subprocess import Popen, PIPE

def ip_neigh(device=None):
    command = ['ip', 'neigh', 'show']
    if device is not None:
        command += ['dev', device]
    return Popen(command, stdout=PIPE, stderr=PIPE)\
            .communicate()[0].decode('utf8').splitlines()


def nslookup(addr):
    result = Popen(['nslookup', addr], stdout=PIPE, stderr=PIPE)\
            .communicate()[0].decode('utf8')
    for line in result.splitlines():
        if 'name = ' in line:
            return line.rsplit('name = ')[-1]
    return None
