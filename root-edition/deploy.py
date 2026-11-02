#!/usr/bin/env python3
"""Fixed Root candidate device driver. Invoke only through an explicit SSH target."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

from observed_install import install as observed_install, OutcomeUnknown
from python_binding import command as python_command, install_launcher

APP = 'com.cleanyourtv.root.preview'
STATE = Path('/var/lib/clean-your-tv-root')
INSTALLED = Path('/media/developer/apps')
RUNTIME_FILES = ('bounded_profile_trial.py', 'cli.py', 'update_guard.py', 'device_adapter.py', 'guardian_device.py',
                 'helper_bridge.py', 'profile_guardian.py', 'profile_plan.py', 'profile_recovery.py', 'provision.py',
                 'staged_publication.py', 'transport.py', 'emergency_gesture.py', 'emergency_reader.py',
                 'emergency_watchdog.py', 'emergency_trial.py', 'persistent_lifecycle.py',
                 'boot_gate.py', 'shutdown_state.py', 'persistent_health.py', 'persistent_lease.py', 'persistent_store.py', 'persistent_recovery.py', 'intent_runtime.py')
SUPPORT_FILES = ('installation.py', 'updater/store.py', 'updater/package.py', 'setup.py', 'deploy.py', 'provision.py', 'observed_install.py', 'installer_status.py', 'personalize.py', 'system_permissions.py', 'activity.py', 'startup_hook.py','package_data.py','package_identity.py','startup_guard.py', 'python_binding.py', 'python_boot.js')


def require_device():
    if os.geteuid() != 0:
        raise PermissionError('Root SSH account required')
    if not Path('/usr/bin/luna-send').is_file() or not Path('/media/developer/apps').is_dir():
        raise PermissionError('Device actions require a webOS TV')


def require_node():
    try:
        result = subprocess.run(['/usr/bin/node', '-e',
            'process.exit(Number(process.versions.node.split(".")[0]) >= 8 ? 0 : 1)'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode == 0:
            return
    except (OSError, subprocess.TimeoutExpired):
        pass
    raise RuntimeError('Root requires TV Node.js 8+')


def checked_file(root, name):
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or '..' in path.parts or '\\' in name:
        raise ValueError('Unsafe bundle path')
    target = root / name
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError('Indirect bundle file')
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('Not a regular bundle file')
    return target.read_bytes()


def verify_bundle(bundle):
    bundle = Path(bundle).resolve()
    manifest = json.loads(checked_file(bundle, 'bundle.json'))
    release = json.loads(checked_file(bundle, 'release.json'))
    import re
    version = release.get('version')
    if not isinstance(version,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',version):
        raise ValueError('Invalid Root release version')
    package = APP + '_' + version + '_all.ipk'
    expected = set(SUPPORT_FILES) | {'runtime/' + n for n in RUNTIME_FILES} | {package, 'release.json', 'SHA256SUMS'}
    if manifest.get('package') != package or set(manifest.get('files', {})) != expected:
        raise ValueError('Unexpected bundle inventory')
    for name, digest in manifest['files'].items():
        if hashlib.sha256(checked_file(bundle, name)).hexdigest() != digest:
            raise ValueError('Bundle integrity mismatch: ' + name)
    if release.get('application_id') != APP:
        raise ValueError('Wrong candidate release')
    return manifest


def write_stage(stage, **extra):
    path = STATE / 'deploy.json'
    temporary = STATE / 'deploy.next'
    data = {'version': 1, 'app': APP, 'stage': stage, **extra}
    with temporary.open('x') as stream:
        os.chmod(temporary, 0o600)
        json.dump(data, stream, sort_keys=True)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(STATE, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def installed_paths():
    return [INSTALLED / 'usr/palm' / kind / name for kind, name in (
        ('applications', APP), ('packages', APP), ('services', APP + '.service'))]


def verify_payload(release):
    prefixes = ('usr/palm/applications/' + APP + '/', 'usr/palm/services/' + APP + '.service/')
    package_info = 'usr/palm/packages/' + APP + '/packageinfo.json'
    files = release.get('files', {})
    if not files:
        raise ValueError('Empty installed payload manifest')
    for name, digest in files.items():
        if not (name.startswith(prefixes) or name == package_info):
            raise ValueError('Unexpected installed payload path')
        from package_data import read_verified
        if hashlib.sha256(read_verified(INSTALLED/name,sha256=digest,limit=32*1024*1024,installed=INSTALLED)).hexdigest() != digest:
            raise ValueError('Installed payload hash mismatch: ' + name)


def command(args):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=True,
                            timeout=700 if args[-1] in ('restore', 'rollback') else 100)
    reply = json.loads(result.stdout)
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        raise ValueError('Device operation failed: ' + str(reply))
    return reply


def runtime(mode, run=command):
    return run([python_command(STATE), str(STATE / 'runtime/cli.py'), mode])


def restore(run=command):
    reply = runtime('restore', run)
    if reply.get('result') not in ('absent', 'restored'):
        raise ValueError('Recovery incomplete; state retained: ' + str(reply))
    return reply


def migration_source():
    import personalize
    profile=INSTALLED/'usr/palm/services/com.cleanyourtv.updater.service/state/profile.json'
    if os.path.lexists(profile):
        files=personalize.from_profile(profile)
        source='validated updater profile; browser storage excluded'
    else:
        home=INSTALLED / 'usr/palm/applications/com.gathin.tvhome'
        if not os.path.lexists(home):
            raise ValueError('Home migration source is unavailable; omit --migrate-packaged-home or prepare ordinary Home first')
        files=personalize.prepare(home)
        source='packaged com.gathin.tvhome only; browser storage excluded'
    return files,source


def migrate_packaged_home(prepared=None):
    files,source=migration_source() if prepared is None else prepared
    destination = INSTALLED / ('usr/palm/applications/' + APP)
    write_stage('personalization-starting')
    for name, data in files.items():
        target = destination / name
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError('Indirect candidate preference path')
        target.parent.mkdir(exist_ok=True)
        temporary = target.with_name(target.name + '.root-preview-tmp')
        with temporary.open('xb') as stream:
            os.chmod(temporary, 0o644)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)
    record = {'source': source,
              'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    path = STATE / 'personalization.json'
    with path.open('x') as stream:
        os.chmod(path, 0o600)
        json.dump(record, stream, sort_keys=True)
        stream.flush(); os.fsync(stream.fileno())
    write_stage('personalization-complete', manifest='personalization.json')


def write_binding(path, data, mode=0o600):
    temporary = path.with_name(path.name+'.binding-tmp')
    fd = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),mode)
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.lexists(temporary): temporary.unlink()


def install(bundle, run=command, observe=observed_install, migrate=False):
    if sys.version_info < (3, 9):
        raise RuntimeError('Root requires TV Python 3.9+')
    if STATE.exists() or STATE.is_symlink() or any(p.exists() or p.is_symlink() for p in installed_paths()):
        raise FileExistsError('Candidate or state already exists; inspect and recover, never retry blindly')
    from provision import require_home_interfaces
    require_home_interfaces()
    manifest = verify_bundle(bundle)
    # Validate and retain the exact migration bytes before any install mutation.
    prepared = migration_source() if migrate else None
    STATE.mkdir(mode=0o700, parents=False)
    write_stage('prepared', package=manifest['package'])
    (STATE / 'runtime').mkdir(mode=0o700)
    for name in SUPPORT_FILES + ('release.json', 'bundle.json'):
        target = STATE / name
        target.parent.mkdir(mode=0o700, exist_ok=True)
        target.write_bytes(checked_file(Path(bundle).resolve(), name)); target.chmod(0o600)
    for name in RUNTIME_FILES:
        target = STATE / 'runtime' / name
        target.write_bytes(checked_file(Path(bundle).resolve(), 'runtime/' + name)); target.chmod(0o600)
    install_launcher(STATE, write_binding)
    package = str(Path(bundle).resolve() / manifest['package'])
    terminal = observe(APP, package, timeout=120,
            on_ready=lambda: write_stage('install-submitting', package=package),
            on_accepted=lambda event: write_stage('install-accepted', package=package, evidence=event))
    if terminal is not None:
        write_binding(STATE/'install-terminal.json',json.dumps(terminal,sort_keys=True).encode())
    write_stage('install-observed')
    release = json.loads((Path(bundle) / 'release.json').read_text())
    verify_payload(release)
    write_stage('payload-verified')
    if migrate:
        migrate_packaged_home(prepared)
    for step in ('apply', 'refresh', 'finalize'):
        write_stage('provision-' + step + '-starting')
        run([python_command(STATE), str(STATE / 'provision.py'), step])
        write_stage('provision-' + step + '-complete')
    write_stage('installed-recovery-only')
    return {'returnValue': True, 'installed': APP, 'home_changed': False}


def verify_removed(evidence):
    """webOS may retain an empty package directory after terminal removal."""
    paths = installed_paths()
    package = paths[1]
    if package.exists() or package.is_symlink():
        event = evidence.get('event', {})
        details = event.get('details', {})
        valid = (evidence.get('completed') is True and event.get('id') == APP
                 and event.get('statusValue') == 31 and event.get('returnValue') is not False
                 and 'errorCode' not in event and isinstance(details, dict)
                 and details.get('packageId') == APP and details.get('state') == 'removed'
                 and 'errorCode' not in details)
        if (not valid or any(p.is_symlink() for p in (package, *package.parents))
                or not package.is_dir() or any(p.exists() or p.is_symlink() for p in (paths[0], paths[2]))):
            raise OutcomeUnknown('Unverified removal remainder; state retained')
        try:
            package.rmdir()  # Empty only: never recursively remove leftover contents.
        except OSError as exc:
            raise OutcomeUnknown('Nonempty or changed package remainder; state retained') from exc
    if any(p.exists() or p.is_symlink() for p in paths):
        raise OutcomeUnknown('Removal terminal received but candidate files remain; state retained')


def uninstall(run=command):
    journal = {}
    if (STATE / 'deploy.json').exists():
        journal = json.loads(checked_file(STATE, 'deploy.json'))
        previous = journal.get('stage')
        if previous in ('remove-submitting', 'remove-observed', 'uninstalled-state-retained'):
            raise OutcomeUnknown('Removal already submitted or completed; inspect retained evidence, never resubmit blindly')
    # apply writes its snapshot before changing any LS2 registrations. Only an
    # exact pre-apply journal can authorize removal without that snapshot.
    early = journal.get('app') == APP and (journal.get('stage') in (
        'payload-verified', 'personalization-starting', 'personalization-complete', 'provision-apply-starting')
        or (journal.get('stage') in ('uninstall-restored', 'uninstall-refresh-complete')
            and journal.get('provisioning_not_started') is True))
    snapshot = STATE/'ls2-provision-snapshot.json'
    if early and (snapshot.is_symlink() or (not os.path.lexists(snapshot) and any(
            os.path.lexists(STATE/name) for name in ('recovery-provision.pending.json','recovery-provision.json')))):
        raise ValueError('Conflicting provisioning evidence; retain state for recovery')
    if early and not os.path.lexists(snapshot):
        import fcntl
        fd = os.open(STATE/'provision.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            if os.path.lexists(snapshot):
                raise ValueError('Provisioning changed; inspect retained state before retrying cleanup')
            return _remove_root(run, {'provisioning_not_started':True})
        finally:
            os.close(fd)
    return _remove_root(run, {})


def _remove_root(run, proof):
    restore(run)
    if proof and any(os.path.lexists(STATE/name) for name in (
            'ls2-provision-snapshot.json','recovery-provision.pending.json','recovery-provision.json')):
        raise ValueError('Conflicting provisioning evidence; retain state for recovery')
    write_stage('uninstall-restored', **proof)
    # No overrides were installed on the pre-provision path. Package removal
    # handles its original registrations; neither rollback nor a scan is needed.
    for step in (() if proof else ('rollback', 'refresh')):
        run([python_command(STATE), str(STATE / 'provision.py'), step])
        write_stage('uninstall-' + step + '-complete', **proof)
    # Removal needs a terminal subscribed result, never just request acceptance.
    from observed_install import remove
    write_stage('remove-submitting', **proof)
    evidence = remove(APP, timeout=120)
    write_stage('remove-observed', evidence=evidence, **proof)
    verify_removed(evidence)
    write_stage('uninstalled-state-retained', evidence=evidence, **proof)
    return {'returnValue': True, 'removed': APP, 'state_retained': str(STATE)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('install', 'inspect', 'status', 'trial', 'emergency-trial', 'intent-trial', 'enable', 'confirm', 'restore', 'uninstall'))
    parser.add_argument('--transaction')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--migrate-packaged-home', action='store_true', help='Copy fixed installed Home packaged preferences; excludes browser storage')
    args = parser.parse_args()
    if args.migrate_packaged_home and args.command != 'install':
        parser.error('migration is only available with install')
    require_device()
    from installation import classify, device_snapshot, device_operation
    from contextlib import nullcontext
    if args.command == 'inspect':
        print(json.dumps({'returnValue':True, 'installation':classify(device_snapshot())}), flush=True)
        return
    # Read-only status remains available during every retained operation.
    # Restore is explicit recovery and does not replace any package.
    if args.command == 'install':
        require_node()
        if args.bundle is None: parser.error('install requires --bundle')
        verify_bundle(args.bundle)
    guard = (device_operation('deploy', recovery=args.command == 'uninstall')
             if args.command in ('install','uninstall') else nullcontext())
    with guard:
        if args.command == 'install':
            result = install(args.bundle, migrate=args.migrate_packaged_home)
        elif args.command == 'uninstall': result = uninstall()
        elif args.command == 'restore': result = restore()
        elif args.command == 'confirm':
            import re
            if not args.transaction or not re.fullmatch(r'[0-9a-f-]{36}',args.transaction): parser.error('confirm requires --transaction')
            result = command([python_command(STATE),str(STATE/'runtime/cli.py'),'confirm',args.transaction])
        else: result = runtime(args.command)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'returnValue': False, 'error': str(exc), 'instruction': 'Stop; retain state and inspect. Do not repeat installation.'}), flush=True)
        sys.exit(1)
