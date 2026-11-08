"""Real read-only selection and storage checks; no vendor package requests."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cytv import no_root_observer as observer
from cytv.errors import UserError


@unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'Requires POSIX and Node')
@unittest.skipIf(getattr(os, 'getuid', lambda: 0)() == 0, 'Requires an unprivileged Developer Mode user')
class StorageSelection(unittest.TestCase):
    def setUp(self):
        directory = '/private/tmp' if Path('/private/tmp').exists() else None
        self.tmp = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.base.chmod(0o755)
        self.blocked = self.base / 'tmp'
        self.blocked.mkdir(mode=0o111)
        self.addCleanup(self.blocked.chmod, 0o755)
        self.jail = self.base / 'jail'
        self.jail.mkdir(mode=0o755)
        self.public = self.base / 'public'
        self.public.mkdir(mode=0o755)
        self.legacy = str(self.blocked / '.cytv-installer')
        self.private = str(self.jail / '.cytv-installer')
        self.runtime = shutil.which('node')
        self.remote = SimpleNamespace(run=self.run_command)
        for name, value in (('ROOT', self.legacy), ('JAIL_ROOT', self.private), ('PUBLIC_ROOT', str(self.public))):
            patcher = patch.object(observer, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.plan = observer.make_plan('a' * 32, 'b' * 32, 'remove', {}, {})

    def run_command(self, command, **kwargs):
        command = command.replace('/usr/bin/node', shlex.quote(self.runtime))
        result = subprocess.run(['sh', '-c', command], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout.decode()

    def test_selection_is_read_only_and_owned_leaf_passes_real_storage_on_legacy_nodes(self):
        runtimes = [self.runtime] + [os.environ[name] for name in
                   ('NODE010', 'NODE01025', 'NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            with self.subTest(runtime=runtime):
                self.runtime = runtime
                selected = observer.invoke(self.remote, self.plan, 'storage-select')['root']
                self.assertEqual(selected, self.private)
                self.assertFalse(Path(self.private).exists())
                self.assertFalse(Path(self.legacy).exists())
                plan = dict(self.plan, private_root=selected)
                observer.invoke(self.remote, plan, 'storage-check')
                self.assertEqual(Path(self.private).stat().st_mode & 0o777, 0o700)
                self.assertEqual(list(Path(self.private).iterdir()), [])
                self.assertEqual(list(self.public.iterdir()), [])
                Path(self.private).rmdir()

    def test_writable_or_symlink_jail_parent_cannot_host_private_evidence(self):
        self.jail.chmod(0o777)
        self.assertEqual(observer.invoke(self.remote, self.plan, 'storage-select')['root'], self.legacy)
        self.jail.chmod(0o755)
        actual = self.base / 'actual'
        self.jail.rename(actual)
        self.jail.symlink_to(actual, target_is_directory=True)
        self.assertEqual(observer.invoke(self.remote, self.plan, 'storage-select')['root'], self.legacy)
        self.assertFalse(Path(self.private).exists())

    def test_existing_symlink_leaf_is_refused_without_touching_target(self):
        target = self.base / 'foreign'
        target.mkdir(mode=0o700)
        evidence = target / 'keep'
        evidence.write_bytes(b'foreign')
        Path(self.private).symlink_to(target, target_is_directory=True)
        selected = observer.invoke(self.remote, self.plan, 'storage-select')['root']
        self.assertEqual(selected, self.private)
        with self.assertRaises(UserError):
            observer.invoke(self.remote, dict(self.plan, private_root=selected), 'storage-check')
        self.assertEqual(evidence.read_bytes(), b'foreign')
        self.assertTrue(Path(self.private).is_symlink())

    def test_existing_jail_leaf_does_not_bypass_parent_safety(self):
        Path(self.private).mkdir(mode=0o700)
        self.jail.chmod(0o777)
        with self.assertRaises(UserError):
            observer.invoke(self.remote, self.plan, 'storage-select')
        self.assertTrue(Path(self.private).exists())

    def test_foreign_owned_jail_parent_is_not_selected(self):
        # Substitute only unavailable host ownership metadata, retaining the
        # real Node selector and all real path/type/mode reads.
        prefix = ("var fs=require('fs'),original=fs.lstatSync;fs.lstatSync=function(name){"
                  "var s=original(name);if(name===" + json.dumps(str(self.jail)) +
                  ")s.uid=process.getuid()+1;return s;};")
        with patch.object(observer, 'STORAGE_SELECT', prefix + observer.STORAGE_SELECT):
            self.assertEqual(observer.invoke(self.remote, self.plan, 'storage-select')['root'], self.legacy)
        self.assertFalse(Path(self.private).exists())

    def test_untrusted_plan_cannot_redirect_observation_or_root_ssh(self):
        calls = []
        remote = SimpleNamespace(run=lambda *args, **kwargs: calls.append(args), root=True)
        for root in ('/media/developer/temp/private', '../private', None, [], {}):
            with self.subTest(root=root), self.assertRaises(UserError):
                observer.invoke(remote, dict(self.plan, private_root=root), 'status')
        with self.assertRaises(UserError):
            observer.invoke(remote, dict(self.plan, connection='root-ssh', private_root=self.private), 'status')
        self.assertEqual(calls, [])
