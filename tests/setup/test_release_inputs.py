"""Reuse must survive only known metadata changes, never unbuilt product inputs."""
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_GUIDES = (
    'android/README.md', 'android/STABLE-READINESS.md',
    'root-edition/README.md', 'root-edition/STATUS.md',
    'root-edition/TESTING.md', 'root-edition/UPDATES.md',
    'root-edition/runtime/README.md',
)


class ReleaseInputs(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'scripts/release-inputs.py').exists(), 'Shared release input verifier is required')
        self.inputs = runpy.run_path(str(ROOT / 'scripts/release-inputs.py'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'CI test')
        self.git('config', 'user.email', 'ci@example.invalid')
        self.write('launcher/app.js', 'product')
        self.write('release-versions.json', '{"release":"2.0.0"}')
        self.write('release-plan.json', '{}')
        self.write('README.md', 'release links')
        self.write('docs/INSTALL.md', 'instructions')
        self.source = self.commit('candidate')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL).strip()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def verify(self, head=None):
        return self.inputs['verify_inputs'](self.source, head or self.git('rev-parse', 'HEAD'), self.root)

    def test_evidence_and_guides_preserve_input_identity(self):
        self.write('release-plan.json', '{"acceptance":"observed"}')
        self.write('README.md', 'corrected release links')
        self.write('docs/INSTALL.md', 'corrected instructions')
        self.write('docs/RELEASE-2.0.0-ACCEPTANCE.md', 'physical observations')
        self.commit('record acceptance')
        self.verify()

    def test_unbuilt_product_inputs_and_packaged_markdown_are_rejected(self):
        for name in ('launcher/app.js', 'release-versions.json', 'package-lock.json',
                     '.github/workflows/cytv.yml', 'scripts/build-cytv.py',
                     'tests/setup/test_release_inputs.py', 'THIRD_PARTY_NOTICES.md',
                     'android/app/src/main/assets/ui/guide/README.md',
                     'LICENSE', 'cytv/licenses/COPYING.md',
                     'android/OTHER-GUIDE.md', 'root-edition/OTHER-GUIDE.md',
                     'root-edition/runtime/OTHER-GUIDE.md',
                     'docs/tool.py', 'docs/source.json', 'unknown/file'):
            with self.subTest(name=name):
                self.git('reset', '--hard', self.source)
                self.git('clean', '-fd')
                self.write(name, 'changed')
                self.commit('unbuilt input')
                with self.assertRaisesRegex(ValueError, 'inputs'):
                    self.verify()

    def test_external_guide_edits_preserve_build_and_test_identity(self):
        for name in EXTERNAL_GUIDES:
            self.write(name, 'original instructions')
        self.source = self.commit('source with external guides')
        key = self.inputs['test_key']
        environment = {'python': '3.12', 'day': '2026-11-02'}
        original = key(self.source, 'tv,installer', environment, self.root)
        for name in EXTERNAL_GUIDES:
            with self.subTest(name=name):
                self.git('reset', '--hard', self.source)
                self.write(name, 'final release instructions')
                head = self.commit('external guide edit')
                self.verify(head)
                self.assertEqual(original, key(head, 'tv,installer', environment, self.root))
                self.assertEqual(self.inputs['acceptance_scope']([name]), set())

    def test_external_guide_executable_and_symlink_changes_invalidate_build(self):
        for name in EXTERNAL_GUIDES:
            self.write(name, 'original instructions')
        self.source = self.commit('regular external guides')
        for name in EXTERNAL_GUIDES:
            for mode in ('executable', 'symlink'):
                with self.subTest(name=name, mode=mode):
                    self.git('reset', '--hard', self.source)
                    path = self.root / name
                    if mode == 'executable':
                        path.chmod(0o755)
                    else:
                        path.unlink()
                        path.symlink_to(self.root / 'launcher/app.js')
                    self.commit('unsafe documentation mode')
                    with self.assertRaisesRegex(ValueError, 'inputs'):
                        self.verify()

    def test_executable_or_symlink_documentation_is_not_exempt(self):
        (self.root / 'README.md').chmod(0o755)
        self.commit('executable documentation')
        with self.assertRaisesRegex(ValueError, 'inputs'):
            self.verify()
        self.git('reset', '--hard', self.source)
        (self.root / 'README.md').unlink()
        (self.root / 'README.md').symlink_to('launcher/app.js')
        self.commit('symlink documentation')
        with self.assertRaisesRegex(ValueError, 'inputs'):
            self.verify()

    def test_equivalent_sibling_source_is_not_accepted(self):
        self.write('docs/INSTALL.md', 'first')
        first = self.commit('first branch')
        self.git('checkout', '-b', 'sibling', self.source)
        self.write('docs/INSTALL.md', 'second')
        second = self.commit('second branch')
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            self.inputs['verify_inputs'](first, second, self.root)

    def test_pin_requires_positive_run_and_full_sha(self):
        valid = {'run_id': 42, 'attempt': 1, 'source': self.source}
        self.assertEqual(self.inputs['build_pin']({'build': valid}), valid)
        self.assertIsNone(self.inputs['build_pin']({}))
        for pin in (None, {}, {'run_id': True, 'source': self.source},
                    {'run_id': 0, 'source': self.source}, {'run_id': 42, 'source': 'main'},
                    {'run_id': '42', 'source': self.source}):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                self.inputs['build_pin']({'build': pin})

    def test_cached_success_never_overrides_newer_failed_evidence(self):
        self.assertTrue('test_cache_hit' in self.inputs, 'Reuse must check the latest CI evidence')
        valid = {'id': 10, 'status': 'completed', 'conclusion': 'success', 'event': 'pull_request',
                 'head_branch': 'feature', 'path': '.github/workflows/tests.yml',
                 'head_repository': {'full_name': 'owner/repo'}}
        for latest, original, expected in (
            (valid, valid, True),
            ({**valid, 'id': 11}, valid, True),
            ({**valid, 'id': 11, 'conclusion': 'failure'}, valid, False),
            ({**valid, 'id': 11, 'status': 'in_progress', 'conclusion': None}, valid, False),
            ({**valid, 'id': 11}, {**valid, 'conclusion': 'failure'}, False),
            (valid, {**valid, 'head_repository': {'full_name': 'someone/fork'}}, False),
        ):
            def provider(path):
                return original if path == 'actions/runs/10' else {'workflow_runs': [latest, {**valid, 'id': 12, 'status': 'in_progress'}]}
            self.assertEqual(self.inputs['test_cache_hit'](10, 12, 'owner/repo', 'feature', provider), expected)


    def test_test_cache_identity_includes_merge_tree_selection_and_environment(self):
        self.assertTrue('test_key' in self.inputs, 'PR tests need an input/environment-bound success key')
        key = self.inputs['test_key']
        environment = {'python': '3.12.9', 'node': '22.1.0', 'dependencies': 'paramiko==3.5.1', 'image': 'ubuntu-1', 'day': '2026-10-28'}
        first = key(self.source, 'tv,installer', environment, self.root)
        self.write('docs/INSTALL.md', 'documentation correction')
        self.write('release-plan.json', '{"acceptance":"observed"}')
        docs = self.commit('evidence only')
        self.assertEqual(first, key(docs, 'tv,installer', environment, self.root))
        self.assertNotEqual(first, key(docs, 'tv', environment, self.root))
        self.assertNotEqual(first, key(docs, 'tv,installer', {**environment, 'dependencies': 'paramiko==9'}, self.root))
        self.assertNotEqual(first, key(docs, 'tv,installer', {**environment, 'day': '2026-10-29'}, self.root))
        self.write('base-only-dependency', 'changed merged base')
        merged = self.commit('base input changed')
        self.assertNotEqual(first, key(merged, 'tv,installer', environment, self.root))


    def test_scope_keeps_metadata_out_and_unknown_inputs_expand(self):
        scope = self.inputs['acceptance_scope']
        self.assertEqual(scope(['docs/INSTALL.md', 'release-plan.json']), set())
        self.assertEqual(scope(['root-edition/service/emergency.py']), {'controls', 'startup', 'update-recovery'})
        self.assertEqual(scope(['root-edition/ui/app.js']), self.inputs['ALL_SCENARIOS'])
        self.assertEqual(scope(['root-edition/ui/style.css']), {'ui-controls'})
        for name in ('launcher/system-updates.js', 'launcher/helper-control.js', 'root-edition/ui/root-profile.js'):
            self.assertEqual(scope([name]), self.inputs['ALL_SCENARIOS'])
        self.assertEqual(scope(['unknown/runtime']), {'ui-controls', 'controls', 'startup', 'update-recovery'})
        self.assertIn('update-recovery', scope(['cytv/root_driver.py']))


if __name__ == '__main__':
    unittest.main()
