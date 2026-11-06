"""Private pinned Python binding shared by Root and its update workers."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import sys

SYSTEM = '/usr/bin/python3'
ARCHIVE_SHA256 = '4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea'
MANAGED_ROOT = Path('/var/lib/clean-your-tv-python')
EXPECTED_UID = 0


def _managed(executable):
    return executable == str(MANAGED_ROOT/ARCHIVE_SHA256/'bin/python3.13')


def current_executable():
    """Host test interpreters and environment variables never select TV executables."""
    return sys.executable if _managed(sys.executable) else SYSTEM


def launcher_bytes(executable=None):
    executable = current_executable() if executable is None else executable
    if executable != SYSTEM and not _managed(executable):
        raise ValueError('Unapproved Python executable')
    return ('#!/bin/sh\nunset PYTHONHOME PYTHONPATH\n'
            'export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+shlex.quote(executable)+' "$@"\n').encode()


def _directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != EXPECTED_UID or info.st_mode & 0o022:
        raise ValueError('Unsafe Python directory: '+str(path))


def _read(path, limit=1048576):
    for parent in path.parents:
        _directory(parent)
    try: fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except OSError as exc: raise ValueError('Unsafe Python file: '+str(path)) from exc
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != EXPECTED_UID or info.st_mode & 0o022 or info.st_size > limit):
            raise ValueError('Unsafe Python file: '+str(path))
        raw = stream.read(limit+1)
        if len(raw) > limit: raise ValueError('Oversized Python file')
        return raw


def _runtime_inventory(executable):
    """Read bounded owned inventory as data, without authorizing execution."""
    if not _managed(executable): raise ValueError('Unapproved managed Python')
    slot = Path(executable).parents[1]
    raw = _read(slot/'.cytv-runtime.json', 4*1024*1024)
    inventory = json.loads(raw)
    files = inventory.get('files')
    if (inventory.get('schema') != 1 or inventory.get('archive_sha256') != ARCHIVE_SHA256
            or not isinstance(files, dict) or not files or len(files) > 20000
            or 'bin/python3.13' not in files):
        raise ValueError('Invalid Python runtime inventory')
    for name, digest in files.items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or str(path) != name or '..' in path.parts
                or '\\' in name or '\x00' in name or name == '.cytv-runtime.json'
                or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest)):
            raise ValueError('Unsafe Python inventory entry')
    return raw, inventory


def _runtime(executable, full=True):
    raw, inventory = _runtime_inventory(executable)
    files = inventory['files']
    slot = Path(executable).parents[1]
    # Cheap launch checks still prove the executable and inventory identity.
    selected = files if full else ('bin/python3.13',)
    for name in selected:
        if hashlib.sha256(_read(slot/name, 256*1024*1024)).hexdigest() != files[name]:
            raise ValueError('Python runtime digest mismatch: '+name)
    if not Path(executable).stat().st_mode & 0o111:
        raise ValueError('Python runtime is not executable')
    if full:
        actual = set()
        for parent, dirs, names in os.walk(slot, followlinks=False):
            for directory in dirs: _directory(Path(parent)/directory)
            actual.update(str((Path(parent)/name).relative_to(slot)) for name in names)
        if actual != set(files)|{'.cytv-runtime.json'}:
            raise ValueError('Unexpected Python runtime inventory')
    return {'schema':1, 'executable':executable, 'archive_sha256':ARCHIVE_SHA256,
            'inventory_sha256':hashlib.sha256(raw).hexdigest()}


def _binding(state, full=True):
    state = Path(state)
    launcher, receipt = state/'python-launcher', state/'python-runtime.json'
    present = (os.path.lexists(launcher), os.path.lexists(receipt))
    if present == (False,False): return SYSTEM
    if present != (True,True): raise ValueError('Incomplete Python binding')
    saved = json.loads(_read(receipt))
    executable = saved.get('executable')
    if executable == SYSTEM:
        expected = {'schema':1, 'executable':SYSTEM}
    else:
        expected = _runtime(executable, full)
    if saved != expected or _read(launcher) != launcher_bytes(executable):
        raise ValueError('Python binding drift')
    if stat.S_IMODE(launcher.lstat().st_mode) != 0o700:
        raise ValueError('Unsafe Python launcher mode')
    return executable


def verify_binding(state):
    """Prove all managed bytes at provisioning, activation and recovery gates."""
    return _binding(state)


def command(state):
    """Return the persisted launcher; never silently bypass damaged evidence."""
    executable = _binding(state, full=False)
    return str(Path(state)/'python-launcher') if os.path.lexists(Path(state)/'python-launcher') else executable


def install_launcher(state, write):
    """Persist once; never switch an existing transaction or adopt partial evidence."""
    state = Path(state)
    if any(os.path.lexists(state/name) for name in ('python-launcher','python-runtime.json')):
        return verify_binding(state)
    executable = current_executable()
    if executable == SYSTEM: return SYSTEM  # Preserve legacy system installations.
    evidence = _runtime(executable)
    _directory(state)
    for parent in state.parents: _directory(parent)
    write(state/'python-runtime.json', (json.dumps(evidence,sort_keys=True)+'\n').encode())
    write(state/'python-launcher', launcher_bytes(executable), mode=0o700)
    return executable
