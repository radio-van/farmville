import subprocess

from exceptions import ShellCommandException


def exec_shell(command: str) -> bytes:
    """
    Low-level executor of shell commands
    """
    argv = command.split()

    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    if proc.returncode != 0:
        raise ShellCommandException(
            error=err,
            message='Failed to execute shell command',
            returncode=proc.returncode
        )

    return out


def write_file(path: str, lines: list, append=False):
    mode = 'a' if append else 'w'
    try:
        with open(path, mode) as file:
            file.writelines(lines)
    except Exception as exc:
        # TODO specify exceptions
        raise Exception(f'Failed to write file {path}') from exc


def pairwise(iterable) -> zip:
    i = iter(iterable)
    return zip(i, i)


def parse_bstring_to_dict(bstring: bytes) -> dict:
    """
    Tool to convert shell output to dict
    b'Key1: value\nKey2: value' -> {Key1: value, Key2: value}
    """
    # TODO add docstring tests
    string = bstring.decode("UTF-8")
    return {key.strip(':'): value for key, value in pairwise(string.split())}


def get_default_gateway(ip: str) -> str:
    """
    10.0.2.254 -> 10.0.2.1
    """
    # TODO add docstring tests
    return '.'.join([*ip.split('.')[:3], '1'])
