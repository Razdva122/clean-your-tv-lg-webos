"""Full candidate builds must catch unversioned changes in shared Engine code."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_build import ROOT


def preflight():
    spec = importlib.util.spec_from_file_location('engine_preflight', ROOT / 'scripts/check-engine-transition.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnginePreflightTests(unittest.TestCase):
    def test_packaged_shared_luna_change_requires_engine_bump(self):
        check = preflight()
        build = check.builder['build']
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp).resolve() / 'system-updater'
            build(bundle)
            prior = check.check_candidate(bundle, None)

        source = build.__globals__['source']
        def changed_source(path):
            raw = source(path)
            if path == ROOT / 'root-edition/updater/luna.py':
                return raw + b'\n# Changed shared Root support\n'
            return raw

        meta = json.dumps({'tag_name': 'v1.28.0'})
        with patch.dict(check.release, gh=lambda *args: meta), patch.object(
            check, 'published_engine', return_value=prior
        ), contextlib.redirect_stdout(io.StringIO()):
            check.main()
            with patch.dict(build.__globals__, source=changed_source):
                with self.assertRaisesRegex(ValueError, 'Engine changed without version bump'):
                    check.main()
                major, minor, patch_version = map(int, prior['version'].split('.'))
                with patch.dict(build.__globals__, ENGINE_VERSION=f'{major}.{minor}.{patch_version + 1}'):
                    check.main()

    def test_unsigned_published_catalog_fails_before_archive_download(self):
        check = preflight()
        meta = {'tag_name': 'v1.29.1', 'draft': False, 'prerelease': False}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            check.release, download=lambda *args: b'{"payload":"","signature":""}'
        ), self.assertRaises(subprocess.CalledProcessError):
            check.published_engine(meta, Path(tmp))

    def test_signed_descriptor_must_match_published_tag_and_archive(self):
        check = preflight()
        meta = {'tag_name': 'v1.29.1', 'draft': False, 'prerelease': False}
        raw = b'published archive'
        name = 'system-engine_1.2.17.tar.gz'
        engine = {'version': '1.2.17', 'size': len(raw), 'sha256': check.release['digest'](raw),
                  'url': check.release['URL'] + meta['tag_name'] + '/' + name}
        assets = {'system-bootstrap-v1.json': b'{}', name: raw}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            check.release, download=lambda meta, name, folder: assets[name]
        ), patch.object(subprocess, 'check_output', return_value=json.dumps({'engine': engine})):
            self.assertEqual(check.published_engine(meta, Path(tmp)), engine)
            with self.assertRaisesRegex(ValueError, 'different release'):
                check.published_engine({**meta, 'tag_name': 'v1.30.0'}, Path(tmp))
            assets[name] = b'corrupted archive'
            with self.assertRaisesRegex(ValueError, 'differs from signed catalog'):
                check.published_engine(meta, Path(tmp))

    def test_full_candidate_preflight_gates_matrix(self):
        workflow = (ROOT / '.github/workflows/cytv.yml').read_text()
        scope = workflow.split('  scope:\n', 1)[1].split('  validation:\n', 1)[0]
        step = scope.split('python scripts/check-engine-transition.py')[0].rsplit('      - ', 1)[1]
        self.assertIn("if: steps.scope.outputs.full == 'true'", step)
        self.assertIn('python scripts/check-engine-transition.py', scope)
        for job in ('validation', 'android-package', 'build', 'homebrew'):
            self.assertIn(f'  {job}:\n    needs: scope\n', workflow)
