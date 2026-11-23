"""Web compilation and filesystem staging regressions."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.tv_web_build import compile_web, stage

ROOT = Path(__file__).resolve().parents[2]


class WebCompilerEncodingTests(unittest.TestCase):
    def test_unicode_assets_survive_a_legacy_windows_text_encoding(self):
        files = {'app.js': 'window.label = "한국어 / Русский";\n'.encode('utf-8')}
        with patch('subprocess._text_encoding', return_value='cp1252'):
            result = compile_web(files)
        self.assertEqual(result['app.js'], files['app.js'])


class LauncherSourceInventoryTests(unittest.TestCase):
    def test_checkout_launcher_uses_index_names_and_working_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / 'launcher'
            source.mkdir()
            (source / 'appinfo.json').write_bytes(b'{"id":"com.gathin.tvhome"}')
            (source / 'index.html').write_bytes(b'committed version')
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'add', 'launcher'], cwd=root, check=True)
            (source / 'index.html').write_bytes(b'working edit')
            (source / 'new resource.txt').write_bytes(b'staged resource')
            subprocess.run(['git', 'add', 'launcher/new resource.txt'], cwd=root, check=True)
            (source / 'local draft.json').write_bytes(b'malformed untracked draft')
            (source / 'apps.js').write_bytes(b'window.TV_APPS = {"apps":[{"icon":"icons/current.png"}]};')
            (source / 'icons').mkdir()
            (source / 'icons/current.png').write_bytes(b'current art')
            (source / 'icons/old.png').write_bytes(b'old art')

            output = root / 'stage'
            with patch('scripts.tv_web_build.ROOT', root):
                stage(source, output, compiler=lambda files: files)
            self.assertEqual((output / 'index.html').read_bytes(), b'working edit')
            self.assertEqual((output / 'new resource.txt').read_bytes(), b'staged resource')
            self.assertEqual((output / 'apps.js').read_bytes(), (source / 'apps.js').read_bytes())
            self.assertEqual((output / 'icons/current.png').read_bytes(), b'current art')
            self.assertFalse((output / 'icons/old.png').exists())
            self.assertFalse((output / 'local draft.json').exists())

    @unittest.skipIf(os.name == 'nt', 'Requires permission to create a symlink')
    def test_indirect_tracked_asset_preserves_previous_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source, output = root / 'launcher', root / 'stage'
            (source / 'assets').mkdir(parents=True)
            (source / 'appinfo.json').write_bytes(b'{"id":"com.gathin.tvhome"}')
            (source / 'assets/logo.png').write_bytes(b'original')
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'add', 'launcher'], cwd=root, check=True)

            with patch('scripts.tv_web_build.ROOT', root):
                stage(source, output, compiler=lambda files: files)
                other_dir = (source / 'assets').rename(root / 'private')
                (other_dir / 'logo.png').write_bytes(b'indirect')
                (source / 'assets').symlink_to(other_dir, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'Indirect web source'):
                    stage(source, output, compiler=lambda files: files)
                self.assertEqual((output / 'assets/logo.png').read_bytes(), b'original')
                entire_launcher = source.rename(root / 'another-launcher')
                source.symlink_to(entire_launcher, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'Indirect web source'):
                    stage(source, output, compiler=lambda files: files)

    def test_export_launcher_matches_the_checkout_inventory(self):
        names = subprocess.check_output(['git', 'ls-files', '-z', '--', 'launcher'],
                                        cwd=ROOT, encoding='utf-8').split('\0')
        expected = {name.removeprefix('launcher/') for name in names
                    if name and name != 'launcher/apps.js' and not name.startswith('launcher/icons/')}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / 'launcher'
            for name in expected:
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / 'launcher' / name, path)
            (source / 'local draft.json').write_bytes(b'malformed workspace file')

            output = root / 'stage'
            with patch('scripts.tv_web_build.ROOT', root):
                stage(source, output, compiler=lambda files: files)
            self.assertEqual({path.relative_to(output).as_posix() for path in output.rglob('*')
                              if path.is_file()}, expected)


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
