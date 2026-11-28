import base64
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('next_candidate_flow', ROOT / 'scripts/release-flow.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


class NextCandidateTests(unittest.TestCase):
    def setUp(self):
        self.main = 'a' * 40
        self.head = 'b' * 40
        self.plan = {'schema': 1, 'version': None, 'changes': [], 'excluded': [], 'acceptance': ''}
        self.versions = {'release': '1.0.3', 'home': '1.3.8', 'helper': '0.6.18',
                         'cytv': '0.2.16', 'root': '0.1.12', 'updater': '0.1.6',
                         'android': '0.1.7-preview', 'android_version_code': 8}
        self.prs = []
        self.ahead = 1
        self.release = {'draft': False, 'prerelease': False, 'tag_name': 'v1.0.3'}
        self.commits = []
        self.refs = []
        self.pr_writes = []

    def api(self, path, *, method='GET', data=None, **kwargs):
        if path.startswith('pulls?'):
            return self.prs
        if path == 'pulls' and method == 'POST':
            self.pr_writes.append((method, data))
            self.prs.append({**data, 'number': 35, 'html_url': 'https://example.com/pull/35'})
            return self.prs[-1]
        if path == 'pulls/35':
            if method == 'PATCH':
                self.pr_writes.append((method, data))
                self.prs[0].update(data)
            return self.prs[0].copy()
        if path.startswith('compare/'):
            return {'ahead_by': self.ahead, 'base_commit': {'sha': self.main},
                    'merge_base_commit': {'sha': self.main}, 'commits': [{'sha': self.head}]}
        if path.startswith('contents/'):
            value = self.plan if path.startswith('contents/release-plan.json') else self.versions
            return {'content': base64.b64encode(json.dumps(value).encode()).decode()}
        if path.startswith('releases/'):
            return self.release
        if path in ('commits/main', 'commits/v1.0.3'):
            return {'sha': self.main, 'commit': {'tree': {'sha': 'c' * 40}}}
        if path == 'commits/release%2Fnext':
            return {'sha': self.head}
        if path == 'git/trees' and method == 'POST':
            self.tree = data
            return {'sha': 'd' * 40}
        if path == 'git/commits' and method == 'POST':
            self.commits.append(data)
            return {'sha': 'e' * 40}
        if path == 'git/refs/heads/release/next' and method == 'PATCH':
            self.refs.append(data)
            self.head = data['sha']
            self.ahead = 1
            self.plan = json.loads(self.tree['tree'][0]['content'])
            return {}
        raise AssertionError((path, method))

    def test_creates_unfrozen_draft_with_real_versions_and_reuses_it(self):
        with patch.object(flow, 'api', side_effect=self.api):
            flow.ensure_candidate()
            flow.ensure_candidate()
        self.assertEqual(len(self.prs), 1)
        pr = self.prs[0]
        self.assertTrue(pr['draft'])
        self.assertEqual((pr['head'], pr['base']), ('release/next', 'main'))
        self.assertIn('1.3.8', pr['body'])
        self.assertIn('0.1.7-preview / 8', pr['body'])
        timing_section = pr['body'].split('## Release timings', 1)[1].split('## Release gates', 1)[0]
        self.assertIn('Project TV window', timing_section)
        self.assertIn('Candidate artifact ready', timing_section)
        self.assertIn('Artifact audit complete', timing_section)
        self.assertIn('Device window opened', timing_section)
        self.assertIn('Device checks started', timing_section)
        self.assertIn(timing_section, flow.replace_record(pr['body'], 'Updated build'))
        self.assertIn('TBD', pr['body'])
        self.assertIn('not', pr['body'].lower())

    def test_does_not_create_pr_without_changes(self):
        self.ahead = 0
        with patch.object(flow, 'api', side_effect=self.api):
            flow.ensure_candidate()
        self.assertEqual(self.prs, [])

    def test_maintenance_creates_one_draft_only_when_next_is_ahead(self):
        self.ahead = 0
        with patch.object(flow, 'api', side_effect=self.api), \
             patch.object(flow, 'git', return_value=self.head), \
             patch.object(flow, 'candidate_record', return_value=('1.0.4', 'Recorded acceptance: Passed')):
            flow.maintain_candidate(automatic=True)
            self.assertEqual(self.pr_writes, [])
            self.ahead = 2
            flow.maintain_candidate(automatic=True)
        self.assertEqual([method for method, _ in self.pr_writes], ['POST'])
        self.assertTrue(self.prs[0]['draft'])
        self.assertEqual(self.prs[0]['title'], 'v1.0.4')
        self.assertIn('Recorded acceptance: Passed', self.prs[0]['body'])
        self.assertNotIn('No new TV acceptance claimed', self.prs[0]['body'])

    def test_duplicate_candidates_fail_without_writes(self):
        self.prs = [{'number': 35}, {'number': 36}]
        with patch.object(flow, 'api', side_effect=self.api), \
             patch.object(flow, 'git', return_value=self.head), \
             self.assertRaisesRegex(ValueError, 'multiple open release candidates'):
            flow.maintain_candidate(automatic=True)
        self.assertEqual(self.pr_writes, [])

    def test_superseded_push_is_logged_while_manual_sync_is_strict(self):
        older = 'f' * 40
        with patch.object(flow, 'api', side_effect=self.api), \
             patch.object(flow, 'git', return_value=older), \
             patch.object(sys, 'argv', ['release-flow.py', 'maintain-candidate']):
            with patch.dict(flow.os.environ, GITHUB_EVENT_NAME='push'), redirect_stdout(io.StringIO()) as output:
                flow.main()
            self.assertIn('superseded', output.getvalue().lower())
            self.assertIn(older, output.getvalue())
            self.assertIn(self.head, output.getvalue())
            with patch.dict(flow.os.environ, GITHUB_EVENT_NAME='workflow_dispatch'), \
                 self.assertRaisesRegex(ValueError, 'current release/next'):
                flow.main()
            with self.assertRaisesRegex(ValueError, 'current release/next'):
                flow.sync_record()
        self.assertEqual(self.pr_writes, [])

    def test_manual_sync_requires_an_open_candidate(self):
        with patch.object(flow, 'api', side_effect=self.api), \
             patch.object(flow, 'git', return_value=self.head), \
             self.assertRaisesRegex(ValueError, 'exactly one open release candidate'):
            flow.sync_record()
        self.assertEqual(self.pr_writes, [])

    def test_listing_api_error_fails_without_writes(self):
        failure = subprocess.CalledProcessError(1, ['gh', 'api'])
        with patch.object(flow, 'git', return_value=self.head), \
             patch.object(sys, 'argv', ['release-flow.py', 'maintain-candidate']), \
             patch.dict(flow.os.environ, GITHUB_EVENT_NAME='push'), \
             patch.object(flow.subprocess, 'check_output',
                          side_effect=[json.dumps({'sha': self.head}).encode(), failure]) as gh:
            with self.assertRaises(subprocess.CalledProcessError):
                flow.main()
        self.assertEqual([call.args[0][3] for call in gh.call_args_list], ['GET', 'GET'])

    def test_verified_publication_resets_plan_on_main_and_opens_next_draft(self):
        self.ahead = 0
        self.plan = {**self.plan, 'version': '1.0.3', 'acceptance': 'Previous acceptance'}
        with patch.object(flow, 'api', side_effect=self.api), patch.object(flow.subprocess, 'run') as verify:
            flow.start_cycle('v1.0.3')
        self.assertIn('--check-only', verify.call_args.args[0])
        self.assertEqual(self.commits[0]['parents'], [self.main])
        self.assertEqual(self.refs, [{'sha': 'e' * 40, 'force': False}])
        self.assertEqual(self.plan, {'schema': 1, 'version': None, 'changes': [], 'excluded': [], 'acceptance': ''})
        self.assertTrue(self.prs[0]['draft'])

    def test_publication_failure_never_changes_branch_or_opens_pr(self):
        for release in ({**self.release, 'draft': True}, {**self.release, 'prerelease': True}):
            self.release = release
            with patch.object(flow, 'api', side_effect=self.api), self.assertRaises(ValueError):
                flow.start_cycle('v1.0.3')
        self.assertEqual(self.refs, [])
        self.assertEqual(self.prs, [])

    def test_does_not_erase_work_already_in_next_cycle(self):
        self.plan['changes'] = [{'pr': 36, 'issues': [], 'summary': 'New work'}]
        with patch.object(flow, 'api', side_effect=self.api), patch.object(flow.subprocess, 'run'):
            flow.start_cycle('v1.0.3')
        self.assertEqual(self.refs, [])
        self.assertEqual(self.plan['changes'][0]['pr'], 36)
        self.assertEqual(len(self.prs), 1)

    def test_failed_feed_verification_never_resets_branch(self):
        with patch.object(flow, 'api', side_effect=self.api), \
             patch.object(flow.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['node'])), \
             self.assertRaises(subprocess.CalledProcessError):
            flow.start_cycle('v1.0.3')
        self.assertEqual(self.refs, [])

    def test_old_published_tag_cannot_reset_current_main(self):
        def github(path, **kwargs):
            return {'sha': 'f' * 40} if path == 'commits/v1.0.3' else self.api(path, **kwargs)
        with patch.object(flow, 'api', side_effect=github), self.assertRaises(ValueError):
            flow.start_cycle('v1.0.3')
        self.assertEqual(self.refs, [])
        self.assertEqual(self.prs, [])

    def test_concurrent_branch_change_rejects_reset_without_opening_pr(self):
        self.ahead = 0
        def github(path, **kwargs):
            if path == 'git/refs/heads/release/next':
                raise subprocess.CalledProcessError(1, ['gh', 'api'])
            return self.api(path, **kwargs)
        with patch.object(flow, 'api', side_effect=github), patch.object(flow.subprocess, 'run'), \
             self.assertRaises(subprocess.CalledProcessError):
            flow.start_cycle('v1.0.3')
        self.assertEqual(self.refs, [])
        self.assertEqual(self.prs, [])


if __name__ == '__main__':
    unittest.main()
