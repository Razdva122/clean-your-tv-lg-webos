"""Automatic formatting must preserve partial staging and excluded sources."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class AutoFormatTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Fixture uses a POSIX node_modules symlink')
    def test_real_commit_formats_index_without_staging_unfinished_edits(self):
        hook = ROOT / '.husky/pre-commit'
        self.assertTrue(hook.is_file(), 'The versioned pre-commit hook must exist')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def run(*args):
                return subprocess.check_output(args, cwd=root, text=True,
                                               env={**os.environ, 'HUSKY': '1'})

            run('git', 'init', '-q')
            run('git', 'config', 'user.name', 'Formatter Test')
            run('git', 'config', 'user.email', 'formatter@example.invalid')
            run('git', 'config', 'commit.gpgsign', 'false')
            # Separate hunks with stable content that Prettier does not collapse.
            separator = ''.join('// separate edit %s\n' % i for i in range(12))
            baseline = 'const first = 1;\n' + separator + 'const second = 1;\n'
            (root / 'partial.js').write_text(baseline)
            run('git', 'add', 'partial.js')
            run('git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Baseline')
            for name in ('package.json', '.lintstagedrc.json', '.prettierrc.json', '.prettierignore'):
                shutil.copy(ROOT / name, root / name)
            (root / '.husky').mkdir()
            shutil.copy(hook, root / '.husky/pre-commit')
            (root / 'node_modules').symlink_to(ROOT / 'node_modules', target_is_directory=True)
            run('npm', 'run', 'prepare')
            self.assertEqual(run('git', 'config', '--get', 'core.hooksPath').strip(), '.husky/_')

            staged = baseline.replace('const first = 1;', 'const first={a:1};')
            (root / 'partial.js').write_text(staged)
            run('git', 'add', 'partial.js')
            (root / 'partial.js').write_text(staged.replace('const second = 1;', 'const second={b:2};'))
            ignored = root / 'native/app/vendor/ignored.js'
            ignored.parent.mkdir(parents=True)
            ignored.write_text('deliberately invalid JS ???\n')
            run('git', 'add', 'native/app/vendor/ignored.js')
            (root / 'private.js').write_text('const privateValue={keep:1};\n')

            run('git', 'commit', '-qm', 'Format staged changes')
            committed = run('git', 'show', 'HEAD:partial.js')
            self.assertIn('const first = { a: 1 };', committed)
            self.assertIn('const second = 1;', committed)
            self.assertNotIn('b: 2', committed)
            self.assertIn('const second={b:2};', (root / 'partial.js').read_text())
            self.assertEqual(run('git', 'diff', '--cached', '--name-only'), '')
            self.assertEqual(run('git', 'show', 'HEAD:native/app/vendor/ignored.js'), ignored.read_text())
            self.assertEqual((root / 'private.js').read_text(), 'const privateValue={keep:1};\n')

            previous = run('git', 'rev-parse', 'HEAD')
            (root / 'broken.js').write_text('const broken = {\n')
            run('git', 'add', 'broken.js')
            failure = subprocess.run(['git', 'commit', '-qm', 'Must fail'], cwd=root,
                                     env={**os.environ, 'HUSKY': '1'}, capture_output=True, text=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn('SyntaxError', failure.stdout + failure.stderr)
            self.assertEqual(run('git', 'rev-parse', 'HEAD'), previous)
            self.assertEqual(run('git', 'show', ':broken.js'), 'const broken = {\n')
            self.assertEqual((root / 'broken.js').read_text(), 'const broken = {\n')
            self.assertIn('const second={b:2};', (root / 'partial.js').read_text())
            self.assertEqual((root / 'private.js').read_text(), 'const privateValue={keep:1};\n')
            self.assertEqual(run('git', 'stash', 'list'), '')
