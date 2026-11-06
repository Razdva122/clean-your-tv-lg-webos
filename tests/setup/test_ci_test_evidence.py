"""Evidence must select only missing test work, never manufacture coverage."""
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'scripts/ci-test-evidence.py'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(HELPER.exists(), 'PR successes need authenticated cross-workflow evidence')
        self.m = runpy.run_path(str(HELPER))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.root / 'code.py').write_text('version = 1\n')
        (self.root / 'README.md').write_text('first\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'initial')
        self.head = self.git('rev-parse', 'HEAD')
        self.ctx = self.context('tv setup installer')
        self.run = dict(id=10, run_attempt=1, status='completed', conclusion='success',
                        event='pull_request', head_branch='feature', head_sha=self.head,
                        path='.github/workflows/tests.yml', head_repository={'full_name': 'owner/repo'},
                        repository={'full_name': 'owner/repo'})
        self.job = dict(id=100, name='runtime (ubuntu-latest, 1)', status='completed',
                        conclusion='success', run_id=10, run_attempt=1)
        receipt = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        self.raw = self.archive(receipt)
        self.artifact = dict(id=50, name=self.ctx['artifact'], size_in_bytes=len(self.raw),
                             digest='sha256:' + hashlib.sha256(self.raw).hexdigest(), expired=False,
                             workflow_run={'id': 10, 'head_sha': self.head})
        self.responses = {
            'actions/artifacts?per_page=100': {'artifacts': [self.artifact]},
            'actions/runs/10': self.run,
            'actions/workflows/tests.yml/runs?branch=feature&event=pull_request&per_page=100': {'workflow_runs': [self.run]},
            'actions/runs/10/attempts/1/jobs?per_page=100': {'jobs': [self.job], 'total_count': 1},
            'commits/' + self.head: {'sha': self.head, 'parents': [], 'commit': {'tree': {'sha': self.ctx['tree']}}},
            'git/trees/' + self.ctx['tree'] + '?recursive=1': self.tree(),
        }

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def context(self, units, kind='runtime', shard='1/4', environment=None):
        return self.m['context'](kind, 'ubuntu-latest', shard, units,
                                 {'day': '2026-11-06', 'python': '3.12'} if environment is None else environment,
                                 root=self.root)

    def tree(self):
        entries = []
        for line in self.git('ls-tree', '-r', 'HEAD').splitlines():
            identity, path = line.split('\t')
            mode, kind, sha = identity.split()
            entries.append(dict(path=path, mode=mode, type=kind, sha=sha))
        return {'truncated': False, 'tree': entries}

    @staticmethod
    def archive(receipt):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as out:
            out.writestr('receipt.json', json.dumps(receipt))
        return data.getvalue()

    def api(self, path, binary=False):
        if binary:
            self.assertEqual(path, 'actions/artifacts/50/zip')
            return self.raw
        if path.startswith('actions/artifacts?'):
            query = parse_qs(path.split('?', 1)[1])
            self.assertEqual(query['per_page'], ['100'])
            return {'artifacts': [copy.deepcopy(self.artifact)] if query['name'] == [self.artifact['name']] else []}
        return copy.deepcopy(self.responses[path])

    def missing(self, ctx=None):
        return self.m['select_missing'](ctx or self.ctx, 'owner/repo', 20, self.api)['missing']

    def test_matching_partial_coverage_runs_only_missing_units(self):
        self.assertEqual(self.missing(self.context('tv setup installer android preview')), ['android', 'preview'])

    def test_alias_and_nonprimary_shard_do_not_claim_nonexecuted_units(self):
        self.assertEqual(self.context('tv ui tv-runtime android preview setup', shard='2/4')['units'], ['setup', 'tv-runtime'])
        self.assertEqual(self.context('ui android preview', shard='2/4')['units'], [])

    def test_metadata_only_change_preserves_runtime_but_invalidates_setup(self):
        (self.root / 'README.md').write_text('second\n')
        self.git('commit', '-qam', 'metadata')
        self.assertEqual(self.missing(self.context('tv setup installer')), ['setup'])

    def test_changed_source_or_environment_runs_selected_work(self):
        self.assertEqual(self.missing(self.context('tv setup installer', environment={'day': '2026-11-07'})), ['installer', 'setup', 'tv-runtime', 'ui'])
        (self.root / 'code.py').write_text('version = 2\n')
        self.git('commit', '-qam', 'source')
        self.assertEqual(self.missing(self.context('tv setup installer')), ['installer', 'setup', 'tv-runtime', 'ui'])

    def test_untrusted_run_latest_attempt_job_and_artifact_never_supply_coverage(self):
        damages = [
            ('run', 'status', 'in_progress'), ('run', 'conclusion', 'failure'),
            ('run', 'event', 'push'), ('run', 'path', '.github/workflows/other.yml'),
            ('run', 'head_repository', {'full_name': 'fork/repo'}),
            ('run', 'repository', {'full_name': 'other/repo'}),
            ('run', 'run_attempt', 2), ('run', 'head_sha', 'b' * 40),
            ('job', 'id', 101), ('job', 'name', 'runtime (macos-latest, 1)'),
            ('job', 'status', 'in_progress'), ('job', 'conclusion', 'failure'),
            ('artifact', 'expired', True), ('artifact', 'size_in_bytes', 999),
            ('artifact', 'digest', 'sha256:' + '0' * 64),
            ('artifact', 'workflow_run', {'id': 10, 'head_sha': 'b' * 40}),
        ]
        for target, field, value in damages:
            with self.subTest(target=target, field=field):
                obj = getattr(self, target)
                old = obj[field]
                obj[field] = value
                self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])
                obj[field] = old
        latest = self.responses['actions/workflows/tests.yml/runs?branch=feature&event=pull_request&per_page=100']['workflow_runs']
        for state in ('failure', None):
            latest.append({**self.run, 'id': 11, 'conclusion': state, 'status': 'completed' if state else 'in_progress'})
            self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])
            latest.pop()

    def test_tree_is_authenticated_even_when_receipt_claims_matching_keys(self):
        tree = self.responses['git/trees/' + self.ctx['tree'] + '?recursive=1']
        for mutation in ('truncated', 'source'):
            saved = copy.deepcopy(tree)
            if mutation == 'truncated':
                tree['truncated'] = True
            else:
                tree['tree'][1]['sha'] = 'f' * 40
            self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])
            tree.clear()
            tree.update(saved)

    def test_only_real_pr_merge_checkout_can_differ_from_run_head(self):
        receipt = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        merge = 'c' * 40
        receipt['checkout'] = merge
        self.raw = self.archive(receipt)
        self.artifact.update(size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        self.responses['commits/' + merge] = {'sha': merge, 'parents': [{'sha': 'd' * 40}, {'sha': self.head}], 'commit': {'tree': {'sha': self.ctx['tree']}}}
        self.assertEqual(self.missing(), [])
        self.responses['commits/' + merge]['parents'].reverse()
        self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])

    def test_wrong_os_shard_or_kind_never_reuses(self):
        for changes in ({'os': 'macos-latest'}, {'shard': '2/4'}, {'kind': 'browser'}):
            ctx = {**self.ctx, **changes}
            self.assertEqual(self.missing(ctx), ['installer', 'setup', 'tv-runtime', 'ui'])

    def test_browser_core_does_not_skip_missing_full_theme_work(self):
        self.ctx = self.context('browser-core', kind='browser')
        self.job['name'] = 'browser'
        self.raw = self.archive(self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100))
        self.artifact.update(name=self.ctx['artifact'], size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.missing(self.context('browser-core browser-themes', kind='browser')), ['browser-themes'])
        self.assertEqual(self.missing(self.context('browser-core', kind='browser', environment={'day': '2026-11-06', 'browser': 'other'})), ['browser-core'])

    def test_optional_python_reuses_only_matching_arm_environment(self):
        self.ctx = self.context('optional-python', kind='optional')
        self.job['name'] = 'optional-python'
        self.raw = self.archive(self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100))
        self.artifact.update(name=self.ctx['artifact'], size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.missing(), [])
        self.assertEqual(self.missing(self.context('optional-python', kind='optional', environment={'arm': 'different'})), ['optional-python'])

    def test_unknown_fields_units_and_nonregular_zip_members_are_misses(self):
        receipt = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        bad = []
        for changed in ({**receipt, 'schema': True}, {**receipt, 'extra': 'untrusted'},
                        {**receipt, 'keys': {'unknown': 'a' * 64}},
                        {**receipt, 'keys': {'ui': 'a' * 64}}):
            bad.append(self.archive(changed))
        for mode in (0o120777, 0o040755):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive:
                entry = zipfile.ZipInfo('receipt.json')
                entry.create_system = 3
                entry.external_attr = mode << 16
                archive.writestr(entry, json.dumps(receipt))
            bad.append(stream.getvalue())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('receipt.json', json.dumps(receipt))
            archive.writestr('unexpected.txt', 'ignored?')
        bad.append(stream.getvalue())
        for raw in bad:
            self.raw = raw
            self.artifact.update(size_in_bytes=len(raw), digest='sha256:' + hashlib.sha256(raw).hexdigest())
            self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])

    def test_zip_and_json_are_strict_bounded_data(self):
        valid = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        invalid = [b'not zip', b'x' * 131073]
        for name, payload in [('../receipt.json', json.dumps(valid)), ('receipt.json', '{"schema":1,"schema":1}'), ('receipt.json', '{"schema":NaN}'), ('receipt.json', 'x' * 65537)]:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as out:
                out.writestr(name, payload)
            invalid.append(stream.getvalue())
        for raw in invalid:
            with self.subTest(raw_size=len(raw)):
                self.raw = raw
                self.artifact.update(size_in_bytes=len(raw), digest='sha256:' + hashlib.sha256(raw).hexdigest())
                self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])

    def test_primary_runtime_binds_actual_system_chrome_and_unknown_is_not_evidence(self):
        version = ['130.0.0.0']
        unavailable = [False]
        def process(*args):
            if args[:2] == ('node', '-e') and 'chromium.launch' in args[2]:
                if unavailable[0]:
                    raise subprocess.CalledProcessError(1, args)
                return version[0]
            return 'fixture'
        with patch.dict(self.m['environment'].__globals__, {'command': process}), patch.dict('os.environ', {'BROWSER_CHANNEL': 'chrome'}):
            before = self.m['environment']('runtime')
            self.assertEqual(before.get('browser'), '130.0.0.0')
            self.assertEqual(before['browser_channel'], 'chrome')
            self.ctx = self.context('installer preview', environment=before)
            self.raw = self.archive(self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100))
            self.artifact.update(name=self.ctx['artifact'], size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
            self.assertEqual(self.missing(), [])
            version[0] = '131.0.0.0'
            after = self.m['environment']('runtime')
            self.assertEqual(self.missing(self.context('installer preview', environment=after)), ['installer', 'preview'])
            version[0] = '130.0.0.0'
            with patch.dict('os.environ', {'BROWSER_CHANNEL': 'chrome-beta'}):
                other_channel = self.m['environment']('runtime')
            self.assertEqual(self.missing(self.context('installer preview', environment=other_channel)), ['installer', 'preview'])
            self.assertNotIn('browser', self.m['environment']('runtime', '2/4'))
            unavailable[0] = True
            unknown = self.m['environment']('runtime')
            self.assertIsNone(unknown['browser'])
            ctx = self.context('installer preview', environment=unknown)
            self.assertEqual(self.missing(ctx), ['installer', 'preview'])
            with self.assertRaisesRegex(ValueError, 'browser'):
                self.m['make_receipt'](ctx, 'owner/repo', 20, 1, 200)

    def test_api_process_rejects_oversized_download_and_failure(self):
        executable = self.root / 'gh'
        executable.write_text('#!/usr/bin/env python3\nimport sys\nsys.stdout.buffer.write(b"x" * 131073)\n')
        executable.chmod(0o755)
        with patch.dict('os.environ', {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}):
            api = self.m['github_api']('owner/repo')
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                api('actions/artifacts/50/zip', binary=True)
            executable.write_text('#!/usr/bin/env python3\nraise SystemExit(1)\n')
            with self.assertRaisesRegex(ValueError, 'API failed'):
                api('actions/artifacts/50/zip', binary=True)

    def test_cli_records_only_fresh_work_and_fork_or_rerun_executes(self):
        directory = self.root / 'evidence'
        event = self.root / 'event.json'
        event.write_text(json.dumps({'pull_request': {'head': {'repo': {'full_name': 'owner/repo'}}}}))
        output = self.root / 'output'
        env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_RUN_ID': '20', 'GITHUB_RUN_ATTEMPT': '1',
               'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_EVENT_PATH': str(event), 'GITHUB_OUTPUT': str(output)}
        self.responses['actions/runs/20/attempts/1/jobs?per_page=100'] = {'total_count': 1, 'jobs': [
            {'id': 200, 'name': 'runtime (ubuntu-latest, 1)', 'status': 'in_progress'}]}
        real_context = self.m['context']
        globals_ = self.m['main'].__globals__
        with redirect_stdout(io.StringIO()), patch.dict('os.environ', env), patch.dict(globals_, {
                'github_api': lambda _repo: self.api,
                'environment': lambda *_args: {'day': '2026-11-06', 'python': '3.12'},
                'context': lambda *args: real_context(*args, root=self.root)}):
            argv = ['ci-test-evidence.py', 'plan', '--directory', str(directory), '--kind', 'runtime',
                    '--os', 'ubuntu-latest', '--units', 'tv setup installer preview']
            with patch('sys.argv', argv):
                self.m['main']()
            self.assertIn('missing=preview\n', output.read_text())
            with patch('sys.argv', ['ci-test-evidence.py', 'record', '--directory', str(directory)]):
                self.m['main']()
            receipt = json.loads((directory / 'receipt.json').read_text())
            self.assertEqual(set(receipt['keys']), {'preview'})
            event.write_text(json.dumps({'pull_request': {'head': {'repo': {'full_name': 'fork/repo'}}}}))
            output.write_text('')
            with patch('sys.argv', argv):
                self.m['main']()
            self.assertIn('missing=installer preview setup tv-runtime ui\n', output.read_text())
            with patch('sys.argv', ['ci-test-evidence.py', 'record', '--directory', str(directory)]):
                with self.assertRaisesRegex(ValueError, 'same-repository'):
                    self.m['main']()
            event.write_text(json.dumps({'pull_request': {'head': {'repo': {'full_name': 'owner/repo'}}}}))
            with patch.dict('os.environ', {'GITHUB_RUN_ATTEMPT': '2'}), patch('sys.argv', argv):
                output.write_text('')
                self.m['main']()
            self.assertIn('missing=installer preview setup tv-runtime ui\n', output.read_text())

    def test_api_outage_runs_tests_and_record_contains_only_fresh_units(self):
        def unavailable(*_args, **_kwargs):
            raise OSError('offline')
        self.assertEqual(self.m['select_missing'](self.ctx, 'owner/repo', 20, unavailable)['missing'], ['installer', 'setup', 'tv-runtime', 'ui'])
        selected = self.m['select_missing'](self.context('tv setup installer preview'), 'owner/repo', 20, self.api)
        record = self.m['make_receipt']({**self.context('tv setup installer preview'), 'units': selected['missing']}, 'owner/repo', 20, 1, 200)
        self.assertEqual(set(record['keys']), {'preview'})


if __name__ == '__main__':
    unittest.main()
