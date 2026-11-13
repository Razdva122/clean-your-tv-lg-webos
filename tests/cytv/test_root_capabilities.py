"""Host preflight uses the retained Root read contract, not model guesses."""
import ast
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from cytv import state
from cytv.checks import CheckList

SETTINGS={'returnValue':True,'settings':{'defaultApps':{}}}
PROFILES={'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},
          'idleApp':{'appId':'com.webos.app.home','support':False}}}


class CapabilityTests(unittest.TestCase):
    def test_keyfilters_probe_records_a_safe_reason_and_clears_stale_evidence(self):
        from cytv.diagnostic_context import tv_summary
        from cytv.errors import TVRejected
        from cytv.root_capabilities import compositor_failure, verify

        identity = {'returnValue': True, 'modelName': 'TV', 'firmwareVersion': '06.10.60',
                    'sdkVersion': '3.9.0'}
        cases = (
            (TimeoutError('private'), {'state': 'timeout'}),
            (TVRejected('private', {'errorCode': -72}), {'state': 'rejected', 'error_code': -72}),
            ({'returnValue': True, 'configs': {}}, {'state': 'not-configured'}),
        )
        info = {}
        for reply, expected in cases:
            with self.subTest(expected=expected):
                remote = Mock()
                remote.luna.side_effect = [identity, reply]
                self.assertIsNotNone(compositor_failure(remote, info))
                self.assertEqual(tv_summary(info)['root_keyfilters_probe'], expected)
                self.assertNotIn('private', json.dumps(tv_summary(info)))

        remote.luna.side_effect = [PROFILES, SETTINGS]
        verify(remote, CheckList(), info, allow_c1=True, allow_compositor=True)
        self.assertNotIn('root_keyfilters_probe', tv_summary(info))

    def test_compositor_preflight_exports_only_fixed_failure_reasons(self):
        from cytv.diagnostics import create_report
        from cytv.errors import TVCommandError, TVRejected
        from cytv.root_capabilities import RootCapabilityError, verify

        missing = {'returnValue': False, 'errorCode': -1,
                   'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
        identity = {'returnValue': True, 'modelName': 'AR-50',
                    'firmwareVersion': '04.66.75', 'sdkVersion': '7.5.9'}
        key = 'com.webos.surfacemanager.keyFilters'
        chain = {'returnValue': True, 'configs': {key: [
            {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]}}
        private = 'private-remote-data'
        cases = (
            ([TimeoutError(private)], '', 'c1-probe-failed'),
            ([identity, TimeoutError(private)], '', 'system-info-request-failed'),
            ([identity, dict(identity, sdkVersion=private)], '', 'system-info-invalid'),
            ([identity, identity, TimeoutError(private)], '', 'keyfilters-request-failed'),
            ([identity, identity, TVRejected(private)], '', 'keyfilters-request-failed'),
            ([identity, identity, {'returnValue': False, 'errorText': private}], '', 'keyfilters-request-failed'),
            ([identity, identity, {'returnValue': True, 'configs': {}}], '', 'keyfilters-not-configured'),
            ([identity, identity, {'returnValue': True, 'configs': {key: []}}], '', 'keyfilters-not-configured'),
            ([identity, identity, {'returnValue': True, 'configs': None}], '', 'keyfilters-incompatible'),
            ([identity, identity, {'returnValue': True, 'configs': {key: None}}], '', 'keyfilters-incompatible'),
            ([identity, identity, {'returnValue': True, 'configs': {key: [private]}}], '', 'keyfilters-incompatible'),
            ([identity, identity, chain], TVCommandError(42), 'native-home-unavailable'),
            ([identity, identity, chain], TVCommandError(127), 'native-home-request-failed'),
            ([identity, identity, chain], TimeoutError(private), 'native-home-request-failed'),
            ([identity, identity, chain], private, 'native-home-incompatible'),
        )
        for replies, native, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as folder:
                remote = Mock()
                remote.luna.side_effect = [missing, *replies]
                if isinstance(native, Exception):
                    remote.run.side_effect = native
                else:
                    remote.run.return_value = native
                info = {}
                checks = CheckList()
                with self.assertRaises(RootCapabilityError) as failure:
                    verify(remote, checks, info, allow_c1=True, allow_compositor=True)
                store = state.Store(folder)
                profile = state.target('192.0.2.10', 'root')
                report = create_report(store, 'install', profile, 'inspect-installation', failure.exception, info)
                data = report.read_text()
                tv = json.loads(data)['tv']
                self.assertEqual(tv.get('root_compositor_failure'), expected)
                self.assertEqual(tv['root_capabilities']['home-profiles'], 'service-absent')
                self.assertNotIn('home_backend', tv)
                self.assertNotIn(private, data)

                remote.luna.side_effect = [PROFILES, SETTINGS]
                verify(remote, checks, info, allow_c1=True, allow_compositor=True)
                report = create_report(store, 'install', profile, 'inspect-installation', tv_info=info)
                self.assertNotIn('root_compositor_failure', json.loads(report.read_text())['tv'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX shell probe')
    def test_home_mount_probe_classifies_topology_without_exporting_paths(self):
        import subprocess
        from cytv.root_capabilities import NATIVE_HOME_MOUNT_PROBE

        root = '10 1 8:1 / / rw - ext4 /dev/private rw'
        mount = '20 10 8:1 /private/file /usr/bin/com.webos.app.home rw shared:2 - ext4 /dev/private rw'
        stacked = mount.replace('20 10 ', '21 20 ', 1)
        overlay = '15 10 0:23 / /usr rw - overlay overlay rw,upperdir=/private/path'
        parent = '16 10 8:1 /private/bin /usr/bin rw - ext4 /dev/private rw'
        other = mount.replace('app.home ', 'app.home.other ', 1)
        cases = (
            ([], 'absent'),
            ([other], 'absent'),
            ([mount], 'file-mount'),
            ([mount, stacked], 'stacked-file-mounts'),
            ([overlay], 'parent-overlay'),
            ([parent], 'parent-mount'),
            ([overlay, parent], 'multiple-parent-mounts'),
            ([overlay, mount], 'file-and-parent-mounts'),
            (['20 10 8:1 / /usr/bin/com.webos.app.home rw'], 'unknown'),
        )
        command = NATIVE_HOME_MOUNT_PROBE.replace('/proc/self/mountinfo', '-')
        for rows, expected in cases:
            with self.subTest(expected=expected):
                reply = subprocess.run(['/bin/sh', '-c', command], input='\n'.join([root, *rows]) + '\n',
                                       text=True, capture_output=True, check=True)
                self.assertEqual(reply.stdout.strip(), expected)

    @unittest.skipUnless(os.name == 'posix', 'POSIX shell probe')
    def test_home_mount_recovery_guard_rejects_unsafe_mount_tables(self):
        import subprocess
        from cytv.root_capabilities import NATIVE_HOME_MOUNT_SNAPSHOT, NATIVE_HOME_STOCK_MOUNT

        root = '10 1 179:1 / / ro - squashfs /dev/mmcblk0p1 ro'
        mount = '20 10 8:1 /other/home /usr/bin/com.webos.app.home rw - ext4 /dev/private rw'
        stacked = mount.replace('20 10 ', '21 20 ', 1)
        parent = '15 10 0:23 / /usr rw - overlay overlay rw'
        shared = mount.replace(' - ext4 ', ' shared:9 - ext4 ')
        foreign_parent = mount.replace('20 10 ', '20 99 ', 1)
        snapshot = NATIVE_HOME_MOUNT_SNAPSHOT.replace('/proc/self/mountinfo', '-')
        stock = NATIVE_HOME_STOCK_MOUNT.replace('/proc/self/mountinfo', '-')

        def run(command, *rows):
            return subprocess.run(['/bin/sh', '-c', command], input='\n'.join(rows) + '\n',
                                  capture_output=True, text=True)

        self.assertEqual(run(snapshot, root, mount).stdout.strip(), mount)
        self.assertEqual(run(stock, root).returncode, 0)
        for rows in ((root,), (root, mount, stacked), (root, parent, mount),
                     (root, shared), (root, foreign_parent), (root, mount, 'truncated')):
            with self.subTest(rows=rows):
                result = run(snapshot, *rows)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
        self.assertNotEqual(run(stock, root, mount).returncode, 0)
        self.assertNotEqual(run(stock, root.replace('squashfs', 'ext4')).returncode, 0)

    def test_home_mount_recovery_refuses_ambiguous_or_unverified_input(self):
        from cytv.root_capabilities import NATIVE_HOME_MOUNT_STATES, restore_native_home

        for state in set(NATIVE_HOME_MOUNT_STATES) - {'file-mount'}:
            with self.subTest(state=state):
                remote = Mock()
                self.assertFalse(restore_native_home(remote, state, lambda: True))
                remote.run.assert_not_called()

        remote = Mock()
        remote.run.side_effect = ['20 10 8:1 /private/file /usr/bin/com.webos.app.home rw - ext4 /dev/private rw\n',
                                  'invalid preview']
        confirm = Mock(return_value=True)
        self.assertFalse(restore_native_home(remote, 'file-mount', confirm))
        confirm.assert_not_called()
        self.assertEqual(remote.run.call_count, 2)

    def test_home_mount_recovery_verifies_elf_and_uses_explicit_confirmation(self):
        import struct
        import subprocess
        from cytv.root_capabilities import restore_native_home

        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01',
                             3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(map(str, header))
        fingerprint = 'a' * 64
        preview = f'{fingerprint}\n0 1 755 1024\n{dump}\nCYTV_HOME_ELF\n{dump}\nCYTV_HOME_FS\n73717368\n'
        mount = '20 10 8:1 /private/file /usr/bin/com.webos.app.home rw - ext4 /dev/private rw'
        for accepted in (False, True):
            with self.subTest(accepted=accepted):
                remote = Mock()
                remote.run.side_effect = [mount, preview, preview]
                self.assertIs(restore_native_home(remote, 'file-mount', lambda: accepted), accepted)
                self.assertEqual(remote.run.call_count, 3 if accepted else 2)
                self.assertIn('unshare --mount --propagation private', remote.run.call_args_list[1].args[0])
                if accepted:
                    self.assertIn(fingerprint, remote.run.call_args.args[0])
                    if os.name == 'posix':
                        subprocess.run(['/bin/sh', '-n'], input=remote.run.call_args.args[0], text=True, check=True)

    def test_ar50_home_script_reports_root_refusal_without_no_root_offer(self):
        from cytv.root_capabilities import NoRootAlternativeError, RootCapabilityError, verify

        missing = {'returnValue': False, 'errorCode': -1,
                   'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
        identity = {'returnValue': True, 'modelName': 'AR-50',
                    'firmwareVersion': '04.66.75', 'sdkVersion': '7.5.9'}
        key = 'com.webos.surfacemanager.keyFilters'
        chain = {'returnValue': True, 'configs': {key: [
            {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]}}
        shell = ('127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 3 0 40 0 1 0 0 0 217 218 '
                 '0 0 52 0 0 0 164 98 10 0 0 2 0 5 52 0 32 0 9 0 40 0 29 0 28 0')
        home = ('35 33 47 98 105 110 47 115 104 10 35 32 83 116 97 110 100 115 32 105 '
                '110 32 102 111 114 32 76 71 39 115 32 72 111 109 101 32 112 114 111 '
                '103 114 97 109 32 111 110 32 84 86 115 32 119')
        remote = Mock()
        remote.luna.side_effect = [missing, identity, identity, chain]
        remote.run.side_effect = [f'0 1 755 7582\n{shell}\nCYTV_HOME_ELF\n{home}\nCYTV_HOME_FS\nef53\n',
                                  'file-mount\n']
        info = {}
        with self.assertRaises(RootCapabilityError) as caught:
            verify(remote, CheckList(), info, allow_c1=True, allow_compositor=True)
        self.assertNotIsInstance(caught.exception, NoRootAlternativeError)
        self.assertEqual(info['root_compositor_failure'], 'native-home-script')
        from cytv.diagnostic_context import tv_summary
        self.assertEqual(tv_summary(info)['root_native_home_mount'], 'file-mount')
        self.assertNotIn('root_native_home_mount', tv_summary({'root_native_home_mount': '/private/source'}))
        self.assertNotIn('home_backend', info)
        from cytv.failure_help import for_error
        advice = for_error(caught.exception, 'inspect-installation', {'edition': 'root'})
        self.assertEqual(advice['code'], 'native-home-script')
        self.assertIn('Restore LG Home', advice['next_step'])

    def test_root_report_retains_only_the_rejected_native_home_mode(self):
        import struct
        from cytv.diagnostic_context import tv_summary
        from cytv.diagnostics import create_report
        from cytv.root_capabilities import RootCapabilityError, verify

        missing = {'returnValue': False, 'errorCode': -1,
                   'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
        c1 = {'returnValue': True, 'modelName': 'OLED55C1TEST',
              'firmwareVersion': '03.00.00', 'sdkVersion': '6.0.0'}
        other = dict(c1, modelName='TEST-QT')
        key = 'com.webos.surfacemanager.keyFilters'
        chain = {'returnValue': True, 'configs': {key: [
            {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]}}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01',
                             3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(map(str, header))
        observed = '1001 1 {mode} 5242880\n' + dump + '\nCYTV_HOME_ELF\n' + dump + '\nCYTV_HOME_FS\n73717368'

        for identity, extra, schema in ((c1, [], 2), (other, [other, chain], 3)):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as folder:
                remote = Mock()
                remote.luna.side_effect = [missing, identity, *extra]
                remote.run.return_value = observed.format(mode='775')
                info = {}
                with self.assertRaises(RootCapabilityError) as failure:
                    verify(remote, CheckList(), info, allow_c1=True, allow_compositor=bool(extra))
                store = state.Store(folder)
                profile = state.target('192.0.2.10', 'root')
                report = create_report(store, 'install', profile, 'inspect-installation', failure.exception, info)
                tv = json.loads(report.read_text())['tv']
                self.assertEqual(tv.get('root_native_home_mode'), '0775')
                self.assertNotIn('home_backend', tv)

                remote.luna.side_effect = [missing, identity, *extra]
                remote.run.return_value = observed.format(mode='755')
                self.assertEqual(verify(remote, CheckList(), info, allow_c1=True, allow_compositor=bool(extra)),
                                 'c1-native-gate')
                self.assertEqual(info['home_backend_schema'], schema)
                self.assertNotIn('root_native_home_mode', tv_summary(info))

        for value in ('0775 private-data', 775, '0888', None):
            self.assertNotIn('root_native_home_mode', tv_summary({'root_native_home_mode': value}))

    def test_report_omits_unrecognized_compositor_failure_values(self):
        from cytv.diagnostic_context import tv_summary

        for value in ('private-remote-data', {'raw': 'private-remote-data'}):
            with self.subTest(value=value):
                self.assertNotIn('root_compositor_failure', tv_summary({'root_compositor_failure': value}))

    @unittest.skipUnless(os.name == 'posix', 'POSIX shell probe')
    def test_native_header_command_collects_filesystem_and_refuses_symlink(self):
        import shlex
        import struct
        import subprocess
        from cytv.root_capabilities import NATIVE_HEADERS, native_headers_valid
        header=struct.pack('<16sHHIIIIIHHHHHH',b'\x7fELF\x01\x01\x01',3,40,1,64,52,0,0,52,32,2,0,0,0)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);home=root/'home';shell=root/'shell';bin=root/'bin';bin.mkdir()
            home.write_bytes(header);home.chmod(0o755);shell.write_bytes(header)
            tool=bin/'stat'
            tool.write_text("#!/bin/sh\ncase \"$1\" in -f) echo 73717368 ;; *) echo '1001 1 755 4530960' ;; esac\n")
            tool.chmod(0o755)
            command=NATIVE_HEADERS.replace('/usr/bin/com.webos.app.home',shlex.quote(str(home))).replace('/bin/sh',shlex.quote(str(shell)))
            env=dict(os.environ,PATH=str(bin)+os.pathsep+os.environ.get('PATH',''))
            reply=subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True,text=True,check=True)
            self.assertTrue(native_headers_valid(reply.stdout))
            home.unlink();home.symlink_to(shell)
            self.assertEqual(subprocess.run(['/bin/sh','-c',command],env=env,capture_output=True).returncode,42)

    def test_reported_c1_home_admission_requires_immutable_nonroot_image(self):
        from cytv.root_capabilities import native_headers_valid
        shell = '127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 3 0 40 0 1 0 0 0 9 218 0 0 52 0 0 0 168 210 9 0 0 2 0 5 52 0 32 0 9 0 40 0 29 0 28 0'
        home = '127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 3 0 40 0 1 0 0 0 240 134 2 0 52 0 0 0 56 30 69 0 0 2 0 5 52 0 32 0 10 0 40 0 31 0 30 0'
        for metadata, filesystem, accepted in (
                ('1001 1 755 4530960', '73717368', True),
                ('0 1 755 4530960', '', True),
                ('1001 1 755 4530960', '', False),
                ('1001 1 755 4530960', 'ef53', False),
                ('1001 1 755 4530960', 'unknown', False),
                ('1002 1 755 4530960', '73717368', False),
                ('1001 2 755 4530960', '73717368', False),
                ('1001 1 777 4530960', '73717368', False),
                ('1001 1 4755 4530960', '73717368', False),
                ('1001 1 755 16777217', '73717368', False)):
            with self.subTest(metadata=metadata,filesystem=filesystem):
                reply=metadata+'\n'+shell+'\nCYTV_HOME_ELF\n'+home
                if filesystem: reply+='\nCYTV_HOME_FS\n'+filesystem+'\n'
                self.assertIs(native_headers_valid(reply),accepted)

    def test_normal_and_beta_share_preflight_selection_and_refusal_before_python(self):
        import struct
        from cytv.operations import Installer
        from cytv.root_capabilities import NATIVE_HEADERS, RootCapabilityError
        from cytv.root_runtime import VENDOR_PROBE
        from tests.cytv.test_operations import Remote
        missing = {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(str(n) for n in header)
        observed = '0 1 755 50684\n'+dump+'\nCYTV_HOME_ELF\n'+dump
        chain = [{'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}]
        for beta in (False, True):
            for case in ('profiles', 'keyfilters', 'sdk3', 'sdk5', 'denied', 'unknown-chain', 'missing-native'):
                with self.subTest(beta=beta,case=case), tempfile.TemporaryDirectory() as folder:
                    class TV(Remote):
                        prepared = False
                        def run(self, command, **kwargs):
                            if command == VENDOR_PROBE: return 'CYTV_VENDOR_READY'
                            if command == NATIVE_HEADERS: return '' if case=='missing-native' else observed
                            if 'CYTV_ROOT_READY' in command and '/usr/bin/python3' in command and not self.prepared:
                                return 'CYTV_ROOT_MISSING'
                            return super().run(command, **kwargs)
                        def luna(self, uri, payload, **kwargs):
                            if 'systemprofile' in uri:
                                return copy.deepcopy(PROFILES if case=='profiles' else dict(missing,errorText='Access denied') if case=='denied' else missing)
                            if 'getSystemInfo' in uri:
                                return dict(returnValue=True,modelName='55NANO77SRA',firmwareVersion='23.25.55',sdkVersion={'sdk3':'3.9.0','sdk5':'5.6.2'}.get(case,'9.2.2'))
                            if 'getConfigs' in uri:
                                return {'returnValue':True,'configs':{'com.webos.surfacemanager.keyFilters':[] if case=='unknown-chain' else chain}}
                            if 'getSystemSettings' in uri: return copy.deepcopy(SETTINGS)
                            return super().luna(uri,payload,**kwargs)
                    remote=TV();root=Path(folder)
                    profile=state.target('192.0.2.10','root',**({'root_variant':'node012-beta'} if beta else {}))
                    manifest={'root_backends':{'c1-native-gate':{'admission_schema':3}}}
                    with patch('cytv.root_runtime.select_payload',return_value=(root,manifest)):
                        installer=Installer(remote,state.Store(root/'host'),profile,root,manifest)
                    def provision(**kwargs):
                        self.assertEqual(kwargs,{'provision':True})
                        self.assertEqual(installer.tv_info['home_backend'],'system-profile' if case=='profiles' else 'c1-native-gate')
                        remote.prepared=True
                        return '/usr/bin/python3'
                    with patch.object(installer,'_python',return_value='/usr/bin/python3'), patch.object(installer,'_select_python',side_effect=provision) as prepare:
                        if case in ('profiles','keyfilters','sdk3','sdk5'):
                            installer.preflight(install=True,home_interfaces=True)
                            prepare.assert_called_once_with(provision=True)
                            if case!='profiles': self.assertEqual(installer.tv_info['home_backend_schema'],3)
                        else:
                            with self.assertRaises(RootCapabilityError):
                                installer.preflight(install=True,home_interfaces=True)
                            prepare.assert_not_called()
                    self.assertIsNone(installer.store.pending(profile))
                    self.assertEqual(remote.uploads,{})

    def test_generic_compositor_admission_is_capability_based_not_model_list(self):
        import struct
        from cytv.root_capabilities import verify
        missing = {'returnValue':False, 'errorCode':-1, 'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(str(n) for n in header)
        observed = '0 1 755 50684\n'+dump+'\nCYTV_HOME_ELF\n'+dump
        chain = [{'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}]
        for model,sdk,firmware in (('55NANO77SRA','9.2.2','23.25.55'),('OLED55C37LA','8.3.0','13.40.90'),('55UP7000PUA','6.5.3','03.53.45'),('60UJ6050-UA','3.9.0','06.10.55'),('OLED55CXPUA','5.6.2','04.64.00'),('future-native-qt','12.0.0','01.00.00')):
            def luna(uri, payload, **kw):
                if 'systemprofile' in uri: return missing
                if 'getSystemInfo' in uri: return dict(returnValue=True, modelName=model, firmwareVersion=firmware, sdkVersion=sdk)
                if 'getConfigs' in uri: return {'returnValue':True,'configs':{'com.webos.surfacemanager.keyFilters':chain}}
                raise AssertionError(uri)
            remote=Mock();remote.luna.side_effect=luna;remote.run.return_value=observed
            info={}
            self.assertEqual(verify(remote,CheckList(),info,allow_c1=True,allow_compositor=True),'c1-native-gate')
            self.assertEqual(info['home_backend_schema'],3)
            self.assertNotIn('home-profiles',info['root_requirements'])

    def test_generic_compositor_refuses_unknown_chain_or_invalid_identity(self):
        from cytv.root_capabilities import compositor_failure
        cases = (
            ('11.2.0', [], 'keyfilters-not-configured'),
            ('9.2.2', [], 'keyfilters-not-configured'),
            ('invalid', [], 'system-info-invalid'),
            ('9.2.2', [{'file':'/foreign/home.js','handler':'handleSystemKeys'}], 'keyfilters-incompatible'),
        )
        for sdk, chain, expected in cases:
            remote=Mock()
            remote.luna.side_effect=[dict(returnValue=True,modelName='55NANO77SRA',firmwareVersion='23.25.55',sdkVersion=sdk),
                {'returnValue':True,'configs':{'com.webos.surfacemanager.keyFilters':chain}}]
            self.assertEqual(compositor_failure(remote), expected)
            remote.run.assert_not_called()

    def test_legacy_ribbon_requires_positive_readback_and_confirmed_missing_routing(self):
        from cytv.errors import TVRejected
        from cytv.root_capabilities import RootCapabilityError, verify

        missing = {'returnValue': False, 'errorCode': -1,
                   'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
        config_uri = 'com.webos.service.config/getConfigs'
        config_absent = TVRejected('missing config', dict(missing,
            errorText='Service does not exist: com.webos.service.config.'), config_uri)
        config_denied = TVRejected('denied config', dict(missing, errorText='Access denied'), config_uri)
        config_empty = {'returnValue': True, 'configs': {}}
        identity = {'returnValue': True, 'modelName': 'OTHER-LEGACY-TV',
                    'firmwareVersion': '04.66.75', 'sdkVersion': '3.5.0'}
        home = {'homeUIState': [{'uiType': 'home', 'visibility': False}], 'private': 'drop-me'}

        for config, reply, expected, probe in (
                (config_empty, home, 'LegacyRibbonError', 'readable'),
                (config_absent, home, 'LegacyRibbonError', 'readable'),
                (config_empty, {'homeUIState': [{'uiType': 'home', 'visibility': 0}]},
                 'RootCapabilityError', 'invalid-reply'),
                (config_empty, TimeoutError(), 'RootCapabilityError', 'timeout'),
                (config_denied, home, 'RootCapabilityError', None),
                (TimeoutError(), home, 'RootCapabilityError', None)):
            with self.subTest(config=config, reply=reply):
                from cytv.diagnostic_context import tv_summary
                remote = Mock()
                remote.luna.side_effect = [missing, identity, identity, config, reply]
                info = {}
                with self.assertRaises(RootCapabilityError) as raised:
                    verify(remote, CheckList(), info, allow_c1=True, allow_compositor=True)
                self.assertEqual(type(raised.exception).__name__, expected)
                report = tv_summary(info)
                self.assertEqual(report.get('root_ribbon_probe'), probe)
                self.assertNotIn('drop-me', str(report))
                self.assertNotIn('home_backend', info)
                remote.run.assert_not_called()

    def test_generic_permission_denial_never_enters_native_admission(self):
        from cytv.root_capabilities import verify,RootCapabilityError
        remote=Mock();remote.luna.return_value={'returnValue':False,'errorCode':-1,'errorText':'Access denied'}
        with self.assertRaises(RootCapabilityError): verify(remote,CheckList(),{},allow_c1=True,allow_compositor=True)
        remote.run.assert_not_called()

    def verify(self, settings=SETTINGS, profiles=PROFILES):
        from cytv.root_capabilities import verify
        remote=Mock();remote.luna.side_effect=[copy.deepcopy(settings),copy.deepcopy(profiles)]
        info={};checks=CheckList()
        verify(remote, checks, info)
        return remote,checks,info

    def test_absent_settings_override_and_false_support_match_runtime_contract(self):
        remote, checks, info=self.verify()
        self.assertEqual([x['status'] for x in checks.results.values()],['pass','pass'])
        self.assertEqual(info['root_capabilities'],{'home-settings':'readable','home-profiles':'readable'})
        self.assertTrue(all(c.kwargs['timeout']==5 for c in remote.luna.call_args_list))
        self.assertNotIn('com.webos.app.home', str(info))

    def test_invalid_readback_is_not_a_capability(self):
        from cytv.errors import UserError
        for settings, profiles in [({},PROFILES),(SETTINGS,{}),
            ({'returnValue':False,'settings':{'defaultApps':{}}},PROFILES),
            (SETTINGS,{'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':' ' }},'idleApp':{'appId':'com.webos.app.home','support':True}}})]:
            with self.subTest(settings=settings,profiles=profiles),self.assertRaises(UserError):self.verify(settings,profiles)

    def test_reported_missing_home_interfaces_are_distinct_from_rejection(self):
        from cytv.diagnostic_context import tv_summary
        from cytv.root_capabilities import CALLS, RootCapabilityError, verify
        from cytv.transport import terminal_reply

        missing_settings = {'returnValue': False, 'errorCode': None,
                            'errorText': 'There is no matched result from DB'}
        missing_profiles = {'returnValue': False, 'errorCode': -1,
                            'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
        for settings, profiles, expected in (
                (missing_settings, missing_profiles, ('setting-not-found', 'service-absent')),
                (dict(missing_settings, errorText='Access denied'),
                 dict(missing_profiles, errorText='Access denied'), ('rejected', 'rejected')),
                (dict(missing_settings, errorCode=-1), missing_profiles, ('rejected', 'service-absent'))):
            for use_transport in (False, True):
                with self.subTest(expected=expected, use_transport=use_transport):
                    replies = dict(zip((uri for uri, _ in CALLS.values()), (settings, profiles)))

                    def luna(uri, payload, **kwargs):
                        reply = replies[uri]
                        if use_transport:
                            terminal_reply(reply, uri=uri)
                        return reply

                    remote = Mock()
                    remote.luna.side_effect = luna
                    info, checklist = {}, CheckList()
                    with self.assertRaises(RootCapabilityError) as raised:
                        verify(remote, checklist, info)
                    self.assertIs(type(raised.exception), RootCapabilityError)
                    self.assertEqual(raised.exception.reason_code, 'root-home-interfaces')
                    summary = tv_summary(info)
                    self.assertEqual(summary['root_capabilities'], dict(zip(CALLS, expected)))
                    self.assertEqual(summary['root_requirements'], dict.fromkeys(CALLS, 'fail'))
                    self.assertEqual(summary['root_capability_codes']['home-profiles'], -1)
                    self.assertNotIn('errorText', str(summary))
                    self.assertNotIn('home_backend', info)
                    remote.run.assert_not_called()

    def test_denied_timedout_and_malformed_calls_keep_fixed_reasons_only(self):
        from cytv.root_capabilities import verify
        from cytv.errors import TVRejected, UserError
        for error,reason in [(TVRejected('PRIVATE-KEY',{'errorCode':-1}),'rejected'),
                             (TimeoutError('PRIVATE-IP'),'unconfirmed')]:
            remote=Mock();remote.luna.side_effect=[error,copy.deepcopy(PROFILES)]
            info={};checks=CheckList()
            with self.assertRaises(UserError):verify(remote,checks,info)
            self.assertEqual(info['root_capabilities']['home-settings'],reason)
            self.assertEqual(checks.results['home-profiles']['status'],'pass')
            self.assertNotIn('PRIVATE',str(info))

    def test_error_codes_are_retained_but_routes_and_untrusted_fields_are_not_exported(self):
        from cytv.root_capabilities import verify
        from cytv.diagnostic_context import tv_summary
        from cytv.errors import TVRejected, UserError
        remote=Mock();remote.luna.side_effect=[TVRejected('PRIVATE',{'returnValue':False,'errorCode':-1}),copy.deepcopy(PROFILES)]
        info={}
        with self.assertRaises(UserError):verify(remote,CheckList(),info)
        self.assertEqual(tv_summary(info)['root_capability_codes'],{'home-settings':-1})
        info['root_capability_codes'].update({'home-profiles':True,'PRIVATE':123})
        self.assertEqual(tv_summary(info)['root_capability_codes'],{'home-settings':-1})
        self.assertNotIn('PRIVATE',str(tv_summary(info)))

    def test_queries_and_validation_stay_aligned_with_current_root_contract(self):
        from cytv.root_capabilities import CALLS
        tree=ast.parse((Path(__file__).resolve().parents[2]/'root-edition/provision.py').read_text())
        rpc=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rpc')
        calls=next(ast.literal_eval(n.value) for n in rpc.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='home_calls' for x in n.targets))
        self.assertEqual(CALLS['home-settings'],calls['home-read'])
        self.assertEqual(CALLS['home-profiles'],calls['home-profiles'])
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_home_interfaces')
        scope={'rpc':lambda method:copy.deepcopy(SETTINGS if method=='home-read' else PROFILES)}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'root-home-contract','exec'),scope)
        scope['require_home_interfaces']()
        self.verify()

    def test_interface_failure_precedes_private_python_and_any_install_submission(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote
        from cytv.errors import UserError
        class TV(Remote):
            def luna(self,uri,payload,**kwargs):
                if uri=='com.webos.service.systemprofile/getProfiles':
                    return {'returnValue':False,'errorCode':-1}
                if uri=='com.webos.settingsservice/getSystemSettings':return copy.deepcopy(SETTINGS)
                return super().luna(uri,payload,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            remote=TV();profile=state.target('192.0.2.10','root');store=state.Store(tmp)
            inst=Installer(remote,store,profile,Path(tmp),{})
            with patch.object(inst,'_python',return_value='/usr/bin/python3'),patch.object(inst,'_select_python') as prepare:
                # Force only Python missing, which previously permitted provisioning.
                run=remote.run
                remote.run=lambda command,**kw:'CYTV_ROOT_MISSING' if 'CYTV_ROOT_READY' in command and '/usr/bin/python3' in command else run(command,**kw)
                with self.assertRaises(UserError):inst.preflight(install=True,home_interfaces=True)
                prepare.assert_not_called()
            self.assertIsNone(store.pending(profile))
            self.assertFalse(any(c[0]=='upload' for c in remote.calls))
            self.assertFalse(any(c[0]=='luna' and c[1].endswith(('/install','/launch')) for c in remote.calls))

    def test_reinstall_gate_precedes_removal_or_new_submission(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote
        from cytv.errors import UserError
        remote=Remote();luna=remote.luna
        def reject(uri,payload,**kwargs):
            if uri=="com.webos.service.systemprofile/getProfiles":return {'returnValue':False}
            return luna(uri,payload,**kwargs)
        remote.luna=reject
        with tempfile.TemporaryDirectory() as tmp:
            profile=state.target('192.0.2.10','root');store=state.Store(tmp)
            inst=Installer(remote,store,profile,tmp,{})
            with patch.object(inst,'select_graphics'),patch.object(inst,'install_root') as submit:
                with self.assertRaises(UserError):inst.install({'apps':[{'id':'youtube','title':'YouTube','icon':'data:image/png;base64,AA=='}],'inputs':[]},reinstall='installed')
                submit.assert_not_called()
            self.assertIsNone(store.pending(profile))
            self.assertFalse(any(c[0]=='upload' for c in remote.calls))

    def test_common_beta_selects_only_confirmed_native_c1(self):
        import struct
        from cytv.root_capabilities import verify
        from cytv.root_capabilities import RootCapabilityError
        missing = {'returnValue':False, 'errorCode':-1, 'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        info = {'returnValue':True, 'modelName':'OLED65C14LB', 'firmwareVersion':'03.51.15', 'sdkVersion':'6.5.3-47'}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(str(n) for n in header)
        observed = '0 1 755 50684\n' + dump + '\nCYTV_HOME_ELF\n' + dump
        remote = Mock()
        for reply, device, observed_elf, accepted in (
                (missing, info, observed, True), (missing, dict(info,modelName='55UP7000PUA'),observed,False),
                (missing, dict(info,sdkVersion='7.0.0'),observed,False), (missing,info,observed.replace('127','128'),False),
                (missing,info,observed.replace('0 1 755','0 1 777'),False),
                (dict(missing,errorText='Access denied'),info,observed,False),
                (dict(missing,errorText='Service does not exist: com.example.other.'),info,observed,False),
                (TimeoutError(),info,observed,False)):
            with self.subTest(reply=reply,device=device):
                remote.reset_mock()
                remote.luna.side_effect = [reply,device]
                remote.run.return_value = observed_elf
                summary = {'home_backend':'stale'}
                if accepted:
                    self.assertEqual(verify(remote,CheckList(),summary,allow_c1=True),'c1-native-gate')
                    self.assertEqual(summary['root_capabilities']['home-profiles'],'service-absent')
                    self.assertNotIn('home-profiles',summary['root_requirements'])
                    self.assertEqual(summary['home_backend'],'c1-native-gate')
                    self.assertFalse(any('getSystemSettings' in str(c) for c in remote.luna.call_args_list))
                else:
                    with self.assertRaises(RootCapabilityError):
                        verify(remote,CheckList(),summary,allow_c1=True)
                    self.assertNotIn('home_backend',summary)

    def test_real_ssh_transport_preserves_only_the_exact_missing_profile_flag(self):
        from cytv.errors import TVRejected
        from cytv.transport import terminal_reply
        from cytv.root_capabilities import verify
        uri='com.webos.service.systemprofile/getProfiles'
        reply={'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        for target, value, expected in ((uri,reply,True),(uri,dict(reply,errorCode='-1'),False),
                (uri,dict(reply,errorText='denied'),False),('com.example.service/query',reply,False)):
            with self.subTest(target=target,value=value), self.assertRaises(TVRejected) as rejected:
                terminal_reply(value, uri=target)
            self.assertIs(rejected.exception.systemprofile_missing, expected)
            self.assertNotIn('errorText',rejected.exception.luna)
            if expected:
                remote=Mock()
                remote.luna.side_effect=rejected.exception
                with patch('cytv.root_capabilities.c1_device', return_value=True):
                    self.assertEqual(verify(remote,CheckList(),{},allow_c1=True),'c1-native-gate')

    def test_detected_profile_prefers_normal_product_without_native_probe(self):
        from cytv.root_capabilities import verify
        remote=Mock()
        remote.luna.side_effect=[PROFILES, SETTINGS]
        info={}
        self.assertEqual(verify(remote,CheckList(),info,allow_c1=True), 'system-profile')
        remote.run.assert_not_called()
        self.assertEqual(info['home_backend'],'system-profile')

    def test_default_maintenance_preflight_does_not_add_home_queries(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote
        with tempfile.TemporaryDirectory() as tmp:
            remote=Remote();inst=Installer(remote,state.Store(tmp),state.target('192.0.2.10','root'),tmp,{})
            inst.preflight()
            self.assertFalse(any(c[0]=='luna' for c in remote.calls))

    def test_doctor_only_adds_home_queries_when_no_operation_is_pending(self):
        from cytv import cli
        for pending in (False,True):
            with self.subTest(pending=pending),tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.Installer') as cls:
                profile=state.target('192.0.2.10','root');store=state.Store(tmp)
                if pending:
                    store.begin(profile,'install');store.save(profile)
                    (store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
                cls.return_value.status.return_value={}
                code=cli.main(['doctor','--host',profile['host'],'--edition','root','--data-dir',tmp],
                              connect=lambda *a:Mock(),write=lambda _:None)
                self.assertEqual(code,0)
                if pending:cls.return_value.preflight.assert_called_once_with()
                else:cls.return_value.preflight.assert_called_once_with(home_interfaces=True)
