from pathlib import Path
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


flow = module('flow_reuse', 'scripts/release-flow.py')
release = module('assembly_reuse', 'scripts/assemble-release.py')


class CandidateReuse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'CI test')
        self.git('config', 'user.email', 'ci@example.invalid')
        (self.root / 'product').write_text('base')
        (self.root / 'release-plan.json').write_text('{}')
        self.commit('base')
        self.git('checkout', '-b', 'release/next')
        (self.root / 'product').write_text('candidate')
        self.source = self.commit('built source')
        self.run = {'id': 42, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
                    'head_sha': self.source, 'head_branch': 'release/next', 'event': 'workflow_dispatch',
                    'path': '.github/workflows/cytv.yml', 'html_url': 'https://example.invalid/build/42',
                    'head_repository': {'full_name': flow.REPO}}
        self.plan = {'build': {'run_id': 42, 'attempt': 1, 'source': self.source}}
        self.write_plan()
        self.head = self.commit('acceptance record')
        self.jobs = [{'name': name, 'conclusion': 'success'} for name in flow.BUILD_JOBS]

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL).strip()

    def write_plan(self):
        (self.root / 'release-plan.json').write_text(json.dumps(self.plan))

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def api(self, path, **kwargs):
        if path == 'actions/runs/42':
            return self.run
        if path.startswith('actions/runs/42/jobs?'):
            return self.jobs if kwargs.get('pages') else {'jobs': self.jobs}
        raise AssertionError(path)

    def resolve(self):
        self.assertTrue(hasattr(flow, 'resolve_candidate_build'), 'Shared non-polling resolver is required')
        return flow.resolve_candidate_build(self.head, self.root, provider=self.api)

    def test_pin_reuses_trusted_pre_acceptance_build(self):
        self.assertEqual(self.resolve(), self.run)

    def test_wrong_source_fork_workflow_and_incomplete_jobs_are_rejected(self):
        original = self.run.copy()
        for change in ({'head_sha': 'b' * 40}, {'event': 'pull_request'}, {'path': '.github/workflows/evil.yml'},
                       {'head_repository': {'full_name': 'someone/fork'}}, {'conclusion': 'failure'}):
            self.run = {**original, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve()
        self.run = original
        self.jobs.pop()
        with self.assertRaises(ValueError):
            self.resolve()

    def test_source_change_invalidates_pin_before_reuse(self):
        (self.root / 'product').write_text('new code')
        self.head = self.commit('code after acceptance')
        with self.assertRaisesRegex(ValueError, 'inputs'):
            self.resolve()

    def test_running_build_is_pending_without_sleep(self):
        self.assertTrue(hasattr(flow, 'PendingBuild'), 'Pending builds must not be failed or polled')
        self.run['status'] = 'in_progress'
        self.run['conclusion'] = None
        with self.assertRaises(flow.PendingBuild):
            self.resolve()

    def test_publication_accepts_pin_but_still_requires_exact_merge_tree(self):
        self.git('checkout', 'main')
        self.git('merge', '--no-ff', 'release/next', '-m', 'release')
        merged = self.git('rev-parse', 'HEAD')
        release.validate_build_run(self.run, merged, root=self.root)
        (self.root / 'README.md').write_text('unreviewed merge change')
        self.git('add', '.')
        self.git('commit', '--amend', '--no-edit')
        with self.assertRaisesRegex(ValueError, 'tree'):
            release.validate_build_run(self.run, self.git('rev-parse', 'HEAD'), root=self.root)

    def test_policy_completion_refreshes_pending_and_success_without_polling(self):
        pr = {'number': 7, 'state': 'open', 'base': {'ref': 'main'}, 'head': {'sha': self.head}}
        states = []
        def provider(path, **kwargs):
            if path.startswith('pulls?'):
                return [pr]
            if path == 'pulls/7':
                return pr
            if path.startswith('statuses/'):
                states.append(kwargs['data']['state'])
                return {}
            raise AssertionError(path)
        with patch.object(flow, 'api', side_effect=provider), patch.object(flow, 'git'), patch.dict(flow.os.environ, GITHUB_RUN_ID='99'):
            with patch.object(flow, 'check_pr', side_effect=flow.PendingBuild('running')):
                flow.refresh_policy({'workflow_run': self.run})
            self.assertEqual(states, ['pending', 'pending'])
            with patch.object(flow, 'check_pr'):
                flow.refresh_policy({'workflow_run': self.run})
            self.assertEqual(states[-2:], ['pending', 'success'])
            with patch.object(flow, 'check_pr', side_effect=ValueError('invalid inventory')):
                flow.refresh_policy({'pull_request': pr})
            self.assertEqual(states[-2:], ['pending', 'failure'])
            with patch.object(flow, 'check_pr', side_effect=RuntimeError('infrastructure failure')), self.assertRaises(RuntimeError):
                flow.refresh_policy({'pull_request': pr})
            self.assertEqual(states[-1], 'pending')
            prior = states.copy()
            flow.refresh_policy({'workflow_run': {**self.run, 'head_repository': {'full_name': 'someone/fork'}}})
            self.assertEqual(states, prior)


    def test_closed_pr_refresh_does_not_overwrite_shared_sha_gate(self):
        # Commit contexts are shared with any open PR at this same SHA.
        pr = {'number': 7, 'state': 'closed', 'base': {'ref': 'main'}, 'head': {'sha': self.head}}
        with patch.object(flow, 'api', return_value=pr) as api, \
             patch.object(flow, 'git') as git, patch.object(flow, 'check_pr') as check:
            flow.refresh_policy({'pull_request': pr})
        self.assertEqual(api.call_count, 1)
        git.assert_not_called()
        check.assert_not_called()

    def test_workflow_preflight_blocks_only_open_prs(self):
        # Execute the actual privileged preflight, including its closed-event guard.
        import re
        workflow = (ROOT / '.github/workflows/release-policy.yml').read_text()
        script = re.search(r'          script: \|\n((?:            .*\n)+)', workflow)[1]
        script = '\n'.join(line[12:] for line in script.splitlines())
        harness = """
const calls = [];
const context = {repo:{owner:'owner',repo:'repo'},payload:{pull_request:{state:process.argv[1],head:{sha:'a'.repeat(40)},base:{ref:'release/next'}}},serverUrl:'https://github.com',runId:99};
const github = {rest:{repos:{createCommitStatus:async p=>calls.push(p)}}};
await (async()=>{ SCRIPT })();
process.stdout.write(JSON.stringify(calls));
""".replace('SCRIPT', script)
        for state in ('open', 'closed'):
            result = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', harness, state]))
            with self.subTest(state=state):
                if state == 'closed':
                    self.assertEqual(result, [], 'Closed edits must not overwrite an open PR sharing its SHA/context')
                else:
                    self.assertEqual([(v['context'], v['state']) for v in result], [('Integration policy', 'pending')])

    def test_jobs_api_pagination_extracts_jobs_from_object_pages(self):
        raw = json.dumps([{'total_count': 2, 'jobs': [{'name': 'first'}]},
                          {'total_count': 2, 'jobs': [{'name': 'second'}]}]).encode()
        with patch.object(flow.subprocess, 'check_output', return_value=raw):
            self.assertEqual(flow.api('actions/runs/42/jobs', pages=True), [{'name': 'first'}, {'name': 'second'}])
        with patch.object(release.subprocess, 'check_output', return_value=raw):
            self.assertEqual(release.github('actions/runs/42/jobs', pages=True), [{'name': 'first'}, {'name': 'second'}])


    def test_repin_resets_old_acceptance_and_requires_new_binding(self):
        self.plan.update(acceptance='Passed on old bytes', acceptance_build='42:1')
        self.write_plan()
        self.commit('old acceptance')
        self.run['run_attempt'] = 2
        with patch.object(flow, 'api', side_effect=self.api):
            flow.pin_build(42, self.root)
        plan = json.loads((self.root / 'release-plan.json').read_text())
        self.assertEqual(plan['acceptance'], '')
        self.assertNotIn('acceptance_build', plan)

    def test_rerun_after_acceptance_invalidates_selected_attempt(self):
        self.run['run_attempt'] = 2
        with self.assertRaisesRegex(ValueError, 'attempt'):
            self.resolve()


    def test_pin_command_records_only_a_complete_compatible_build(self):
        self.assertTrue(hasattr(flow, 'pin_build'), 'Validated build pin command is required')
        with patch.object(flow, 'api', side_effect=self.api):
            flow.pin_build(42, self.root)
        self.assertEqual(json.loads((self.root / 'release-plan.json').read_text())['build'], self.plan['build'])
        (self.root / 'product').write_text('new code')
        self.commit('unbuilt code')
        with patch.object(flow, 'api', side_effect=self.api), self.assertRaisesRegex(ValueError, 'inputs'):
            flow.pin_build(42, self.root)


    def test_pr_record_replaces_only_generated_block(self):
        self.assertTrue(hasattr(flow, 'replace_record'), 'Idempotent candidate record rendering is required')
        original = 'Human acceptance: observed controls.\n\n' + flow.replace_record('', 'old') + '\nHuman limitation: cold boot untested.\n'
        updated = flow.replace_record(original, 'new')
        self.assertIn('Human acceptance: observed controls.', updated)
        self.assertIn('Human limitation: cold boot untested.', updated)
        self.assertNotIn('\nold\n', updated)
        self.assertEqual(flow.replace_record(updated, 'new'), updated)


if __name__ == '__main__':
    unittest.main()
