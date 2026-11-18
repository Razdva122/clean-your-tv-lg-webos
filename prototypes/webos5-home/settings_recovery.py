"""Offline transaction prototype for an explicit webOS 5.x defaultApps.home."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'root-edition' / 'runtime'))
from c1_gate import atomic, secure, trusted_directory

ROOT_HOME = 'com.cleanyourtv.root.preview'
LG_HOME = ('com.webos.app.home', 'com.webos.app.fullhome')


@contextmanager
def locked(journal):
    trusted_directory(journal.parent, os.getuid())
    fd = os.open(journal.with_suffix('.lock'), os.O_RDONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def read_journal(journal):
    try:
        state = json.loads(secure(journal, os.getuid(), limit=4096))
    except FileNotFoundError:
        return None
    if (not isinstance(state, dict) or set(state) != {'stock', 'phase'}
            or state['stock'] not in LG_HOME
            or state['phase'] not in ('pending', 'active', 'stopping', 'stopped')):
        raise ValueError('Invalid recovery journal')
    return state


def read_record(read):
    record = read()
    if not isinstance(record, dict):
        raise ValueError('Invalid defaultApps record')
    return record


def write_and_verify(read, write, record):
    try:
        write(record)
    except TimeoutError:
        if read_record(read) != record:
            raise
        return
    if read_record(read) != record:
        raise ValueError('Settings write could not be verified')


def enable(journal, read, write, *, explicit=False):
    with locked(journal):
        state = read_journal(journal)
        if not explicit or (state is not None and state['phase'] != 'stopped'):
            raise ValueError('Recover the previous attempt and use explicit Enable')
        record = read_record(read)
        stock = record.get('home')
        if stock not in LG_HOME:
            raise ValueError('An explicit stock Home is required')
        atomic(journal, {'stock': stock, 'phase': 'pending'}, os.getuid())
        write_and_verify(read, write, dict(record, home=ROOT_HOME))
        atomic(journal, {'stock': stock, 'phase': 'active'}, os.getuid())


def restore(journal, read, write):
    with locked(journal):
        state = read_journal(journal)
        if state is None:
            raise ValueError('Missing recovery journal')
        stock = state['stock']
        if state['phase'] == 'stopped':
            if read_record(read).get('home') != stock:
                raise ValueError('Home selection changed after Stop')
            return 'restored'
        record = read_record(read)
        home = record.get('home')
        if state['phase'] == 'pending' and home == stock:
            raise ValueError('Previous activation is unresolved')
        if state['phase'] == 'stopping' and home == ROOT_HOME:
            raise ValueError('Previous restore is unresolved')
        if home == ROOT_HOME:
            atomic(journal, {'stock': stock, 'phase': 'stopping'}, os.getuid())
            write_and_verify(read, write, dict(record, home=stock))
        elif home != stock:
            raise ValueError('Home selection changed outside this transaction')
        atomic(journal, {'stock': stock, 'phase': 'stopped'}, os.getuid())
        return 'restored'
