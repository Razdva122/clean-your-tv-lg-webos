"""Exercise installer ordering/failures without downloading tools or touching a TV."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InstallTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Requires a POSIX terminal')
    def test_shell_errors_are_red_on_terminal_and_plain_when_redirected(self):
        import pty
        import select
        env = dict(os.environ, TERM='xterm')
        env.pop('NO_COLOR', None)
        command = ['bash', str(ROOT / 'install.sh'), 'extra', 'arguments']
        plain = subprocess.run(command, capture_output=True, env=env)
        self.assertNotEqual(plain.returncode, 0)
        self.assertNotIn(b'\x1b', plain.stderr)
        master, slave = pty.openpty()
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=slave, env=env)
            # The bash stderr filter can flush just after its parent exits.
            # Keep the PTY slave open until that final line has arrived.
            self.assertTrue(select.select([master], [], [], 5)[0])
            output = os.read(master, 4096)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'\x1b[31m', output)
            self.assertIn(b'Usage:', output)
        finally:
            os.close(master)
            if slave is not None:
                os.close(slave)

    def run_installer(self, fault='', existing=False, host='192.0.2.10',
                      external_zig=False, path_zig=False, termux=False, zig_version='0.14.1',
                      tv_node_output=None, tv_node_exit=0):
        with tempfile.TemporaryDirectory(prefix='tv install ') as tmp:
            root = Path(tmp)
            installer = ROOT / 'install.sh'
            self.assertTrue(installer.exists(), 'one-command installer is missing')
            shutil.copy(installer, root)
            (root / 'scripts').mkdir()
            (root / 'launcher').mkdir()
            for name, appid, version in [('launcher', 'com.gathin.tvhome', '1.1.0'),
                                         ('native/app', 'com.local.nativehome', '0.6.13')]:
                (root / name).mkdir(parents=True, exist_ok=True)
                (root / name / 'appinfo.json').write_text(json.dumps({'id': appid, 'version': version}))
            # External CLI calls are recorded; failure must stop subsequent TV mutations.
            bindir = root / 'bin'; bindir.mkdir()
            # Keep an installed host Zig out of the simulated tool search.
            for tool in ('bash', 'dirname', 'mkdir', 'ln'):
                (bindir / tool).symlink_to(shutil.which(tool))
            cli = bindir / 'cli'
            cli.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
name=pathlib.Path(sys.argv[0]).name
with open('calls.jsonl','a') as f: f.write(json.dumps([name]+sys.argv[1:])+'\\n')
if name=='ares-setup-device' and '--add' in sys.argv:
    print('other-tv saved passphrase: SECRET-EXISTING-PASSPHRASE')
if name=='ares-setup-device' and '--listfull' in sys.argv:
    print(json.dumps([{'name':os.environ['DEVICE'],'deviceinfo':{'ip':os.environ['PROFILE_HOST'],'port':'9922','user':'prisoner'}}] if os.environ['EXISTING']=='1' else []))
if name=='ares-novacom' and '--getkey' in sys.argv and os.environ['FAULT']=='pair': sys.exit(1)
if name=='ares-novacom' and '--run' in sys.argv:
    if 'process.versions.node' in sys.argv[-1]:
        sys.stdout.write(os.environ['TV_NODE_OUTPUT'])
        sys.exit(int(os.environ['TV_NODE_EXIT']))
    else: print('no confirmation' if os.environ['FAULT']=='ssh' else 'CYTV_SSH_OK')
if name=='ares-install' and os.environ['FAULT']=='install': sys.exit(1)
'''); cli.chmod(0o755)
            for name in ['ares-setup-device', 'ares-novacom', 'ares-install', 'ares-launch', 'ares-package']:
                (bindir / name).symlink_to(cli)
            (bindir / 'node').write_text('#!/bin/sh\necho 22\n')
            (bindir / 'npm').write_text('#!/bin/sh\n[ "$FAULT" != tools ]\n')
            for name in ['node', 'npm']: (bindir / name).chmod(0o755)
            # Fake only package download/bootstrap; all embedded Python validation runs normally.
            py = bindir / 'python3'
            py.write_text(f'''#!/bin/sh
if [ "$1" = -m ] && [ "$2" = venv ]; then
 mkdir -p "$3/bin"
 ln -s "$0" "$3/bin/python3"
 exit 0
fi
if [ "$1" = -m ] && [ "$2" = pip ]; then
 '{sys.executable}' -c 'import json,sys; open("calls.jsonl","a").write(json.dumps(["pip"]+sys.argv[1:])+"\\n")' "$@"
 if [ -n "$TERMUX_VERSION" ]; then
  case "$*" in *ziglang*) exit 1 ;; esac
 fi
 exit 0
fi
exec '{sys.executable}' "$@"
'''); py.chmod(0o755)
            zigpkg = root / 'ziglang'; zigpkg.mkdir(); (zigpkg / '__init__.py').touch()
            zig = zigpkg / 'zig'; zig.write_text('#!/bin/sh\necho 0.14.1\n'); zig.chmod(0o755)
            (root / 'requirements.txt').write_text('websockets>=13,<16\n')
            (root / 'sync-apps.py').write_text('''import json,os,pathlib,sys
with open('calls.jsonl','a') as f: f.write(json.dumps(['sync',sys.argv[1]])+'\\n')
icons=pathlib.Path('launcher/icons'); icons.mkdir()
with open('calls.jsonl','a') as f: f.write(json.dumps(['icons-traversable', bool(icons.stat().st_mode & 1)])+'\\n')
apps=[] if os.environ['FAULT']=='empty' else [{'id':'example.app'}]
pathlib.Path('launcher/apps.js').write_text('window.TV_APPS = '+json.dumps({'apps':apps})+';')
''')
            (root / 'scripts/build.sh').write_text('''#!/bin/sh
[ "$FAULT" != build ] || exit 1
mkdir -p dist
printf 'package' > dist/com.gathin.tvhome_1.1.0_all.ipk
printf 'package' > dist/com.local.nativehome_0.6.13_arm.ipk
''')
            (root / 'scripts/configure-tv.sh').write_text('''#!/bin/sh
printf '["configure"]\\n' >> calls.jsonl
[ "$FAULT" != configure ]
''')
            env = dict(os.environ, PATH=str(bindir),
                       PYTHONPATH=str(root), FAULT=fault, EXISTING='1' if existing else '0',
                       DEVICE='test-tv', PROFILE_HOST='192.0.2.99' if fault=='profile' else host,
                       TV_NODE_OUTPUT=tv_node_output if tv_node_output is not None else
                           ('0.10.24\n' if fault=='tv-node' else '0.12.2\n'),
                       TV_NODE_EXIT=str(tv_node_exit))
            env.pop('ZIG', None); env.pop('TV_HOST', None)
            env.pop('TERMUX_VERSION', None); env.pop('PREFIX', None)
            if termux:
                env['TERMUX_VERSION'] = 'test'
            if external_zig or path_zig:
                supplied = bindir / ('zig' if path_zig else 'external-zig')
                supplied.write_text('#!/bin/sh\necho ' + zig_version + '\n')
                supplied.chmod(0o755)
                if external_zig:
                    env['ZIG'] = str(supplied)
            result = subprocess.run(['bash', 'install.sh', host], cwd=root, env=env,
                                    text=True, capture_output=True)
            calls = [json.loads(line) for line in (root/'calls.jsonl').read_text().splitlines()] if (root/'calls.jsonl').exists() else []
            return result, calls

    def test_installs_configures_then_launches(self):
        result, calls = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertNotIn('SECRET-EXISTING-PASSPHRASE', result.stdout+result.stderr)
        self.assertIn(['icons-traversable', True], calls)
        installs = [c for c in calls if c[0]=='ares-install']
        self.assertEqual(len(installs), 2)
        self.assertTrue(all(c[1:3]==['-d','test-tv'] for c in installs))
        self.assertLess(calls.index(installs[-1]), calls.index(['configure']))
        self.assertEqual(calls[-1], ['ares-launch','-d','test-tv','-p','{"nativeHomeStart":true}','com.local.nativehome'])

    def test_tv_node_below_01025_stops_before_inventory_and_package_install(self):
        result, calls = self.run_installer(fault='tv-node')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('TV Node.js 0.10.25', result.stdout+result.stderr)
        self.assertFalse(any(c[0] in ('sync', 'ares-install', 'configure', 'ares-launch') for c in calls))

    def test_supported_tv_node_with_cli_banners_reaches_install_and_launch(self):
        for output in (
            '0.10.25\n',
            '0.12.2\n',
            '[Info] Set target device : test-tv\n0.12.2\n',
            '[Info] Set target device : test-tv\r\n20.12.2\r\n',
            '8.12.0\n[Info] Command complete\n',
            '\n[Info] Set target device : test-tv\n0.12.2\n\n',
        ):
            with self.subTest(output=output):
                result, calls = self.run_installer(tv_node_output=output)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(sum(c[0]=='ares-install' for c in calls), 2)
                self.assertEqual(calls[-1][0], 'ares-launch')

    def test_invalid_tv_node_output_stops_before_inventory_and_package_install(self):
        for output in (
            '',
            '[Info] Set target device : test-tv\n',
            '[Info] Set target device : test-tv\n0.10.24\n',
            '0.10.24\n',
            '0.12\n',
            'Warning: command failed\n0.12.2\n',
            '0.12.2\n20.12.2\n',
        ):
            with self.subTest(output=output):
                result, calls = self.run_installer(tv_node_output=output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('TV Node.js 0.10.25', result.stdout+result.stderr)
                self.assertFalse(any(c[0] in ('sync', 'ares-install', 'configure', 'ares-launch') for c in calls))

    def test_failed_tv_node_probe_preserves_exit_status_and_stops_installation(self):
        for output in ('', '[Info] Set target device : test-tv\n0.12.2\n'):
            with self.subTest(output=output):
                result, calls = self.run_installer(tv_node_output=output, tv_node_exit=7)
                self.assertEqual(result.returncode, 7, result.stdout+result.stderr)
                self.assertFalse(any(c[0] in ('sync', 'ares-install', 'configure', 'ares-launch') for c in calls))

    def test_default_bootstrap_installs_pinned_zig_distribution(self):
        result, calls = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertTrue(any('ziglang==0.14.1' in call for call in calls if call[0] == 'pip'))

    def test_termux_supplied_zig_skips_python_zig_distribution(self):
        for option in ('external_zig', 'path_zig'):
            with self.subTest(option=option):
                result, calls = self.run_installer(termux=True, **{option: True})
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                pip = [call for call in calls if call[0] == 'pip']
                self.assertTrue(pip)
                self.assertFalse(any('ziglang' in arg for call in pip for arg in call))
                self.assertEqual(calls[-1], ['ares-launch', '-d', 'test-tv', '-p', '{"nativeHomeStart":true}', 'com.local.nativehome'])

    def test_termux_without_zig_stops_with_instructions_before_pairing(self):
        result, calls = self.run_installer(termux=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ZIG', result.stdout+result.stderr)
        self.assertIn('Termux', result.stdout+result.stderr)
        self.assertFalse(any('ziglang' in arg for call in calls if call[0] == 'pip' for arg in call))
        self.assertFalse(any(call[0].startswith('ares-') for call in calls))

    def test_wrong_external_zig_stops_before_pairing(self):
        result, calls = self.run_installer(external_zig=True, zig_version='0.15.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('0.14.1', result.stdout+result.stderr)
        self.assertFalse(any(call[0].startswith('ares-') for call in calls))

    def test_reuses_profile_without_retargeting(self):
        result, calls = self.run_installer(existing=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertFalse(any('--add' in c or '--modify' in c for c in calls))

    def test_failure_never_launches_helper(self):
        for fault in ['tools', 'pair', 'ssh', 'empty', 'build', 'install', 'configure', 'profile']:
            with self.subTest(fault=fault):
                result, calls = self.run_installer(fault, existing=fault=='profile')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(c[0]=='ares-launch' for c in calls))
                if fault in ['tools', 'pair', 'ssh', 'empty', 'build', 'profile']:
                    self.assertFalse(any(c[0]=='ares-install' for c in calls))

    def test_rejects_host_before_touching_tv(self):
        result, calls = self.run_installer(host='192.0.2.10;touch nope')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])


if __name__ == '__main__': unittest.main()
