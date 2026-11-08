"""Evidence must select only missing test work, never manufacture coverage."""
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
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

    def test_lookup_reads_each_json_endpoint_once_and_does_not_cache_across_plans(self):
        calls = []
        def counted(path, binary=False):
            calls.append((path, binary))
            return self.api(path, binary)
        self.assertEqual(self.m['select_missing'](self.ctx, 'owner/repo', 20, counted)['missing'], [])
        self.assertEqual(calls.count(('actions/runs/10', False)), 1)
        self.run['conclusion'] = 'failure'
        self.assertEqual(self.m['select_missing'](self.ctx, 'owner/repo', 20, counted)['missing'],
                         ['installer', 'setup', 'tv-runtime', 'ui'])
        self.assertEqual(calls.count(('actions/runs/10', False)), 2)

    def test_nonmatching_receipt_keys_skip_provenance_requests(self):
        receipt = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        receipt['keys'] = {unit: '0' * 64 for unit in receipt['keys']}
        self.raw = self.archive(receipt)
        self.artifact.update(size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        calls = []
        def counted(path, binary=False):
            calls.append(path)
            return self.api(path, binary)
        result = self.m['select_missing'](self.ctx, 'owner/repo', 20, counted)
        self.assertEqual(result['missing'], ['installer', 'setup', 'tv-runtime', 'ui'])
        self.assertEqual(len(calls), 2)  # Listing and bounded, digest-checked receipt only.

    def write_commit(self, path, content='first\n'):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self.git('add', path)
        self.git('commit', '-qm', 'change ' + path)
        return target

    def all_keys(self):
        result = {}
        for shard in ('1/4', '2/4', '3/4', '4/4'):
            ctx = self.context('ui tv-runtime setup installer android preview', shard=shard)
            result.update({(unit, shard): key for unit, key in ctx['keys'].items()})
        for kind, units in (('browser', 'browser-core browser-themes'), ('optional', 'optional-python')):
            result.update({(unit, '1/4'): key for unit, key in self.context(units, kind=kind)['keys'].items()})
        return result

    def test_git_test_leaf_mutations_invalidate_owning_families_across_all_shards(self):
        # Expectations come from executed test groups and cross-family fixture imports.
        cases = [
            ('tests/cytv/test_long_ssh_commands.py', {'installer', 'setup'}),
            ('tests/cytv/test_operations.py', {'installer', 'android', 'browser-core', 'setup'}),
            ('tests/cytv/test_desktop_recovery.py', {'installer', 'android', 'browser-core', 'setup'}),
            ('tests/cytv/test_no_root_integration.py', {'installer', 'android', 'browser-core', 'setup'}),
            ('tests/cytv/test_no_root_observer.py', {'installer', 'android', 'browser-core', 'setup'}),
            ('tests/cytv/clean_removal_fixture.py', {'installer', 'android', 'browser-core', 'setup'}),
            ('tests/cytv/test_python_runtime.py', {'installer', 'optional-python', 'setup'}),
            ('root-edition/tests/test_installation.py', {'tv-runtime', 'installer', 'setup'}),
            ('tests/system_updates/test_core.py', {'tv-runtime', 'installer', 'setup'}),
            ('homebrew/tests/runtime.cjs', {'installer', 'setup'}),
            ('homebrew/tests/test_payload.py', {'installer', 'setup'}),
            ('android/tests/test_bridge.py', {'android', 'browser-core', 'setup'}),
            ('android/tests/auto-recovery-journey.cjs', {'android', 'browser-core', 'setup'}),
            ('tests/updates/feed.cjs', {'tv-runtime', 'setup'}),
            ('tests/apps/inventory-fallback.cjs', {'tv-runtime', 'setup'}),
            ('tests/i18n/coverage.cjs', {'tv-runtime', 'setup'}),
            ('tests/showcase/registry.cjs', {'preview', 'setup'}),
            ('tests/preview-bridge.cjs', {'preview', 'setup'}),
            ('tests/test_preview.py', {'preview', 'setup'}),
        ]
        for path, expected in cases:
            with self.subTest(path=path):
                self.git('reset', '--hard', self.head)
                before = self.all_keys()
                target = self.write_commit(path)
                added = self.all_keys()
                self.assertEqual({key for key in before if before[key] != added[key]},
                                 {key for key in before if key[0] in expected})
                self.write_commit(path, 'second\n')
                edited = self.all_keys()
                self.assertEqual({key for key in added if added[key] != edited[key]},
                                 {key for key in before if key[0] in expected})
                target.unlink()
                self.git('add', path)
                self.git('commit', '-qm', 'delete test')
                deleted = self.all_keys()
                self.assertEqual({key for key in edited if edited[key] != deleted[key]},
                                 {key for key in before if key[0] in expected})

    def test_unknown_shared_policy_product_and_dependency_mutations_invalidate_every_unit(self):
        paths = ('new/product.py', 'scripts/ci-test-evidence.py', 'scripts/test.sh',
                 '.github/workflows/tests.yml', 'package-lock.json', 'scripts/build-requirements.txt',
                 'tests/setup/test_ci_test_evidence.py', 'tests/setup/test_release_inputs.py',
                 'tests/cytv/__init__.py', 'tests/cytv/helper.py', 'tests/cytv/fixtures/input.py',
                 'root-edition/tests/install_fixture.py', 'android/tests/recovery_events.py',
                 'tests/themes/presentation.cjs', 'tests/showcase/fixture.cjs',
                 'tests/apps/ui.cjs', 'tests/i18n/browser.cjs')
        for path in paths:
            with self.subTest(path=path):
                before = self.all_keys()
                self.write_commit(path)
                after = self.all_keys()
                self.assertTrue(all(before[key] != after[key] for key in before), path)

    def test_nonregular_test_leaf_is_global_but_regular_executable_mode_stays_scoped(self):
        path = 'tests/cytv/test_long_ssh_commands.py'
        target = self.write_commit(path)
        before = self.all_keys()
        target.chmod(0o755)
        self.git('add', path)
        self.git('commit', '-qm', 'executable test')
        after = self.all_keys()
        self.assertEqual({key[0] for key in before if before[key] != after[key]}, {'setup', 'installer'})
        target.unlink()
        target.symlink_to('../../code.py')
        self.git('add', path)
        self.git('commit', '-qm', 'nonregular test')
        nonregular = self.all_keys()
        self.assertTrue(all(after[key] != nonregular[key] for key in after))

    def test_partial_receipt_remains_discoverable_after_unrelated_source_changes(self):
        self.write_commit('tests/cytv/test_long_ssh_commands.py')
        consumer = self.context('tv setup installer android preview')
        self.assertEqual(self.missing(consumer), ['android', 'installer', 'setup'])
        self.assertEqual(set(self.m['select_missing'](consumer, 'owner/repo', 20, self.api)['reused']),
                         {'ui', 'tv-runtime'})
        # A forged projected key must still be recomputed from the producer tree.
        forged = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        forged['keys']['installer'] = consumer['keys']['installer']
        self.raw = self.archive(forged)
        self.artifact.update(size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.missing(consumer), ['android', 'installer', 'setup'])

    def test_old_schema_cannot_bootstrap_new_policy_receipts(self):
        receipt = self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100)
        receipt['schema'] = 1
        self.raw = self.archive(receipt)
        self.artifact.update(size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.missing(), ['installer', 'setup', 'tv-runtime', 'ui'])

    def candidate_producer(self, kind='runtime', platform='ubuntu-latest', units='tv setup installer'):
        self.ctx = self.m['context'](kind, platform, '1/4', units,
                                    {'day': '2026-11-06', 'python': '3.12'}, root=self.root)
        self.run.update(event='workflow_dispatch', head_branch='release/next',
                        path='.github/workflows/cytv.yml', conclusion='failure')
        names = {'runtime': 'validation / runtime (ubuntu-latest, 1)',
                 'browser': 'validation / browser', 'optional': 'validation / optional-python',
                 'desktop': 'build (windows-latest, cytv-windows-x64, dist/cytv.exe)'}
        self.job['name'] = names[kind]
        self.raw = self.archive(self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100))
        self.artifact.update(name=self.ctx['artifact'], size_in_bytes=len(self.raw),
                             digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
        self.responses['actions/workflows/cytv.yml/runs?branch=release%2Fnext&event=workflow_dispatch&per_page=100'] = {'workflow_runs': [self.run]}
        jobs = [self.job, {'id': 101, 'name': 'scope', 'status': 'completed', 'conclusion': 'success'},
                {'id': 102, 'name': 'validation / full-release', 'status': 'completed', 'conclusion': 'failure'}]
        self.responses['actions/runs/10/attempts/1/jobs?per_page=100'] = {'jobs': jobs, 'total_count': len(jobs)}

    def test_failed_full_candidate_can_supply_successful_direct_units(self):
        for kind, units in (('runtime', 'tv setup installer'), ('browser', 'browser-core browser-themes'),
                            ('optional', 'optional-python')):
            with self.subTest(kind=kind):
                self.candidate_producer(kind=kind, units=units)
                self.assertEqual(self.missing(), [])

    def test_full_candidate_requires_authentic_origin_full_marker_and_latest_job_success(self):
        self.candidate_producer()
        all_units = ['installer', 'setup', 'tv-runtime', 'ui']
        jobs = self.responses['actions/runs/10/attempts/1/jobs?per_page=100']['jobs']
        for obj, field, value in ((self.run, 'conclusion', 'cancelled'), (self.run, 'run_attempt', 2),
                                  (self.run, 'head_branch', 'main'), (self.run, 'head_sha', 'f' * 40),
                                  (self.run, 'head_repository', {'full_name': 'fork/repo'}),
                                  (self.run, 'path', '.github/workflows/other.yml'),
                                  (self.job, 'name', 'validation / runtime (macos-latest, 1)'),
                                  (self.job, 'conclusion', 'failure'), (jobs[1], 'conclusion', 'failure'),
                                  (jobs[2], 'conclusion', 'skipped'), (jobs[2], 'status', 'in_progress')):
            with self.subTest(field=field, value=value):
                saved = obj[field]
                obj[field] = value
                self.assertEqual(self.missing(), all_units)
                obj[field] = saved
        latest = {**self.run, 'id': 11}
        listing = self.responses['actions/workflows/cytv.yml/runs?branch=release%2Fnext&event=workflow_dispatch&per_page=100']['workflow_runs']
        listing.append(latest)
        self.responses['actions/runs/11/attempts/1/jobs?per_page=100'] = {'jobs': copy.deepcopy(jobs), 'total_count': len(jobs)}
        latest_jobs = self.responses['actions/runs/11/attempts/1/jobs?per_page=100']['jobs']
        # Newer green job permits older direct proof; it does not attest new keys.
        self.assertEqual(self.missing(), [])
        for changes in ({'conclusion': 'failure'}, {'status': 'in_progress'}, {'name': 'missing job'}):
            original = latest_jobs[0].copy()
            latest_jobs[0].update(changes)
            self.assertEqual(self.missing(), all_units)
            latest_jobs[0].clear()
            latest_jobs[0].update(original)
        latest['run_attempt'] = 2
        self.assertEqual(self.missing(), all_units)

    def test_desktop_proof_is_platform_specific_and_separate_from_runtime_homebrew(self):
        self.candidate_producer('desktop', 'windows-latest', 'installer-host')
        self.assertEqual(self.missing(), [])
        for platform in ('ubuntu-22.04', 'macos-15', 'macos-15-intel'):
            ctx = self.m['context']('desktop', platform, '1/4', 'installer-host', self.ctx['environment'], root=self.root)
            self.assertEqual(self.missing(ctx), ['installer-host'])
        self.assertEqual(self.missing(self.context('installer')), ['installer'])
        self.write_commit('homebrew/tests/test_payload.py')
        consumer = self.m['context']('desktop', 'windows-latest', '1/4', 'installer-host', self.ctx['environment'], root=self.root)
        self.assertEqual(self.missing(consumer), [])
        self.write_commit('tests/cytv/test_long_ssh_commands.py')
        consumer = self.m['context']('desktop', 'windows-latest', '1/4', 'installer-host', self.ctx['environment'], root=self.root)
        self.assertEqual(self.missing(consumer), ['installer-host'])

    def test_cli_records_only_authorized_full_dispatch_fresh_units(self):
        directory = self.root / 'evidence'
        directory.mkdir()
        (directory / 'plan.json').write_text(json.dumps({**self.ctx, 'units': ['ui']}))
        event = self.root / 'event.json'
        event.write_text(json.dumps({'inputs': {'full_candidate': True}}))
        env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_RUN_ID': '20', 'GITHUB_RUN_ATTEMPT': '1',
               'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_EVENT_PATH': str(event)}
        self.responses['actions/runs/20'] = {**self.run, 'id': 20, 'event': 'workflow_dispatch',
             'path': '.github/workflows/cytv.yml', 'head_branch': 'release/next', 'status': 'in_progress'}
        self.responses['actions/runs/20/attempts/1/jobs?per_page=100'] = {'total_count': 1, 'jobs': [
             {'id': 200, 'name': 'validation / runtime (ubuntu-latest, 1)', 'status': 'in_progress'}]}
        with patch.dict('os.environ', env), patch.dict(self.m['main'].__globals__, {'github_api': lambda _repo: self.api}), patch('sys.argv', ['ci-test-evidence.py', 'record', '--directory', str(directory)]):
            self.m['main']()
            self.assertEqual(set(json.loads((directory / 'receipt.json').read_text())['keys']), {'ui'})
            for value in (False, 'false', None):
                event.write_text(json.dumps({'inputs': {'full_candidate': value}}))
                with self.assertRaises(ValueError):
                    self.m['main']()

    def test_desktop_missing_required_tool_identity_runs_fresh_and_cannot_record(self):
        missing = [False]
        def process(*args):
            if args == ('git', '--version') and missing[0]:
                raise OSError('unavailable Git')
            if args[0] == '/bin/sh':
                return 'cytv-ci-shell'
            return 'actual-version'
        runner = {'RUNNER_OS': 'Windows', 'RUNNER_ARCH': 'X64', 'ImageOS': 'win25', 'ImageVersion': '20261101'}
        with patch.dict(self.m['environment'].__globals__, {'command': process}), patch.dict('os.environ', runner):
            known = self.m['environment']('desktop')
            self.assertEqual(known['git'], 'actual-version')
            self.assertEqual(known['zig'], 'actual-version')
            self.assertTrue(known['identity_ready'])
            self.candidate_producer('desktop', 'windows-latest', 'installer-host')
            missing[0] = True
            unavailable = self.m['environment']('desktop')
            ctx = self.m['context']('desktop', 'windows-latest', '1/4', 'installer-host', unavailable, root=self.root)
            self.assertEqual(self.missing(ctx), ['installer-host'])
            with self.assertRaises(ValueError):
                self.m['make_receipt'](ctx, 'owner/repo', 20, 1, 200)

    def test_desktop_shell_content_and_probe_bind_actual_git_shell(self):
        git = (self.root / 'Git' / 'cmd' / 'git.exe').resolve()
        git.parent.mkdir(parents=True)
        git.write_bytes(b'git')
        shell = git.parent.parent / 'bin' / 'sh.exe'
        shell.parent.mkdir()
        shell.write_bytes(b'first shell')
        broken = [False]
        def process(*args):
            if args[0] == str(shell):
                if broken[0]:
                    raise OSError('unprobeable shell')
                return 'cytv-ci-shell'
            return 'actual-version'
        runner = {'RUNNER_OS': 'Windows', 'RUNNER_ARCH': 'X64', 'ImageOS': 'win25', 'ImageVersion': '20261101'}
        with patch.dict(self.m['environment'].__globals__, {'command': process}), patch.dict('os.environ', runner), patch('sys.platform', 'win32'), patch('shutil.which', side_effect=lambda name: str(git) if name == 'git' else None):
            first = self.m['environment']('desktop')
            self.assertTrue(first['identity_ready'])
            self.assertEqual(first['shell']['path'], str(shell))
            before = self.m['context']('desktop', 'windows-latest', '1/4', 'installer-host', first, root=self.root)
            shell.write_bytes(b'different shell, identical Git version')
            second = self.m['environment']('desktop')
            after = self.m['context']('desktop', 'windows-latest', '1/4', 'installer-host', second, root=self.root)
            self.assertNotEqual(before['keys'], after['keys'])
            for missing_file in (False, True):
                broken[0] = not missing_file
                if missing_file:
                    shell.unlink()
                unavailable = self.m['environment']('desktop')
                self.assertFalse(unavailable['identity_ready'])
                ctx = self.m['context']('desktop', 'windows-latest', '1/4', 'installer-host', unavailable, root=self.root)
                self.assertEqual(self.missing(ctx), ['installer-host'])
                with self.assertRaises(ValueError):
                    self.m['make_receipt'](ctx, 'owner/repo', 20, 1, 200)

    def test_desktop_absent_cc_is_observed_but_unprobeable_present_cc_is_not_evidence(self):
        present = [False]
        def process(*args):
            if args == ('cc', '--version'):
                raise OSError('compiler cannot execute')
            if args[0] == '/bin/sh':
                return 'cytv-ci-shell'
            return 'actual-version'
        runner = {'RUNNER_OS': 'macOS', 'RUNNER_ARCH': 'ARM64', 'ImageOS': 'macos15', 'ImageVersion': '20261101'}
        real_which = shutil.which
        with patch.dict(self.m['environment'].__globals__, {'command': process}), patch.dict('os.environ', runner), patch('shutil.which', side_effect=lambda name: ('/toolchain/cc' if present[0] else None) if name == 'cc' else real_which(name)):
            self.assertTrue(self.m['environment']('desktop')['identity_ready'])
            present[0] = True
            unavailable = self.m['environment']('desktop')
            self.assertFalse(unavailable['identity_ready'])
            ctx = self.m['context']('desktop', 'macos-15', '1/4', 'installer-host', unavailable, root=self.root)
            self.assertEqual(self.missing(ctx), ['installer-host'])
            with self.assertRaises(ValueError):
                self.m['make_receipt'](ctx, 'owner/repo', 20, 1, 200)

    def test_api_pipe_reader_works_without_posix_selectors(self):
        executable = self.root / 'gh'
        executable.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps(dict(ok=True)))\n')
        executable.chmod(0o755)
        with patch.dict('os.environ', {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}), patch('selectors.DefaultSelector', side_effect=OSError('Windows pipe')):
            self.assertEqual(self.m['github_api']('owner/repo')('test'), {'ok': True})

    def test_matching_partial_coverage_runs_only_missing_units(self):
        self.assertEqual(self.missing(self.context('tv setup installer android preview')), ['android'])

    def test_alias_and_nonprimary_shard_do_not_claim_nonexecuted_units(self):
        self.assertEqual(self.context('tv ui tv-runtime android preview setup', shard='2/4')['units'], ['preview', 'setup', 'tv-runtime'])
        self.assertEqual(self.context('ui android preview', shard='2/4')['units'], ['preview'])
        # Keep these assertions in this existing test so verification itself does
        # not shift every subsequent setup test's modulo partition.
        expected = {1: ['android', 'setup', 'ui'], 2: ['preview', 'setup'],
                    3: ['setup'], 4: ['setup']}
        for index, units in expected.items():
            self.assertEqual(self.context('ui android preview setup', shard=f'{index}/4')['units'], units)

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
            self.ctx = self.context('installer preview', shard='2/4', environment=before)
            self.job['name'] = 'runtime (ubuntu-latest, 2)'
            self.raw = self.archive(self.m['make_receipt'](self.ctx, 'owner/repo', 10, 1, 100))
            self.artifact.update(name=self.ctx['artifact'], size_in_bytes=len(self.raw), digest='sha256:' + hashlib.sha256(self.raw).hexdigest())
            self.assertEqual(self.missing(), [])
            version[0] = '131.0.0.0'
            after = self.m['environment']('runtime')
            self.assertEqual(self.missing(self.context('installer preview', shard='2/4', environment=after)), ['installer', 'preview'])
            version[0] = '130.0.0.0'
            with patch.dict('os.environ', {'BROWSER_CHANNEL': 'chrome-beta'}):
                other_channel = self.m['environment']('runtime')
            self.assertEqual(self.missing(self.context('installer preview', shard='2/4', environment=other_channel)), ['installer', 'preview'])
            self.assertEqual(self.m['environment']('runtime', '2/4').get('browser'), '130.0.0.0')
            self.assertNotIn('browser', self.m['environment']('runtime', '3/4'))
            self.assertNotIn('browser', self.m['environment']('runtime', '4/4'))
            unavailable[0] = True
            unknown = self.m['environment']('runtime')
            self.assertIsNone(unknown['browser'])
            ctx = self.context('installer preview', shard='2/4', environment=unknown)
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
            executable.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n')
            with patch.object(self.m['github_api'].__globals__['time'], 'monotonic', side_effect=[0, 21]):
                with self.assertRaisesRegex(TimeoutError, 'deadline'):
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
                    '--os', 'ubuntu-latest', '--units', 'tv setup installer android']
            with patch('sys.argv', argv):
                self.m['main']()
            self.assertIn('missing=android\n', output.read_text())
            with patch('sys.argv', ['ci-test-evidence.py', 'record', '--directory', str(directory)]):
                self.m['main']()
            receipt = json.loads((directory / 'receipt.json').read_text())
            self.assertEqual(set(receipt['keys']), {'android'})
            event.write_text(json.dumps({'pull_request': {'head': {'repo': {'full_name': 'fork/repo'}}}}))
            output.write_text('')
            with patch('sys.argv', argv):
                self.m['main']()
            self.assertIn('missing=android installer setup tv-runtime ui\n', output.read_text())
            with patch('sys.argv', ['ci-test-evidence.py', 'record', '--directory', str(directory)]):
                with self.assertRaisesRegex(ValueError, 'same-repository'):
                    self.m['main']()
            event.write_text(json.dumps({'pull_request': {'head': {'repo': {'full_name': 'owner/repo'}}}}))
            with patch.dict('os.environ', {'GITHUB_RUN_ATTEMPT': '2'}), patch('sys.argv', argv):
                output.write_text('')
                self.m['main']()
            self.assertIn('missing=android installer setup tv-runtime ui\n', output.read_text())

    def test_api_outage_runs_tests_and_record_contains_only_fresh_units(self):
        def unavailable(*_args, **_kwargs):
            raise OSError('offline')
        self.assertEqual(self.m['select_missing'](self.ctx, 'owner/repo', 20, unavailable)['missing'], ['installer', 'setup', 'tv-runtime', 'ui'])
        selected = self.m['select_missing'](self.context('tv setup installer android'), 'owner/repo', 20, self.api)
        record = self.m['make_receipt']({**self.context('tv setup installer android'), 'units': selected['missing']}, 'owner/repo', 20, 1, 200)
        self.assertEqual(set(record['keys']), {'android'})


if __name__ == '__main__':
    unittest.main()
