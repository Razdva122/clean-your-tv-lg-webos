"""Host-only compositor routing and ownership tests; no TV acceptance."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'runtime'), str(ROOT)]


class RuntimeTests(unittest.TestCase):

    def test_bsp_lower_home_accepts_anonymous_overlay_device_only_without_shadow(self):
        import stat

        lines = [
            '1 0 179:27 / / ro - squashfs /dev/root ro',
            '2 1 0:34 / /usr rw - overlay overlay ro,lowerdir=/overlay/bsppart/bsp/usr:/usr',
            '3 1 179:29 / /overlay/bsppart ro - squashfs /dev/mmcblk0p29 ro',
        ]
        critical = ('/usr/bin/com.webos.app.home', '/usr/palm/applications/com.webos.app.home')
        bsp = '/overlay/bsppart/bsp/usr'
        real_lstat = Path.lstat
        for home_device, shadow, bin_kind, extra_mount, accepted in (
                ((179, 27), False, 'missing', None, True),
                ((0, 45), False, 'missing', None, True),
                ((0, 45), False, 'directory', None, True),
                ((0, 34), False, 'directory', None, False),
                ((179, 30), False, 'directory', None, False),
                ((0, 45), True, 'directory', None, False),
                ((0, 45), False, 'symlink', None, False),
                ((0, 45), False, 'denied', None, False),
                ((0, 45), False, 'directory', bsp + '/bin', False),
                ((0, 45), False, 'directory', bsp + '/bin/com.webos.app.home', False)):
            with self.subTest(device=home_device, shadow=shadow, bin_kind=bin_kind, mount=extra_mount):
                mounts = []
                for line in lines + ([f'4 3 0:99 / {extra_mount} ro - tmpfs tmpfs ro'] if extra_mount else []):
                    fields = line.split()
                    index = fields.index('-')
                    mounts.append((fields, fields[4], fields[index+1], fields[index+2],
                                   fields[index+3].split(',')))
                devices = dict(zip((*critical, bsp), (home_device, (0, 34), (179, 29))))

                def lower_lstat(path, *args, **kwargs):
                    if str(path) == bsp + '/bin':
                        if bin_kind == 'missing':
                            raise FileNotFoundError()
                        if bin_kind == 'denied':
                            raise PermissionError()
                        return SimpleNamespace(st_mode=stat.S_IFLNK if bin_kind == 'symlink' else stat.S_IFDIR)
                    if str(path) == bsp + '/bin/com.webos.app.home':
                        if shadow:
                            return SimpleNamespace(st_mode=stat.S_IFREG)
                        raise FileNotFoundError()
                    return real_lstat(path, *args, **kwargs)

                def trusted(path):
                    if str(path) == bsp + '/bin' and bin_kind == 'symlink':
                        raise ValueError('Unsafe experimental backend directory')

                with patch.object(self.k.os, 'stat', side_effect=lambda path, **kw:
                        SimpleNamespace(st_dev=devices[str(path)])), \
                        patch.object(self.k.os, 'major', side_effect=lambda device: device[0]), \
                        patch.object(self.k.os, 'minor', side_effect=lambda device: device[1]), \
                        patch.object(Path, 'lstat', lower_lstat), \
                        patch.object(self.k.legacy, 'trusted_directory', side_effect=trusted):
                    try:
                        actual = self.k.stock_bsp_overlay(mounts, mounts[1], critical)
                    except (OSError, ValueError):
                        actual = False
                    self.assertEqual(actual, accepted)

    def read_factory_home_setting(self, uri, payload, *, allow_failure):
        self.assertEqual(uri, 'luna://com.webos.settingsservice/getSystemSettings')
        self.assertEqual(payload, {'category': 'general', 'keys': ['defaultApps']})
        self.assertTrue(allow_failure)
        return {'returnValue': True, 'settings': {'defaultApps': {'home': self.k.STOCK}}}

    def test_missing_plural_home_setting_uses_factory_single_key_request(self):
        missing = {'returnValue': True, 'settings': {'defaultApps': {}}}
        stock = {'returnValue': True, 'settings': {'defaultApps': {'home': self.k.STOCK}}}
        with patch.object(self.k, 'luna', side_effect=[missing, stock]) as setting:
            self.k.require_stock_home_destination()
        self.assertEqual([request.args[1] for request in setting.call_args_list], [
            {'category': 'general', 'keys': ['defaultApps']},
            {'category': 'general', 'key': 'defaultApps'},
        ])

    def test_restore_failure_preserves_native_reason_without_accepting_refusal(self):
        from types import SimpleNamespace
        failure = dict(self.proof(), returnValue=False, reason='ui_release_failed')
        with patch.object(self.k, 'binary'), patch.object(self.k.subprocess, 'run',
                return_value=SimpleNamespace(returncode=1, stdout=json.dumps(failure).encode())), \
                patch.object(self.k, 'change_chain') as change:
            with self.assertRaisesRegex(ValueError, 'Native compositor recovery failed') as caught:
                self.k.restore_locked(self.root, self.uid)
            change.assert_not_called()
        self.assertEqual(caught.exception.native_reason, 'ui_release_failed')
        self.assertEqual(caught.exception.restore_check, 'native-restore-unverified')

    def test_restore_failure_distinguishes_stock_home_identity(self):
        with patch.object(self.k, 'native', side_effect=[{}, dict(self.proof(), stock_verified=False)]), \
                patch.object(self.k, 'selection', return_value={'schema': 2}), \
                patch.object(self.k, 'change_chain') as change:
            with self.assertRaisesRegex(ValueError, 'Native stop retirement unverified') as caught:
                self.k.restore_locked(self.root, self.uid)
            change.assert_not_called()
        self.assertEqual(caught.exception.restore_check, 'stock-home-unverified')


    def test_restore_failure_survives_runtime_and_deploy_envelopes(self):
        import contextlib
        import io
        import subprocess
        import cli as runtime_cli
        import deploy

        failure = ValueError('PRIVATE')
        failure.restore_check = 'native-restore-unverified'
        failure.native_reason = 'retirement_failed'
        child_reply = runtime_cli.runtime_failure('restore', failure)
        child_reply['root_restore_failure']['token'] = 'PRIVATE'

        def command(_args):
            raise subprocess.CalledProcessError(1, ['PRIVATE'], output=json.dumps(child_reply).encode())

        with patch.object(deploy, 'python_command', return_value=sys.executable), \
                patch.object(deploy, 'main', side_effect=lambda: deploy.restore(run=command)), \
                contextlib.redirect_stdout(io.StringIO()) as output, self.assertRaises(SystemExit) as caught:
            deploy.entrypoint()
        self.assertEqual(caught.exception.code, 1)
        outer = json.loads(output.getvalue())
        self.assertFalse(outer['returnValue'])
        self.assertEqual(outer['root_restore_failure'], {
            'restore_check': 'native-restore-unverified', 'native_reason': 'retirement_failed'})
        self.assertNotIn('PRIVATE', output.getvalue())

    def test_large_stock_home_is_read_with_immutable_nonroot_proof(self):
        import hashlib
        import stat
        import struct
        from types import SimpleNamespace
        target=self.root/'stock-home'
        header=struct.pack('<16sHHIIIIIHHHHHH',b'\x7fELF\x01\x01\x01',3,40,1,64,52,0,0,52,32,2,0,0,0)
        content=header+b'\0'*(4530960-len(header))
        target.write_bytes(content);target.chmod(0o755)
        original=os.fstat
        def attributes(fd):
            observed=original(fd)
            return SimpleNamespace(st_uid=1002,st_nlink=observed.st_nlink,
                st_mode=observed.st_mode,st_size=observed.st_size,st_dev=observed.st_dev,st_ino=observed.st_ino,st_mtime_ns=observed.st_mtime_ns,st_ctime_ns=observed.st_ctime_ns)
        with patch.object(self.k.legacy,'TARGET',target), patch.object(self.k.legacy,'trusted_directory'), patch.object(os,'fstat',side_effect=attributes), patch.object(os,'fstatvfs',create=True,return_value=SimpleNamespace(f_flag=1)), patch.object(self.k.legacy.subprocess,'run',return_value=SimpleNamespace(stdout=b'73717368\n',returncode=0)) as filesystem:
            self.assertEqual(hashlib.sha256(self.k.legacy.native_home()).hexdigest(),hashlib.sha256(content).hexdigest())
            self.assertTrue(filesystem.called)
            device=dict(returnValue=True,modelName='OLED55C16LA',firmwareVersion='03.53.45',sdkVersion='6.5.3')
            with patch.object(self.k.os,'geteuid',return_value=0), patch.object(self.k.sys,'platform','linux'), patch('struct.calcsize',return_value=4), patch.object(self.k,'luna',return_value=device), patch.object(self.k,'read_chain',return_value=[]), patch.object(self.k,'require_generic_environment') as environment:
                observed=self.k.probe()
                self.assertEqual(observed['target']['size'],4530960)
                self.assertEqual(observed['target_sha256'],hashlib.sha256(content).hexdigest())
                environment.assert_called_once_with(removed_apps=(self.k.APP,))
            # Root-owned stock files retain admission without a filesystem exception.
            def root_attributes(fd):
                value=attributes(fd); value.st_uid=0; return value
            with patch.object(os,'fstat',side_effect=root_attributes), patch.object(self.k.legacy.subprocess,'run',side_effect=AssertionError('root needs no exception')):
                self.assertEqual(self.k.legacy.native_home(),content)
            for magic,flags in ((b'ef53\n',1),(b'73717368\n',0),(b'unknown\n',1)):
                with self.subTest(magic=magic,flags=flags), patch.object(os,'fstatvfs',return_value=SimpleNamespace(f_flag=flags)):
                    filesystem.return_value=SimpleNamespace(stdout=magic,returncode=0)
                    with self.assertRaises(ValueError): self.k.legacy.native_home()
            filesystem.return_value=SimpleNamespace(stdout=b'73717368\n',returncode=0)
            for change in (dict(st_nlink=2),dict(st_mode=stat.S_IFREG|0o777),dict(st_mode=stat.S_IFREG|0o4755),dict(st_size=16777217)):
                value=dict(st_uid=1001,st_nlink=1,st_mode=stat.S_IFREG|0o755,st_size=4530960);value.update(change)
                with self.subTest(change=change), patch.object(os,'fstat',return_value=SimpleNamespace(**value)):
                    with self.assertRaises(ValueError): self.k.legacy.native_home()

    def test_old_sdk_probe_and_saved_selection_use_capabilities_end_to_end(self):
        import struct
        target=self.root/'native-home'
        header=struct.pack('<16sHHIIIIIHHHHHH',b'\x7fELF\x01\x01\x01',3,40,1,64,52,0,0,52,32,2,0,0,0)
        target.write_bytes(header);target.chmod(0o700)
        for sdk in ('3.9.0','4.4.3','5.6.2','12.0.0'):
            with self.subTest(sdk=sdk),patch.object(self.k.legacy,'TARGET',target),patch.object(self.k.os,'geteuid',return_value=0),patch.object(self.k.sys,'platform','linux'),patch.object(self.k.legacy,'native_home',return_value=header),patch('struct.calcsize',return_value=4),patch.object(self.k,'luna',return_value=dict(returnValue=True,modelName='capability-admitted',firmwareVersion='06.10.55',sdkVersion=sdk)),patch.object(self.k,'require_generic_environment') as environment,patch.object(self.k,'read_chain',return_value=[]):
                observed=self.k.probe()
                self.assertEqual(observed['webos'],sdk)
                self.assertTrue(self.k.admission_valid(observed))
                environment.assert_called_once_with()
                self.admission=observed
                marker=self.prepare()
                self.assertEqual(marker['schema'],3)
                self.assertEqual(self.k.legacy.selection(self.root,self.uid),marker)
                (self.root/'home-backend.json').unlink()
                import shutil
                shutil.rmtree(self.root/'c1-keyfilter')

    def test_vendor_qt5_alias_is_read_only_and_cannot_resolve_outside_vendor_tree(self):
        allowed=Path('/usr/lib/qml/KeyFilters/systemUi.js')
        with patch.object(Path,'resolve',return_value=allowed),patch.object(self.k,'secure',return_value=b'vendor') as read:
            self.assertEqual(self.k.vendor_script('/usr/lib/qt5/qml/KeyFilters/systemUi.js'),b'vendor')
            read.assert_called_once_with(allowed,limit=256*1024)
        with patch.object(Path,'resolve',return_value=Path('/foreign/systemUi.js')),patch.object(self.k,'secure') as read:
            with self.assertRaises(ValueError): self.k.vendor_script('/usr/lib/qt5/qml/KeyFilters/systemUi.js')
            read.assert_not_called()

    def generic(self):
        return dict(self.admission,model='55NANO77SRA',firmware='23.25.55',webos='9.2.2')

    def test_generic_environment_refuses_takeover_and_requires_exact_absence(self):
        missing={'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        vendor={'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}
        app={'id':'com.webos.app.home','type':'native','main':'file:///usr/bin/com.webos.app.home'}
        mountinfo=self.root/'mountinfo';mountinfo.write_text('1 0 0:1 / / rw - squashfs /dev/root ro\n')
        appinfo=self.root/'appinfo.json';appinfo.write_text(json.dumps(app));appinfo.chmod(0o600)
        other=self.root/'other-home'
        bindings=self.root/'bindings.json'
        import emergency_reader
        keys=bytearray(128)
        for code in (773,412):keys[code//8]|=1<<(code%8)
        def reader():
            fd=os.open(os.devnull,os.O_RDONLY);return fd
        real_secure=self.k.secure
        def secure(path,*args,**kw):
            if str(path)==vendor['file']:return b'function handleSystemKeys() { return Qt.Key_Super_L; }'
            if str(path)=='/usr/palm/applications/com.webos.app.home/appinfo.json':return json.dumps(app).encode()
            return real_secure(path,self.uid,*args,**kw)
        with patch.object(self.k,'STOCK_APPINFO',appinfo),patch.object(self.k,'MOUNTINFO',mountinfo),patch.object(self.k,'OTHER_HOME_STATE',(other,)),patch.object(self.k,'INPUT_BINDINGS',bindings),patch.object(self.k,'secure',side_effect=secure),patch.object(self.k,'vendor_script',side_effect=lambda path:secure(Path(path))),patch.object(self.k,'luna',return_value=missing),patch.object(self.k,'read_chain',return_value=[vendor]),patch.object(emergency_reader,'open_remote',side_effect=reader),patch.object(emergency_reader,'query',return_value=keys):
            self.k.require_generic_environment()
            glasshouse = {'file': '/var/lib/tvweb/remotekeys-filter.js', 'handler': 'handleGlasshouseKeys'}
            other_launcher = {'file': '/media/developer/other/systemUi.js', 'handler': 'handleSystemKeys'}
            mixed = [glasshouse, vendor, other_launcher]
            with self.assertRaisesRegex(ValueError, 'Stock Qt Home'):
                self.k.require_generic_environment(mixed)
            with patch.object(self.k, 'vendor_script', wraps=self.k.vendor_script) as read_vendor:
                self.k.require_generic_environment(mixed, removed_apps=('com.cleanyourtv.root.preview',))
            read_vendor.assert_called_once_with(vendor['file'])
            # A separate, whole read-only system image is not a Home takeover.
            stock_mount='2 1 179:27 / /usr ro,relatime - squashfs /dev/mmcblk0p27 ro\n'
            from types import SimpleNamespace
            # Encode Linux mountinfo device pairs without using the host's dev_t.
            def device_id(major, minor):
                return major * 256 + minor

            for name, extract in (('major', lambda dev: dev // 256), ('minor', lambda dev: dev % 256)):
                override = patch.object(self.k.os, name, side_effect=extract)
                override.start()
                self.addCleanup(override.stop)
            with patch.object(self.k,'STOCK_APPINFO',Path('/usr/palm/applications/com.webos.app.home/appinfo.json')),patch.object(self.k.legacy,'TARGET',Path('/usr/bin/com.webos.app.home')),patch.object(self.k.os,'stat',return_value=SimpleNamespace(st_dev=device_id(179,27))):
                mountinfo.write_text(stock_mount)
                self.k.require_generic_environment()
                for invalid in (
                    stock_mount.replace(' / /usr ', ' /foreign /usr '),
                    stock_mount.replace('/usr ro,', '/usr rw,'),
                    stock_mount.replace('p27 ro\n', 'p27 rw\n'),
                    stock_mount.replace('squashfs', 'overlay'),
                    stock_mount.replace('179:27', '179:28'),
                    stock_mount.replace('/dev/mmcblk0p27', '/dev/loop0'),
                    stock_mount+stock_mount.replace('2 1 ', '3 1 '),
                    stock_mount+'3 2 0:2 / /usr/bin ro - tmpfs tmpfs ro\n',
                    stock_mount+'3 2 0:2 / /usr/bin/com.webos.app.home ro - tmpfs tmpfs ro\n',
                    stock_mount+'3 2 0:2 / /usr/palm/applications/com.webos.app.home ro - tmpfs tmpfs ro\n',
                ):
                    with self.subTest(mounts=invalid):
                        mountinfo.write_text(invalid)
                        with self.assertRaises(ValueError):self.k.require_generic_environment()
                root = '1 0 179:27 / / ro - squashfs /dev/root ro\n'
                bsp = '3 1 179:29 / /overlay/bsppart ro - squashfs /dev/mmcblk0p29 ro\n'
                overlay = '2 1 0:34 / /usr rw - overlay overlay ro,lowerdir=/overlay/bsppart/bsp/usr:/usr\n'
                devices = {
                    '/usr/bin/com.webos.app.home': device_id(179, 27),
                    '/usr/palm/applications/com.webos.app.home': device_id(0, 34),
                    '/overlay/bsppart/bsp/usr': device_id(179, 29),
                }
                with patch.object(self.k.os, 'stat', side_effect=lambda path, **kw: SimpleNamespace(st_dev=devices[str(path)])), patch.object(self.k.legacy, 'trusted_directory') as trusted:
                    mountinfo.write_text(root + overlay + bsp)
                    self.k.require_generic_environment()
                    trusted.assert_called_with(Path('/overlay/bsppart/bsp/usr'))
                    for invalid in (
                        root + overlay,
                        root.replace('/ ro -', '/ rw -') + overlay + bsp,
                        root + overlay + bsp.replace('squashfs', 'ext4'),
                        root + overlay.replace('overlay ro,', 'overlay rw,') + bsp,
                        root + overlay.replace(':/usr', ':/usr,upperdir=/foreign') + bsp,
                        root + overlay.replace(':/usr', ':/usr,workdir=/foreign') + bsp,
                        root + overlay.replace(':/usr', ':/usr:/foreign') + bsp,
                        root + overlay.replace(':/usr', ':/usr,lowerdir=/foreign') + bsp,
                        root + overlay.replace(':/usr', ':/usr,datadir+=/foreign') + bsp,
                        root + overlay + bsp + '4 3 0:2 / /overlay/bsppart/bsp ro - tmpfs tmpfs ro\n',
                        root + overlay + bsp + '4 2 0:2 / /usr/bin ro - tmpfs tmpfs ro\n',
                        root + overlay + bsp + overlay.replace('2 1 ', '5 1 '),
                    ):
                        with self.subTest(mounts=invalid):
                            mountinfo.write_text(invalid)
                            with self.assertRaisesRegex(ValueError, 'covered by a mount'):
                                self.k.require_generic_environment()
                    mountinfo.write_text(root + overlay + bsp)
                    devices['/overlay/bsppart/bsp/usr'] = device_id(179, 30)
                    with self.assertRaisesRegex(ValueError, 'covered by a mount'):
                        self.k.require_generic_environment()
            mountinfo.write_text('1 0 0:1 / / rw - squashfs /dev/root ro\n')
            for invalid in (dict(app,type='flutter'),dict(app,type='web'),dict(app,main='ribbon.qml')):
                appinfo.write_text(json.dumps(invalid))
                with self.assertRaisesRegex(ValueError,'manifest'): self.k.require_generic_environment()
            appinfo.write_text(json.dumps(app))
            bindings.write_text('{"773":{"action":"launch","id":"foreign.home"}}');bindings.chmod(0o600)
            with self.assertRaises(ValueError):self.k.require_generic_environment()
            bindings.unlink()
            with patch.object(emergency_reader,'query',return_value=bytearray(128)),self.assertRaises(ValueError):self.k.require_generic_environment()
            other.mkdir()
            with self.assertRaises(ValueError):self.k.require_generic_environment()
            other.rmdir()
            mountinfo.write_text('2 1 0:1 /foreign '+str(appinfo.parent)+' rw - tmpfs tmpfs rw\n')
            with self.assertRaises(ValueError):self.k.require_generic_environment()
            mountinfo.write_text('1 0 0:1 / / rw - squashfs /dev/root ro\n')
            for reply in (dict(missing,errorText='Access denied'),dict(missing,errorCode='-1'),{'returnValue':True}):
                with patch.object(self.k,'luna',return_value=reply),self.assertRaises(ValueError):self.k.require_generic_environment()
            with patch.object(emergency_reader,'open_remote',side_effect=ValueError('unknown ABI')),self.assertRaises(ValueError):self.k.require_generic_environment()
            with patch.object(self.k,'read_chain',return_value=[dict(vendor,file='/foreign/home.js')]),self.assertRaises(ValueError):self.k.require_generic_environment()

    def test_schema3_admits_capabilities_without_expanding_legacy_c1_schema(self):
        for sdk in ('3.9.0','4.4.3','5.6.2','10.3.1','12.0.0'):
            value=dict(self.generic(),webos=sdk)
            self.assertTrue(self.k.admission_valid(value))
            self.assertFalse(self.k.legacy.admission_valid(value))
        for model in ('55NANO77SRA','OLED55C37LA','55UP7000PUA'):
            value=dict(self.generic(),model=model)
            self.assertTrue(self.k.admission_valid(value))
            self.assertFalse(self.k.legacy.admission_valid(value))
        self.admission=self.generic()
        marker=self.prepare()
        self.assertEqual(marker['schema'],3)
        self.assertEqual(self.k.legacy.selection(self.root,self.uid),marker)
        marker['schema']=2
        self.k.atomic(self.root/'home-backend.json',marker,self.uid)
        with self.assertRaises(ValueError): self.k.selection(self.root,self.uid)

    def test_schema3_writes_volatile_and_preserves_foreign_chain_on_restore(self):
        self.admission=self.generic();self.prepare()
        vendor={'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}
        foreign={'file':'/foreign/buttons.js','handler':'buttons','extra':42}
        chain=[vendor];effects=[]
        def rpc(uri,payload,**kw):
            if uri.endswith('getConfigs'): return {'returnValue':True,'configs':{self.k.KEY:list(chain)}}
            self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())
            effects.append(payload)
            chain[:]=payload['configs'][self.k.KEY]
            return {'returnValue':True}
        with patch.object(self.k,'luna',side_effect=rpc):
            self.k.change_chain(self.root,True,self.uid)
            chain.append(foreign)
            self.k.change_chain(self.root,False,self.uid)
        self.assertEqual(chain,[vendor,foreign])
        self.assertEqual([v.get('volatile') for v in effects],[True,True])
        self.assertFalse((self.root/'c1-keyfilter/pending.json').exists())

    def test_schema3_refuses_foreign_filter_added_between_probe_and_enable(self):
        self.admission=self.generic();self.prepare()
        chain=[{'file':'/foreign/home.js','handler':'home'}]
        with patch.object(self.k,'read_chain',return_value=chain),patch.object(self.k,'write_chain') as write:
            with self.assertRaises(ValueError): self.k.change_chain(self.root,True,self.uid)
        write.assert_not_called()
        self.assertFalse((self.root/'c1-keyfilter/pending.json').exists())

    def test_generic_unknown_identity_is_refused(self):
        for change in ({'model':''},{'webos':'invalid'},{'firmware':'unknown'},{'target_sha256':'x'*64}):
            self.assertFalse(self.k.admission_valid(dict(self.generic(),**change)))

    def test_schema3_interrupted_write_is_recoverable_after_firmware_change(self):
        self.admission=self.generic();self.prepare();vendor={'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'};chain=[vendor]
        def write(value,**kw): chain[:]=value;raise TimeoutError('outcome unknown')
        with patch.object(self.k,'read_chain',side_effect=lambda:list(chain)),patch.object(self.k,'write_chain',side_effect=write):
            with self.assertRaises(TimeoutError): self.k.change_chain(self.root,True,self.uid)
        self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())
        with patch.object(self.k,'native',return_value=self.proof()),patch.object(self.k,'probe',side_effect=AssertionError('restore must not re-admit')),patch.object(self.k,'read_chain',side_effect=lambda:list(chain)),patch.object(self.k,'write_chain',side_effect=lambda v,**kw:chain.__setitem__(slice(None),v)):
            self.k.execute('boot',root=self.root,uid=self.uid)
        self.assertEqual(chain,[vendor])
        self.assertFalse(self.k.read_intent(self.root,self.uid)['enabled'])

    def test_schema3_previous_boot_controller_pid_is_never_followed(self):
        self.admission=self.generic();self.prepare()
        record=self.root/'c1-keyfilter/controller.json'
        self.k.atomic(record,dict(pid=123,start=456,token='1'*32,boot='00000000-0000-0000-0000-000000000001'),self.uid)
        with patch.object(self.k,'process_start',side_effect=AssertionError('previous boot PID must not be inspected')):
            self.k.stop_controller(self.root,self.uid)
        self.assertFalse(record.exists())

    def test_same_boot_recovery_preserves_active_home_until_explicit_off(self):
        self.admission = self.generic()
        self.prepare()
        active = dict(self.proof(), state='armed', healthy=True, stock_verified=False,
                      stopped=False, guardian_pid=123)
        self.k.write_intent(self.root, True, active['token'], 'active', self.uid)
        chain = [self.k.filter_entry(self.root)]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json',
                      dict(schema=1, entry=chain[0], token=active['token']), self.uid)

        def native(args, *_args, **_kwargs):
            if args == ['--restore']:
                active.update(self.proof(), reason='explicit_off')
            return active.copy()

        with patch.object(self.k, 'native', side_effect=native) as guard, \
                patch.object(self.k, 'read_chain', side_effect=lambda: chain.copy()), \
                patch.object(self.k, 'write_chain', side_effect=lambda value, **_: chain.__setitem__(slice(None), value)), \
                patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}):
            for _ in range(2):
                reply = self.k.execute('boot', root=self.root, uid=self.uid)
                self.assertIsInstance(reply, dict, 'Same-boot callback stopped Home routing')
                self.assertTrue(reply['effective']['routing_active'])
            active.update(state='reconnecting', healthy=False, reason='none')
            for _ in range(2):
                reply = self.k.execute('boot', root=self.root, uid=self.uid)
                self.assertTrue(reply['intent']['enabled'])
                self.assertEqual(reply['intent']['phase'], 'input-reconnecting')
                self.assertFalse(reply['effective']['routing_active'])
            self.assertTrue(all(call.args[0] == ['--status'] for call in guard.call_args_list))
            self.assertEqual(self.k.execute('restore', root=self.root, uid=self.uid), 'restored')
            self.assertEqual(active['reason'], 'explicit_off')
            self.assertEqual(chain, [])
            self.assertFalse(self.k.read_intent(self.root, self.uid)['enabled'])

    def test_boot_restores_when_same_boot_active_routing_cannot_be_proven(self):
        self.prepare()
        active = dict(self.proof(), state='armed', healthy=True, stock_verified=False,
                      stopped=False, guardian_pid=123)
        intent = self.k.write_intent(self.root, True, active['token'], 'active', self.uid)
        own = self.k.filter_entry(self.root)
        cases = (
            ('previous boot', dict(intent, boot='00000000-0000-0000-0000-000000000001'), active, [own], True),
            ('wrong token', dict(intent, token='2'*32), active, [own], True),
            ('stopped guardian', intent, dict(self.proof(), reason='emergency'), [own], True),
            ('missing filter', intent, active, [], True),
            ('invalid recovery', intent, active, [own], False),
            ('trial', dict(intent, phase='trial', enabled=False), active, [own], True),
        )
        for name, saved, proof, chain, verified in cases:
            with self.subTest(name=name):
                self.k.atomic(self.root/'c1-keyfilter/intent.json', saved, self.uid)
                with patch.object(self.k, 'native', return_value=proof), \
                        patch.object(self.k, 'read_chain', return_value=chain), \
                        patch.object(self.k, 'verify_ready', return_value={'integrity_verified': verified}), \
                        patch.object(self.k, 'restore_locked', return_value='restored') as restore:
                    self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
                    restore.assert_called_once_with(self.root, self.uid, routing_only=True)

    def test_failed_enable_retires_filter_when_stock_home_is_independently_verified(self):
        self.admission = dict(self.generic(), model='55UM7450PLA', firmware='05.40.97', webos='4.10.0')
        self.prepare()
        filter_file = self.root / 'runtime/c1-home-filter.js'
        filter_file.parent.mkdir()
        filter_file.touch(mode=0o600)
        stock = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        chain = stock.copy()
        stopped = self.proof()
        failure = TimeoutError('Guardian startup failed')

        def change(root, enabled, uid):
            chain[:] = self.k.reconcile(chain, root, enabled)
            if enabled:
                raise failure

        def native(args, *_args, allow_ui_failure=False):
            if args == ['--restore']:
                if not allow_ui_failure:
                    raise ValueError('Native UI release failed')
                return dict(stopped, returnValue=False, reason='ui_release_failed')
            return stopped

        with patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), \
                patch.object(self.k, 'probe', return_value=self.admission), \
                patch.object(self.k, 'binary'), \
                patch.object(self.k, 'read_chain', side_effect=lambda: chain.copy()), \
                patch.object(self.k, 'change_chain', side_effect=change), \
                patch.object(self.k, 'native', side_effect=native), \
                patch.object(self.k, 'luna', side_effect=[
                    {'returnValue': True, 'appId': self.k.STOCK},
                    {'returnValue': True, 'foregroundAppInfo': [{'appId': self.k.STOCK, 'windowType': self.k.HOME}]},
                ]), patch('helper_bridge.require_idle'):
            with self.assertRaises(TimeoutError) as caught:
                self.k.enable_locked(self.root, self.uid, 0)
            self.assertIs(caught.exception, failure)
        self.assertEqual(chain, stock)
        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')

    def test_shutdown_probe_requires_running_manager_and_trusted_executable(self):
        import stat
        proc_init = Path('/proc/1/exe')
        for init, command, expected in (
            ('/lib/systemd/systemd', '/bin/systemctl', 'systemd-is-system-running-v1'),
            ('/sbin/init.upstart', '/sbin/initctl', 'upstart-shutdown-jobs-v1'),
            ('/bin/tini', '/bin/systemctl', None),
        ):
            trust = SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o755)

            def resolve(path, *, strict):
                self.assertTrue(strict)
                return Path(init) if path == proc_init else path

            systemctl = init != '/sbin/init.upstart'

            def lstat(path):
                if path == Path('/bin/systemctl') and not systemctl:
                    raise FileNotFoundError(path)
                return trust

            with self.subTest(init=init), \
                    patch.object(Path, 'resolve', autospec=True, side_effect=resolve), \
                    patch.object(Path, 'lstat', autospec=True, side_effect=lstat), \
                    patch.object(Path, 'stat', autospec=True, return_value=trust) as file_stat, \
                    patch.object(self.k.legacy, 'trusted_directory'), \
                    patch.object(self.k, 'secure') as secure:
                self.assertEqual(self.k.shutdown_probe(), expected)
                if expected is not None:
                    file_stat.assert_any_call(Path(command))
                    trust.st_mode |= 0o002
                    self.assertIsNone(self.k.shutdown_probe())
                    trust.st_mode &= ~0o002
                else:
                    file_stat.assert_not_called()
                if init == '/sbin/init.upstart':
                    secure.assert_any_call(Path('/etc/init/shutdown.conf'))
                    secure.assert_any_call(Path('/etc/init/reboot.conf'))
                    secure.side_effect = FileNotFoundError('job')
                    self.assertFalse(self.k.reboot_resume_supported({'schema': 3}))
                    secure.side_effect = None
                    trust.st_mode = stat.S_IFLNK | 0o777
                    self.assertIsNone(self.k.shutdown_probe())
                    trust.st_mode = stat.S_IFREG | 0o755
                    systemctl = True
                    self.assertIsNone(self.k.shutdown_probe())

    def test_boot_without_guard_capability_restores_without_waiting_or_rearming(self):
        self.prepare_schema3()
        boot = self.k.boot_identity()
        self.k.write_intent(self.root, True, '1'*32, 'active', self.uid,
                            session=boot+':session-'+'2'*32)
        with patch.object(self.k, 'shutdown_probe', return_value=None), \
                patch.object(self.k, 'boot_resume_observation') as observe, \
                patch.object(self.k, 'status', side_effect=ValueError('No active guard')), \
                patch.object(self.k, 'restore_locked', return_value='restored') as restore, \
                patch.object(self.k, 'enable_locked') as enable:
            self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
            observe.assert_not_called()
            enable.assert_not_called()
            restore.assert_called_once_with(self.root, self.uid, explicit_restore=False)

    def test_reboot_resume_requires_matching_guard_and_shutdown_capabilities(self):
        descriptor = self.prepare_schema3()
        systemd = 'systemd-is-system-running-v1'
        upstart = 'upstart-shutdown-jobs-v1'
        reply = dict(returnValue=True, backend=self.k.BACKEND, routing=self.k.ROUTING,
                     protocol=1, resumable_guard=True, boot_retirement=True,
                     shutdown_probes=[systemd, upstart])
        for detector in (systemd, upstart, None):
            for proof, valid in (
                (reply, True),
                (dict(reply, shutdown_probes=[systemd]), detector == systemd),
                (dict(reply, protocol=True), False),
                (dict(reply, resumable_guard=1), False),
                (dict(reply, boot_retirement=False), False),
                (dict(reply, shutdown_probes=systemd), False),
                (dict(reply, shutdown_probes=[systemd, upstart, None]), False),
                (dict(reply, returnValue=False), False),
                ({}, False),
            ):
                with self.subTest(detector=detector, proof=proof), \
                        patch.object(self.k, 'shutdown_probe', return_value=detector), \
                        patch.object(self.k, 'native', return_value=proof) as native:
                    self.assertEqual(self.k.reboot_resume_supported(descriptor, self.root, self.uid),
                                     detector is not None and valid)
                    if detector is not None:
                        native.assert_called_once_with(['--capabilities'], self.root, self.uid, timeout=1)

    def test_reboot_resume_refuses_old_untrusted_and_unresponsive_guards(self):
        descriptor = self.prepare_schema3()
        with patch.object(self.k, 'shutdown_probe', return_value='upstart-shutdown-jobs-v1'), \
                patch.object(self.k.subprocess, 'run') as run:
            self.assertFalse(self.k.reboot_resume_supported(descriptor, self.root, self.uid))
            run.assert_not_called()  # Missing guard never reaches exec.
        import hashlib
        old = b'verified retained guard bytes'
        data = b'new guard fixture\0--capabilities\0'
        guard = self.root / 'runtime/c1-keyfilter-guard'
        guard.parent.mkdir(mode=0o700)
        guard.write_bytes(old)
        guard.chmod(0o700)
        descriptor['native_sha256'] = hashlib.sha256(old).hexdigest()
        self.k.atomic(self.root/'home-backend.json', descriptor, self.uid)
        with patch.object(self.k, 'shutdown_probe', return_value='upstart-shutdown-jobs-v1'), \
                patch.object(self.k.subprocess, 'run') as run:
            self.assertFalse(self.k.reboot_resume_supported(descriptor, self.root, self.uid))
            run.assert_not_called()  # Unknown commands on the old guard acquire a state lock.
        guard.write_bytes(data)
        descriptor['native_sha256'] = hashlib.sha256(data).hexdigest()
        self.k.atomic(self.root/'home-backend.json', descriptor, self.uid)
        for result in (SimpleNamespace(returncode=2, stdout=b''),
                       SimpleNamespace(returncode=0, stdout=b'not json'),
                       self.k.subprocess.TimeoutExpired('guard', .5)):
            with self.subTest(result=result), \
                    patch.object(self.k, 'shutdown_probe', return_value='upstart-shutdown-jobs-v1'), \
                    patch.object(self.k.subprocess, 'run', side_effect=[result]) as run:
                self.assertFalse(self.k.reboot_resume_supported(descriptor, self.root, self.uid))
                self.assertEqual(run.call_args.args[0], [str(guard), '--capabilities'])
        guard.write_bytes(data + b'changed')
        with patch.object(self.k, 'shutdown_probe', return_value='upstart-shutdown-jobs-v1'), \
                patch.object(self.k.subprocess, 'run') as run:
            self.assertFalse(self.k.reboot_resume_supported(descriptor, self.root, self.uid))
            run.assert_not_called()

    def test_resume_refuses_to_arm_without_an_explicit_lg_destination(self):
        self.prepare_resumable()
        stock = [{'file': '/usr/lib/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        for defaults in ({}, {'home': self.k.APP}, {'home': None}, '{"home":'):
            with self.subTest(defaults=defaults), \
                    patch.object(self.k, 'probe', return_value=self.admission), \
                    patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), \
                    patch.object(self.k, 'native', return_value=self.proof()), \
                    patch.object(self.k, 'read_chain', return_value=stock), \
                    patch.object(self.k, 'luna', return_value={'returnValue': True,
                                 'settings': {'defaultApps': defaults}}), \
                    patch.object(self.k, 'write_config') as write_config, \
                    patch.object(self.k, 'change_chain') as change:
                with self.assertRaisesRegex(ValueError, 'LG Home destination'):
                    self.k.enable_locked(self.root, self.uid, 0, resume_token='1'*32)
                write_config.assert_not_called()
                change.assert_not_called()

    def test_missing_stock_destination_keeps_generic_enable_in_the_current_session(self):
        self.prepare_resumable()
        stock = [{'file': '/usr/lib/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        session = self.k.boot_identity() + ':session-' + 'a'*32
        script = self.root / 'runtime/c1-home-filter.js'
        script.parent.mkdir(mode=0o700)
        script.write_text('filter')
        script.chmod(0o600)
        with patch.object(self.k, 'probe', return_value=self.admission), \
                patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), \
                patch.object(self.k, 'native', return_value=self.proof()), \
                patch.object(self.k, 'read_chain', return_value=stock), \
                patch.object(self.k, 'vendor_script', return_value=b'other compatible vendor handler'), \
                patch.object(self.k, 'luna', return_value={'returnValue': True,
                             'settings': {'defaultApps': {}}}), \
                patch.object(self.k, 'binary', return_value=Path('/fixture')), \
                patch('helper_bridge.require_idle'), \
                patch.object(self.k, 'change_chain', side_effect=RuntimeError('interrupted activation')), \
                patch.object(self.k, 'restore_locked') as restore:
            with self.assertRaisesRegex(RuntimeError, 'interrupted activation'):
                self.k.enable_locked(self.root, self.uid, 0, session=session)
            restore.assert_called_once_with(self.root, self.uid, explicit_restore=True)

    def test_reported_schema3_explicit_restore_verifies_routing_without_forcing_foreground(self):
        self.prepare_resumable()
        own = self.k.filter_entry(self.root)
        stock = [{'file': '/usr/lib/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        token = '1'*32
        self.k.atomic(self.root/'c1-keyfilter/ownership.json', dict(schema=1, entry=own, token=token), self.uid)
        for destination in (self.k.STOCK, 'com.webos.app.fullhome', self.k.APP, 'org.example.home'):
            with self.subTest(destination=destination):
                is_stock = destination in (self.k.STOCK, 'com.webos.app.fullhome')
                session = self.k.boot_identity() + ':session-' + 'a'*32
                self.k.write_intent(self.root, True, token, 'active', self.uid, session=session)
                chain = [own, *stock]

                def native(args, *_args, **_options):
                    self.assertIn(args, (['--restore-routing'], ['--status']))
                    return self.proof()

                def settings(uri, payload, **options):
                    reply = self.read_factory_home_setting(uri, payload, **options)
                    reply['settings']['defaultApps'] = json.dumps({'home': destination})
                    return reply

                with patch.object(self.k, 'native', side_effect=native), \
                        patch.object(self.k, 'read_chain', side_effect=lambda: chain.copy()), \
                        patch.object(self.k, 'write_chain', side_effect=lambda value, **_: chain.__setitem__(slice(None), value)), \
                        patch.object(self.k, 'luna', side_effect=settings):
                    if not is_stock:
                        with self.assertRaisesRegex(ValueError, 'LG Home destination') as caught:
                            self.k.execute('restore', root=self.root, uid=self.uid)
                        self.assertEqual(caught.exception.restore_check, 'stock-routing-unverified')
                    else:
                        self.assertEqual(self.k.execute('restore', root=self.root, uid=self.uid), 'restored')
                    self.assertEqual(chain, stock)
                    intent = self.k.read_intent(self.root, self.uid)
                    self.assertFalse(intent['enabled'])
                    self.assertEqual(intent['phase'], 'disabled' if is_stock else 'recovering')

    def test_reported_schema3_rearms_once_on_a_new_normal_session(self):
        self.check_schema3_boot(missing_input=False)

    def test_confirmed_compositor_boot_waits_for_input_without_changing_saved_choice(self):
        self.check_schema3_boot(missing_input=True)

    def check_schema3_boot(self, *, missing_input):
        import intent_runtime
        self.prepare_resumable()
        boot = self.k.boot_identity()
        old_session = boot + ':session-' + 'a'*32
        new_session = boot + ':session-' + 'b'*32
        token = '1'*32
        self.k.write_config(self.root, self.admission, token, self.uid)
        self.k.write_intent(self.root, True, token, 'active', self.uid, session=old_session)
        script = self.root/'runtime/c1-home-filter.js'
        script.parent.mkdir()
        script.write_text('filter')
        script.chmod(0o600)
        stock = [{'file':'/usr/lib/qml/KeyFilters/systemUi.js', 'handler':'handleSystemKeys'}]
        chain = stock.copy()
        writes = []

        def write(value, *, volatile):
            self.assertTrue(volatile)
            chain[:] = value
            writes.append(value.copy())

        def native(args, *_args, **_options):
            if args[0] == '--retire-boot':
                self.assertEqual(args, ['--retire-boot', token])
                return dict(self.proof(), reason='normal_shutdown')
            self.assertEqual(args, ['--status'])
            if chain == stock:
                return self.proof()
            current = self.k.read_intent(self.root, self.uid)
            return dict(self.proof(), token=current['token'], state='reconnecting' if missing_input else 'armed',
                        healthy=not missing_input, reason='none',
                        guardian_pid=123, stopped=False, stock_verified=False)

        def guard_binary(root, uid, *, features):
            features.update(wait_input=missing_input, boot_wait=missing_input)
            return Path('/fixture')

        child = Mock()
        child.poll.return_value = None

        observed = []

        def after_boot(result, *, root, uid):
            with self.k.operation(root, uid):
                observed.append(self.k.read_intent(root, uid))
            raise ValueError('Optional startup policy failed')

        startup = Mock(side_effect=after_boot)
        with patch.object(self.k, 'startup_after_boot', startup), \
                patch.object(intent_runtime, 'boot_identity', return_value=new_session), \
                patch('boot_gate.wait', return_value=True) as normal, \
                patch('boot_gate.observation', return_value=(True, False)), \
                patch.object(self.k, 'read_chain', side_effect=lambda: chain.copy()), \
                patch.object(self.k, 'write_chain', side_effect=write), \
                patch.object(self.k, 'verify_ready', return_value={'integrity_verified':True}), \
                patch.object(self.k, 'probe', return_value=self.admission), \
                patch.object(self.k, 'binary', side_effect=guard_binary), \
                patch.object(self.k, 'luna', side_effect=self.read_factory_home_setting), \
                patch('helper_bridge.require_idle'), patch('python_binding.command', return_value='/python'), \
                patch.object(self.k, 'native', side_effect=native), \
                patch.object(self.k, 'start_controller', return_value=child), \
                patch.object(self.k, 'read_handshake') as handshake, \
                patch.object(self.k.subprocess, 'Popen', return_value=child) as start:
            result = self.k.execute('boot', root=self.root, uid=self.uid)
            replay = self.k.execute('boot', root=self.root, uid=self.uid)
            self.assertEqual(result['effective']['routing_active'], not missing_input)
            self.assertTrue(result['intent']['enabled'])
            self.assertEqual(result, replay)
            self.assertEqual(result['intent']['session'], new_session)
            self.assertNotEqual(result['intent']['token'], token)
            self.assertEqual(writes, [[self.k.filter_entry(self.root), *stock]])
            self.assertEqual(start.call_count, 2)
            mode = '--guard-boot-wait-input' if missing_input else '--guard-resumable-reconnect'
            self.assertEqual(start.call_args.args[0][:2], ['/fixture', mode])
            reader = '--boot-wait-input' if missing_input else '--recover-input'
            self.assertEqual(start.call_args_list[0].args[0][-1], reader)
            ack = 'SUPERVISED' if missing_input else 'ARMED'
            self.assertEqual(handshake.call_args.args[1], f"{ack} {result['intent']['token']}\n".encode())
            normal.assert_called_once()
            startup.assert_called_once_with(result, root=self.root, uid=self.uid)
            self.assertEqual(observed, [dict(result['intent'], phase='active')])

    def test_reported_schema3_boot_failure_and_stop_leave_routing_with_lg(self):
        import intent_runtime
        self.prepare_resumable()
        boot = self.k.boot_identity()
        old_session = boot + ':session-' + 'a'*32
        new_session = boot + ':session-' + 'b'*32
        token = '1'*32
        stock = [{'file':'/usr/lib/qml/KeyFilters/systemUi.js', 'handler':'handleSystemKeys'}]
        for case in ('emergency-stop', 'boot-gate', 'activation-failure', 'same-session'):
            with self.subTest(case=case):
                intent = self.k.write_intent(self.root, True, token, 'active', self.uid)
                self.k.atomic(self.root/'c1-keyfilter/intent.json', dict(intent, session=old_session), self.uid)
                retired = dict(self.proof(), state='stock', stopped=False, reason='boot_retired')
                startup = Mock()
                with patch.object(self.k, 'startup_after_boot', startup), \
                        patch.object(intent_runtime, 'boot_identity',
                                     return_value=old_session if case=='same-session' else new_session), \
                        patch('boot_gate.wait', return_value=case!='boot-gate'), \
                        patch('boot_gate.observation', return_value=(True, False)), \
                        patch.object(self.k, 'read_chain', return_value=stock), \
                        patch.object(self.k, 'native', return_value=retired,
                                     side_effect=ValueError('native stop latched') if case=='emergency-stop' else None), \
                        patch.object(self.k, 'enable_locked', side_effect=TimeoutError('startup failed')) as enable, \
                        patch.object(self.k, 'restore_locked', return_value='restored') as restore:
                    self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
                    restore.assert_called_once_with(self.root, self.uid, routing_only=True)
                    self.assertEqual(enable.call_count, int(case=='activation-failure'))
                    startup.assert_not_called()

    def test_reported_schema3_failed_controller_restores_the_written_chain(self):
        self.check_reported_schema3_interrupted_rearm(lost_ack=False)

    def test_reported_schema3_lost_configd_ack_rolls_back_once_and_stays_off(self):
        self.check_reported_schema3_interrupted_rearm(lost_ack=True)

    def check_reported_schema3_interrupted_rearm(self, *, lost_ack):
        import intent_runtime
        self.prepare_resumable()
        boot = self.k.boot_identity()
        token = '1'*32
        self.k.write_config(self.root, self.admission, token, self.uid)
        self.k.write_intent(self.root, True, token, 'active', self.uid, session=boot+':session-'+'a'*32)
        script = self.root/'runtime/c1-home-filter.js'
        script.parent.mkdir()
        script.write_text('filter')
        script.chmod(0o600)
        stock = [{'file':'/usr/lib/qml/KeyFilters/systemUi.js', 'handler':'handleSystemKeys'}]
        chain = stock.copy()
        writes = []

        def write(value, *, volatile):
            self.assertTrue(volatile)
            chain[:] = value
            writes.append(value.copy())
            if lost_ack and len(writes) == 1:
                self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())
                raise TimeoutError('configd committed without replying')

        def native(args, *_args, **_options):
            if args[0] == '--retire-boot':
                return dict(self.proof(), reason='normal_shutdown')
            if args[0] == '--restore-routing':
                expected = [self.k.filter_entry(self.root), *stock] if len(writes) == 1 else stock
                self.assertEqual(chain, expected)
            else:
                self.assertEqual(args, ['--status'])
            return self.proof()

        with patch.object(intent_runtime, 'boot_identity', return_value=boot+':session-'+'b'*32), \
                patch('boot_gate.wait', return_value=True), \
                patch('boot_gate.observation', return_value=(True, False)), \
                patch.object(self.k, 'verify_ready', return_value={'integrity_verified':True}), \
                patch.object(self.k, 'probe', return_value=self.admission), \
                patch.object(self.k, 'binary', return_value=Path('/fixture')), \
                patch('helper_bridge.require_idle'), \
                patch.object(self.k, 'luna', side_effect=self.read_factory_home_setting), \
                patch.object(self.k, 'read_chain', side_effect=lambda: chain.copy()), \
                patch.object(self.k, 'write_chain', side_effect=write), \
                patch.object(self.k, 'native', side_effect=native), \
                patch.object(self.k, 'start_controller', side_effect=TimeoutError('startup')) as start:
            self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
            self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
            self.assertEqual(start.call_count, 0 if lost_ack else 1)
            self.assertEqual(writes, [[self.k.filter_entry(self.root), *stock], stock])
            self.assertEqual(chain, stock)
            self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
            self.assertFalse((self.root/'c1-keyfilter/pending.json').exists())

    def test_direct_native_off_vetoes_rotation_after_boot_retirement(self):
        self.prepare_resumable()
        token = '1'*32
        directory = self.root/'c1-keyfilter'
        self.k.write_config(self.root, self.admission, token, self.uid)
        config = (directory/'config').read_bytes()
        self.k.atomic(directory/'stopped', (token+' explicit_off\n').encode(), self.uid, raw=True)
        with self.assertRaisesRegex(ValueError, 'explicit Enable'):
            self.k.rotate_boot_config(self.root, self.uid, self.admission, token, '2'*32)
        self.assertEqual((directory/'config').read_bytes(), config)

    def test_reported_schema3_off_during_boot_wait_cancels_continuation(self):
        import intent_runtime
        self.prepare_resumable()
        boot = self.k.boot_identity()
        self.k.write_intent(self.root, True, '1'*32, 'active', self.uid, session=boot+':session-'+'a'*32)

        def wait():
            with self.k.operation(self.root, self.uid):
                self.k.write_intent(self.root, False, '1'*32, 'disabled', self.uid)
            return True

        with patch.object(intent_runtime, 'boot_identity', return_value=boot+':session-'+'b'*32), \
                patch('boot_gate.wait', side_effect=wait), \
                patch.object(self.k, 'native', side_effect=AssertionError('do not retire or reactivate')) as native, \
                patch.object(self.k, 'restore_locked', return_value='restored'):
            self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
            native.assert_not_called()

    def test_same_boot_recovery_still_handles_interrupted_filter_write(self):
        self.prepare()
        self.k.write_intent(self.root, True, '1'*32, 'active', self.uid)
        (self.root/'c1-keyfilter/pending.json').touch()
        with patch.object(self.k, 'status') as status, \
                patch.object(self.k, 'restore_locked', return_value='restored') as restore:
            self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
            status.assert_not_called()
            restore.assert_called_once_with(self.root, self.uid, routing_only=True)

    def test_schema3_configd_reset_cancels_lifecycle_return_without_reinstalling(self):
        self.admission=self.generic();self.prepare()
        self.k.write_intent(self.root,True,'1'*32,'active',self.uid)
        proof=self.proof();proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        replies=[{'returnValue':True,'state':'Active'},{'returnValue':True,'foregroundAppInfo':[]},{'returnValue':True,'appId':''}]
        with patch.object(self.k,'luna',side_effect=replies),patch.object(self.k,'native',return_value=proof),patch.object(self.k,'read_chain',return_value=[]),patch.object(self.k,'write_chain',side_effect=AssertionError('must not reinstall')):
            self.assertFalse(self.k.return_ready(self.root,self.uid,'1'*32,lambda:False))

    def test_schema3_changed_home_can_release_filter_without_claiming_stock_proof(self):
        self.admission=self.generic();self.prepare();own=self.k.filter_entry(self.root);chain=[own]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json',dict(schema=1,entry=own,token='1'*32),self.uid)
        stopped=self.proof();stopped['stock_verified']=False
        with patch.object(self.k,'native',return_value=stopped),patch.object(self.k,'read_chain',side_effect=lambda:list(chain)),patch.object(self.k,'write_chain',side_effect=lambda v,**kw:chain.__setitem__(slice(None),v)):
            with self.assertRaisesRegex(ValueError,'identity'): self.k.execute('restore',root=self.root,uid=self.uid)
        self.assertEqual(chain,[])
        self.assertFalse(self.k.read_intent(self.root,self.uid)['enabled'])
        self.assertEqual(self.k.read_intent(self.root,self.uid)['phase'],'recovering')

    def setUp(self):
        try: self.k = importlib.import_module('c1_keyfilter')
        except ModuleNotFoundError: self.fail('schema2 runtime missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.uid = os.getuid()
        boot=patch.object(self.k,'boot_identity',return_value='12345678-1234-1234-1234-123456789abc')
        boot.start(); self.addCleanup(boot.stop)
        self.admission = dict(model='OLED65C14LB', firmware='03.51.15', webos='6.5.0',
                              target_sha256='b'*64, target=dict(dev=1, ino=2, size=52, mtime_ns=3))

    def prepare(self):
        return self.k.prepare(self.root, 'a'*64, self.admission, self.uid)

    def prepare_schema3(self):
        self.admission = dict(self.generic(), model='OLED65B9PLA', firmware='05.50.00', webos='4.10.0')
        return self.prepare()

    def prepare_resumable(self):
        self.prepare_schema3()
        capabilities = patch.object(self.k, 'reboot_resume_supported', return_value=True)
        capabilities.start()
        self.addCleanup(capabilities.stop)

    def proof(self, **kw):
        return dict(returnValue=True, backend='c1-native-gate', routing='compositor-keyfilter-v1',
                    state='stopped', mounted=False, healthy=False, stock_verified=True,
                    stopped=True, token='1'*32, guardian_pid=0, reason='', profiles=None, **kw)

    def test_persistent_embedded_enable_recovers_disconnected_input(self):
        self.check_embedded_input_protocol(b'fixture\0--guard-wait-input\0', '--wait-input', '--guard-wait-input')

    def test_older_embedded_guard_keeps_its_original_reader_protocol(self):
        self.check_embedded_input_protocol(b'older guardian', None, '--guard')

    def check_embedded_input_protocol(self, guard_bytes, reader_flag, guard_flag):
        self.prepare()
        runtime = self.root / 'runtime'
        runtime.mkdir()
        script = runtime / 'c1-home-filter.js'
        script.write_text('filter')
        script.chmod(0o600)
        child = Mock()
        child.poll.return_value = 0
        guard = self.root / 'runtime/c1-keyfilter-guard'
        guard.write_bytes(guard_bytes)
        guard.chmod(0o700)
        descriptor = self.k.selection(self.root, self.uid)
        descriptor['native_sha256'] = hashlib.sha256(guard.read_bytes()).hexdigest()
        self.k.atomic(self.root/'home-backend.json', descriptor, self.uid)
        with patch.object(self.k, 'embedded_adapter', return_value=Mock()), \
                patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), \
                patch.object(self.k, 'native', return_value=self.proof()), \
                patch.object(self.k, 'probe', return_value=self.admission), \
                patch('helper_bridge.require_idle'), \
                patch('python_binding.command', return_value='/python'), \
                patch.object(self.k, 'change_chain'), \
                patch.object(self.k, 'start_controller', return_value=child), \
                patch.object(self.k, 'restore_locked'), \
                patch.object(self.k, 'read_handshake', side_effect=TimeoutError), \
                patch.object(self.k.subprocess, 'Popen', return_value=child) as start:
            with self.assertRaises(TimeoutError):
                self.k.enable_locked(self.root, self.uid, 0)
        observer, guardian = [call.args[0] for call in start.call_args_list]
        self.assertEqual(observer[3:], [reader_flag] if reader_flag else [])
        self.assertEqual(guardian[1], guard_flag)

    def test_standalone_enable_waits_for_observer_pipe_before_starting_guard(self):
        self.prepare_schema3()
        runtime = self.root/'runtime'
        runtime.mkdir()
        filter_script = runtime/'c1-home-filter.js'
        filter_script.write_text('filter')
        filter_script.chmod(0o600)
        child = Mock()
        child.poll.return_value = 0
        calls = []

        def start(args, **_):
            calls.append('guard' if args[1].startswith('--guard') else 'observer')
            return child

        def wait(readers, writers, errors, timeout):
            calls.append('input-pipe')
            self.assertEqual((len(readers), writers, errors), (1, [], []))
            self.assertGreater(timeout, 2)
            return readers, [], []

        with patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), \
                patch.object(self.k, 'native', return_value=self.proof()), \
                patch.object(self.k, 'probe', return_value=self.admission), \
                patch.object(self.k, 'read_chain', return_value=[]), \
                patch.object(self.k, 'binary', return_value=Path('/fixture')), \
                patch('helper_bridge.require_idle'), \
                patch('python_binding.command', return_value='/python'), \
                patch.object(self.k, 'change_chain'), \
                patch.object(self.k, 'start_controller', return_value=child), \
                patch.object(self.k, 'restore_locked'), \
                patch.object(self.k, 'read_handshake', side_effect=TimeoutError), \
                patch.object(self.k.select, 'select', side_effect=wait), \
                patch.object(self.k.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(TimeoutError):
                self.k.enable_locked(self.root, self.uid, 0)
        self.assertEqual(calls, ['observer', 'input-pipe', 'guard'])

    def test_embedded_restore_uses_stock_compositor_readback_without_standalone_home(self):
        self.prepare()
        selected = self.k.selection(self.root, self.uid)
        selected['schema'] = 4
        self.k.atomic(self.root/'home-backend.json', selected, self.uid)
        adapter = Mock(STOCK_QML='qrc:///main.qml')
        adapter.current.return_value = (42, adapter.STOCK_QML)
        with patch.object(self.k, 'embedded_adapter', return_value=adapter), patch.object(self.k, 'native', return_value=self.proof()), patch.object(self.k, 'stop_controller'), patch.object(self.k, 'change_chain') as change, patch.object(self.k, 'luna') as luna, patch.object(self.k, 'read_chain') as chain:
            self.assertEqual(self.k.restore_for_removal(self.root, self.uid), 'restored')
        change.assert_called_once_with(self.root, False, self.uid)
        adapter.current.assert_called_once_with(self.root)
        luna.assert_not_called()
        chain.assert_not_called()
        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')

    def test_embedded_boot_restores_routing_despite_ui_failure_but_retains_cleanup_gap(self):
        self.prepare()
        selected = self.k.selection(self.root, self.uid)
        selected['schema'] = 4
        self.k.atomic(self.root/'home-backend.json', selected, self.uid)
        adapter = Mock(STOCK_QML='qrc:///main.qml')
        adapter.current.return_value = (42, adapter.STOCK_QML)
        calls = []
        def native(args, *extra, **kwargs):
            calls.append((args, kwargs))
            if args == ['--restore']:
                if not kwargs.get('allow_ui_failure'):
                    raise ValueError('close failed before routing recovery')
                return dict(self.proof(), returnValue=False, reason='ui_release_failed')
            return self.proof()
        with patch.object(self.k, 'embedded_adapter', return_value=adapter), patch.object(self.k, 'native', side_effect=native), patch.object(self.k, 'stop_controller'), patch.object(self.k, 'change_chain') as change, patch.object(self.k, 'luna') as luna, patch.object(self.k, 'read_chain') as chain:
            with self.assertRaisesRegex(ValueError, 'Root window cleanup unverified') as caught:
                self.k.execute('boot', root=self.root, uid=self.uid)
        change.assert_called_once_with(self.root, False, self.uid)
        adapter.current.assert_called_once_with(self.root)
        self.assertEqual(caught.exception.native_reason, 'ui_release_failed')
        self.assertEqual(caught.exception.restore_check, 'stock-surface-unverified')
        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'recovering')
        luna.assert_not_called()
        chain.assert_not_called()

    def test_embedded_removal_preserves_assets_on_owned_window_close_failure(self):
        self.prepare()
        selected = self.k.selection(self.root, self.uid)
        selected['schema'] = 4
        self.k.atomic(self.root/'home-backend.json', selected, self.uid)
        adapter = Mock(STOCK_QML='qrc:///main.qml')
        adapter.current.return_value = (42, adapter.STOCK_QML)
        failure = dict(self.proof(), returnValue=False, reason='ui_release_failed')
        with patch.object(self.k, 'embedded_adapter', return_value=adapter), patch.object(self.k, 'native', side_effect=[failure, self.proof(), self.proof()]), patch.object(self.k, 'stop_controller'), patch.object(self.k, 'change_chain') as change, patch.object(self.k, 'luna') as luna:
            with self.assertRaisesRegex(ValueError, 'Root window cleanup unverified'):
                self.k.restore_for_removal(self.root, self.uid)
        change.assert_called_once_with(self.root, False, self.uid)
        self.assertTrue((self.root/'home-backend.json').exists())
        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'recovering')
        luna.assert_not_called()

    def test_embedded_restore_rejects_stale_stock_readback(self):
        for case in ('wrapper-still-selected', 'different-native-token'):
            with self.subTest(case=case):
                adapter = Mock(STOCK_QML='qrc:///main.qml')
                adapter.current.return_value = (42, 'file:///wrapper.qml' if case == 'wrapper-still-selected' else adapter.STOCK_QML)
                selected = {'schema': 4}
                fresh = dict(self.proof(), token='2'*32)
                with patch.object(self.k, 'embedded_adapter', return_value=adapter), patch.object(self.k, 'selection', return_value=selected), patch.object(self.k, 'native', side_effect=[self.proof(), self.proof(), fresh]), patch.object(self.k, 'write_intent') as intent, patch.object(self.k, 'stop_controller'), patch.object(self.k, 'change_chain'), patch.object(self.k, 'luna') as luna:
                    with self.assertRaisesRegex(ValueError, 'unverified'):
                        self.k.restore_locked(self.root, self.uid, for_removal=True)
                self.assertEqual(intent.call_args.args[3], 'recovering')
                luna.assert_not_called()

    def test_prepare_exact_marker_and_seven_line_config(self):
        self.prepare()
        self.assertEqual(self.k.selection(self.root, self.uid)['schema'], 2)
        lines = (self.root/'c1-keyfilter/config').read_text().splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'CYTV-C1-KEYFILTER-1')
        self.assertEqual((self.root/'c1-keyfilter').stat().st_mode & 0o777, 0o700)

    def test_no_selection_has_no_effect_and_no_checkpoint_dependency(self):
        with patch.object(self.k, 'luna', side_effect=AssertionError('effect')):
            self.assertIsNone(self.k.selection(self.root, self.uid))
        self.assertEqual(list(self.root.iterdir()), [])
        # An unrelated world writable subtree must never be inspected.
        other = self.root/'checkpoint'; other.mkdir(mode=0o777); other.chmod(0o777)
        self.prepare()

    def test_chain_preserves_foreign_entries_and_requires_exact_owned_identity(self):
        foreign = [{'file':'/foreign', 'handler':'other', 'opaque':{'x':[1, True, None]}}]
        own = self.k.filter_entry(self.root)
        self.assertEqual(self.k.reconcile(foreign, self.root, True), [own]+foreign)
        self.assertEqual(self.k.reconcile([own]+foreign, self.root, False), foreign)
        for chain in ([dict(own, handler='changed')], [dict(own, extra=True)], [own, own]):
            with self.assertRaises(ValueError): self.k.reconcile(chain, self.root, False)

    def test_c1_home_replaces_foreign_filters_and_off_leaves_lg_chain(self):
        self.prepare()
        vendor = {'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}
        glasshouse = {'file':'/var/lib/tvweb/remotekeys-filter.js','handler':'handleGlasshouseKeys'}
        another = {'file':'/var/lib/other-launcher/home.js','handler':'otherHome'}
        original = [glasshouse, another, vendor]
        chain = original.copy()
        with patch.object(self.k,'read_chain',side_effect=lambda: chain.copy()), \
                patch.object(self.k,'write_chain',side_effect=lambda value: chain.__setitem__(slice(None),value)):
            self.k.change_chain(self.root,True,self.uid)
            self.assertEqual(chain,[self.k.filter_entry(self.root), vendor])
            self.k.change_chain(self.root,False,self.uid)
            self.assertEqual(chain,[vendor])
        for chain in (None, {}, ['opaque'], [{'file':1,'handler':'x'}]):
            with self.assertRaises(ValueError): self.k.reconcile(chain, self.root, False)

    def test_schema2_off_unmasks_volatile_writes_after_restoring_factory_chain(self):
        self.prepare()
        stock = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        foreign = {'file': '/var/lib/other/buttons.js', 'handler': 'buttons'}
        factory = self.root / 'factory.json'
        factory.write_text(json.dumps({'keyFilters': stock}))
        database = self.root / 'database.json'
        pending = self.root / 'c1-keyfilter/pending.json'
        namespace = 'com.webos.surfacemanager'
        service = 'com.webos.service.config'
        for case in ('stock', 'foreign', 'old-off', 'direct-reset', 'interrupted-reset'):
            with self.subTest(case=case):
                later_edit = [foreign] if case == 'foreign' else []
                interrupt = case == 'interrupted-reset'
                reset_count = 0
                state = {service: {'usrDefined': ['other.keep']}, 'other': {'keep': 42}}
                database.write_text(json.dumps(state))
                temporary = None

                def rpc(uri, payload, **kwargs):
                    nonlocal temporary, interrupt, reset_count
                    if uri.endswith('/getConfigs'):
                        if self.k.KEY in state[service]['usrDefined'] and namespace in state and not state[namespace]:
                            return {'returnValue': True, 'configs': {}}
                        live = state.get(namespace, {}).get('keyFilters', temporary or stock)
                        return {'returnValue': True, 'configs': {self.k.KEY: live.copy()}}
                    if uri.endswith('/reconfigure'):
                        self.assertTrue(pending.exists())
                        if interrupt:
                            interrupt = False
                            raise TimeoutError('reconfigure outcome unknown')
                        del state[namespace]
                        state[service]['usrDefined'].remove(self.k.KEY)
                    else:
                        self.assertTrue(uri.endswith('/setConfigs'))
                        value = payload['configs'][self.k.KEY]
                        if payload.get('volatile'):
                            temporary = value
                        else:
                            self.assertTrue(pending.exists())
                            defined = state[service]['usrDefined']
                            if self.k.KEY not in defined:
                                defined.append(self.k.KEY)
                            if value is None:
                                reset_count += 1
                                if case == 'direct-reset':
                                    del state[namespace]
                                    defined.remove(self.k.KEY)
                                else:
                                    state[namespace] = {}
                            else:
                                state[namespace] = {'keyFilters': value.copy()}
                    database.write_text(json.dumps(state))
                    return {'returnValue': True}

                with patch.object(self.k, 'luna', side_effect=rpc), \
                        patch.object(self.k, 'FACTORY_FILTERS', factory, create=True), \
                        patch.object(self.k, 'CONFIGD_FACTORY_DB', database, create=True):
                    self.k.change_chain(self.root, True, self.uid)
                    state[namespace]['keyFilters'].extend(later_edit)
                    if case == 'old-off':
                        state[namespace] = {'keyFilters': stock.copy()}
                        database.write_text(json.dumps(state))
                    if interrupt:
                        with self.assertRaises(TimeoutError):
                            self.k.change_chain(self.root, False, self.uid)
                        self.assertTrue(pending.exists())
                        with self.assertRaises(ValueError):
                            self.k.read_chain()
                    self.k.change_chain(self.root, False, self.uid)
                    self.assertEqual(reset_count, 0 if later_edit else 1)
                    self.assertEqual(self.k.read_chain(), stock + later_edit)
                    self.assertEqual(state['other']['keep'], 42)
                    self.assertIn('other.keep', state[service]['usrDefined'])
                    self.assertEqual(self.k.KEY in state[service]['usrDefined'], bool(later_edit))
                    probe = [dict(stock[0], probe=True)]
                    self.k.write_chain(probe, volatile=True)
                    self.assertEqual(self.k.read_chain(), stock + later_edit if later_edit else probe)
                    self.assertFalse(pending.exists())

    def test_pending_durable_before_write_and_readback_failure_retains_evidence(self):
        self.prepare()
        chain=[{'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}]
        def read(): return list(chain)
        def write(value):
            pending=json.loads((self.root/'c1-keyfilter/pending.json').read_text())
            self.assertEqual(pending['before'], chain)
            self.assertEqual(pending['after'], value)
            # Simulate configd acknowledging but not applying its write.
        with patch.object(self.k,'read_chain',side_effect=read), patch.object(self.k,'write_chain',side_effect=write):
            with self.assertRaises(ValueError): self.k.change_chain(self.root, True, self.uid)
        self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())

    def test_stock_projection_requires_absent_filter(self):
        self.prepare()
        with patch.object(self.k,'native',return_value=self.proof()), patch.object(self.k,'verify_ready',return_value={'integrity_verified':True}):
            with patch.object(self.k,'read_chain',return_value=[self.k.filter_entry(self.root)]):
                self.assertFalse(self.k.status(self.root,self.uid)['effective']['stock_verified'])
            with patch.object(self.k,'read_chain',return_value=[]):
                self.assertTrue(self.k.status(self.root,self.uid)['effective']['stock_verified'])

    def test_routing_status_requires_cytv_to_be_first(self):
        self.prepare()
        own = self.k.filter_entry(self.root)
        foreign = {'file':'/var/lib/tvweb/remotekeys-filter.js','handler':'handleGlasshouseKeys'}
        armed = dict(self.proof(), healthy=True, stopped=False, state='armed', guardian_pid=123, stock_verified=False)
        with patch.object(self.k,'native',return_value=armed), patch.object(self.k,'verify_ready',return_value={}):
            for chain, active in (([own,foreign], True), ([foreign,own], False)):
                with patch.object(self.k,'read_chain',return_value=chain):
                    effective = self.k.status(self.root,self.uid)['effective']
                    self.assertTrue(effective['filter_installed'])
                    self.assertIs(effective['routing_active'],active)

    def test_restore_stops_native_before_removing_filter(self):
        self.prepare(); calls=[]; chain=[self.k.filter_entry(self.root)]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json',dict(schema=1,entry=chain[0],token='1'*32),self.uid)
        def native(args,*a,**kw): calls.append(args[0]); return self.proof()
        def write(value): calls.append('chain'); chain[:]=value
        with patch.object(self.k,'native',side_effect=native), patch.object(self.k,'read_chain',side_effect=lambda:list(chain)), patch.object(self.k,'write_chain',side_effect=write):
            self.assertEqual(self.k.execute('restore',root=self.root,uid=self.uid),'restored')
        self.assertLess(calls.index('--restore'),calls.index('chain'))

    def test_removal_reconciles_ui_failure_only_with_fresh_stock_proof(self):
        self.admission = dict(self.generic(), model='OLED48A19LA', firmware='03.53.45', webos='6.5.3')
        self.check_ui_failure_recovery(lambda: self.k.restore_for_removal(self.root, self.uid))

    def test_webos6_removal_with_home_over_content(self):
        self.admission = dict(self.generic(), model='65NANO926PB', firmware='03.34.55', webos='6.3.2')
        work = self.root
        vendor = {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}
        stopped = self.proof()
        failure = dict(stopped, returnValue=False, reason='ui_release_failed')
        content = 'content.youtube'
        for case in ('home-over-content', 'home-only', 'content-only', 'hidden-home', 'wrong-home-type',
                     'other-card', 'extra-card', 'duplicate-home', 'project-card', 'helper-card',
                     'other-display', 'malformed-visible', 'foreign-filter', 'chain-drift',
                     'foreground-changed', 'other-attempt', 'other-sdk', 'ordinary-restore'):
            with self.subTest(case=case):
                self.root = work/case; self.root.mkdir(mode=0o700)
                self.admission['webos'] = '7.3.2' if case == 'other-sdk' else '6.3.2'
                self.prepare()
                background = self.k.APP if case == 'project-card' else (
                    'com.local.nativehome' if case == 'helper-card' else content)
                own = self.k.filter_entry(self.root)
                self.k.atomic(self.root/'c1-keyfilter/ownership.json',
                              dict(schema=1, entry=own, token='1'*32), self.uid)
                chain = [own, vendor]
                if case == 'foreign-filter':
                    chain.append({'file': '/foreign/home.js', 'handler': 'otherHome'})
                home = {'appId': self.k.STOCK, 'windowType': self.k.HOME, 'displayId': 0}
                card = {'appId': background, 'windowType': self.k.CARD, 'displayId': 0}
                surfaces = {
                    'home-only': [home],
                    'content-only': [card],
                    'hidden-home': [card, dict(home, visible=False)],
                    'wrong-home-type': [card, dict(home, windowType=self.k.CARD)],
                    'other-card': [dict(card, appId='other.content'), home],
                    'extra-card': [card, home, dict(card, appId='extra.content')],
                    'duplicate-home': [card, home, home],
                    'other-display': [card, dict(home, displayId=1)],
                    'malformed-visible': [card, dict(home, visible=1)],
                }.get(case, [card, home])
                sam_reads = []
                def luna(uri, payload):
                    if uri == 'luna://com.webos.applicationManager/getForegroundAppInfo':
                        sam_reads.append(uri)
                        if case == 'chain-drift' and len(sam_reads)>1:
                            chain.append({'file': '/foreign/home.js', 'handler': 'otherHome'})
                        app = 'other.content' if case == 'foreground-changed' and len(sam_reads)>1 else background
                        return {'returnValue': True, 'appId': app}
                    self.assertEqual(uri, 'luna://com.webos.surfacemanager/getForegroundAppInfo')
                    return {'returnValue': True, 'foregroundAppInfo': surfaces}
                native_calls = []
                def native(args, *_args, **_kwargs):
                    native_calls.append(args)
                    if args == ['--restore']:
                        return failure
                    if case == 'other-attempt' and len(native_calls)>2:
                        return dict(stopped, token='2'*32)
                    return stopped
                with patch.object(self.k, 'native', side_effect=native), \
                        patch.object(self.k, 'read_chain', side_effect=lambda: list(chain)), \
                        patch.object(self.k, 'write_chain', side_effect=lambda value, **kw: chain.__setitem__(slice(None), value)), \
                        patch.object(self.k, 'luna', side_effect=luna):
                    if case == 'home-over-content':
                        self.assertEqual(self.k.restore_for_removal(self.root, self.uid), 'restored')
                        self.assertEqual(chain, [vendor])
                        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
                        self.assertEqual(len(sam_reads), 2)
                    else:
                        with self.assertRaises(ValueError):
                            if case == 'ordinary-restore':
                                self.k.restore_locked(self.root, self.uid, explicit_restore=True)
                            else:
                                self.k.restore_for_removal(self.root, self.uid)
                        self.assertNotEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')


    def test_removal_with_unchanged_boot_id_and_reused_controller_pid(self):
        self.admission = dict(self.generic(), model='OLED48A19LA', firmware='03.53.45', webos='6.5.3')
        self.prepare()
        record = self.root/'c1-keyfilter/controller.json'
        controller = dict(pid=5618, start=351275, token='1'*32, boot=self.k.boot_identity())
        chain = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        for case in ('stock', 'unverified-stock', 'foreign-overlay'):
            with self.subTest(case=case):
                self.k.atomic(record, controller, self.uid)
                stopped = dict(self.proof(), reason='input_lost', stock_verified=case != 'unverified-stock')
                failure = dict(self.proof(), returnValue=False, reason='ui_release_failed')
                surfaces = [{'appId': self.k.STOCK, 'windowType': self.k.HOME}]
                if case == 'foreign-overlay':
                    surfaces.append({'appId': self.k.APP, 'windowType': '_WEBOS_WINDOW_TYPE_OVERLAY'})
                with patch.object(self.k, 'native', side_effect=[failure, stopped, stopped]), \
                        patch.object(self.k, 'read_chain', return_value=chain), \
                        patch.object(self.k, 'process_start', return_value=9619) as start, \
                        patch.object(self.k.os, 'kill') as signal, \
                        patch.object(self.k, 'luna', side_effect=[
                            {'returnValue': True, 'appId': self.k.STOCK},
                            {'returnValue': True, 'foregroundAppInfo': surfaces},
                        ]):
                    if case == 'stock':
                        self.assertEqual(self.k.restore_for_removal(self.root, self.uid), 'restored')
                        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
                    else:
                        with self.assertRaises(ValueError) as caught:
                            self.k.restore_for_removal(self.root, self.uid)
                        self.assertEqual(caught.exception.restore_check,
                                         'native-stop-unverified' if case == 'unverified-stock'
                                         else 'stock-surface-unverified')
                    signal.assert_not_called()
                    if case == 'unverified-stock':
                        start.assert_not_called()
                        self.assertEqual(json.loads(record.read_text()), controller)
                    else:
                        start.assert_called_once_with(controller['pid'])
                        self.assertFalse(record.exists())

    def test_schema2_boot_restores_stock_routing_without_opening_home(self):
        self.admission.update(model='OLED55C14LB', firmware='03.53.45', webos='6.5.3')
        self.assertEqual(self.prepare()['schema'], 2)
        token = '1'*32
        own = self.k.filter_entry(self.root)
        stock = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        chain = [own, *stock]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json',
                      dict(schema=1, entry=own, token=token), self.uid)
        self.k.write_intent(self.root, False, token, 'recovering', self.uid)

        def write(value):
            chain[:] = value

        with patch.object(self.k, 'native', return_value=self.proof()) as native, \
                patch.object(self.k, 'read_chain', side_effect=lambda: chain.copy()), \
                patch.object(self.k, 'write_chain', side_effect=write) as configd, \
                patch.object(self.k, 'luna', side_effect=self.read_factory_home_setting) as settings:
            for _ in range(2):
                native.reset_mock()
                self.assertEqual(self.k.execute('boot', root=self.root, uid=self.uid), 'restored')
                self.assertEqual(chain, stock)
                self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
                self.assertEqual([call.args[0] for call in native.call_args_list],
                                 [['--restore-routing'], ['--status'], ['--status']])
            configd.assert_called_once_with(stock)
            self.assertEqual(settings.call_count, 2)

            native.reset_mock()
            settings.reset_mock()
            self.assertEqual(self.k.execute('restore', root=self.root, uid=self.uid), 'restored')
            self.assertEqual([call.args[0] for call in native.call_args_list], [['--restore'], ['--status']])
            settings.assert_not_called()

    def test_schema2_boot_keeps_recovering_when_stock_destination_is_unverified(self):
        self.prepare()
        stock = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        with patch.object(self.k, 'native', return_value=self.proof()) as native, \
                patch.object(self.k, 'read_chain', return_value=stock), \
                patch.object(self.k, 'luna', return_value={'returnValue': False}):
            with self.assertRaisesRegex(ValueError, 'Explicit LG Home destination not verified') as error:
                self.k.execute('boot', root=self.root, uid=self.uid)
        self.assertEqual(error.exception.restore_check, 'stock-destination-readback-unverified')
        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'recovering')
        self.assertEqual([call.args[0] for call in native.call_args_list], [['--restore-routing'], ['--status']])

    def test_c1_boot_and_restore_retire_reused_controller_pid_after_reboot(self):
        # Observed on OLED55C14LB 03.53.45 (schema 2): the record has no boot
        # field, the kernel boot ID survives reboots, and after a cold boot the
        # recorded PID belonged to /usr/sbin/physical-device-manager.
        self.admission = dict(self.admission, model='OLED55C14LB', firmware='03.53.45', webos='6.5.3')
        self.assertEqual(self.prepare()['schema'], 2)
        record = self.root/'c1-keyfilter/controller.json'
        controller = dict(pid=4282, start=23011, token='1'*32)
        chain = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        stopped = dict(self.proof(), reason='input_lost')
        for mode in ('boot', 'restore'):
            with self.subTest(mode=mode):
                self.k.atomic(record, controller, self.uid)
                self.k.write_intent(self.root, False, '1'*32, 'recovering', self.uid)
                with patch.object(self.k, 'native', return_value=stopped), \
                        patch.object(self.k, 'read_chain', side_effect=lambda: list(chain)), \
                        patch.object(self.k, 'luna', side_effect=self.read_factory_home_setting), \
                        patch.object(self.k, 'process_start', return_value=2335) as start, \
                        patch.object(self.k.os, 'kill') as signal:
                    self.assertEqual(self.k.execute(mode, root=self.root, uid=self.uid), 'restored')
                start.assert_called_once_with(controller['pid'])
                signal.assert_not_called()
                self.assertFalse(record.exists())
                self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
        # A changed Home identity still retains the record and its evidence.
        self.k.atomic(record, controller, self.uid)
        with patch.object(self.k, 'native', return_value=dict(stopped, stock_verified=False)), \
                patch.object(self.k, 'read_chain', side_effect=lambda: list(chain)), \
                patch.object(self.k, 'process_start', return_value=2335) as start:
            with self.assertRaises(ValueError):
                self.k.execute('boot', root=self.root, uid=self.uid)
        start.assert_not_called()
        self.assertEqual(json.loads(record.read_text()), controller)

    def test_webos5_ribbon_removal_with_live_tv_foreground(self):
        import hashlib

        self.admission = dict(self.generic(), model='50UN7300AUD', firmware='04.64.00', webos='5.6.2')
        work = self.root
        vendor = {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}
        stopped = self.proof()
        failure = dict(stopped, returnValue=False, reason='ui_release_failed')
        live_tv = {'appId': 'com.webos.app.livetv', 'windowType': self.k.CARD}
        ribbon = {'appId': self.k.STOCK, 'windowType': self.k.HOME, 'visible': True}
        settings_uri = 'luna://com.webos.settingsservice/getSystemSettings'
        for case in ('ribbon', 'ribbon-only', 'string-settings', 'live-tv-only', 'hidden-ribbon',
                     'project-overlay', 'foreign-filter', 'unknown-script', 'foreign-home',
                     'unknown-home', 'bad-settings', 'chain-drift', 'other-attempt', 'ordinary-restore', 'other-sdk'):
            with self.subTest(case=case):
                self.root = work/case
                self.root.mkdir(mode=0o700)
                self.admission['webos'] = '6.5.3' if case == 'other-sdk' else '5.6.2'
                self.prepare()
                own = self.k.filter_entry(self.root)
                self.k.atomic(self.root/'c1-keyfilter/ownership.json',
                              dict(schema=1, entry=own, token='1'*32), self.uid)
                chain = [own, vendor]
                if case == 'foreign-filter':
                    chain.append({'file': '/foreign/home.js', 'handler': 'otherHome'})
                surfaces = {
                    'ribbon-only': [ribbon],
                    'live-tv-only': [live_tv],
                    'hidden-ribbon': [dict(ribbon, visible=False), live_tv],
                    'project-overlay': [ribbon, live_tv, {'appId': self.k.APP, 'windowType': self.k.CARD}],
                }.get(case, [ribbon, live_tv])
                defaults = {
                    'foreign-home': {'home': 'other.home'},
                    'unknown-home': {},
                    'bad-settings': '{"home":',
                    'string-settings': json.dumps({'home': self.k.STOCK}),
                }.get(case, {'home': self.k.STOCK})
                replies = {
                    'luna://com.webos.applicationManager/getForegroundAppInfo':
                        {'returnValue': True, 'appId': live_tv['appId']},
                    'luna://com.webos.surfacemanager/getForegroundAppInfo':
                        {'returnValue': True, 'foregroundAppInfo': surfaces},
                    settings_uri: {'returnValue': True, 'settings': {'defaultApps': defaults}},
                }
                current = dict(stopped, token='2'*32) if case == 'other-attempt' else stopped
                def native(args, *_args, **_kwargs):
                    if args == ['--restore']:
                        return failure
                    return current if chain == [vendor] else stopped
                def write(value, **_kwargs):
                    chain[:] = value
                def read_luna(uri, _payload):
                    if uri == settings_uri and case == 'chain-drift':
                        chain.append({'file': '/foreign/home.js', 'handler': 'otherHome'})
                    return replies[uri]

                factory_script = b'factory-system-ui'
                script = b'unknown-system-ui' if case == 'unknown-script' else factory_script
                with patch.object(self.k, 'native', side_effect=native), \
                        patch.object(self.k, 'read_chain', side_effect=lambda: list(chain)), \
                        patch.object(self.k, 'write_chain', side_effect=write), \
                        patch.object(self.k, 'luna', side_effect=read_luna) as luna, \
                        patch.object(self.k, 'vendor_script', return_value=script), \
                        patch.object(self.k, 'WEBOS5_RIBBON_SYSTEM_UI_SHA256',
                                     hashlib.sha256(factory_script).hexdigest(), create=True):
                    if case in ('ribbon', 'ribbon-only', 'string-settings'):
                        self.assertEqual(self.k.restore_for_removal(self.root, self.uid), 'restored')
                        self.assertEqual(chain, [vendor])
                        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
                        luna.assert_any_call(settings_uri, {'category': 'general', 'keys': ['defaultApps']})
                    else:
                        with self.assertRaises(ValueError) as caught:
                            if case == 'ordinary-restore':
                                self.k.restore_locked(self.root, self.uid, explicit_restore=True)
                            else:
                                self.k.restore_for_removal(self.root, self.uid)
                        self.assertEqual(caught.exception.native_reason, 'ui_release_failed')
                        if case == 'chain-drift':
                            self.assertEqual(caught.exception.restore_check, 'stock-routing-unverified')
                        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'recovering')

    def test_review_recovery_reconciles_ui_failure_on_reported_c1(self):
        self.admission.update(model='OLED65C1PSA', firmware='03.53.45', webos='6.5.3')
        self.check_ui_failure_recovery(lambda: self.k.execute('restore', root=self.root, uid=self.uid))


    def test_verified_activation_restore_uses_current_guard_on_retained_c1(self):
        import hashlib
        from types import SimpleNamespace
        from unittest.mock import Mock
        import clean_removal

        work = self.root
        self.root = work/'retained'
        self.root.mkdir(mode=0o700)
        self.admission.update(model='OLED65C1PSA', firmware='03.53.45', webos='6.5.3')
        self.prepare()
        token = '1'*32
        own = self.k.filter_entry(self.root)
        vendor = {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}
        chain = [own, vendor]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json', dict(schema=1, entry=own, token=token), self.uid)
        retained_script = self.root/'runtime/c1_keyfilter.py'
        retained_script.parent.mkdir(mode=0o700)
        retained_script.write_text('raise AssertionError("retained mutation code executed")')
        selection_path = self.root/'home-backend.json'
        selection = selection_path.read_bytes()
        payload = work/'current'
        guard = payload/'runtime/c1-keyfilter-guard'
        guard.parent.mkdir(parents=True)
        guard.write_bytes(b'verified current executable')
        guard.chmod(0o600)
        manifest = {'files': {'runtime/c1-keyfilter-guard': hashlib.sha256(guard.read_bytes()).hexdigest()}}
        installed = Mock(STATE=self.root)
        installed.selection.side_effect = self.k.selection
        cli = Mock()
        cli.gate_backend.return_value = installed
        replies = Mock(side_effect=[
            {'returnValue': True, 'appId': self.k.STOCK},
            {'returnValue': True, 'foregroundAppInfo': [{'appId': self.k.STOCK, 'windowType': self.k.HOME}]},
        ])
        native_actions = []

        def run(argv, **_):
            self.assertEqual(argv[0], str(guard))
            native_actions.append(argv[-1])
            value = self.proof()
            value['reason'] = 'input_expired'
            if argv[-1] == '--restore':
                value.update(returnValue=False, reason='ui_release_failed')
            return SimpleNamespace(stdout=json.dumps(value).encode(), returncode=int(not value['returnValue']))

        with patch.dict(sys.modules, {'cli': cli}), patch.object(sys, 'path', list(sys.path)), \
                patch.object(self.k, 'STATE', self.root), patch.object(self.k, 'binary'), \
                patch.object(self.k.subprocess, 'run', side_effect=run), \
                patch.object(self.k, 'luna', replies), \
                patch.object(self.k, 'read_chain', side_effect=lambda: list(chain)), \
                patch.object(self.k, 'write_chain', side_effect=lambda value: chain.__setitem__(slice(None), value)) as write, \
                patch('deploy.verify_bundle', return_value=manifest), \
                patch('deploy.checked_file', return_value=guard.read_bytes()):
            with self.assertRaisesRegex(ValueError, 'native_recovery_attempt_changed'):
                clean_removal.runtime_restore(payload, self.uid, activation_token='2'*32)
            write.assert_not_called()
            self.assertEqual(native_actions, ['--status'])
            native_actions.clear()

            reply = clean_removal.runtime_restore(payload, self.uid, activation_token=token)
            self.assertEqual(reply['result'], 'restored')
            self.assertEqual(reply['native_restored_sha256'], hashlib.sha256(selection).hexdigest())
            self.assertEqual(chain, [vendor])
            self.assertEqual(native_actions, ['--status', '--restore', '--status', '--status'])
            self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')

            chain[:] = [own, vendor]
            native_actions.clear()
            write.reset_mock()
            ownership = self.root/'c1-keyfilter/ownership.json'
            self.k.atomic(ownership, dict(schema=1, entry=own, token='2'*32), self.uid)
            with self.assertRaisesRegex(ValueError, 'native_recovery_filter_unverified'):
                clean_removal.runtime_restore(payload, self.uid, activation_token=token, routing_only=True)
            write.assert_not_called()
            self.assertEqual(native_actions, ['--status'])

            native_actions.clear()
            self.k.atomic(ownership, dict(schema=1, entry=own, token=token), self.uid)
            replies.side_effect = None
            replies.return_value = {'returnValue':True, 'settings':{'defaultApps':{'home':self.k.APP}}}
            with self.assertRaisesRegex(ValueError, 'LG Home destination') as refused:
                clean_removal.runtime_restore(payload, self.uid, activation_token=token, routing_only=True)
            self.assertEqual(refused.exception.restore_check, 'stock-destination-unverified')
            self.assertEqual(refused.exception.destination_check, 'home-overridden')
            self.assertEqual(native_actions, ['--status'])
            write.assert_not_called()

            native_actions.clear()
            replies.reset_mock()
            replies.return_value['settings']['defaultApps']['home'] = self.k.STOCK
            reply = clean_removal.runtime_restore(payload, self.uid, activation_token=token, routing_only=True)
            self.assertEqual(reply['result'], 'restored')
            self.assertEqual(reply['native_restored_sha256'], hashlib.sha256(selection).hexdigest())
            self.assertEqual(chain, [vendor])
            self.assertEqual(native_actions, ['--status', '--restore-routing', '--status', '--status'])
            self.assertTrue(all(request.args[0].endswith('/getSystemSettings') for request in replies.call_args_list))
            self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
        self.assertEqual(selection_path.read_bytes(), selection)
        cli.main.assert_not_called()

    def check_ui_failure_recovery(self, restore):
        from types import SimpleNamespace

        self.prepare()
        own = self.k.filter_entry(self.root)
        vendor = {'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}
        self.k.atomic(self.root/'c1-keyfilter/ownership.json', dict(schema=1, entry=own, token='1'*32), self.uid)
        for case in ('stock', 'explicit-stock', 'other-foreground', 'cytv-overlay', 'stock-changed',
                     'other-attempt', 'lock-failed', 'display-false', 'display-float',
                     'hidden', 'absent', 'malformed-visibility', 'retirement-failed', 'malformed-proof', 'readback-drift'):
            with self.subTest(case=case):
                chain = [own, vendor]
                initial = self.proof()
                stopped = dict(initial)
                failure = dict(initial, returnValue=False, reason='ui_release_failed')
                if case == 'stock-changed':
                    stopped['stock_verified'] = False
                if case == 'other-attempt':
                    stopped['token'] = '2'*32
                if case == 'lock-failed':
                    failure['reason'] = 'effect_busy'
                if case == 'retirement-failed':
                    failure['reason'] = 'retirement_failed'
                if case == 'malformed-proof':
                    del failure['guardian_pid']
                def run(argv, **kwargs):
                    value = failure if argv[-1] == '--restore' else stopped
                    if case == 'readback-drift' and argv[-1] == '--status' and chain == [vendor]:
                        value = dict(stopped, token='2'*32)
                    return SimpleNamespace(stdout=json.dumps(value).encode(), returncode=int(not value['returnValue']))
                def write(value, **kwargs):
                    chain[:] = value
                foreground = {'returnValue': True, 'appId': self.k.APP if case == 'other-foreground' else self.k.STOCK}
                surfaces = [{'appId': self.k.STOCK, 'windowType': self.k.HOME}]
                if case == 'cytv-overlay':
                    surfaces.append({'appId': self.k.APP, 'windowType': '_WEBOS_WINDOW_TYPE_OVERLAY'})
                if case == 'absent':
                    surfaces.clear()
                if case == 'display-false':
                    surfaces[0].update(displayId=False, visible=True)
                if case == 'display-float':
                    surfaces[0].update(displayId=0.0, visible=True)
                if case == 'hidden':
                    surfaces[0]['visible'] = False
                if case == 'malformed-visibility':
                    surfaces.append(dict(surfaces[0], visible=0))
                if case == 'explicit-stock':
                    surfaces[0].update(displayId=0, visible=True)
                def read_foreground(uri, payload):
                    if uri == 'luna://com.webos.surfacemanager/getForegroundAppInfo':
                        return {'returnValue': True, 'foregroundAppInfo': surfaces}
                    self.assertEqual(uri, 'luna://com.webos.applicationManager/getForegroundAppInfo')
                    return foreground
                with patch.object(self.k, 'binary', return_value=Path('/verified-guard')), \
                        patch.object(self.k.subprocess, 'run', side_effect=run), \
                        patch.object(self.k, 'read_chain', side_effect=lambda: list(chain)), \
                        patch.object(self.k, 'write_chain', side_effect=write), \
                        patch.object(self.k, 'luna', side_effect=read_foreground):
                    if case in ('stock', 'explicit-stock'):
                        self.assertEqual(restore(), 'restored')
                        self.assertEqual(chain, [vendor])
                        self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'disabled')
                    else:
                        with self.assertRaises(ValueError) as caught:
                            restore()
                        if case in ('other-attempt', 'lock-failed', 'retirement-failed',
                                    'stock-changed', 'malformed-proof'):
                            self.assertEqual(chain, [own, vendor])
                        else:
                            self.assertEqual(self.k.read_intent(self.root, self.uid)['phase'], 'recovering')
                        self.assertFalse(self.k.read_intent(self.root, self.uid)['enabled'])
                        self.assertEqual(caught.exception.native_reason, failure['reason'])

    def test_lifecycle_replay_cancel_and_unknown_visibility(self):
        policy=self.k.ReturnPolicy('1'*32)
        card=lambda app,event='foreground':dict(event=event,appId=app,windowType='_WEBOS_WINDOW_TYPE_CARD')
        policy.event(card('content'),0)
        policy.event(card('content','stop'),1)
        self.assertFalse(policy.due(1.4))
        self.assertTrue(policy.due(2))
        policy.event(card('new-content'),2.1)
        self.assertFalse(policy.due(3))
        policy.event(card('com.webos.app.home'),3)
        home={'returnValue':True,'foregroundAppInfo':[dict(appId='com.webos.app.home',windowType='_WEBOS_WINDOW_TYPE_CARD')]}
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        self.assertTrue(self.k.can_return(home,{'returnValue':True,'state':'Active'},proof,'1'*32,{'returnValue':True,'appId':self.k.STOCK}))
        home['foregroundAppInfo'].append(dict(appId=self.k.APP,windowType='_WEBOS_WINDOW_TYPE_OVERLAY'))
        self.assertFalse(self.k.can_return(home,{'returnValue':True,'state':'Active'},proof,'1'*32))
        for value in ({}, {'returnValue':True,'foregroundAppInfo':[]}, {'returnValue':True,'foregroundAppInfo':[{}]}):
            self.assertFalse(self.k.can_return(value,{'returnValue':True,'state':'Active'},proof,'1'*32))
        policy.event({'event':'unknown'},3.1)
        self.assertFalse(policy.due(4))

    def test_return_to_confirmed_empty_requires_both_views_and_active_intent(self):
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        power={'returnValue':True,'state':'Active'}
        empty={'returnValue':True,'foregroundAppInfo':[]}
        self.assertTrue(self.k.can_return(empty,power,proof,'1'*32,{'returnValue':True,'appId':''}))
        self.assertFalse(self.k.can_return(empty,power,proof,'1'*32,{'returnValue':True,'appId':'new-content'}))
        self.assertFalse(self.k.can_return(empty,{},proof,'1'*32,{'returnValue':True,'appId':''}))
        policy=self.k.ReturnPolicy('1'*32)
        policy.event(dict(event='stop',appId='background',windowType='_WEBOS_WINDOW_TYPE_CARD'),1)
        self.assertFalse(policy.due(2))

    def test_sam_stop_and_close_without_window_type_keep_original_return_deadline(self):
        policy = self.k.ReturnPolicy('1' * 32)
        foreground = dict(event='foreground', appId='player', windowType=self.k.CARD)
        stop = dict(event='stop', appId='player', reason='windowPolicy')
        close = dict(stop, event='close')
        policy.event(foreground, 0)
        policy.event(stop, 1)
        self.assertFalse(policy.due(1.9))
        self.assertTrue(policy.due(2))
        policy.event(close, 1.5)
        self.assertTrue(policy.due(2))
        home = dict(event='foreground', appId=self.k.STOCK, windowType='_WEBOS_WINDOW_TYPE_HOME')
        for events in ((stop, home, close), (home, stop, close)):
            with self.subTest(events=events):
                policy = self.k.ReturnPolicy('1' * 32)
                policy.event(foreground, 0)
                for at, event in enumerate(events):
                    policy.event(event, 1 + at / 10)
                self.assertFalse(policy.due(1.9))
                self.assertTrue(policy.due(2))

    def test_sam_stop_needs_tracked_content_and_new_activity_cancels_return(self):
        foreground = dict(event='foreground', appId='player', windowType=self.k.CARD)
        stop = dict(event='stop', appId='player', reason='windowPolicy')
        for interruption in (
            dict(stop, event='launch', appId='new-app'),
            dict(stop, event='close', appId='other-app'),
            dict(foreground, appId='settings', windowType='_WEBOS_WINDOW_TYPE_OVERLAY'),
        ):
            with self.subTest(interruption=interruption):
                policy = self.k.ReturnPolicy('1' * 32)
                policy.event(stop, 0)
                self.assertFalse(policy.due(1))
                policy.event(foreground, 1)
                policy.event(stop, 2)
                self.assertTrue(policy.due(3))
                policy.event(interruption, 2.5)
                self.assertFalse(policy.due(3))

    def test_native_home_surface_requires_stock_identity_and_no_other_visible_app(self):
        token = '1' * 32
        home = dict(appId=self.k.STOCK, windowType='_WEBOS_WINDOW_TYPE_HOME', displayId=0)
        policy = self.k.ReturnPolicy(token)
        policy.event(dict(home, event='foreground'), 1)
        self.assertTrue(policy.due(2))

        proof = self.proof()
        proof.update(healthy=True, stopped=False, state='armed', guardian_pid=123, stock_verified=False)
        power = dict(returnValue=True, state='Active')
        def ready(rows, foreground=''):
            return self.k.can_return(dict(returnValue=True, foregroundAppInfo=rows), power,
                                     proof, token, dict(returnValue=True, appId=foreground))
        self.assertTrue(ready([home]))
        self.assertFalse(ready([home], 'player'))
        self.assertFalse(ready([dict(home, appId='foreign')]))
        self.assertFalse(ready([dict(home, displayId=1)]))
        self.assertFalse(ready([dict(home, multiview=True)]))
        self.assertFalse(ready([home, dict(appId='settings', windowType='_WEBOS_WINDOW_TYPE_OVERLAY')]))

    def test_modified_owned_entry_restore_retains_native_stop_and_evidence(self):
        self.prepare()
        changed=dict(self.k.filter_entry(self.root),handler='foreign')
        with patch.object(self.k,'native',return_value=self.proof()) as native, patch.object(self.k,'read_chain',return_value=[changed]), patch.object(self.k,'write_chain') as write:
            with self.assertRaises(ValueError): self.k.execute('restore',root=self.root,uid=self.uid)
        self.assertEqual(native.call_args_list[0].args[0],['--restore'])
        write.assert_not_called()

    def test_unknown_exact_owned_entry_is_not_destructively_removed(self):
        self.prepare()
        with patch.object(self.k,'read_chain',return_value=[self.k.filter_entry(self.root)]), patch.object(self.k,'write_chain') as write:
            with self.assertRaises(ValueError): self.k.change_chain(self.root,False,self.uid)
        write.assert_not_called()

    def test_orphan_filter_is_retired_only_after_verified_stock_readback(self):
        import struct

        target = self.root / 'native-home'
        elf = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        target.write_bytes(elf)
        target.chmod(0o700)
        own = self.k.filter_entry()
        stock = [{'file': '/usr/lib/qt5/qml/KeyFilters/systemUi.js', 'handler': 'handleSystemKeys'}]
        glasshouse = {'file': '/var/lib/glasshouse/remotekeys-filter.js', 'handler': 'handleGlasshouseKeys',
                      'options': {'enabled': True}}
        remaining = [glasshouse, *stock]
        stale = [glasshouse, own, *stock]
        info = dict(returnValue=True, modelName='OLED65C11LB', firmwareVersion='03.53.45', sdkVersion='6.5.3')

        with (
            patch.object(self.k.legacy, 'TARGET', target),
            patch.object(self.k.legacy, 'native_home', return_value=elf),
            patch.object(self.k.os, 'geteuid', return_value=0),
            patch.object(self.k.sys, 'platform', 'linux'),
            patch('struct.calcsize', return_value=4),
            patch.object(self.k, 'luna', return_value=info),
            patch.object(self.k, 'require_generic_environment', side_effect=self.k.removal_vendor_chain) as verify,
            patch.object(self.k, 'read_chain') as read,
            patch.object(self.k, 'write_chain') as write,
        ):
            read.side_effect = [stale, stale, remaining]
            self.k.probe(removed_apps=('com.cleanyourtv.root.preview',), retire_orphan=True)
            verify.assert_called_once_with(remaining, removed_apps=('com.cleanyourtv.root.preview',))
            write.assert_called_once_with(remaining)

            for before, recheck in (
                (stale, stock),
                ([own, own, *stock], stale),
                ([dict(own, extra=True), *stock], stale),
                ([own], stale),
                ([own, *stock, {'file': '/var/lib/other/../clean-your-tv-root/extra.js', 'handler': 'foreign'}], stale),
                ([own, *stock, {'file': '/media/developer/apps/usr/palm/services/com.cleanyourtv.root.preview.service/filter.js',
                                'handler': 'foreign'}], stale),
            ):
                with self.subTest(before=before, recheck=recheck):
                    write.reset_mock()
                    read.side_effect = [before, recheck]
                    with self.assertRaises(ValueError):
                        self.k.probe(removed_apps=('com.cleanyourtv.root.preview',), retire_orphan=True)
                    write.assert_not_called()

            read.side_effect = [stale, stale, stale]
            with self.assertRaisesRegex(ValueError, 'readback'):
                self.k.probe(removed_apps=('com.cleanyourtv.root.preview',), retire_orphan=True)
            write.assert_called_once_with(remaining)
            write.reset_mock()
            read.side_effect = [remaining, remaining]
            self.k.probe(removed_apps=('com.cleanyourtv.root.preview',))
            write.assert_not_called()
            read.side_effect = [stale, stale]
            with self.assertRaisesRegex(ValueError, 'CYTV filter remains'):
                self.k.probe(removed_apps=('com.cleanyourtv.root.preview',))
            write.assert_not_called()

    def test_probe_is_independent_of_legacy_checkpoint_probe(self):
        target=self.root/'home'; target.write_bytes(b'ELF')
        with patch.object(self.k.legacy,'TARGET',target), patch.object(self.k.os,'geteuid',return_value=0), patch.object(self.k.sys,'platform','linux'), patch.object(self.k.legacy,'probe',side_effect=AssertionError('legacy checkpoint probe')), patch.object(self.k.legacy,'native_home',return_value=b'ELF'), patch.object(self.k.legacy,'admit',return_value={k:self.admission[k] for k in ('model','firmware','webos')}), patch.object(self.k,'luna',return_value={'returnValue':True}), patch.object(self.k,'read_chain',return_value=[]),patch.object(self.k,'require_generic_environment') as environment:
            target.chmod(0o700)
            observed=self.k.probe()
        self.assertEqual(observed['target']['size'],3)
        environment.assert_called_once_with(removed_apps=(self.k.APP,))
        self.assertEqual(observed['model'],self.admission['model'])

    def test_restore_clears_interrupted_prewrite_intent_after_absence_readback(self):
        self.prepare()
        own=self.k.filter_entry(self.root)
        pending=self.root/'c1-keyfilter/pending.json'
        self.k.atomic(pending,dict(schema=1,before=[],after=[own],entry=own),self.uid)
        with patch.object(self.k,'read_chain',return_value=[]): self.k.change_chain(self.root,False,self.uid)
        self.assertFalse(pending.exists())

    def test_native_selfcheck_accepts_only_exact_success_shape(self):
        from types import SimpleNamespace
        value=dict(returnValue=True,backend=self.k.BACKEND,routing=self.k.ROUTING,selfcheck=True)
        with patch.object(self.k,'binary',return_value=Path('/fake')), patch.object(self.k.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(value).encode())):
            self.assertEqual(self.k.native(['--selfcheck'],self.root,self.uid),value)
        for bad in (dict(value,selfcheck=False),dict(value,extra=True),dict(value,routing='old')):
            with patch.object(self.k,'binary',return_value=Path('/fake')), patch.object(self.k.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(bad).encode())):
                with self.assertRaises(ValueError): self.k.native(['--selfcheck'],self.root,self.uid)

    def test_cold_package_import_without_runtime_search_path(self):
        import subprocess
        result=subprocess.run([sys.executable,'-c','from runtime import c1_keyfilter, emergency_reader; assert c1_keyfilter.ROUTING == "compositor-keyfilter-v1"; assert callable(emergency_reader.open_remote)'],cwd=ROOT,env=dict(os.environ,PYTHONPATH=''),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_controller_retirement_never_signals_a_pid_after_identity_check(self):
        self.prepare()
        record=self.root/'c1-keyfilter/controller.json'
        self.k.atomic(record,dict(pid=123,start=456,token='1'*32),self.uid)
        with patch.object(self.k,'process_start',side_effect=[456,FileNotFoundError()]), patch.object(Path,'read_bytes',return_value=str(self.root/'runtime/c1_keyfilter.py').encode()+b'\0--watch\0'+b'1'*32+b'\0'), patch.object(self.k.os,'kill',side_effect=AssertionError('unsafe PID signal')):
            self.k.stop_controller(self.root,self.uid)
        self.assertFalse(record.exists())

    def test_delayed_return_cancels_on_event_after_each_rpc(self):
        self.prepare()
        self.k.write_intent(self.root,True,'1'*32,'active',self.uid)
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        replies=[{'returnValue':True,'state':'Active'},{'returnValue':True,'foregroundAppInfo':[]},{'returnValue':True,'appId':''}]
        for stage in range(4):
            with patch.object(self.k,'luna',side_effect=replies), patch.object(self.k,'native',return_value=proof):
                changes=iter([False]*stage+[True])
                self.assertFalse(self.k.return_ready(self.root,self.uid,'1'*32,lambda:next(changes)))

    def test_optional_return_timeout_preserves_controller_heartbeat(self):
        self.prepare()
        token = '1' * 32
        self.k.write_intent(self.root, True, token, 'active', self.uid)
        proof = dict(self.proof(), healthy=True, stopped=False, state='armed',
                     guardian_pid=123, stock_verified=False)
        replies = [
            {'returnValue': True, 'state': 'Active'},
            {'returnValue': True, 'foregroundAppInfo': []},
            {'returnValue': True, 'appId': self.k.STOCK},
        ]
        subscription = b'{"returnValue":true,"subscribed":true}\n'

        for stage in ('power', 'surfaces', 'foreground', 'native'):
            with self.subTest(stage=stage):
                child = Mock()
                child.poll.side_effect = [None, None, 0, 0]
                policy = Mock(generation=0)
                policy.due.side_effect = [True, False]
                luna_replies = replies
                native_replies = [proof, proof]
                if stage == 'native':
                    native_replies = [proof, self.k.subprocess.TimeoutExpired('guard', .3), proof]
                else:
                    index = ('power', 'surfaces', 'foreground').index(stage)
                    luna_replies = replies[:index] + [TimeoutError(stage)]

                with patch.object(self.k.subprocess, 'Popen', return_value=child), \
                     patch.object(self.k, 'ReturnPolicy', return_value=policy), \
                     patch.object(self.k.select, 'select', side_effect=[([child.stdout], [], [])] + [([], [], [])] * 4), \
                     patch.object(self.k.os, 'read', return_value=subscription), \
                     patch.object(self.k.os, 'set_blocking'), \
                     patch.object(self.k.os, 'close'), \
                     patch.object(self.k.os, 'write', side_effect=lambda fd, data: len(data)) as write, \
                     patch.object(self.k, 'luna', side_effect=luna_replies) as luna, \
                     patch.object(self.k, 'native', side_effect=native_replies) as native, \
                     patch.object(self.k, 'launch_return') as launch:
                    self.k.watch(token, 10, 11, self.root, self.uid)

                self.assertEqual([data for fd, data in (call.args for call in write.call_args_list)
                                  if fd == 10], [b'READY\n', b'PING\n', b'PING\n', b'LOST\n'])
                self.assertEqual(luna.call_count, len(luna_replies))
                self.assertEqual(native.call_count, len(native_replies))
                launch.assert_not_called()

    def test_return_dispatch_uses_only_fixed_native_home_barrier(self):
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        with patch.object(self.k,'native',return_value=proof) as native, patch.object(self.k,'luna',side_effect=AssertionError('raw launch bypass')):
            self.k.launch_return(self.root,self.uid,'1'*32)
        native.assert_called_once_with(['--home','1'*32],self.root,self.uid,timeout=2.5)
        stopped=self.proof()
        for value in (stopped,dict(proof,token='2'*32)):
            with patch.object(self.k,'native',return_value=value):
                with self.assertRaises(ValueError): self.k.launch_return(self.root,self.uid,'1'*32)

    def test_stock_surface_does_not_override_conflicting_or_unknown_sam(self):
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        power={'returnValue':True,'state':'Active'}
        stock={'returnValue':True,'foregroundAppInfo':[dict(appId=self.k.STOCK,windowType=self.k.CARD)]}
        for foreground in ({'returnValue':True,'appId':'netflix'},None,{}, {'returnValue':True}, {'returnValue':False,'appId':self.k.STOCK}, {'returnValue':True,'appId':None}, {'returnValue':True,'appId':[]}):
            with self.subTest(foreground=foreground):
                self.assertFalse(self.k.can_return(stock,power,proof,'1'*32,foreground))
        for app in ('',self.k.STOCK):
            self.assertTrue(self.k.can_return(stock,power,proof,'1'*32,{'returnValue':True,'appId':app}))

    def test_native_rejects_mount_or_inconsistent_lease(self):
        proof=self.proof(); proof['opaque']=True
        with self.assertRaises(ValueError): self.k.validate_native(proof)
        proof=self.proof(); proof['mounted']=True
        with self.assertRaises(ValueError): self.k.validate_native(proof)
        proof=self.proof(); proof['healthy']=True
        with self.assertRaises(ValueError): self.k.validate_native(proof)


    def test_enable_chain_failure_restores_and_does_not_retry(self):
        self.prepare()
        (self.root/'runtime').mkdir()
        (self.root/'runtime/c1-home-filter.js').write_text('filter')
        (self.root/'runtime/c1-home-filter.js').chmod(0o600)
        with patch.object(self.k,'verify_ready',return_value={'integrity_verified':True}), patch.object(self.k,'native',return_value=self.proof()), patch.object(self.k,'probe',return_value=self.admission), patch.object(self.k,'read_chain',return_value=[]), patch.object(self.k,'binary',return_value=Path('/fake')), patch('helper_bridge.require_idle'), patch.object(self.k,'change_chain',side_effect=RuntimeError('write')) as chain, patch.object(self.k,'restore_locked') as restore:
            with self.assertRaises(RuntimeError): self.k.execute('enable',root=self.root,uid=self.uid)
        self.assertEqual(chain.call_count,1)
        restore.assert_called_once()


    def test_enable_controller_failure_restores_without_native_guard_launch(self):
        self.prepare()
        (self.root/'runtime').mkdir()
        script=self.root/'runtime/c1-home-filter.js'; script.write_text('filter'); script.chmod(0o600)
        with patch.object(self.k,'verify_ready',return_value={'integrity_verified':True}), patch.object(self.k,'native',return_value=self.proof()), patch.object(self.k,'probe',return_value=self.admission), patch.object(self.k,'read_chain',return_value=[]), patch.object(self.k,'binary',return_value=Path('/fake')), patch('helper_bridge.require_idle'), patch.object(self.k,'change_chain'), patch.object(self.k,'start_controller',side_effect=RuntimeError('controller startup')), patch.object(self.k,'restore_locked') as restore, patch.object(self.k.subprocess,'Popen') as popen:
            with self.assertRaises(RuntimeError): self.k.execute('enable',root=self.root,uid=self.uid)
        restore.assert_called_once()
        popen.assert_not_called()


if __name__=='__main__': unittest.main()
