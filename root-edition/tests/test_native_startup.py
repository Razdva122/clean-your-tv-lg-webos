"""Native startup routing with real policy/receipt files, no TV effects."""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import runpy
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import c1_keyfilter as gate
try:
    import native_startup as startup
except ImportError:
    startup = None


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(startup, 'Native startup policy is missing')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'c1-keyfilter').mkdir(mode=0o700)
        self.uid = os.getuid()
        self.boot = '11111111-1111-4111-8111-111111111111'
        self.session = self.boot + ':session-' + 'a' * 32
        self.intent = dict(schema=1, enabled=True, phase='active', token='b'*32,
                           boot=self.boot, session=self.session)
        self.current = dict(intent=self.intent, effective=dict(returnValue=True,
            backend=gate.BACKEND, routing=gate.ROUTING, state='armed', mounted=False,
            healthy=True, stock_verified=False, stopped=False, token=self.intent['token'],
            guardian_pid=123, reason='', profiles=None), recovery=dict(integrity_verified=True))
        self.result = copy.deepcopy(self.current)
        self.app = 'com.webos.app.livetv'
        self.window = gate.CARD
        for target, value in ((gate, {'status': lambda *_: copy.deepcopy(self.current),
                'boot_identity': lambda: self.boot, 'boot_session': lambda: self.session}),):
            for name, replacement in value.items():
                p = patch.object(target, name, replacement); p.start(); self.addCleanup(p.stop)
        p = patch('boot_gate.observation', return_value=(True, False)); self.normal = p.start(); self.addCleanup(p.stop)
        p = patch.object(gate, 'luna', side_effect=self.luna); self.call = p.start(); self.addCleanup(p.stop)
        p = patch.object(gate, 'native', side_effect=self.native); self.launch = p.start(); self.addCleanup(p.stop)

    def luna(self, uri, payload, timeout=5, **kw):
        self.assertEqual(uri, 'luna://com.webos.surfacemanager/getForegroundAppInfo')
        self.assertLessEqual(timeout, .5)
        return dict(returnValue=True, foregroundAppInfo=[dict(appId=self.app, windowType=self.window)])

    def native(self, args, *unused, **kw):
        self.assertEqual(args, ['--home', self.intent['token']])
        self.assertTrue((self.root/'c1-keyfilter/startup-attempt.json').exists(), 'Receipt must precede launch')
        return dict(self.current['effective'])

    def after(self):
        return startup.after_boot(self.result, self.root, self.uid)

    def test_tv_launch_and_repeat_callback(self):
        self.assertEqual(self.after(), 'launched')
        self.assertEqual(self.after(), 'already-attempted')
        self.assertEqual(self.launch.call_count, 1)

    def test_selected_sources_and_hdmi_protection(self):
        self.assertEqual(startup.status(self.root, self.uid), dict(sources=dict(tv=True,youtube=False),active=True))
        for app in ('com.webos.app.hdmi1', 'youtube.leanback.v4', gate.APP, '', 'other.app'):
            self.app=app
            self.assertEqual(self.after(), 'preserved')
        self.launch.assert_not_called()
        startup.configure(dict(tv=False,youtube=True), self.root,self.uid)
        self.app='com.webos.app.livetv'; self.assertEqual(self.after(),'preserved')
        self.app='youtube.leanback.v4'; self.assertEqual(self.after(),'launched')

    def test_inactive_mismatched_stale_and_emergency_contexts(self):
        for fault in ('off','token','boot','session','recovery','health','normal','emergency'):
            with self.subTest(fault=fault):
                current=copy.deepcopy(self.current)
                if fault=='off':self.current['intent']['enabled']=False
                if fault=='token':self.current['effective']['token']='c'*32
                if fault=='boot':self.current['intent']['boot']='22222222-2222-4222-8222-222222222222'
                if fault=='session':self.current['intent']['session']=self.boot+':session-'+'d'*32
                if fault=='recovery':self.current['recovery']['integrity_verified']=False
                if fault=='health':self.current['effective']['healthy']=False
                self.normal.return_value=(fault!='normal',fault=='emergency')
                self.assertEqual(self.after(),'unavailable')
                self.current=current;self.intent=self.current['intent']
        self.launch.assert_not_called()

    def test_uncertain_launch_is_not_replayed(self):
        self.launch.side_effect=TimeoutError('unknown launch result')
        self.assertEqual(self.after(),'unavailable')
        self.assertEqual(self.after(),'already-attempted')
        self.assertEqual(self.launch.call_count,1)

    def test_ambiguous_foreground_and_changed_context_are_preserved(self):
        self.window='_WEBOS_WINDOW_TYPE_OVERLAY'
        self.assertEqual(self.after(),'preserved')
        self.window=gate.CARD
        self.call.side_effect=lambda *a,**kw: dict(returnValue=True,foregroundAppInfo=[
            dict(appId=self.app,windowType=self.window), dict(appId='other',windowType=self.window)])
        self.assertEqual(self.after(),'preserved')
        self.call.side_effect=TimeoutError('no fresh foreground')
        self.assertEqual(self.after(),'unavailable')
        self.launch.assert_not_called()

    def test_context_changing_during_foreground_read_cannot_launch(self):
        def changed(*args, **kw):
            self.current['intent']['enabled']=False
            return self.luna(*args, **kw)
        self.call.side_effect=changed
        self.assertEqual(self.after(),'unavailable')
        self.launch.assert_not_called()

    def test_slow_status_cannot_submit_stale_foreground(self):
        with patch.object(startup.time,'monotonic',side_effect=[0,0,0,2]):
            self.assertEqual(self.after(),'preserved')
        self.launch.assert_not_called()

    def test_verified_channel_metadata_is_tv_and_unknown_metadata_is_preserved(self):
        self.app='mgg4.5.channelplus'
        path='/media/cryptofs/apps/usr/palm/applications/'+self.app
        metadata=dict(returnValue=True,appInfo=dict(id=self.app,type='web',vendor='LifeStream ltd.',
            folderPath=path,activeFolderPath=path,CPApp=True,internalInstallationOnly=True))
        def replies(uri,payload,**kw):
            return self.luna(uri,payload,**kw) if 'surfacemanager' in uri else metadata
        self.call.side_effect=replies
        metadata['appInfo']['CPApp']=1
        self.assertEqual(self.after(),'preserved')
        metadata['appInfo']['CPApp']=True
        self.assertEqual(self.after(),'launched')

    def test_real_cli_configure_envelope_uses_native_policy(self):
        import device_adapter as d
        cli=Path(__file__).resolve().parents[1]/'runtime/cli.py'
        with patch.object(d,'STATE',self.root), patch.object(d,'EXPECTED_UID',self.uid), \
                patch.object(gate.legacy,'selection',return_value={'schema':3}), \
                patch.object(sys,'argv',[str(cli),'startup','configure']), \
                patch('sys.stdin',io.TextIOWrapper(io.BytesIO(b'{"tv":false,"youtube":true}'))), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            runpy.run_path(str(cli),run_name='__main__')
        self.assertEqual(json.loads(output.getvalue()),dict(returnValue=True,
            result=dict(sources=dict(tv=False,youtube=True),active=True)))
        self.assertEqual(json.loads((self.root/'startup-policy.json').read_text()),
                         dict(version=2,sources=dict(tv=False,youtube=True)))

    def test_entry_configures_v2_and_preserves_legacy_or_unreadable_evidence(self):
        path=self.root/'startup-policy.json'
        path.write_text(json.dumps(dict(version=1,sources=dict(tv=False,youtube=True,hdmi=True))));path.chmod(0o600)
        before=path.read_bytes()
        self.assertEqual(startup.entry(['status'],self.root,self.uid)['sources'],dict(tv=False,youtube=True))
        self.assertEqual(path.read_bytes(),before)
        with patch('sys.stdin',io.TextIOWrapper(io.BytesIO(b'{"tv": true,"youtube": false}'))):
            self.assertTrue(startup.entry(['configure'],self.root,self.uid)['active'])
        self.assertEqual(json.loads(path.read_text()),dict(version=2,sources=dict(tv=True,youtube=False)))
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.current['intent']['enabled']=False
        with self.assertRaises(ValueError):startup.configure(dict(tv=False,youtube=True),self.root,self.uid)
        self.current['intent']['enabled']=True
        for raw in ('{', '{"version":2,"sources":{"tv":1,"youtube":false}}'):
            path.write_text(raw)
            with self.assertRaises(ValueError):startup.configure(dict(tv=False,youtube=True),self.root,self.uid)
            self.assertEqual(path.read_text(),raw)

    def test_invalid_receipt_is_retained(self):
        directory=gate.private_directory(self.root,self.uid)
        path=directory/'startup-attempt.json';path.write_text('{}');path.chmod(0o600)
        self.assertEqual(self.after(),'unavailable')
        self.assertEqual(path.read_text(),'{}');self.launch.assert_not_called()


if __name__=='__main__':unittest.main()
