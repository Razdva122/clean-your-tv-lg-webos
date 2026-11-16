"""Verified engine slots; a trial never replaces the last confirmed engine."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import uuid
from .support.package import archive, safe_bytes
from .support.store import Store


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic(path, raw):
    path = Path(path)
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError('Indirect engine destination')
    parent = Store(path.parent, uid=os.geteuid())
    temporary = path.with_name('.engine-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = parent._directory()
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if temporary.exists(): temporary.unlink()


class Slots:
    def __init__(self, store, bootstrap_code, verify):
        self.store = store
        self.root = Path(store.root)
        self.bootstrap_code = Path(bootstrap_code)
        self.verify = verify

    def _manifest(self, raw, catalog):
        engine = catalog['engine']
        if len(raw) != engine['size'] or digest(raw) != engine['sha256']:
            raise ValueError('Engine archive hash mismatch')
        files = archive(raw)
        manifest = json.loads(files.pop('engine.json', b'{}'))
        if (set(manifest) != {'schema', 'version', 'files'} or manifest['schema'] != 1
                or manifest['version'] != engine['version'] or not files
                or manifest['files'] != {name: digest(data) for name, data in files.items()}
                or 'engine-entry.py' not in files):
            raise ValueError('Engine inventory mismatch')
        for name in files:
            path = PurePosixPath(name)
            if path.is_absolute() or str(path) != name or '..' in path.parts or '\\' in name:
                raise ValueError('Unsafe engine inventory')
        return manifest, files

    def verify_slot(self, record):
        if not isinstance(record, dict) or set(record) != {'slot', 'proof'} or record['slot'] not in ('a', 'b'):
            raise ValueError('Invalid engine slot record')
        catalog = self.verify(record['proof'])
        slot = self.root / 'slots' / record['slot']
        Store(slot, uid=self.store.uid)
        raw = safe_bytes(slot / 'engine.tar.gz', limit=64*1024*1024, uid=self.store.uid)
        manifest, files = self._manifest(raw, catalog)
        observed = set()
        for directory, directories, names in os.walk(slot, followlinks=False):
            for name in directories:
                path = Path(directory) / name
                info = path.lstat()
                if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.store.uid or info.st_mode & 0o022:
                    raise ValueError('Unsafe engine directory')
            for name in names:
                path = Path(directory) / name
                relative = path.relative_to(slot).as_posix()
                if relative == 'engine.tar.gz': continue
                observed.add(relative)
                if relative not in files or digest(safe_bytes(path, limit=32*1024*1024, uid=self.store.uid)) != manifest['files'][relative]:
                    raise ValueError('Engine code changed')
        if observed != set(files): raise ValueError('Engine code missing')
        return slot

    def active(self):
        active = self.store.read('active')
        return self.verify_slot(active) if active else self.bootstrap_code

    def stage(self, proof, raw):
        catalog = self.verify(proof)
        _, files = self._manifest(raw, catalog)
        active = self.store.read('active')
        name = 'b' if active and active['slot'] == 'a' else 'a'
        slots = self.root / 'slots'; Store(slots, uid=self.store.uid)
        target = slots / name
        record = {'slot': name, 'proof': proof}
        inventory = {key: digest(value) for key, value in files.items()}
        inventory['engine.tar.gz'] = digest(raw)
        retained = self.store.read('retained-' + name)
        staging = self.store.read('staging-' + name)
        if staging and staging.get('phase') != 'complete':
            if staging.get('candidate') != record:
                # The common lease admits a new offer only after the old one
                # closes. Keep its authenticated hashes through retirement.
                partial = staging['phase'] == 'staging'
                previous = staging['inventory'] if partial else staging['previous']
                staging = dict(candidate=record, inventory=inventory, previous=previous,
                               temporary=partial or staging.get('temporary', False), phase='retiring')
                self.store.write('staging-' + name, staging)
        else:
            previous = {}
            if target.exists():
                if not retained: raise ValueError('Unowned engine slot')
                self.verify_slot(retained)
                old = safe_bytes(target/'engine.tar.gz', limit=64*1024*1024, uid=self.store.uid)
                _, old_files = self._manifest(old, self.verify(retained['proof']))
                previous = {key: digest(value) for key, value in old_files.items()}
                previous['engine.tar.gz'] = digest(old)
            staging = dict(candidate=record, inventory=inventory, previous=previous, phase='retiring')
            self.store.write('staging-' + name, staging)
        if staging['phase'] == 'retiring':
            # Retirement may have stopped after any unlink. Authenticate every
            # remaining byte against the inventory captured before the first
            # unlink, then resume deletion. Never adopt a foreign partial tree.
            if target.exists():
                for directory, directories, names in os.walk(target, followlinks=False):
                    for entry in directories:
                        Store(Path(directory)/entry, uid=self.store.uid)
                    for entry in names:
                        path = Path(directory)/entry
                        key = path.relative_to(target).as_posix()
                        content = safe_bytes(path, limit=64*1024*1024, uid=self.store.uid)
                        if staging.get('temporary') and re.fullmatch(r'\.engine-[a-f0-9]{32}', entry):
                            continue
                        if staging['previous'].get(key) != digest(content):
                            raise ValueError('Retiring engine changed')
                shutil.rmtree(target)
                directory = os.open(slots, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try: os.fsync(directory)
                finally: os.close(directory)
            staging = dict(staging, phase='staging')
            self.store.write('staging-' + name, staging)
        Store(target, uid=self.store.uid)
        expected = set(files) | {'engine.tar.gz'}
        for directory, dirs, names in os.walk(target, followlinks=False):
            for entry in dirs:
                if (Path(directory)/entry).is_symlink(): raise ValueError('Indirect partial engine')
            for entry in names:
                path = Path(directory)/entry
                if re.fullmatch(r'\.engine-[a-f0-9]{32}', entry):
                    safe_bytes(path, limit=32*1024*1024, uid=self.store.uid)
                    path.unlink()  # Private atomic-write temporary after power loss.
                elif path.relative_to(target).as_posix() not in expected: raise ValueError('Foreign partial engine')
        for relative, value in files.items():
            path = target / relative
            for parent in reversed(path.parent.parents):
                if parent == target or target in parent.parents: Store(parent, uid=self.store.uid)
            Store(path.parent, uid=self.store.uid)
            atomic(path, value)
        atomic(target/'engine.tar.gz', raw)
        record = {'slot': name, 'proof': proof}
        self.verify_slot(record)
        self.store.write('retained-' + name, record)
        self.store.write('staging-' + name, dict(staging, phase='complete'))
        return target

    def begin(self, operation, slot):
        if not re.fullmatch('[a-f0-9]{32}', operation): raise ValueError('Invalid engine operation')
        record = self.store.read('retained-' + Path(slot).name)
        if self.verify_slot(record) != Path(slot): raise ValueError('Engine stage mismatch')
        previous = self.store.read('active')
        self.store.write('trial', {'operation': operation, 'candidate': record, 'previous': previous})

    def confirm(self, operation):
        trial = self.store.read('trial')
        if not trial or trial.get('operation') != operation: raise ValueError('Engine trial mismatch')
        self.verify_slot(trial['candidate'])
        self.store.write('active', trial['candidate'])
        self.store.write('trial', dict(trial, confirmed=True))

    def cancel(self, operation):
        trial = self.store.read('trial')
        if not trial or trial.get('operation') != operation: raise ValueError('Engine trial mismatch')
        active = self.store.read('active')
        if active not in (trial['candidate'], trial['previous']):
            raise ValueError('Engine activation changed')
        if trial['previous']: self.verify_slot(trial['previous'])
        # Caller holds the common owner and proves no product handoff occurred.
        # Also restores a crash between active-pointer and confirmation writes.
        if trial['previous']:
            self.store.write('active', trial['previous'])
        elif active:
            directory = self.store._directory()
            try:
                os.unlink('active.json', dir_fd=directory); os.fsync(directory)
            finally: os.close(directory)
        self.store.write('trial', dict(trial, cancelled=True))
