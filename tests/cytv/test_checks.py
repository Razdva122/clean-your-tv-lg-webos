"""Visible checks must describe observed results, never inferred success."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cytv import cli
from cytv.desktop import DesktopConsole


class CheckTests(unittest.TestCase):
    def test_private_python_is_rechecked_and_node_failure_blocks_preparation(self):
        from cytv.checks import CheckList
        from cytv.operations import Installer
        from cytv.errors import UserError
        for node_ready in (True, False):
            with self.subTest(node_ready=node_ready):
                class Remote:
                    def run(self, command, **kwargs):
                        if 'CYTV_ROOT_READY' in command:
                            missing = '/usr/bin/python3' in command or ('/usr/bin/node' in command and not node_ready)
                            return 'CYTV_ROOT_MISSING' if missing else 'CYTV_ROOT_READY'
                        return ''
                events = []
                checks = CheckList(events.append)
                checks.prepare('root', 'install')
                inst = Installer(Remote(), None, {'edition':'root'}, Path('/unused'), {}, checks=checks)
                with patch.object(inst, '_python', return_value='/usr/bin/python3'), \
                        patch.object(inst, '_select_python', return_value='/verified/python') as prepare:
                    if node_ready:
                        inst.preflight(install=True)
                        prepare.assert_called_once_with(provision=True)
                        self.assertEqual(checks.results['python3']['status'], 'pass')
                        self.assertTrue(any(e['id']=='python3' and e['status']=='fail' for e in events))
                    else:
                        with self.assertRaises(UserError): inst.preflight(install=True)
                        prepare.assert_not_called()
                        self.assertEqual(checks.results['node-version']['status'], 'fail')

    def test_cancelled_signin_does_not_claim_bad_credentials(self):
        events = []
        def connect(*args): raise EOFError()
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['doctor', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp,
                             '--language', 'en', '--yes'], connect=connect,
                            write=DesktopConsole(lambda kind, value: events.append((kind, value))))
        self.assertEqual(code, 130)
        checks = {e['id']: e for kind, e in events if kind == 'check'}
        self.assertEqual(checks['ssh']['status'], 'unknown')
        self.assertEqual(checks['root-user']['status'], 'pending')

    def test_issue164_doctor_keeps_ssh_pass_and_unrun_pairing(self):
        class Remote:
            def run(self, command, **kwargs):
                if 'CYTV_ROOT_READY' in command:
                    missing = '/usr/bin/python3' in command or '/usr/bin/node' in command
                    return 'CYTV_ROOT_MISSING' if missing else 'CYTV_ROOT_READY'
                return ''
            def close(self): pass
        events = []
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.package.verify_payload', return_value={}), \
                patch('cytv.operations.Installer._python', return_value='/usr/bin/python3'), patch('cytv.tv.SSAP') as ssap:
            code = cli.main(['doctor', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp,
                             '--language', 'en', '--yes'], connect=lambda *args: Remote(),
                            write=DesktopConsole(lambda kind, value: events.append((kind, value))))
        self.assertEqual(code, 2)
        checks = {e['id']: e for kind, e in events if kind == 'check'}
        self.assertIn('ssh', checks, 'SSH result must be visible')
        self.assertEqual(checks['ssh']['status'], 'pass')
        self.assertEqual(checks['root-user']['status'], 'pass')
        self.assertEqual(checks['node-version']['status'], 'fail')
        self.assertEqual(checks['python3']['status'], 'fail')
        self.assertEqual(checks['pairing']['status'], 'pending')
        self.assertIn('doctor', checks['pairing']['detail'])
        ssap.assert_not_called()

    def test_connection_failure_marks_only_ssh_failed_without_remote_text(self):
        events = []
        def connect(*args): raise OSError('SECRET-NETWORK-DETAILS')
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['doctor', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp,
                             '--language', 'en', '--yes'], connect=connect,
                            write=DesktopConsole(lambda kind, value: events.append((kind, value))))
        self.assertEqual(code, 1)
        checks = {e['id']: e for kind, e in events if kind == 'check'}
        self.assertIn('ssh', checks, 'Failed SSH result must be visible')
        self.assertEqual(checks['ssh']['status'], 'fail')
        self.assertEqual(checks['node-version']['status'], 'pending')
        self.assertNotIn('SECRET-NETWORK-DETAILS', str(events))

    def test_terminal_checks_show_status_and_requirement_in_plain_text(self):
        from cytv.terminal import Console
        lines = []
        self.assertTrue(hasattr(Console, 'check'), 'Console must render visible checks')
        Console(lines.append, color=False).check({'id':'node-version', 'label':'TV Node.js 8+',
            'status':'fail', 'detail':'Node.js 8+ is required on the TV.'})
        output = '\n'.join(lines)
        self.assertIn('Failed', output)
        self.assertIn('Node.js 8+', output)
        self.assertNotIn('\x1b', output)
