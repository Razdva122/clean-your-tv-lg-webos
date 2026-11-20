"""Journaled private-runtime migration; installed application bytes are read only."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

import provision as p

JOURNAL = 'beta-startup-migration.json'
BACKUP = 'beta-startup-backup'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Transaction:
    """Accept only exact old/new bytes on retry and retain a byte-exact inverse."""
    def __init__(self, root, targets):
        self.root = Path(root)
        self.targets = targets
        for name, (raw, mode) in targets.items():
            path = Path(name)
            if (path.is_absolute() or '..' in path.parts or str(path) != name
                    or not path.parts or path.parts[0] in (BACKUP, JOURNAL)
                    or mode not in (0o600, 0o700)):
                raise ValueError('Invalid private migration member')
        self.identity = digest(p.encoded({name: [digest(raw), mode]
                                         for name, (raw, mode) in targets.items()}))

    def load(self):
        path = self.root/JOURNAL
        if not os.path.lexists(path):
            return None
        value = json.loads(p.secure(path))
        if (value.get('schema') != 1 or value.get('candidate') != self.identity
                or value.get('phase') not in ('prepared', 'writing', 'published', 'complete', 'rolled-back')
                or set(value.get('original', {})) != set(self.targets)):
            raise ValueError('Original startup migration required')
        return value

    def save(self, value, phase):
        temporary = self.root/(JOURNAL+'.root-preview-tmp')
        if os.path.lexists(temporary):
            prefix = p.secure(temporary)
            if not any(p.encoded(dict(value, phase=step)).startswith(prefix)
                       for step in ('prepared', 'writing', 'published', 'complete', 'rolled-back')):
                raise ValueError('Interrupted migration journal changed')
            temporary.unlink()
        value['phase'] = phase
        p.beta_repair_write(self.root/JOURNAL, p.encoded(value))

    def original(self, value, name):
        entry = value['original'][name]
        if entry is None:
            return None
        if (not isinstance(entry, dict) or set(entry) != {'sha256', 'mode'}
                or type(entry['mode']) is not int or not 0 <= entry['mode'] <= 0o777
                or entry['mode'] & 0o022):
            raise ValueError('Invalid original migration member')
        raw = p.secure(self.root/BACKUP/name)
        if digest(raw) != entry['sha256']:
            raise ValueError('Original migration backup changed')
        return raw

    def prepare(self):
        current = self.load()
        if current is not None:
            return current
        backup = self.root/BACKUP
        if os.path.lexists(backup):
            info = backup.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise ValueError('Unsafe migration backup')
        else:
            backup.mkdir(mode=0o700)
        # Before the journal exists the live tree is still the original. An
        # interrupted backup must match it byte for byte before completion.
        originals = {}
        for name in self.targets:
            target = self.root/name
            if os.path.lexists(target):
                raw = p.secure(target)
                mode = stat.S_IMODE(target.stat().st_mode)
                if mode & 0o7022:
                    raise ValueError('Unexpected original private mode')
                copy = backup/name
                copy.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if os.path.lexists(copy) and p.secure(copy) != raw:
                    raise ValueError('Unrecorded migration backup changed')
                p.beta_repair_write(copy, raw, mode)
                originals[name] = {'sha256': digest(raw), 'mode': mode}
            else:
                originals[name] = None
        value = {'schema': 1, 'candidate': self.identity, 'phase': 'prepared', 'original': originals}
        self.save(value, 'prepared')
        return value

    def validate(self, value):
        temporary_files = []
        for name, (raw, mode) in self.targets.items():
            old = self.original(value, name)
            path = self.root/name
            observed = p.secure(path) if os.path.lexists(path) else None
            # A revoked readiness proof is the only third live value.
            revoked = p.encoded({'version': 1, 'mode': 'startup-migration'})
            allowed = (old, raw, revoked) if name == 'recovery-provision.json' else (old, raw)
            temporary = path.with_name(path.name+'.root-preview-tmp')
            if os.path.lexists(temporary):
                prefix = p.secure(temporary)
                if not any(option is not None and option.startswith(prefix) for option in allowed):
                    raise ValueError('Interrupted migration member changed')
                temporary_files.append(temporary)
            if observed not in allowed:
                raise ValueError('Private migration member changed')
            if observed is not None:
                modes = {mode} if observed == raw or name == 'recovery-provision.json' else set()
                if old is not None and observed == old:
                    modes.add(value['original'][name]['mode'])
                if stat.S_IMODE(path.stat().st_mode) not in modes:
                    raise ValueError('Private migration mode changed')
        return temporary_files

    def apply(self, verify, checkpoint=lambda _: None):
        value = self.prepare()
        temporary_files = self.validate(value)
        if value['phase'] == 'complete':
            verify()
            return value
        for temporary in temporary_files:
            temporary.unlink()
        p.beta_repair_write(self.root/'recovery-provision.json',
                            p.encoded({'version': 1, 'mode': 'startup-migration'}))
        self.save(value, 'writing')
        checkpoint('readiness-revoked')
        # Readiness is published last, after every dependent file and proof.
        names = [name for name in self.targets if name != 'recovery-provision.json']
        names.append('recovery-provision.json')
        for name in names:
            raw, mode = self.targets[name]
            target = self.root/name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            p.beta_repair_write(target, raw, mode)
            checkpoint(name)
        self.save(value, 'published')
        verify()
        self.save(value, 'complete')
        return value

    def rollback(self):
        value = self.load()
        if value is None:
            raise ValueError('Original startup migration required')
        temporary_files = self.validate(value)
        for temporary in temporary_files:
            temporary.unlink()
        p.beta_repair_write(self.root/'recovery-provision.json',
                            p.encoded({'version': 1, 'mode': 'startup-migration'}))
        for name in [n for n in self.targets if n != 'recovery-provision.json'] + ['recovery-provision.json']:
            raw = self.original(value, name)
            path = self.root/name
            if raw is None:
                if os.path.lexists(path):
                    path.unlink()
            else:
                p.beta_repair_write(path, raw, value['original'][name]['mode'])
        self.save(value, 'rolled-back')
        return value


def candidate_targets(bundle, original, *, metadata=None):
    import deploy
    from updater.package import archive, members
    manifest = deploy.verify_bundle(bundle, allow_experimental=True)
    release = json.loads(deploy.checked_file(bundle, 'release.json'))
    if (release.get('runtime_variant') != 'node012-beta'
            or release.get('routing') != 'compositor-keyfilter-v1'):
        raise ValueError('Root Beta compositor migration payload required')
    helper = Path(bundle)/'runtime/c1-keyfilter-guard'
    # Only this verified bundled executable can report candidate capabilities.
    helper.chmod(0o700)
    process = subprocess.run([str(helper), '--capabilities'], capture_output=True, timeout=5, check=True)
    if len(process.stdout) > 4096:
        raise ValueError('Oversized native capability reply')
    features = json.loads(process.stdout)
    if (features.get('returnValue') is not True or features.get('protocol') != 1
            or features.get('resumable_guard') is not True or features.get('boot_retirement') is not True):
        raise ValueError('Resumable native migration payload required')
    # Read the package as authenticated data only. It is never submitted to SAM.
    package = archive(members(deploy.checked_file(bundle, manifest['package']))['data.tar.gz'])
    if {name: digest(raw) for name, raw in package.items()} != release['files']:
        raise ValueError('Migration package inventory changed')
    names = list(deploy.SUPPORT_FILES) + ['runtime/'+name for name in deploy.RUNTIME_FILES]
    names += ['runtime/c1_gate.py', 'runtime/c1_keyfilter.py', 'runtime/c1-home-filter.js',
              'runtime/c1-keyfilter-guard']
    targets = {name: (deploy.checked_file(bundle, name),
                      0o700 if name == 'runtime/c1-keyfilter-guard' else 0o600) for name in names}
    # Keep the installed package identity and its UI/preferences intact.
    metadata = p.STATE if metadata is None else Path(metadata)
    retained_release = json.loads(p.secure(metadata/'release.json'))
    retained_release['native_sha256'] = release['native_sha256']
    targets['release.json'] = (p.encoded(retained_release), 0o600)
    backend = json.loads(p.secure(metadata/'home-backend.json'))
    backend['native_sha256'] = release['native_sha256']
    targets['home-backend.json'] = (p.encoded(backend), 0o600)
    retained_bundle = json.loads(p.secure(metadata/'bundle.json'))
    for name, (raw, _) in targets.items():
        retained_bundle['files'][name] = digest(raw)
    targets['bundle.json'] = (p.encoded(retained_bundle), 0o600)
    proof = dict(original, files=dict(original['files']))
    for name, (raw, _) in targets.items():
        proof['files'][str(p.STATE/name)] = digest(raw)
    targets['recovery-provision.pending.json'] = (p.encoded(proof), 0o600)
    targets['recovery-provision.json'] = (p.encoded(proof), 0o600)
    return targets


def verify_status():
    reply = p.rpc('status')
    runtime = reply.get('result')
    result = runtime.get('result') if isinstance(runtime, dict) else None
    recovery = result.get('recovery') if isinstance(result, dict) else None
    if (reply.get('root') is not True or not isinstance(runtime, dict)
            or runtime.get('returnValue') is not True or not isinstance(recovery, dict)
            or recovery.get('integrity_verified') is not True):
        raise ValueError('Migrated Root Beta status not verified')


def require_quiescent(tx, value):
    from runtime import c1_keyfilter as gate
    # The descriptor and helper may belong to different authenticated halves
    # after interruption. Validate both as old/new data before executing status.
    tx.validate(value)
    intent = gate.read_intent(tx.root, 0)
    if intent.get('enabled') is not False or intent.get('phase') != 'disabled':
        raise ValueError('Turn Change Home off before runtime migration')
    helper = tx.root/'runtime/c1-keyfilter-guard'
    process = subprocess.run([str(helper), '--status'], check=True, capture_output=True, timeout=5)
    if len(process.stdout) > 4096:
        raise ValueError('Oversized native status')
    status = gate.validate_native(json.loads(process.stdout))
    if not status['stock_verified'] or status['healthy'] or status['guardian_pid']:
        raise ValueError('Stock native routing required for runtime migration')
    chain = gate.read_chain()
    if gate.reconcile(chain, tx.root, False) != chain:
        raise ValueError('Restore retained compositor filter before runtime migration')


def ensure_stock_destination():
    """Materialize only an absent Home override, with one durable submission."""
    path = p.STATE/'beta-startup-home-setting.json'
    reply = p.rpc('home-read')
    defaults = reply.get('settings', {}).get('defaultApps')
    if isinstance(defaults, str):
        defaults = json.loads(defaults)
    if not isinstance(defaults, dict):
        raise ValueError('Home destination readback required')
    receipt = json.loads(p.secure(path)) if os.path.lexists(path) else None
    if receipt is not None:
        if (not isinstance(receipt, dict) or set(receipt) != {'schema', 'original'}
                or receipt['schema'] != 1 or not isinstance(receipt['original'], dict)
                or 'home' in receipt['original']):
            raise ValueError('Startup Home initialization evidence changed')
        if defaults != dict(receipt['original'], home='com.webos.app.home'):
            raise ValueError('Submitted LG Home selection remains unverified; keep migration records')
        return
    if defaults.get('home') in ('com.webos.app.home', 'com.webos.app.fullhome'):
        return
    if 'home' in defaults:
        raise ValueError('Preserve the existing custom Home destination')
    p.beta_repair_write(path, p.encoded({'schema': 1, 'original': defaults}))
    try:
        p.rpc('home-stock')
    except p.RecoveryRPCError:
        pass  # A lost acknowledgement is resolved only by readback.
    reply = p.rpc('home-read')
    observed = reply.get('settings', {}).get('defaultApps')
    if isinstance(observed, str):
        observed = json.loads(observed)
    if observed != dict(defaults, home='com.webos.app.home'):
        raise ValueError('Submitted LG Home selection remains unverified; keep migration records')


def unstarted_removal(owner, lease, selection):
    """Admit only the selected removal whose original component files are intact."""
    from installation import JOURNALS, read_journal
    if (not isinstance(selection, tuple) or len(selection) != 2
            or any(not isinstance(value, str) or len(value) != 32
                   or any(c not in '0123456789abcdef' for c in value) for value in selection)):
        raise ValueError('Original removal selection required')
    operation, intent = selection
    if (lease['owner'], lease['journal']) != ('clean-removal', 'product-'+operation+'.json'):
        raise ValueError('Original removal reservation changed')
    record = owner.store.read('clean-removal-'+operation)
    if not isinstance(record, dict):
        raise ValueError('Original removal record required')
    original = record.get('original', {})
    previous = original.get('lease')
    if (record.get('schema') != 1 or record.get('protocol') != 'clean-removal-v1'
            or record.get('operation') != operation or record.get('removal') != intent
            or record.get('lease') != lease['id'] or record.get('stage') != 'requested'
            or record.get('done') != [] or record.get('packages') != {}
            or any(key in record for key in ('routes', 'archives', 'runtime_cleanup', 'fenced_components'))
            or not isinstance(previous, dict) or previous.get('terminal') is not True
            or (previous.get('owner'), previous.get('journal')) != ('deploy', 'deploy.json')
            or original.get('components') != {name: read_journal(path) for name, (path, _, _) in JOURNALS.items()}):
        raise ValueError('Removal has effects or its original evidence changed; keep records')
    return record


def migrate(bundle, *, rollback=False, keep_removal=None):
    import deploy
    from installation import Ownership
    from package_identity import bootstrap_inventory
    from runtime import c1_keyfilter
    deploy.require_device()
    deploy.require_node()
    bundle = Path(bundle)
    owner = Ownership()
    with owner._lock(create=True):
        lease = owner.status()
        preserved_removal = None
        resuming = lease and (lease['owner'], lease['journal']) == ('beta-startup', JOURNAL)
        if not resuming and lease and lease['owner'] == 'clean-removal':
            preserved_removal = unstarted_removal(owner, lease, keep_removal)
        elif not resuming and (lease is None or lease['terminal'] is not True
                or (lease['owner'], lease['journal']) != ('deploy', 'deploy.json')):
            raise ValueError('Resolve original device operation before startup migration')
        with ExitStack() as stack:
            fd = os.open(p.STATE/'provision.lock', os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
            stack.callback(os.close, fd)
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            stack.enter_context(c1_keyfilter.operation(p.STATE, 0))
            prior = json.loads(p.secure(p.STATE/JOURNAL)) if os.path.lexists(p.STATE/JOURNAL) else None
            metadata = p.STATE if prior is None else p.STATE/BACKUP
            if prior is None:
                bootstrap_inventory(p.STATE)
            deploy.verify_payload(json.loads(p.secure(metadata/'release.json')))
            if prior is None:
                if json.loads(p.secure(p.STATE/'deploy.json')).get('stage') != 'installed-recovery-only':
                    raise ValueError('Completed retained Root Beta recovery required')
                release = json.loads(p.secure(p.STATE/'release.json'))
                if (release.get('runtime_variant'), release.get('home_backend'), release.get('routing')) != (
                        'node012-beta', 'c1-native-gate', 'compositor-keyfilter-v1'):
                    raise ValueError('Retained Root Beta compositor required')
                original = json.loads(p.secure(p.STATE/'recovery-provision.json'))
                if p.manifest() != original:
                    raise ValueError('Retained recovery proof changed')
                p.prepare_stock_home()
                intent = c1_keyfilter.read_intent(p.STATE, 0)
                if intent.get('enabled') or intent.get('phase') in ('active', 'trial', 'starting', 'recovering'):
                    raise ValueError('Turn Change Home off before runtime migration')
                # Preserve the exact original proof for retry target construction.
                original_path = p.STATE/'beta-startup-original-proof.json'
                if os.path.lexists(original_path) and p.secure(original_path) != p.encoded(original):
                    raise ValueError('Unrecorded startup migration proof changed')
                p.beta_repair_write(original_path, p.encoded(original))
            else:
                original = json.loads(p.secure(p.STATE/'beta-startup-original-proof.json'))
            tx = Transaction(p.STATE, candidate_targets(bundle, original, metadata=metadata))
            value = tx.prepare()
            if rollback or value['phase'] != 'complete':
                require_quiescent(tx, value)
                if not rollback:
                    ensure_stock_destination()
            if preserved_removal is not None:
                owner.store.write('beta-startup-preserved-'+preserved_removal['operation'], preserved_removal)
            if 'lease' in value:
                if ((resuming and value['lease'] != lease['id'])
                        or (not resuming and value.get('predecessor') != lease)):
                    raise ValueError('Startup migration reservation changed')
            else:
                value.update(lease=digest((tx.identity+lease['id']).encode())[:32], predecessor=lease)
                tx.save(value, value['phase'])
            current = dict(lease, id=value['lease'], owner='beta-startup', journal=JOURNAL,
                           stage='migrating', terminal=False)
            owner.store.write('operation', current)
            if rollback:
                value = tx.rollback()
            else:
                value = tx.apply(verify_status)
            current.update(stage=value['phase'], terminal=True)
            owner.store.write('operation', current)
    return {'returnValue': True, 'phase': value['phase'], 'application_preserved': True,
            'preferences_preserved': True, 'home_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle')
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--preserve-removal', nargs=2)
    args = parser.parse_args()
    print(json.dumps(migrate(args.bundle, rollback=args.rollback,
                             keep_removal=tuple(args.preserve_removal) if args.preserve_removal else None)))
