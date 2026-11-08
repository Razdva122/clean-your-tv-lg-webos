"""TV Node evidence survives failed admission without exporting remote output."""
import json
from itertools import product
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cytv import diagnostics, state
from cytv.errors import TVCommandError, UserError
from cytv.operations import Installer


@unittest.skipUnless(os.name == 'posix', 'TV version probe requires a POSIX shell')
class NodeDiagnosticsTests(unittest.TestCase):
    def test_preflight_reports_version_or_distinct_failure_before_other_requirements(self):
        cases = (
            ('old', 'printf "v0.12.2\\n"', 'read', '0.12.2'),
            ('current', 'printf "v8.12.0\\n"', 'read', '8.12.0'),
            ('missing', None, 'missing', None),
            ('broken-link', None, 'launch-error', None),
            ('not-executable', 'printf "v8.12.0\\n"', 'launch-error', None),
            ('failed', 'echo PRIVATE-ERROR >&2; exit 127', 'launch-error', None),
            ('invalid', 'printf "PRIVATE-OUTPUT\\n"', 'invalid-output', None),
            ('extra-output', 'printf "v8.12.0\\nPRIVATE-OUTPUT\\n"', 'invalid-output', None),
        )
        for edition, install in product(('root', 'no-root'), (False, True)):
            for name, script, expected_status, expected_version in cases:
                with self.subTest(edition=edition, install=install, case=name), tempfile.TemporaryDirectory() as tmp:
                    node = Path(tmp)/'node'
                    if script is not None:
                        node.write_text('#!/bin/sh\n'+script+'\n')
                        node.chmod(0o600 if name == 'not-executable' else 0o700)
                    elif name == 'broken-link':
                        node.symlink_to(Path(tmp)/'absent')

                    class Remote:
                        def run(self, command, **kwargs):
                            if '/usr/bin/node --version' in command:
                                command = command.replace('/usr/bin/node', shlex.quote(str(node)))
                                return subprocess.check_output(['sh', '-c', command], text=True)
                            if 'CYTV_ROOT_READY' in command:
                                return 'CYTV_ROOT_MISSING'
                            return 'x86_64' if command == 'uname -m' else ''

                    info = {'node_version': '99.99.99'}
                    installer = Installer(Remote(), None, {'edition': edition}, '.', {}, tv_info=info)
                    with patch.object(installer, '_python', return_value='/usr/bin/python3'):
                        with self.assertRaises(UserError) as error:
                            installer.preflight(install=install)
                    store = state.Store(Path(tmp)/'state')
                    profile = state.target('192.0.2.10', edition)
                    report = diagnostics.create_report(store, 'install', profile,
                        'inspect-installation', error.exception, tv_info=info)
                    value = json.loads(report.read_text())
                    self.assertEqual(value['tv'].get('node_version_status'), expected_status)
                    self.assertEqual(value['tv'].get('node_version'), expected_version)
                    self.assertNotIn('PRIVATE-', report.read_text())
                    self.assertNotIn('99.99.99', report.read_text())
                    later = json.loads(diagnostics.create_report(store, 'status', profile, 'status').read_text())
                    previous = later['previous_attempt_failure']['tv']
                    self.assertEqual(previous.get('node_version_status'), expected_status)
                    self.assertEqual(previous.get('node_version'), expected_version)

    def test_status_keeps_version_when_status_inspection_fails(self):
        for edition in ('root', 'no-root'):
            with self.subTest(edition=edition), tempfile.TemporaryDirectory() as tmp:
                class Remote:
                    def run(self, command, **kwargs):
                        return 'CYTV_NODE_VERSION v0.12.2'

                info = {}
                installer = Installer(Remote(), state.Store(tmp), state.target('192.0.2.10', edition),
                    '.', {}, tv_info=info)
                with patch.object(installer, '_status', side_effect=UserError('primary failure')):
                    with self.assertRaisesRegex(UserError, 'primary failure'):
                        installer.status()
                self.assertEqual(info.get('node_version'), '0.12.2')
                self.assertEqual(info.get('node_version_status'), 'read')

    def test_unavailable_version_read_preserves_primary_failure(self):
        for edition in ('root', 'no-root'):
            with self.subTest(edition=edition):
                class Remote:
                    def run(self, command, **kwargs):
                        if '/usr/bin/node --version' in command:
                            raise TVCommandError(255)
                        raise UserError('primary failure')

                info = {'node_version': '99.99.99'}
                installer = Installer(Remote(), None, {'edition': edition}, '.', {}, tv_info=info)
                with self.assertRaisesRegex(UserError, 'primary failure'):
                    installer.preflight()
                value = diagnostics.context.tv_summary(info)
                self.assertEqual(value.get('node_version_status'), 'unavailable')
                self.assertNotIn('node_version', value)

    def test_report_filters_untrusted_version_status(self):
        value = diagnostics.context.tv_summary({'node_version': 'PRIVATE-VERSION',
            'node_version_status': 'PRIVATE-STATUS'})
        self.assertEqual(value.get('node_version_status'), 'unavailable')
        self.assertNotIn('PRIVATE-', json.dumps(value))


if __name__ == '__main__':
    unittest.main()
