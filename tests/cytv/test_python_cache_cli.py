"""Offline runtime preparation must never discover or contact a TV."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cytv import cli
from cytv.errors import UserError


class PythonCacheCLITests(unittest.TestCase):
    def test_explicit_prepare_downloads_to_private_cache_without_tv_or_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, output = [], []
            def prime(directory, progress):
                calls.append(Path(directory))
                return Path(directory) / 'verified-python.tar.gz'
            def no_tv(*args, **kwargs):
                self.fail('Offline preparation tried to contact a TV or ask for credentials')
            with patch.dict('sys.modules', {'cytv.python_runtime': SimpleNamespace(prime_cache=prime)}), \
                 patch('cytv.cli.package.verify_payload', side_effect=no_tv):
                code = cli.main(['--prepare-python-runtime', '--language', 'en', '--data-dir', tmp],
                                ask=no_tv, secret=no_tv, connect=no_tv, search=no_tv,
                                inspect=no_tv, write=output.append)
            self.assertEqual(code, 0)
            self.assertEqual(calls, [Path(tmp) / 'python-cache'])
            self.assertIn('verified-python.tar.gz', '\n'.join(output))

    def test_preparation_failure_has_its_own_diagnostic_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fail(*args):
                raise UserError('Could not prepare Python runtime.')
            with patch.dict('sys.modules', {'cytv.python_runtime': SimpleNamespace(prime_cache=fail)}):
                code = cli.main(['--prepare-python-runtime', '--language', 'en', '--data-dir', tmp],
                                write=lambda _: None)
            self.assertEqual(code, 2)
            import json
            report = next((Path(tmp) / 'reports').glob('*.json'))
            self.assertEqual(json.loads(report.read_text())['phase'], 'prepare-python-runtime')

    def test_real_cache_failure_exports_safe_reason_without_contacting_tv(self):
        import json
        from cytv import python_runtime
        def no_tv(*args, **kwargs):
            self.fail('Offline cache diagnostics must not contact a TV')
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(python_runtime.urllib.request, 'build_opener') as builder:
            builder.return_value.open.side_effect = OSError('PRIVATE-NETWORK-URL')
            output = []
            code = cli.main(['--prepare-python-runtime', '--language', 'en', '--data-dir', str(Path(tmp).resolve())],
                            ask=no_tv, secret=no_tv, connect=no_tv, search=no_tv,
                            inspect=no_tv, write=output.append)
            self.assertEqual(code, 2)
            report = next((Path(tmp) / 'reports').glob('*.json'))
            self.assertEqual(json.loads(report.read_text())['python_cache'], {'reason': 'network'})
            self.assertNotIn('PRIVATE-NETWORK', report.read_text() + '\n'.join(output))
