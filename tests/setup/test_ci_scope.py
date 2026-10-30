import importlib.util
from pathlib import Path
import unittest
import json
import os
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class CIScope(unittest.TestCase):
    def test_visual_assets_use_ui_checks_without_device_recovery_or_emulation(self):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT/'scripts/ci-scope.py')
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        for path in ('launcher/style.css', 'root-edition/ui/logo.svg', 'updater-app/font.woff2'):
            with self.subTest(path=path):
                self.assertEqual(scope.components([path]), {'ui', 'preview'})
        for path in ('native/prototype/filter.c', 'root-edition/input/evdev.py',
                     'updater-service/service.js', 'system-updater/service.py'):
            with self.subTest(path=path):
                self.assertIn('tv', scope.components([path]))
        self.assertEqual(scope.components(['shared-unknown.py']), set(scope.COMPONENTS))

    @patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo'})
    def test_full_candidate_is_an_explicit_same_repository_release_branch_freeze(self):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT/'scripts/ci-scope.py')
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        event = {'inputs': {'full_candidate': True}, 'repository': {'full_name': 'owner/repo'}}
        plan = {'version': '1.1.0', 'acceptance': ''}
        self.assertTrue(scope.build_installers(event, 'workflow_dispatch', 'refs/heads/release/next', plan, '1.1.0', '1.0.0', True))
        for ref in ('refs/heads/main', 'refs/heads/codex/draft', 'refs/tags/v1.1.0'):
            with self.subTest(ref=ref):
                self.assertFalse(scope.build_installers(event, 'workflow_dispatch', ref, plan, '1.1.0', '1.0.0', True))
        self.assertFalse(scope.build_installers(event, 'push', 'refs/heads/release/next', plan, '1.1.0', '1.0.0', True))

    def test_draft_scope_retains_each_affected_safety_group(self):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT/'scripts/ci-scope.py')
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        for path, expected in (
            ('cytv/operations.py', {'installer', 'android', 'setup'}),
            ('launcher/style.css', {'ui', 'preview'}),
            ('native/prototype/filter.c', {'tv', 'installer', 'setup'}),
            ('shared-unknown.py', set(scope.COMPONENTS)),
        ):
            with self.subTest(path=path), patch.object(scope, 'git', return_value=(path + '\0').encode()):
                self.assertEqual(scope.draft_components(), expected)
        with patch.object(scope, 'git', side_effect=subprocess.CalledProcessError(1, ['git'])):
            self.assertEqual(scope.draft_components(), set(scope.COMPONENTS))

    def test_theme_catalog_changes_select_preview_checks(self):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT/'scripts/ci-scope.py')
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        for name in ('showcase/registry/example.json', 'scripts/build-showcase.cjs',
                     'scripts/check-theme-submissions.cjs', 'tests/showcase/site.cjs'):
            with self.subTest(name=name):
                self.assertEqual(scope.components([name]), {'preview'})

    @patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo'})
    def test_manual_draft_build_produces_installers_without_claiming_acceptance(self):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT/'scripts/ci-scope.py')
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        plan = {'version': '1.1.0', 'acceptance': ''}
        event = {'inputs': {'test_build': 'true'}, 'repository': {'full_name': 'owner/repo'}}
        self.assertTrue(scope.build_installers(event, 'workflow_dispatch',
            'refs/heads/release/next', plan, '1.1.0', '1.0.3', True))
        self.assertFalse(scope.is_candidate(plan, '1.1.0', '1.0.3'))
        self.assertFalse(scope.build_installers({}, 'push', 'refs/heads/release/next', plan, '1.1.0', '1.0.3', True))
        for kind, ref, inputs, version, notes in (
            ('pull_request', 'refs/heads/release/next', event, '1.1.0', True),
            ('workflow_dispatch', 'refs/heads/main', event, '1.1.0', True),
            ('workflow_dispatch', 'refs/heads/feature', {}, '1.1.0', True),
            ('workflow_dispatch', 'refs/heads/release/next', {}, '1.1.0', True),
            ('workflow_dispatch', 'refs/heads/release/next', {'inputs': {'test_build': 'false'}}, '1.1.0', True),
            ('workflow_dispatch', 'refs/heads/release/next', event, '1.0.3', True),
            ('workflow_dispatch', 'refs/heads/release/next', event, '1.1.0', False),
        ):
            with self.subTest(kind=kind, ref=ref, inputs=inputs, version=version, notes=notes):
                self.assertFalse(scope.build_installers(inputs, kind, ref, plan, version, '1.0.3', notes))

    def test_builds_require_dispatch_even_after_product_or_metadata_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
            def commit(message):
                git('add', '.'); git('commit', '-m', message)
                return git('rev-parse', 'HEAD')
            git('init', '-b', 'main')
            git('config', 'user.name', 'CI test')
            git('config', 'user.email', 'ci@example.invalid')
            (root / 'release-versions.json').write_text('{"release":"1.0.0"}')
            base = commit('published')
            git('update-ref', 'refs/remotes/origin/main', base)
            git('checkout', '-b', 'release/next')
            (root / 'docs').mkdir()
            (root / 'docs/RELEASE-1.1.0.md').write_text('candidate')
            (root / 'release-versions.json').write_text('{"release":"1.1.0"}')
            plan = {'version': '1.1.0', 'acceptance': ''}
            (root / 'release-plan.json').write_text(json.dumps(plan))
            (root / 'product.js').write_text('built product')
            source = commit('prepared candidate')
            event_path, output = root / '.git/event.json', root / '.git/output'
            env = {**os.environ, 'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/release/next',
                   'GITHUB_EVENT_PATH': str(event_path), 'GITHUB_OUTPUT': str(output), 'CI_FULL_SUITE': 'false'}
            def route(event, **updates):
                output.write_text('')
                event_path.write_text(json.dumps(event))
                subprocess.check_output(['python3', str(ROOT / 'scripts/ci-scope.py')], cwd=root, env={**env, **updates})
                return dict(line.split('=') for line in output.read_text().splitlines())
            self.assertEqual(route({'before': base, 'after': source})['installers'], 'false')
            draft_event = {'inputs': {'test_build': 'true'}, 'repository': {'full_name': 'owner/repo'}}
            draft_env = {'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/codex/rc-fix', 'GITHUB_REPOSITORY': 'owner/repo'}
            draft = route(draft_event, **draft_env)
            self.assertEqual(draft['installers'], 'true', 'explicit branch feedback builds must not wait for PR integration')
            self.assertEqual(draft['candidate'], 'false', 'draft branch builds cannot claim release acceptance')
            for ref, payload, kind in (
                ('refs/heads/codex/rc-fix', {}, 'workflow_dispatch'),
                ('refs/heads/codex/rc-fix', {'inputs': {'test_build': 'false'}, 'repository': {'full_name': 'owner/repo'}}, 'workflow_dispatch'),
                ('refs/tags/v1.1.0', draft_event, 'workflow_dispatch'),
                ('refs/pull/1/merge', draft_event, 'workflow_dispatch'),
                ('refs/heads/main', draft_event, 'workflow_dispatch'),
                ('refs/heads/codex/rc-fix', {'before': base, 'after': source}, 'push'),
                ('refs/heads/codex/rc-fix', {'inputs': {'test_build': True}, 'repository': {'full_name': 'other/repo'}}, 'workflow_dispatch'),
            ):
                with self.subTest(ref=ref, payload=payload, kind=kind):
                    rejected = route(payload, GITHUB_EVENT_NAME=kind, GITHUB_REF=ref, GITHUB_REPOSITORY='owner/repo')
                    self.assertEqual(rejected['installers'], 'false')
                    self.assertEqual(rejected['candidate'], 'false')
            plan.update(build={'run_id': 42, 'attempt': 1, 'source': source}, acceptance='Controls observed', acceptance_build='42:1')
            (root / 'release-plan.json').write_text(json.dumps(plan))
            pinned = commit('pin and evidence')
            draft = route(draft_event, **draft_env)
            self.assertEqual(draft['installers'], 'true', 'explicit draft builds do not reuse the selected release pin')
            self.assertEqual(draft['candidate'], 'false', 'even accepted release metadata cannot make another branch a candidate')
            result = route({'before': source, 'after': pinned})
            self.assertEqual(result['installers'], 'false')
            self.assertEqual(result['tv'], 'false')
            frozen_event = {'inputs': {'full_candidate': 'true'}, 'repository': {'full_name': 'owner/repo'}}
            frozen = route(frozen_event, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='owner/repo')
            self.assertEqual(frozen['installers'], 'true', 'explicit freeze must build even with an equivalent old pin')
            self.assertEqual(frozen['full'], 'true')
            quick = route(draft_event, **draft_env, CI_QUICK_SUITE='true')
            self.assertEqual({name for name in ('ui', 'tv', 'installer', 'setup', 'android', 'preview') if quick[name] == 'true'}, {'ui', 'tv', 'installer', 'android', 'setup', 'preview'})
            self.assertEqual(quick['full'], 'false')
            (root / 'product.js').write_text('new input')
            changed = commit('new code')
            self.assertEqual(route({'before': pinned, 'after': changed})['installers'], 'false')
            event = {'pull_request': {'base': {'sha': base, 'ref': 'main'}, 'head': {'sha': changed, 'ref': 'release/next'}}}
            checks = route(event, GITHUB_EVENT_NAME='pull_request', GITHUB_REF='refs/pull/1/merge')
            self.assertEqual({name for name in ('tv','installer','setup','android','preview') if checks[name] == 'true'}, {'setup'})
            full = route(event, GITHUB_EVENT_NAME='pull_request', GITHUB_REF='refs/pull/1/merge', CI_FULL_SUITE='true')
            self.assertTrue(all(full[name] == 'true' for name in ('tv','installer','setup','android','preview')))

    def test_draft_branch_build_requires_explicit_same_repository_branch_dispatch(self):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT/'scripts/ci-scope.py')
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        plan = {'version': '1.1.0', 'acceptance': ''}
        event = {'inputs': {'test_build': True}, 'repository': {'full_name': 'owner/repo'}}
        branch = 'refs/heads/codex/rc-fix'
        with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo'}):
            self.assertTrue(scope.build_installers(event, 'workflow_dispatch', branch, plan, '1.1.0', '1.0.3', True))
            for kind, ref, payload in (
                ('push', branch, event), ('pull_request', branch, event),
                ('workflow_dispatch', 'refs/tags/v1.1.0', event),
                ('workflow_dispatch', 'refs/pull/1/head', event),
                ('workflow_dispatch', 'refs/heads/', event),
                ('workflow_dispatch', 'refs/heads/main', event),
                ('workflow_dispatch', branch, {'repository': event['repository']}),
                ('workflow_dispatch', branch, {'inputs': {'test_build': 'false'}, 'repository': event['repository']}),
                ('workflow_dispatch', branch, {'inputs': {'test_build': True}, 'repository': {'full_name': 'other/repo'}}),
                ('workflow_dispatch', branch, {'inputs': {'test_build': True}}),
            ):
                with self.subTest(kind=kind, ref=ref, payload=payload):
                    self.assertFalse(scope.build_installers(payload, kind, ref, plan, '1.1.0', '1.0.3', True))

    def test_event_diff_handles_documentation_renames_and_full_release_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-b', 'main')
            git('config', 'user.name', 'CI test')
            git('config', 'user.email', 'ci@example.invalid')
            (root / 'README.md').write_text('before')
            git('add', '.'); git('commit', '-m', 'base')
            base = git('rev-parse', 'HEAD')
            (root / 'README.md').write_text('after')
            git('commit', '-am', 'docs')
            docs = git('rev-parse', 'HEAD')
            event = root / 'event.json'
            output = root / 'output'
            env = {**os.environ, 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_REF': 'refs/pull/1/merge',
                   'GITHUB_EVENT_PATH': str(event), 'GITHUB_OUTPUT': str(output), 'CI_FULL_SUITE': 'false'}
            def route(head, full=False):
                event.write_text(json.dumps({'pull_request': {'base': {'sha': base}, 'head': {'sha': head}}}))
                subprocess.check_output(['python3', str(ROOT / 'scripts/ci-scope.py')], cwd=root,
                                        env={**env, 'CI_FULL_SUITE': str(full).lower()})
                return dict(line.split('=') for line in output.read_text().splitlines())
            self.assertEqual(route(docs)['setup'], 'true', 'README changes must run release metadata validation')
            full = route(docs, full=True)
            self.assertTrue(all(full[name] == 'true'
                                for name in ('tv', 'installer', 'android', 'setup', 'preview')))
            (root / 'android').mkdir()
            git('mv', 'README.md', 'android/stage.py')
            git('commit', '-m', 'move doc to runtime code')
            result = route(git('rev-parse', 'HEAD'))
            self.assertEqual(result['android'], 'true')
            self.assertEqual(result['tv'], 'false')

    def test_routes_changes_and_shared_dependencies(self):
        path = ROOT / 'scripts/ci-scope.py'
        self.assertTrue(path.exists(), 'Component routing is missing')
        spec = importlib.util.spec_from_file_location('ci_scope', path)
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        cases = [
            (['README.md', 'docs/INSTALL.md', 'android/README.md'], {'setup'}),
            (['docs/INSTALL.md', 'android/README.md'], set()),
            (['launcher/app.js'], {'tv', 'installer', 'setup', 'preview'}),
            (['native/service/service.js'], {'tv', 'installer', 'setup'}),
            (['root-edition/ui/main.js'], {'tv', 'installer', 'setup', 'preview'}),
            (['root-edition/preview.py'], {'tv', 'installer', 'setup', 'preview'}),
            (['cytv/transport.py'], {'installer', 'android', 'setup'}),
            (['cytv/desktop.py'], {'installer'}),
            (['android/app/src/main/AndroidManifest.xml'], {'android'}),
            (['preview/settings.html'], {'preview'}),
            (['preview/bridge.js'], {'preview'}),
            (['tests/preview-bridge.cjs'], {'preview'}),
            (['scripts/ci-scope.py'], set(scope.COMPONENTS)),
            (['new-component/main.py'], set(scope.COMPONENTS)),
            (['requirements.txt'], set(scope.COMPONENTS)),
            (['.gitignore'], set(scope.COMPONENTS)),
            (['docs/README.md', 'android/stage.py'], {'android'}),
        ]
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assertEqual(scope.components(paths), expected)

    def test_only_final_new_release_is_a_candidate(self):
        path = ROOT / 'scripts/ci-scope.py'
        self.assertTrue(path.exists(), 'Candidate routing is missing')
        spec = importlib.util.spec_from_file_location('ci_scope', path)
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        self.assertTrue(scope.is_candidate({'version': '1.0.2', 'acceptance': 'TV passed'}, '1.0.2', '1.0.1'))
        for plan, version, previous in [
            ({'version': None, 'acceptance': ''}, '1.0.1', '1.0.1'),
            ({'version': '1.0.2', 'acceptance': ''}, '1.0.2', '1.0.1'),
            ({'version': '1.0.2', 'acceptance': 'TV passed'}, '1.0.3', '1.0.1'),
            ({'version': '1.0.2', 'acceptance': 'TV passed'}, '1.0.2', '1.0.2'),
            *[({'version': '1.0.2', 'acceptance': value}, '1.0.2', '1.0.1')
              for value in (None, False, 0, {}, [])],
        ]:
            with self.subTest(plan=plan, version=version):
                self.assertFalse(scope.is_candidate(plan, version, previous))
