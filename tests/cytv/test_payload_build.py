"""Public payload rebuilds preserve the previously verified output."""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import package


def write_payload(directory, members):
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in members.items():
        (directory / name).write_bytes(data)
    (directory / 'payload.json').write_text(json.dumps({
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in members.items()}
    }), encoding='utf-8')


class PayloadBuildTests(unittest.TestCase):
    def setUp(self):
        repo = Path(__file__).resolve().parents[2]
        self.build_payload = runpy.run_path(str(repo / 'scripts/build-cytv.py'))['build_payload']
        self.namespace = self.build_payload.__globals__
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.root / 'release-versions.json').write_text('{}', encoding='utf-8')
        self.enterContext(patch.dict(self.namespace, {'ROOT': self.root}))
        self.output = self.root / 'build/cytv/payload'
        write_payload(self.output, {'old.txt': b'previous public asset'})
        self.original_manifest = package.verify_payload(self.output)
        self.workspace = self.output.parent / '.cytv-payload-build'
        self.previous = self.workspace / 'previous'
        self.attempts = self.workspace / 'attempts'
        self.lock = self.workspace / '.cytv-payload-build-v1.lock'

    def test_failed_first_compiler_preserves_previous_payload(self):
        def compile_installer_support(payload, work):
            (payload / 'partial.txt').write_bytes(b'incomplete native output')
            raise subprocess.CalledProcessError(1, ['zig'])

        with patch.dict(self.namespace, {'stage_installer_support': compile_installer_support}):
            with self.assertRaises(subprocess.CalledProcessError):
                self.build_payload()
        self.assertEqual(package.verify_payload(self.output), self.original_manifest)
        self.assertEqual({path.name for path in self.output.iterdir()}, {'old.txt', 'payload.json'})
        self.assert_work_clean()

    def prepared(self, prepare, verify_versions=None):
        if verify_versions is None:
            verify_versions = Mock()
        return patch.dict(self.namespace, {'_prepare_payload': prepare,
                                           'verify_release_versions': verify_versions})

    def prepare_next_payload(self, payload, work, versions):
        self.assertEqual(package.verify_payload(self.output), self.original_manifest)
        self.assertEqual(list(payload.iterdir()), [])
        write_payload(payload, {'new.txt': b'updated public asset'})
        (payload.parent / 'intermediate').write_bytes(b'compiler output')

    def assert_work_clean(self):
        self.assertEqual(set(self.workspace.iterdir()), {self.lock})

    def test_failed_integrity_check_preserves_previous_payload(self):
        def prepare_invalid(payload, work, versions):
            self.prepare_next_payload(payload, work, versions)
            (payload / 'new.txt').write_bytes(b'damaged after writing manifest')

        verify_versions = Mock()
        with self.prepared(prepare_invalid, verify_versions):
            with self.assertRaisesRegex(ValueError, 'payload integrity mismatch'):
                self.build_payload()
        verify_versions.assert_not_called()
        self.assertEqual(package.verify_payload(self.output), self.original_manifest)
        self.assert_work_clean()

    def test_failed_version_check_preserves_previous_payload(self):
        verify_versions = Mock(side_effect=ValueError('version mismatch'))
        with self.prepared(self.prepare_next_payload, verify_versions):
            with self.assertRaisesRegex(ValueError, 'version mismatch'):
                self.build_payload()
        staged, versions = verify_versions.call_args.args
        self.assertNotEqual(staged, self.output)
        self.assertEqual(versions, {})
        self.assertEqual(package.verify_payload(self.output), self.original_manifest)
        self.assert_work_clean()

    def test_rebuild_replaces_payload_without_copying_stale_files(self):
        (self.output / 'untracked.txt').write_bytes(b'old scratch file')
        with self.prepared(self.prepare_next_payload):
            self.assertEqual(self.build_payload(), self.output)
        self.assertEqual(set(package.verify_payload(self.output)['files']), {'new.txt'})
        self.assertEqual({path.name for path in self.output.iterdir()}, {'new.txt', 'payload.json'})
        self.assert_work_clean()

    def test_failed_promotion_restores_previous_payload_and_can_retry(self):
        rename = Path.rename

        def fail_publish(path, target):
            if target == self.output and path != self.previous:
                raise PermissionError('cannot move staged payload')
            return rename(path, target)

        with self.prepared(self.prepare_next_payload):
            with patch.object(Path, 'rename', fail_publish):
                with self.assertRaisesRegex(PermissionError, 'cannot move staged payload'):
                    self.build_payload()
            self.assertEqual(package.verify_payload(self.output), self.original_manifest)
            self.assert_work_clean()
            self.assertEqual(self.build_payload(), self.output)
        self.assertEqual(set(package.verify_payload(self.output)['files']), {'new.txt'})
        self.assert_work_clean()

    def test_retry_restores_previous_after_interrupted_promotion(self):
        self.workspace.mkdir()
        self.lock.touch()
        self.output.rename(self.previous)
        abandoned = self.attempts / 'interrupted' / 'payload'
        write_payload(abandoned, {'abandoned.txt': b'different verified candidate'})

        with self.prepared(self.prepare_next_payload):
            self.assertEqual(self.build_payload(), self.output)
        self.assertEqual(set(package.verify_payload(self.output)['files']), {'new.txt'})
        self.assert_work_clean()

    def test_retry_cleans_previous_after_interruption_following_promotion(self):
        self.workspace.mkdir()
        self.lock.touch()
        self.output.rename(self.previous)
        write_payload(self.output, {'new.txt': b'already promoted public asset'})
        promoted_manifest = package.verify_payload(self.output)

        with self.prepared(Mock(side_effect=ValueError('next build failed'))):
            with self.assertRaisesRegex(ValueError, 'next build failed'):
                self.build_payload()
        self.assertEqual(package.verify_payload(self.output), promoted_manifest)
        self.assert_work_clean()

    def test_unmanaged_workspace_is_preserved(self):
        self.previous.mkdir(parents=True)
        private_file = self.previous / 'keep'
        private_file.write_bytes(b'user file')
        with self.assertRaisesRegex(ValueError, 'Unmanaged payload build directory'):
            self.build_payload()
        self.assertEqual(private_file.read_bytes(), b'user file')
        self.assertEqual(package.verify_payload(self.output), self.original_manifest)

    def test_indirect_output_is_preserved(self):
        external = self.root / 'external'
        self.output.rename(external)
        try:
            self.output.symlink_to(external, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'cannot create test symlink: {error}')
        with self.assertRaisesRegex(ValueError, 'Invalid payload build directory'):
            self.build_payload()
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(package.verify_payload(external), self.original_manifest)

    def test_cli_holds_build_lock_through_host_packaging(self):
        def build_host(payload, desktop):
            self.assertEqual(payload, self.output)
            with self.assertRaisesRegex(RuntimeError, 'Another build is using'):
                self.build_payload()
            self.assertEqual(set(package.verify_payload(payload)['files']), {'new.txt'})

        host = Mock(side_effect=build_host)
        with (self.prepared(self.prepare_next_payload),
              patch.dict(self.namespace, {'build_host': host}),
              patch.object(sys, 'argv', ['build-cytv.py', '--desktop'])):
            self.namespace['main']()
        host.assert_called_once_with(self.output, True)
        self.assert_work_clean()
