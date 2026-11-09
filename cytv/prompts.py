"""Small, explanatory terminal prompts; input mistakes stay in the wizard."""
import os
from pathlib import Path
import shlex

from . import state
from .terminal import console

NETWORK_GUIDE = 'https://www.lg.com/us/support/help-library/lg-tv-how-to-manually-change-the-dns-server-settings--20150576570174'


def answer(ask, prompt):
    value = ask(prompt).strip()
    if value.lower() in ('q', 'quit', 'exit'):
        raise EOFError
    return value


def address_help(write, link=False):
    write = console(write)
    write.heading('Find the IP address on your TV')
    write('Settings > All Settings > General > Network')
    write('  Wi-Fi: Advanced Wi-Fi Settings > IP Address')
    write('  Cable: Wired Connection (Ethernet) > IP Address')
    write('Example: 192.168.1.50 — use the address shown on your TV.')
    if link:
        write('')
        write('Older TVs: All Settings > Connection or Network.')
        write('Keep the TV on, on the same network as this computer.')
        write('Read the address without changing network settings.')
        write('VPNs, guest Wi-Fi and router isolation can block discovery.')
        write.heading('LG network settings guide')
        write(NETWORK_GUIDE)


def tv_address(ask, write, search=None):
    write = console(write)
    write.step(1, 'Connect to your TV')
    scan = search is not None
    while True:
        if scan:
            write('Searching for LG webOS TVs…')
            write('Keep the TV on, on the same network as this computer.')
            try:
                found = search()
            except OSError:
                found = []
                write.error('! Allow Local Network access for cytv or your terminal.')
            if found:
                write.heading('Found TVs — choose yours')
                for index, tv in enumerate(found, 1):
                    write.option(index, tv['name'], tv['host'])
                write.option(0, 'Enter an IP address manually')
                write('')
                write('Enter = first TV   |   r = search again   |   q = quit')
                while True:
                    choice = answer(ask, 'TV number [1]: ').lower()
                    if choice == 'r':
                        break
                    if not choice:
                        choice = '1'
                    if choice.isdecimal() and 0 <= int(choice) <= len(found):
                        if int(choice):
                            return found[int(choice) - 1]['host']
                        scan = False
                        break
                    write.error(f'Enter a number from 0 to {len(found)}, r to search again, or q to quit.')
                if scan:
                    continue
            else:
                write('')
                write.error('! No LG webOS TV found. Retry, or enter its IP below.')
                write('Check VPN and Local Network/firewall access if needed.')
            scan = False
        address_help(write)
        write('')
        write('? = more help   |   ' + ('r = search again   |   ' if search else '') + 'q = quit')
        while True:
            value = answer(ask, 'TV IP address: ')
            if search and value.lower() == 'r':
                scan = True
                break
            if value in ('?', 'help'):
                write.step(1, 'TV address help')
                address_help(write, link=True)
                write('')
                write('Enter the IP below' + (', or r to search again.' if search else '.'))
                continue
            try:
                return state.target(value, 'no-root')['host']
            except ValueError:
                write.error('Enter the TV address, for example 192.168.1.50. Type ? for help finding it.')


def number(ask, write, prompt, minimum, maximum, default=None):
    write = console(write)
    while True:
        value = answer(ask, prompt)
        if not value and default is not None:
            return default
        if value.isdecimal() and minimum <= int(value) <= maximum:
            return int(value)
        write.error(f'Enter a number from {minimum} to {maximum}, or q to quit.')


def confirm(prompt, ask, write, default=False):
    write = console(write)
    write.heading(prompt)
    write('Enter / y = yes   |   n = no   |   q = quit' if default else 'y = yes   |   Enter / n = no   |   q = quit')
    while True:
        value = answer(ask, prompt + ' ' + ('[Y/n]' if default else '[y/N]') + ': ').lower()
        if not value:
            return default
        if value in ('y', 'yes', 'да', 'д'):
            return True
        if value in ('', 'n', 'no', 'нет', 'н'):
            return False
        write.error('Type y for yes, n for no, or q to quit. Enter chooses ' + ('yes.' if default else 'no.'))


def tv_name(ask, write):
    from .package import normalize_tv_name as validate
    write = console(write)
    write.heading('What would you like to name your TV?')
    while True:
        try:
            return validate(answer(ask, 'TV name [Home]: '))
        except ValueError as error:
            write.error(str(error))


def wait_for_tv(ask, write):
    write = console(write)
    write.heading('Turn on your TV')
    write('Turn it on with the remote and wait for the Home screen.')
    write('Installation has not started. Enter = check again   |   q = quit')
    while True:
        if answer(ask, 'TV ready? Press Enter: ').lower() in ('', 'y', 'yes', 'r', 'retry', 'да'):
            return
        write.error('Press Enter once the TV is on, or q to quit.')


def trust_tv(host, port, fingerprint, ask, write):
    write = console(write)
    write.heading('First connection to this TV')
    write(f'TV: {host}  |  SSH port: {port}')
    write('Only continue for your own TV on your trusted home network.')
    write('cytv will remember it and stop if its identity changes.')
    write('')
    write('Enter / y = connect and remember   |   n / q = cancel   |   ? = details')
    while True:
        choice = answer(ask, 'Connect and remember this TV? [Y/n]: ').lower()
        if choice in ('?', 'help'):
            write.heading('Connection details')
            write('This is the public SSH key fingerprint of the TV:')
            write.raw('  ' + fingerprint)
            write('Compare it with a previously trusted SSH connection if available.')
            write('This is not your password or private SSH key. No copying is required.')
            continue
        if choice in ('', 'y', 'yes', 'да', 'д'):
            return True
        if choice in ('n', 'no', 'нет', 'н'):
            return False
        write.error('Press Enter to connect, n to cancel, or ? for connection details.')


def root_credentials(ask, write):
    write = console(write)
    write.heading('Automatic sign-in did not succeed')
    write('Choose how you normally connect to this TV.')
    write.option(1, 'Use the root SSH password')
    write.option(2, 'Choose an SSH private key file')
    write('')
    write('Enter = password   |   q = quit')
    choice = number(ask, write, 'Sign-in method [1]: ', 1, 2, default=1)
    return identity_path(ask, write) if choice == 2 else None


def identity_path(ask, write):
    write = console(write)
    write.heading('SSH key file')
    write('Drag the private key file here, or paste its full path.')
    write('It stays on this computer.')
    write('Enter = use an existing password/passwordless login   |   q = quit')
    while True:
        value = answer(ask, 'Private key file: ')
        if not value:
            return None
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        path = Path(value).expanduser()
        if not path.is_file() and os.name != 'nt' and '\\' in value:
            try:
                parts = shlex.split(value)
                if len(parts) == 1:
                    path = Path(parts[0]).expanduser()
            except ValueError:
                pass
        if path.is_file():
            return str(path.resolve())
        write.error('That file was not found. Drag the private key file here, paste its path, or press Enter to skip.')
