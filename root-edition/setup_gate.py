#!/usr/bin/env python3
"""Developer-only experimental C1 setup; no automatic firmware fallback."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid


def execute(action, alias, bundle=None, identity=None, python='/usr/bin/python3', run=subprocess.run):
    from setup import ssh_options
    from python_binding import launcher_bytes
    from deploy import checked_file, verify_bundle
    if action not in ('install', 'status', 'enable', 'trial', 'restore', 'uninstall'):
        raise ValueError('Unsupported experimental C1 operation')
    launcher_bytes(python)
    options = ssh_options(alias, identity)
    driver = '/var/lib/clean-your-tv-root/deploy.py'
    if action == 'install':
        if bundle is None: raise ValueError('Experimental installation requires its reviewed bundle')
        bundle = Path(bundle).resolve()
        manifest = verify_bundle(bundle, allow_experimental=True)
        release = json.loads(checked_file(bundle, 'release.json'))
        if release.get('home_backend') != 'c1-native-gate' or release.get('experimental') is not True:
            raise ValueError('This entry point only accepts explicit experimental C1 bundles')
        staging = '/tmp/cytv-c1-gate-' + uuid.uuid4().hex
        run(['ssh', *options, 'umask 077; test "$(id -u)" = 0 && mkdir ' + shlex.quote(staging)],
            check=True, stdin=subprocess.DEVNULL)
        with tempfile.TemporaryDirectory(prefix='cytv-c1-bundle-') as folder:
            local = Path(folder)
            for name in (*manifest['files'], 'bundle.json'):
                target = local / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(checked_file(bundle, name))
            run(['scp', '-O', *options[:-1], '-r', *[str(p) for p in sorted(local.iterdir())],
                 alias + ':' + staging + '/'], check=True, stdin=subprocess.DEVNULL)
        driver = staging + '/deploy.py'
        argv = [python, driver, 'install', '--experimental-c1-gate', '--bundle', staging]
    else:
        argv = [python, driver, action, '--experimental-c1-gate']
    command = ('unset PYTHONHOME PYTHONPATH; export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1; exec '
               + shlex.join(argv))
    return run(['ssh', *options, command], check=True, stdin=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('install', 'status', 'enable', 'trial', 'restore', 'uninstall'))
    parser.add_argument('--ssh', required=True, help='Existing pinned OpenSSH alias for a separately authorized test device')
    parser.add_argument('--identity', type=Path)
    parser.add_argument('--python', default='/usr/bin/python3', help='Already available pinned TV Python 3.9+; no provisioning')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--apply', action='store_true', help='Execute the displayed experimental operation')
    args = parser.parse_args()
    from setup import ssh_options
    from python_binding import launcher_bytes
    ssh_options(args.ssh, args.identity); launcher_bytes(args.python)
    if args.command == 'install':
        if args.bundle is None: parser.error('install requires --bundle')
        from deploy import verify_bundle, checked_file
        verify_bundle(args.bundle, allow_experimental=True)
        if json.loads(checked_file(args.bundle, 'release.json')).get('home_backend') != 'c1-native-gate':
            parser.error('install requires an experimental C1 bundle')
    print(json.dumps(dict(operation=args.command, backend='c1-native-gate', experimental=True,
                         hardware_validated=False, automatic_profile_fallback=False,
                         installs_updater=False, home_changed_by_install=False), sort_keys=True), flush=True)
    if args.apply:
        execute(args.command, args.ssh, args.bundle, args.identity, args.python)


if __name__ == '__main__':
    main()
