"""Web compilation and filesystem staging regressions."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.tv_web_build import compile_web, stage


class WebCompilerEncodingTests(unittest.TestCase):
    def test_unicode_assets_survive_a_legacy_windows_text_encoding(self):
        files = {'app.js': 'window.label = "한국어 / Русский";\n'.encode('utf-8')}
        with patch('subprocess._text_encoding', return_value='cp1252'):
            result = compile_web(files)
        self.assertEqual(result['app.js'], files['app.js'])


class WebStagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / 'source'
        self.output = self.root / 'output'
        self.source.mkdir()
        (self.source / 'first.js').write_bytes(b'new first')
        (self.source / 'second.js').write_bytes(b'new second')
        self.output.mkdir()
        (self.output / 'first.js').write_bytes(b'old first')
        (self.output / 'old').mkdir()
        (self.output / 'old' / 'image.bin').write_bytes(b'\x00\xff')
        self.old = self.snapshot(self.output)
        self.new = self.snapshot(self.source)

    def snapshot(self, directory):
        return {path.relative_to(directory).as_posix(): path.read_bytes()
                for path in directory.rglob('*') if path.is_file()}

    def assert_stage_clean(self):
        # The lock inode survives retries. Neither tree should have a spare copy.
        self.assertEqual(self.snapshot(self.source), self.new)
        self.assertEqual({path.name for path in self.root.iterdir()},
                         {'source', 'output', '.cytv-web-stage-output'})
        sidecar = self.root / '.cytv-web-stage-output'
        self.assertEqual({path.name for path in sidecar.iterdir()}, {'.cytv-web-stage-v1.lock'})
        self.assertEqual(self.snapshot(sidecar), {'.cytv-web-stage-v1.lock': b''})

    def assert_successful_retry(self):
        stage(self.source, self.output, compiler=lambda files: self.new)
        self.assertEqual(self.snapshot(self.output), self.new)
        self.assert_stage_clean()

    def test_failed_second_write_preserves_previous_stage(self):
        write_bytes = Path.write_bytes
        writes = []

        def fail_second_write(path, raw):
            writes.append(path.name)
            if len(writes) == 2:
                raise OSError('injected write failure')
            return write_bytes(path, raw)

        with patch.object(Path, 'write_bytes', fail_second_write):
            with self.assertRaisesRegex(OSError, 'injected write failure'):
                stage(self.source, self.output, compiler=lambda files: self.new)
        self.assertEqual(len(writes), 2)
        self.assertEqual(self.snapshot(self.output), self.old)
        self.assert_stage_clean()
        self.assert_successful_retry()

    def test_failed_promotion_restores_previous_stage(self):
        rename = Path.rename
        failed = False

        def fail_promotion(path, target):
            nonlocal failed
            if target == self.output and not failed:
                failed = True
                raise OSError('injected promotion failure')
            return rename(path, target)

        with patch.object(Path, 'rename', fail_promotion):
            with self.assertRaisesRegex(OSError, 'injected promotion failure'):
                stage(self.source, self.output, compiler=lambda files: self.new)
        self.assertEqual(self.snapshot(self.output), self.old)
        self.assert_stage_clean()
        self.assert_successful_retry()

    def test_retry_recovers_after_process_exits_between_renames(self):
        result = subprocess.run(
            [sys.executable, '-c', """
import os
from pathlib import Path
import sys
from unittest.mock import patch
from scripts.tv_web_build import stage

source, output = map(Path, sys.argv[1:])
rename = Path.rename

def exit_after_backup(path, target):
    renamed = rename(path, target)
    if path == output:
        os._exit(23)
    return renamed

with patch.object(Path, 'rename', exit_after_backup):
    stage(source, output, compiler=lambda files: files)
""", str(self.source), str(self.output)],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 23, result.stderr)

        def check_restored(files):
            self.assertEqual(self.snapshot(self.output), self.old)
            raise OSError('injected compile failure')

        with self.assertRaisesRegex(OSError, 'injected compile failure'):
            stage(self.source, self.output, compiler=check_restored)
        self.assert_stage_clean()
        self.assert_successful_retry()

    def test_concurrent_staging_to_same_output_reports_busy(self):
        def compile_while_locked(files):
            result = subprocess.run(
                [sys.executable, '-c', """
import sys
from scripts.tv_web_build import stage

stage(sys.argv[1], sys.argv[2], compiler=lambda files: files)
""", str(self.source), str(self.output)],
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Another build is using', result.stderr)
            self.assertEqual(self.snapshot(self.output), self.old)
            return files

        stage(self.source, self.output, compiler=compile_while_locked)
        self.assertEqual(self.snapshot(self.output), self.new)
        self.assert_stage_clean()

    def test_rejects_overlapping_sources_and_outputs(self):
        for source, output in ((self.source, self.source),
                               (self.source, self.source / 'nested'),
                               (self.source, self.root)):
            with self.subTest(source=source, output=output):
                with self.assertRaisesRegex(ValueError, 'separate staging directory'):
                    stage(source, output, compiler=lambda files: files)
        self.assertEqual(self.snapshot(self.source), self.new)
        self.assertEqual(self.snapshot(self.output), self.old)

    def test_preserves_unmanaged_sibling(self):
        sidecar = self.root / '.cytv-web-stage-output'
        (sidecar / 'new').mkdir(parents=True)
        (sidecar / 'new' / 'unrelated').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'Unmanaged web staging'):
            stage(self.source, self.output, compiler=lambda files: files)
        self.assertEqual(self.snapshot(sidecar), {'new/unrelated': b'keep'})
        self.assertEqual(self.snapshot(self.output), self.old)

    def test_missing_or_non_directory_source_preserves_previous_stage(self):
        for source in (self.root / 'missing', self.source / 'first.js'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'Web source must be a directory'):
                stage(source, self.output, compiler=lambda files: self.fail('unexpected compilation'))
            self.assertEqual(self.snapshot(self.output), self.old)

    def test_inaccessible_source_directory_preserves_previous_stage(self):
        images = self.source / 'images'
        images.mkdir()
        (images / 'asset.png').write_bytes(b'asset')
        iterdir = Path.iterdir

        def fail_read(path):
            if path == images:
                raise PermissionError('injected source directory error')
            return iterdir(path)

        with patch.object(Path, 'iterdir', fail_read):
            with self.assertRaisesRegex(PermissionError, 'injected source directory error'):
                stage(self.source, self.output, compiler=lambda files: files)
        self.assertEqual(self.snapshot(self.output), self.old)
