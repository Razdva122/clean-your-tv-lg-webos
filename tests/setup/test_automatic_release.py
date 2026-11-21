from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
import tempfile
import struct
import tarfile
import zipfile
import subprocess
import sys
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from cytv.package import ipk

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('assemble_release', ROOT / 'scripts/assemble-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
VERSIONS = {'release': '0.10.9', 'cytv': '0.2.12', 'home': '1.3.5', 'helper': '0.6.16', 'root': '0.1.9', 'updater': '0.1.5'}
SHA = 'a' * 40


class AutomaticRelease(unittest.TestCase):
    def test_assembly_failure_leaves_output_available_for_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            artifacts = parent / 'builds'
            first = artifacts / 'cytv-windows-x64/cytv.exe'
            first.parent.mkdir(parents=True)
            first.write_bytes(b'first build artifact')
            output = parent / 'assets'

            # Setup tests do not install the CI-only archive reader. The missing
            # artifact must fail before assembly tries to open any archive.
            reader = SimpleNamespace(CArchiveReader=None)
            with patch.dict(sys.modules, {'PyInstaller.archive.readers': reader}):
                with self.assertRaises(FileNotFoundError) as error:
                    release.assemble(artifacts, output, VERSIONS, SHA)
            self.assertEqual(Path(error.exception.filename),
                             artifacts / 'cytv-windows-x64-desktop/cytv-windows-x64-desktop.zip')
            self.assertEqual(set(parent.iterdir()), {artifacts})

            def assemble_fixture(builds, staged, versions, commit, build_commit):
                self.assertFalse(output.exists())
                self.assertEqual(staged.parent.parent, parent)
                (staged / 'BUILD-INFO.json').write_text(json.dumps({'source_commit': commit}))
                (staged / 'cytv-windows-x64.exe').write_bytes(first.read_bytes())

            with patch.object(release, '_assemble_assets', side_effect=assemble_fixture):
                release.assemble(artifacts, output, VERSIONS, SHA)
            self.assertEqual(set(parent.iterdir()), {artifacts, output})
            self.assertEqual({path.name for path in output.iterdir()},
                             {'BUILD-INFO.json', 'cytv-windows-x64.exe'})
            self.assertEqual(json.loads((output / 'BUILD-INFO.json').read_text()), {'source_commit': SHA})
            self.assertEqual((output / 'cytv-windows-x64.exe').read_bytes(), first.read_bytes())

    def test_assembly_refuses_an_existing_empty_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'assets'
            output.mkdir()
            with self.assertRaises(FileExistsError) as error:
                release.assemble(Path(directory) / 'missing', output, VERSIONS, SHA)
            self.assertEqual(Path(error.exception.filename), output)
            self.assertEqual(list(output.iterdir()), [])

    def test_competing_assemblies_keep_the_successful_output(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            output = parent / 'assets'
            promotion = Barrier(2)
            rename = Path.rename

            def assemble_fixture(builds, staged, versions, commit, build_commit):
                (staged / 'BUILD-INFO.json').write_text(builds.name)

            def promote(staged, target):
                # Both attempts have checked that the destination is absent.
                promotion.wait(timeout=5)
                return rename(staged, target)

            candidates = ('first', 'second')
            with patch.object(release, '_assemble_assets', side_effect=assemble_fixture), \
                 patch.object(Path, 'rename', promote), ThreadPoolExecutor(2) as workers:
                attempts = [workers.submit(release.assemble, parent / name, output, VERSIONS, SHA)
                            for name in candidates]
                results = {name: attempt.exception(timeout=10) for name, attempt in zip(candidates, attempts)}
            winner = (output / 'BUILD-INFO.json').read_text()
            self.assertIn(winner, candidates)
            self.assertIsNone(results.pop(winner))
            self.assertIsInstance(next(iter(results.values())), FileExistsError)
            self.assertEqual(list(parent.iterdir()), [output])

    @unittest.skipIf(os.name == 'nt', 'Release assembly preserves POSIX package modes')
    def test_outer_archives_repeat_across_assembly_clocks_and_umasks(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            timestamp = 1_767_225_600  # 2026-01-01 00:00:00 UTC
            subprocess.run(['git', 'init', '-q', str(source)], check=True)
            subprocess.run(['git', '-c', 'user.name=Release fixture', '-c',
                            'user.email=fixture@example.invalid', 'commit', '--allow-empty',
                            '--no-gpg-sign', '-qm', 'Archive fixture'],
                           cwd=source, check=True, env={**os.environ,
                               'GIT_AUTHOR_DATE': f'{timestamp} +0000',
                               'GIT_COMMITTER_DATE': f'{timestamp} +0000'})
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
            note = 'docs/RELEASE-' + VERSIONS['release'] + '.md'
            script = 'scripts/update-permissions.cjs'
            for name in ('docs/MANUAL_INSTALL.md', 'docs/INSTALL.md', 'docs/CLI.md', note,
                         'LICENSE', 'THIRD_PARTY_NOTICES.md', script,
                         'scripts/lib/update-permissions.cjs', 'updater-service/permissions.js'):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            (source / script).chmod(0o755)

            def create_bundle(name, clock, umask, content):
                run = source / name
                payload, staging, output = (run / folder for folder in
                                            ('payload', 'clean-your-tv-root-0.1.9', 'output'))
                previous = os.umask(umask)
                try:
                    for folder, files in (
                        (payload, {'launcher.ipk': b'1080p', 'launcher-720p.ipk': b'720p',
                                   'helper.ipk': content, 'updater.ipk': b'updater',
                                   'system-updater/b/manifest.json': b'manifest',
                                   'system-updater/a/updater.ipk': b'system updater'}),
                        (staging, {'build/root-candidate/root.ipk': content,
                                   'install.sh': b'#!/bin/sh\nexit 0\n'}),
                    ):
                        for member, data in files.items():
                            path = folder / member
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_bytes(data)
                    (staging / 'install.sh').chmod(0o777 & ~umask)
                    output.mkdir()
                    for path in [run, *run.rglob('*')]:
                        os.utime(path, (clock, clock))
                    with patch.object(release, 'ROOT', source), patch('time.time', return_value=clock):
                        release.write_outer_archives(payload, staging, output, VERSIONS, commit)
                finally:
                    os.umask(previous)
                return (output / 'clean-your-tv-no-root-1.3.5.zip',
                        output / 'clean-your-tv-root-0.1.9.tar.gz')

            first = create_bundle('first', timestamp + 100, 0o022, b'unchanged IPK')
            retry = create_bundle('retry', timestamp + 900, 0o077, b'unchanged IPK')
            changed = create_bundle('changed', timestamp + 900, 0o077, b'changed IPK')
            for original, duplicate, modified in zip(first, retry, changed):
                sha = lambda path: hashlib.sha256(path.read_bytes()).digest()
                self.assertEqual(sha(original), sha(duplicate))
                self.assertNotEqual(sha(original), sha(modified))

            with zipfile.ZipFile(first[0]) as archive:
                helper = archive.getinfo('com.local.nativehome_0.6.16_arm.ipk')
                self.assertEqual(archive.read(helper), b'unchanged IPK')
                self.assertEqual(helper.date_time, (2026, 1, 1, 0, 0, 0))
                self.assertEqual((helper.external_attr >> 16) & 0o777, 0o644)
                self.assertEqual((archive.getinfo(script).external_attr >> 16) & 0o777, 0o755)
                self.assertEqual(archive.read('system-updater/a/updater.ipk'), b'system updater')
            self.assertEqual(struct.unpack_from('<I', first[1].read_bytes(), 4)[0], timestamp)
            prefix = 'clean-your-tv-root-0.1.9/'
            with tarfile.open(first[1]) as archive:
                root = archive.getmember(prefix.rstrip('/'))
                install = archive.getmember(prefix + 'install.sh')
                package = archive.getmember(prefix + 'build/root-candidate/root.ipk')
                self.assertEqual(archive.extractfile(package).read(), b'unchanged IPK')
                self.assertEqual(archive.extractfile(install).read(), b'#!/bin/sh\nexit 0\n')
                self.assertEqual((root.mode, install.mode, package.mode), (0o755, 0o755, 0o644))
                self.assertTrue(all(member.mtime == timestamp for member in archive.getmembers()))

    def test_resolver_requires_all_successful_candidate_jobs(self):
        import runpy
        names = runpy.run_path(str(ROOT / 'scripts/release-flow.py'))['BUILD_JOBS']
        jobs = [{'name': name, 'conclusion': 'success'} for name in names]
        run = {'id': 42, 'head_sha': SHA}
        for explicit in (None, 42):
            responses = [run, jobs] if explicit else [{'workflow_runs': [run]}, jobs]
            with self.subTest(explicit=explicit), \
                 patch.object(release, 'github', side_effect=responses) as api, \
                 patch.dict(release.INPUTS, {'pin_at': lambda *args: None}), \
                 patch.object(release, 'validate_build_run') as validate, \
                 patch.object(release.subprocess, 'check_output', return_value=SHA):
                self.assertEqual(release.resolve_build_source('b' * 40, explicit), run)
                validate.assert_called_once_with(run, 'b' * 40)
                self.assertIn('actions/runs/42/jobs', api.call_args.args[0])
                if not explicit:
                    self.assertNotIn('&event=push', api.call_args_list[0].args[0],
                                     'full workflow_dispatch builds must be discoverable without a pin')
        for incomplete in (jobs[1:], [{**job, 'conclusion': 'skipped'} if job['name'] == 'android' else job for job in jobs]):
            with self.subTest(jobs=incomplete), \
                 patch.object(release, 'github', side_effect=[run, incomplete]), \
                 patch.object(release, 'validate_build_run'), self.assertRaises(ValueError):
                release.resolve_build_source('b' * 40, 42)
        with patch.dict(release.INPUTS, {'pin_at': lambda *args: None}), \
             patch.object(release, 'github', return_value={'workflow_runs': []}), \
             patch.object(release.subprocess, 'check_output', return_value=SHA), self.assertRaisesRegex(ValueError, 'No successful build'):
            release.resolve_build_source('b' * 40)

    def test_candidate_artifacts_require_exact_merge_parent_and_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-b', 'main')
            git('config', 'user.name', 'CI test')
            git('config', 'user.email', 'ci@example.invalid')
            (root / 'file').write_text('base')
            git('add', '.'); git('commit', '-m', 'base')
            git('checkout', '-b', 'release/next')
            (root / 'file').write_text('candidate')
            git('commit', '-am', 'candidate')
            candidate = git('rev-parse', 'HEAD')
            git('checkout', 'main')
            git('merge', '--no-ff', 'release/next', '-m', 'release')
            commit = git('rev-parse', 'HEAD')
            run = {'conclusion': 'success', 'status': 'completed', 'head_sha': candidate,
                   'head_branch': 'release/next', 'event': 'push', 'path': '.github/workflows/cytv.yml',
                   'head_repository': {'full_name': 'Razdva122/clean-your-tv-lg-webos'}}
            release.validate_build_run(run, commit, root=root)
            for change in ({'head_sha': 'b' * 40}, {'event': 'pull_request'},
                           {'head_repository': {'full_name': 'someone/fork'}}, {'conclusion': 'failure'}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    release.validate_build_run({**run, **change}, commit, root=root)
            # A merge that adds even one unbuilt file cannot ship these artifacts.
            (root / 'extra').write_text('unbuilt')
            git('add', '.'); git('commit', '--amend', '--no-edit')
            with self.assertRaisesRegex(ValueError, 'tree'):
                release.validate_build_run(run, git('rev-parse', 'HEAD'), root=root)

    def test_android_release_binds_apk_to_trusted_source_metadata_and_payload(self):
        self.assertTrue(hasattr(release, 'verify_android_package'), 'Android release verification is missing')
        versions = {**VERSIONS, 'android': '0.1.3-preview', 'android_version_code': 4}
        files = {}
        for name, app, key in [('launcher.ipk', 'com.gathin.tvhome', 'home'), ('helper.ipk', 'com.local.nativehome', 'helper'), ('root/root.ipk', 'com.cleanyourtv.root.preview', 'root')]:
            files[name] = ipk(app, versions[key], {'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': versions[key]}).encode()})
        files['root/bundle.json'] = b'{"package":"root.ipk"}'
        files['root/release.json'] = json.dumps({'version': versions['root']}).encode()
        files['payload.json'] = json.dumps({'home_version': versions['home'], 'helper_version': versions['helper'], 'files': {n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}).encode()
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / 'android.apk'
            report = Path(directory) / 'android.build.json'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('assets/cytv-build.json', json.dumps({'schema': 1, 'source_commit': SHA, 'versions': versions}))
                for name, raw in files.items(): archive.writestr('assets/payload/' + name, raw)
            metadata = {'schema': 1, 'source_commit': SHA, 'versions': versions,
                        'android_version_name': versions['android'], 'android_version_code': 4,
                        'package': 'com.cleanyourtv.android', 'abi': 'arm64-v8a', 'min_sdk': 24, 'target_sdk': 35,
                        'debuggable': False,
                        'signer_sha256': (ROOT / 'android/preview-certificate.sha256').read_text().strip(),
                        'sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}
            report.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError,'graphics'):
                release.verify_android_package(apk, report, versions, SHA)
            self.assertGreater(release.verify_android_package(apk, report, versions, SHA, allow_legacy=True), 0)
            for key, value in [('source_commit', 'b'*40), ('sha256', '0'*64), ('signer_sha256', '0'*64), ('android_version_code', 3), ('abi', 'x86_64'), ('debuggable', True), ('debuggable', 0), ('debuggable', None)]:
                report.write_text(json.dumps({**metadata, key: value}))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    release.verify_android_package(apk, report, versions, SHA)
            report.write_text(json.dumps({key: value for key, value in metadata.items() if key != 'debuggable'}))
            with self.assertRaises(ValueError):
                release.verify_android_package(apk, report, versions, SHA)

    def test_windows_desktop_rejects_console_binary_and_stale_package(self):
        self.assertTrue(hasattr(release, 'verify_windows_desktop'), 'Windows GUI release verification is missing')
        files = {}
        for name, app, key in [('launcher.ipk', 'com.gathin.tvhome', 'home'), ('helper.ipk', 'com.local.nativehome', 'helper'), ('root/root.ipk', 'com.cleanyourtv.root.preview', 'root')]:
            files[name] = ipk(app, VERSIONS[key], {'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': VERSIONS[key]}).encode()})
        files['root/bundle.json'] = b'{"package":"root.ipk"}'
        files['root/release.json'] = json.dumps({'version': VERSIONS['root']}).encode()
        files['payload.json'] = json.dumps({'home_version': VERSIONS['home'], 'helper_version': VERSIONS['helper'], 'files': {n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}).encode()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'desktop.zip'
            for subsystem, version, valid in [(2, VERSIONS['cytv'], True), (3, VERSIONS['cytv'], False), (2, '0.0.1', False)]:
                pe = bytearray(512); pe[:2] = b'MZ'; struct.pack_into('<I', pe, 60, 128)
                pe[128:132] = b'PE\0\0'; struct.pack_into('<H', pe, 132, 0x8664)
                struct.pack_into('<H', pe, 152, 0x20b); struct.pack_into('<H', pe, 220, subsystem)
                with zipfile.ZipFile(target, 'w') as archive:
                    archive.writestr('cytv-desktop/cytv-desktop.exe', pe)
                    archive.writestr('cytv-desktop/version.json', json.dumps({'cytv': version, 'platform': 'windows-x64', 'entrypoint': 'cytv-desktop.exe'}))
                    for name, data in files.items(): archive.writestr('cytv-desktop/_internal/payload/' + name, data)
                if valid:
                    with self.assertRaisesRegex(ValueError,'graphics'):
                        release.verify_windows_desktop(target, VERSIONS)
                    self.assertEqual(release.verify_windows_desktop(target, VERSIONS, allow_legacy=True), len(files)-1)
                else:
                    with self.assertRaises(ValueError): release.verify_windows_desktop(target, VERSIONS)

    def test_new_version_starts_release(self):
        self.assertTrue(release.plan_release(VERSIONS, SHA, [], False))

    def test_published_release_is_not_overwritten(self):
        existing = [{'tag_name': 'v0.10.9', 'draft': False, 'prerelease': False, 'target_commitish': 'b' * 40}]
        self.assertFalse(release.plan_release(VERSIONS, SHA, existing, False))
        self.assertTrue(release.plan_release(VERSIONS, SHA, existing, True))

    def test_retry_requires_same_draft_commit(self):
        existing = [{'tag_name': 'v0.10.9', 'draft': True, 'prerelease': False, 'target_commitish': SHA}]
        self.assertTrue(release.plan_release(VERSIONS, SHA, existing, False))
        with self.assertRaisesRegex(ValueError, 'different commit'):
            release.plan_release(VERSIONS, 'b' * 40, existing, False)

    def test_older_release_and_invalid_versions_stop(self):
        existing = [{'tag_name': 'v0.10.10', 'draft': False, 'prerelease': False}]
        with self.assertRaisesRegex(ValueError, 'newer'):
            release.plan_release(VERSIONS, SHA, existing, False)
        with self.assertRaisesRegex(ValueError, 'version'):
            release.plan_release({**VERSIONS, 'release': '../bad'}, SHA, [], False)

    def test_payload_hashes_and_actual_versions_are_verified(self):
        files = {}
        for name, app, version in [('launcher.ipk', 'com.gathin.tvhome', VERSIONS['home']), ('helper.ipk', 'com.local.nativehome', VERSIONS['helper']), ('root/root.ipk', 'com.cleanyourtv.root.preview', VERSIONS['root'])]:
            files[name] = ipk(app, version, {'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': version}).encode()})
        files['root/bundle.json'] = json.dumps({'package': 'root.ipk'}).encode()
        files['root/release.json'] = json.dumps({'version': VERSIONS['root']}).encode()
        files['payload.json'] = json.dumps({'home_version': VERSIONS['home'], 'helper_version': VERSIONS['helper'], 'files': {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}).encode()
        self.assertGreater(release.verify_embedded(files.__getitem__, VERSIONS, allow_legacy=True), 0)
        with self.assertRaisesRegex(ValueError, 'version'):
            release.verify_embedded(files.__getitem__, {**VERSIONS, 'root': '0.1.10'}, allow_legacy=True)
        files['launcher.ipk'] = b'corrupted'
        with self.assertRaisesRegex(ValueError, 'hash'):
            release.verify_embedded(files.__getitem__, VERSIONS, allow_legacy=True)

    def test_artifacts_require_successful_trusted_main_builds(self):
        run = {'conclusion': 'success', 'status': 'completed', 'head_sha': SHA, 'head_branch': 'main', 'event': 'push', 'path': '.github/workflows/cytv.yml', 'head_repository': {'full_name': 'Razdva122/clean-your-tv-lg-webos'}}
        release.validate_build_run(run, SHA)
        for field, value in [('conclusion', 'failure'), ('head_sha', 'b' * 40), ('event', 'pull_request'), ('head_branch', 'feature'), ('path', '.github/workflows/other.yml'), ('head_repository', {'full_name': 'someone/fork'})]:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'trusted main'):
                release.validate_build_run({**run, field: value}, SHA)

    def test_debian_zstandard_archives_work_on_python_312(self):
        import gzip
        import shutil
        import subprocess
        from cytv.package import tgz
        if not shutil.which('zstd'):
            self.skipTest('zstd CLI is installed by the release packaging job')
        raw = gzip.decompress(tgz({'control': b'Package: cytv\nVersion: 0.2.12\n'}))
        compressed = subprocess.check_output(['zstd', '-q', '-c'], input=raw)
        self.assertTrue(hasattr(release, 'open_deb_tar'), 'Debian zstd reader is required')
        with release.open_deb_tar({'control.tar.zst': compressed}, 'control') as archive:
            self.assertIn(b'Version: 0.2.12', archive.extractfile('control').read())
