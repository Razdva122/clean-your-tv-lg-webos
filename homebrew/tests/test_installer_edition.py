"""Exercise the same Root admission policy through the fixed local reader."""
import os
import sys
import unittest
from unittest.mock import patch

from cytv import root_capabilities as home
from cytv.errors import TVCommandError
from homebrew.edition import LocalReads, decision


class LocalEditionTests(unittest.TestCase):
    def inspect(self, replies, embedded_failure=None, native_failure=None):
        def read(args, timeout, *, json_reply=False):
            if json_reply:
                return replies[args[3].removeprefix('luna://')]
            if args[2] == home.EMBEDDED_HEADERS:
                raise embedded_failure or AssertionError('unexpected embedded probe')
            if args[2] == home.NATIVE_HEADERS:
                raise native_failure or AssertionError('unexpected native probe')
            self.fail('unexpected probe')
        with patch.object(LocalReads, '_read', side_effect=read):
            return decision(LocalReads())

    def test_system_profile_is_local_root(self):
        self.assertEqual(self.inspect({
            home.CALLS['home-settings'][0]: {'returnValue': True, 'settings': {'defaultApps': {}}},
            home.CALLS['home-profiles'][0]: {'returnValue': True, 'profiles': {
                'defaultApps': {'categories': {'home': 'com.webos.app.home'}},
                'idleApp': {'support': False, 'appId': 'com.webos.app.home'}}}
        }), 'root')

    def test_rejection_does_not_establish_incompatibility(self):
        self.assertEqual(self.inspect({
            home.CALLS['home-profiles'][0]: {'returnValue': False, 'errorText': 'access denied'},
            home.CALLS['home-settings'][0]: {'returnValue': False}
        }), 'unconfirmed')

    def test_ribbon_requires_both_positive_readback_and_an_excluded_embedded_backend(self):
        replies = {
            home.CALLS['home-profiles'][0]: {'returnValue': False, 'errorCode': -1,
                'errorText': 'Service does not exist: com.webos.service.systemprofile.'},
            'com.webos.service.tv.systemproperty/getSystemInfo': {'returnValue': True,
                'modelName': 'fixture', 'firmwareVersion': '1.2.3', 'sdkVersion': '3.4.5'},
            'com.webos.service.config/getConfigs': {'returnValue': True, 'configs': {}},
            'com.webos.surfacemanager.home/getCurrentHomeUIState': {
                'homeUIState': [{'uiType': 'home', 'visibility': False}]}
        }
        self.assertEqual(self.inspect(replies, TVCommandError(42)), 'external_no_root')
        self.assertEqual(self.inspect(replies, TimeoutError()), 'unconfirmed')
        replies['com.webos.surfacemanager.home/getCurrentHomeUIState'] = {'returnValue': False}
        self.assertEqual(self.inspect(replies, TVCommandError(42)), 'unconfirmed')

    def test_compositor_support_routes_to_root_on_the_computer(self):
        with patch.object(home, 'verify', return_value='c1-native-gate'):
            self.assertEqual(decision(LocalReads()), 'external_root')

    def test_local_reader_rejects_other_commands_uris_and_arguments(self):
        reader = LocalReads()
        with patch.object(reader, '_read') as run:
            with self.assertRaises(ValueError):
                reader.run('uname -a', timeout=1)
            uri, payload = home.CALLS['home-settings']
            for target, args in (('invalid', {}), (uri, dict(payload, extra='x'))):
                with self.assertRaises(ValueError):
                    reader.luna(target, args, timeout=1)
            run.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'TV subprocess pipe polling requires POSIX')
    def test_reader_keeps_stdin_open_and_reads_one_limited_reply(self):
        script = ('import json,sys;print(json.dumps({"observed":True}),flush=True);'
                  'sys.stdin.buffer.read()')
        self.assertEqual(LocalReads._read([sys.executable, '-c', script], 2, json_reply=True),
                         {'observed': True})
        with self.assertRaisesRegex(ValueError, 'oversized'):
            LocalReads._read([sys.executable, '-c', "print('x' * 65537)"], 2)
        with self.assertRaises(TVCommandError) as error:
            LocalReads._read([sys.executable, '-c', 'raise SystemExit(42)'], 2)
        self.assertEqual(error.exception.exit_status, 42)
