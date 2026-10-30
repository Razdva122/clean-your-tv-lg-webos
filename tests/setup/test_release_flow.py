from unittest.mock import patch
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReleaseFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'scripts/release-flow.py'
        if path.exists():
            spec = importlib.util.spec_from_file_location('release_flow', path)
            cls.flow = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.flow)
        else:
            cls.flow = None

    def setUp(self):
        self.assertIsNotNone(self.flow, 'release-flow.py must implement the release policy')
        self.plan = {'schema': 1, 'version': '1.0.2', 'changes': [
            {'pr': 25, 'issues': [8], 'summary': 'Fix focus'}], 'excluded': [],
            'acceptance': 'TV model X: focus, emergency release and rollback passed.'}
        self.prs = [{'number': 25, 'merged_at': '2026-10-25',
                     'merge_commit_sha': 'a' * 40, 'base': {'ref': 'release/next'},
                     'head': {'repo': {'full_name': 'owner/repo'}}}]
        self.context = dict(branch='release/next', same_repo=True, final=True,
                            version='1.0.2', previous_version='1.0.1',
                            merged_prs=self.prs, commits={'a' * 40}, notes='Release notes')

    def test_protection_uses_app_bound_checks_without_deprecated_contexts(self):
        names = ['Release policy', 'tests (ubuntu-latest)', 'tests (macos-latest)']
        actual = {'enforce_admins': {'enabled': True},
                  'required_status_checks': {'strict': True, 'checks': [{'context': n, 'app_id': 15368} for n in names]},
                  'allow_force_pushes': {'enabled': False}, 'allow_deletions': {'enabled': False},
                  'required_conversation_resolution': {'enabled': True}, 'required_pull_request_reviews': {}}
        settings = {'allow_merge_commit': True, 'allow_squash_merge': False,
                    'allow_rebase_merge': False, 'delete_branch_on_merge': False}
        with patch.object(self.flow, 'api', side_effect=[{}, settings, {}, actual]) as call:
            self.flow.protect()
            payload = call.call_args_list[2].kwargs['data']['required_status_checks']
            self.assertIn('checks', payload)
            self.assertNotIn('contexts', payload, 'GitHub rejects both contexts and checks in one protection request')

    def test_repository_api_path_has_no_trailing_slash(self):
        with patch.object(self.flow.subprocess, 'check_output', return_value=b'{}') as call:
            self.flow.api('')
            self.assertEqual(call.call_args.args[0][-1], 'repos/' + self.flow.REPO)

    def test_candidate_build_requires_every_platform_job_to_succeed(self):
        self.assertTrue(hasattr(self.flow, 'validate_build_jobs'), 'Complete candidate job validation is required')
        jobs = [{'name': name, 'conclusion': 'success'} for name in self.flow.BUILD_JOBS]
        self.flow.validate_build_jobs(jobs)
        for broken in [jobs[1:], [{**j, 'conclusion': 'skipped'} if j['name'] == 'android' else j for j in jobs]]:
            with self.subTest(jobs=broken), self.assertRaises(ValueError):
                self.flow.validate_build_jobs(broken)

    def test_quick_success_cannot_replace_full_suite_and_browser_evidence(self):
        jobs = [{'name': name, 'conclusion': 'success'} for name in self.flow.BUILD_JOBS]
        for required in ('validation / full-release', 'validation / browser'):
            self.assertIn(required, self.flow.BUILD_JOBS)
            with self.subTest(required=required), self.assertRaises(ValueError):
                self.flow.validate_build_jobs([job for job in jobs if job['name'] != required])

    def test_related_issue_line_ignores_unrelated_mentions(self):
        self.assertEqual(self.flow.related_issues('Discuss #99.\nRelated issues: #8, #9\nOther #12'), {8, 9})

    def test_every_linked_issue_must_be_in_the_committed_plan(self):
        with patch.object(self.flow, 'linked_issues', return_value={8, 9}), \
             patch.object(self.flow, 'api', return_value={'number': 8}):
            with self.assertRaisesRegex(ValueError, 'linked issues'):
                self.flow.validate_issues(self.plan, check_links=True)
            complete = {**self.plan, 'changes': [{**self.plan['changes'][0], 'issues': [8, 9]}]}
            self.flow.validate_issues(complete, check_links=True)
        # Publication retries use the frozen plan, not later description edits.
        with patch.object(self.flow, 'linked_issues', side_effect=AssertionError('mutable scope read')), \
             patch.object(self.flow, 'api', return_value={'number': 8}):
            self.flow.validate_issues(self.plan)

    def test_unversioned_preparation_is_valid(self):
        plan = {**self.plan, 'version': None, 'acceptance': ''}
        self.flow.validate_plan(plan, **{**self.context, 'final': False, 'version': '1.0.1'})

    def test_main_requires_same_repository_release_branch_and_final_version(self):
        for update, plan in [({'branch': 'feature/x'}, self.plan),
                             ({'same_repo': False}, self.plan),
                             ({}, {**self.plan, 'version': None}),
                             ({'version': '1.0.1'}, self.plan),
                             ({'previous_version': '1.0.2'}, self.plan),
                             ({'notes': ''}, self.plan),
                             ({}, {**self.plan, 'acceptance': ''})]:
            with self.subTest(update=update, plan=plan), self.assertRaises(ValueError):
                self.flow.validate_plan(plan, **{**self.context, **update})

    def test_pinned_acceptance_requires_matching_build_attempt(self):
        pin = {'run_id': 42, 'attempt': 2, 'source': 'a' * 40}
        for binding in (None, '42:1', '43:2'):
            with self.subTest(binding=binding), self.assertRaisesRegex(ValueError, 'acceptance'):
                self.flow.validate_plan({**self.plan, 'build': pin, 'acceptance_build': binding}, **self.context)
        self.flow.validate_plan({**self.plan, 'build': pin, 'acceptance_build': '42:2'}, **self.context)


    def test_inventory_requires_all_merged_prs_and_explicit_exclusions(self):
        self.flow.validate_plan(self.plan, **self.context)
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.flow.validate_plan({**self.plan, 'changes': []}, **self.context)
        self.flow.validate_plan({**self.plan, 'changes': [],
                                 'excluded': [{'pr': 25, 'reason': 'Reverted in full'}]}, **self.context)
        for changes in [[self.plan['changes'][0]] * 2,
                        [{**self.plan['changes'][0], 'pr': 99}],
                        [{**self.plan['changes'][0], 'issues': [True]}]]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.flow.validate_plan({**self.plan, 'changes': changes}, **self.context)

    def test_previous_release_prs_are_not_in_new_release_inventory(self):
        old = {**self.prs[0], 'number': 24, 'merge_commit_sha': 'b' * 40}
        self.flow.validate_plan(self.plan, **{**self.context, 'merged_prs': [old] + self.prs})

    def test_notification_targets_deduplicate_issues_and_omit_excluded_prs(self):
        inventory = {'schema': 1, 'tag': 'v1.0.2', 'source_commit': 'c' * 40,
                     'release_pr': 30, 'changes': self.plan['changes'] + [
                         {'pr': 26, 'issues': [8, 9], 'summary': 'Fix tiles'}],
                     'excluded': [{'pr': 27, 'reason': 'Reverted'}]}
        notices = self.flow.notification_bodies(inventory, 'https://github.com/owner/repo/releases/tag/v1.0.2')
        self.assertEqual(set(notices), {8, 9, 25, 26, 30})
        self.assertIn('Fix focus', notices[8])
        self.assertIn('Fix tiles', notices[8])
        self.assertNotIn('Fix focus', notices[9])
        self.assertIn('<!-- shipped:v1.0.2 -->', notices[8])

    def test_retry_updates_bot_comment_and_never_uses_human_marker(self):
        comments = [{'id': 1, 'body': '<!-- shipped:v1.0.2 -->',
                     'user': {'login': 'someone', 'type': 'User'}},
                    {'id': 2, 'body': '<!-- shipped:v1.0.2 -->',
                     'user': {'login': 'github-actions[bot]', 'type': 'Bot'}}]
        self.assertEqual(self.flow.existing_notice(comments, 'v1.0.2'), comments[1])
        self.assertIsNone(self.flow.existing_notice(comments[:1], 'v1.0.2'))

    def test_notice_delivery_retries_only_failed_targets(self):
        self.assertTrue(hasattr(self.flow, 'deliver_notices'), 'Retryable delivery must be testable independently')
        inventory = {'schema': 1, 'tag': 'v1.0.2', 'source_commit': 'c' * 40,
                     'release_pr': 30, 'changes': self.plan['changes'], 'excluded': []}
        comments, failures, writes = {}, {8}, []
        def github(path, *, method='GET', data=None, pages=False):
            target = int(path.split('/')[1])
            if method == 'GET':
                return comments.get(target, [])
            if target in failures:
                raise subprocess.CalledProcessError(1, ['gh', 'api'])
            writes.append(target)
            comments.setdefault(target, []).append({'id': target, 'body': data['body'],
                'user': {'login': 'github-actions[bot]', 'type': 'Bot'}})
            return comments[target][-1]
        with patch.object(self.flow, 'api', side_effect=github):
            with self.assertRaisesRegex(ValueError, '8'):
                self.flow.deliver_notices(inventory, 'https://example.com/release')
            self.assertEqual(set(writes), {25, 30})
            failures.clear()
            self.flow.deliver_notices(inventory, 'https://example.com/release')
            self.assertEqual(sorted(writes), [8, 25, 30])
            self.flow.deliver_notices(inventory, 'https://example.com/release')
            self.assertEqual(sorted(writes), [8, 25, 30])

    def test_legacy_release_skips_notices_and_modern_missing_inventory_fails(self):
        calls = []
        modern = False
        def github(path, **kwargs):
            calls.append((path, kwargs))
            if path.startswith('releases/'):
                return {'assets': [], 'draft': False, 'tag_name': 'v1.0.1'}
            if path.startswith('commits/'):
                return {'sha': 'a' * 40}
            if path.startswith('git/trees/'):
                return {'tree': [{'path': 'release-plan.json'}] if modern else []}
            raise AssertionError(path)
        with patch.object(self.flow, 'api', side_effect=github), \
             patch.object(self.flow.subprocess, 'run') as command:
            self.flow.notify('v1.0.1')
            self.assertIn('--check-only', command.call_args.args[0])
            self.assertFalse(any(kwargs.get('method', 'GET') != 'GET' for _, kwargs in calls))
            modern = True
            with self.assertRaisesRegex(ValueError, 'inventory is missing'):
                self.flow.notify('v1.0.1')
        with patch.object(self.flow, 'api', side_effect=github), \
             patch.object(self.flow.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['node'])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.flow.notify('v1.0.1')

    def test_publication_identity_requires_exact_tag_and_commit(self):
        release = {'draft': False, 'prerelease': False, 'tag_name': 'v1.0.2'}
        inventory = {'schema': 1, 'tag': 'v1.0.2', 'source_commit': 'c' * 40}
        self.flow.validate_publication(release, inventory, {'tag': 'v1.0.2', 'source_commit': 'c' * 40}, 'c' * 40)
        for key, value in [('draft', True), ('prerelease', True), ('tag_name', 'v1.0.3')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.flow.validate_publication({**release, key: value}, inventory,
                                               {'tag': 'v1.0.2', 'source_commit': 'c' * 40}, 'c' * 40)
        with self.assertRaises(ValueError):
            self.flow.validate_publication(release, inventory,
                                           {'tag': 'v1.0.2', 'source_commit': 'd' * 40}, 'c' * 40)


if __name__ == '__main__':
    unittest.main()
