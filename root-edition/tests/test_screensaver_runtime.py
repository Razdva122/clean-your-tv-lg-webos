"""Screensaver ownership reuses verified Root health without starting readers."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import intent_runtime as s

class ScreensaverRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.root.chmod(0o700)
        self.intent=dict(generation=8,enabled=True,phase='active',boot='private-boot',token='private-token')
        self.coordinator=SimpleNamespace(store=SimpleNamespace(read=lambda:dict(self.intent)),read_binding=lambda:{'transaction':'private-transaction'})
        for name,value in [('coordinator',lambda:self.coordinator),('_screensaver_verify',lambda:{'integrity_verified':True}),('_screensaver_require_idle',lambda:{}),('startup_require',lambda *args:None),('boot_identity',lambda:'private-boot'),('screensaver_remaining_health_ms',lambda transaction:1200),('_screensaver_luna',self.luna)]:
            p=patch.object(s,name,value);p.start();self.addCleanup(p.stop)
        for name,value in [('STATE',self.root),('EXPECTED_UID',os.getuid())]:
            p=patch.object(s.d,name,value);p.start();self.addCleanup(p.stop)
        self.surfaces=[{'appId':'com.cleanyourtv.root.preview','windowType':'_WEBOS_WINDOW_TYPE_CARD'}]
        self.power='Active'
        self.app_info={'returnValue':True,'appInfo':{'id':'com.cleanyourtv.screensaver','type':'web','defaultWindowType':'popup'}}
    def luna(self,uri,payload,timeout):
        if uri.endswith('/getAppInfo'):
            self.assertEqual(payload,{'id':'com.cleanyourtv.screensaver'})
            return self.app_info
        if uri.endswith('/getPowerState'):return {'returnValue':True,'state':self.power}
        self.assertTrue(uri.endswith('/getForegroundAppInfo'))
        return {'returnValue':True,'foregroundAppInfo':self.surfaces}
    def test_current_verified_generation_only_and_no_private_tokens(self):
        result=s.screensaver_status();self.assertTrue(result['owner']['active']);self.assertEqual(result['owner']['generation'],8)
        self.assertTrue(result['foregroundOwn']);self.assertEqual(result['validForMs'],1200)
        self.assertNotIn('private-',json.dumps(result));self.assertFalse(result['state']['enabled'])
        self.assertTrue(result['popupInstalled'])
    def test_companion_requires_verified_id_web_type_and_popup_metadata(self):
        for info in ({'returnValue':False}, {'returnValue':True,'appInfo':{}},
                     {'returnValue':True,'appInfo':dict(self.app_info['appInfo'],id='other')},
                     {'returnValue':True,'appInfo':dict(self.app_info['appInfo'],type='native')},
                     {'returnValue':True,'appInfo':dict(self.app_info['appInfo'],defaultWindowType='card')}):
            with self.subTest(info=info):
                self.app_info=info
                result=s.screensaver_status()
                self.assertFalse(result['popupInstalled'])
                self.assertIsNone(result['owner'])
    def test_failed_guard_or_competing_helper_leaves_owner_unavailable(self):
        for method in ('_screensaver_verify','_screensaver_require_idle','startup_require','screensaver_remaining_health_ms'):
            with self.subTest(method=method),patch.object(s,method,side_effect=ValueError('private-token')):
                result=s.screensaver_status();self.assertIsNone(result['owner']);self.assertFalse(result['foregroundOwn']);self.assertNotIn('private-token',json.dumps(result))
    def test_foreground_rejects_unknown_other_apps_and_allows_only_owned_popup(self):
        for surfaces,want in [([],False),([{'appId':'youtube','windowType':'_WEBOS_WINDOW_TYPE_CARD'}],False),(self.surfaces+[{'appId':'com.cleanyourtv.screensaver','windowType':'_WEBOS_WINDOW_TYPE_POPUP'}],True),(self.surfaces+[{'appId':'com.palm.app.settings','windowType':'_WEBOS_WINDOW_TYPE_OVERLAY'}],False),(self.surfaces+[{}],False)]:
            self.surfaces=surfaces;self.assertEqual(s.screensaver_status()['foregroundOwn'],want)
    def test_global_foreground_requires_an_ordinary_card_without_overlay(self):
        youtube = {'appId': 'youtube.leanback.v4', 'windowType': '_WEBOS_WINDOW_TYPE_CARD'}
        overlay = {'appId': 'com.palm.app.settings', 'windowType': '_WEBOS_WINDOW_TYPE_OVERLAY'}
        popup = {'appId': 'com.cleanyourtv.screensaver', 'windowType': '_WEBOS_WINDOW_TYPE_POPUP'}
        for surfaces, expected in [([youtube], True), ([youtube, overlay], False),
                                   ([youtube, popup], False), ([youtube, youtube], False),
                                   ([dict(youtube, pip=True)], False)]:
            with self.subTest(surfaces=surfaces):
                self.surfaces = surfaces
                result = s.screensaver_status()
                self.assertEqual(result['foregroundForeign'], expected)
                self.assertEqual(result['popupOwn'], surfaces == [youtube, popup])
    def test_standby_unknown_power_and_owner_change_during_read_fail_closed(self):
        for state in ('Suspend','Screen Off','Screen Saver','Unknown'):
            self.power=state;self.assertIsNone(s.screensaver_status()['owner'])
        self.power='Active'
        with patch.object(s,'startup_require',side_effect=[None,ValueError('owner changed')]):self.assertIsNone(s.screensaver_status()['owner'])
    def test_fresh_settings_choose_ambient_with_optional_clock(self):
        state = s.screensaver_settings()
        self.assertEqual(state['mode'], 'ambient')
        self.assertTrue(state['clockOverlay'])
        self.assertEqual(s.screensaver_configure(dict(state, clockOverlay=False)),
                         dict(state, clockOverlay=False))
    def test_settings_are_private_and_saved_global_media_intent_never_grants_capability(self):
        state={'enabled':True,'scope':'global','mode':'video','assetId':'fixture_1','idleTimeoutMs':60000}
        self.assertEqual(s.screensaver_configure(state),dict(state,clockOverlay=True,quality='auto'))
        state['clockOverlay']=False
        state['quality']='1080p'
        self.assertEqual(s.screensaver_configure(state),state);self.assertEqual(s.screensaver_status()['state'],state)
        path=self.root/'screensaver-settings.json';self.assertEqual(path.stat().st_mode&0o777,0o600)
        with self.assertRaises(ValueError):s.screensaver_configure(dict(state,idleTimeoutMs=0))
        with self.assertRaises(ValueError):s.screensaver_configure(dict(state,path='/tmp/untrusted'))
        path.unlink();path.symlink_to(self.root/'other')
        with self.assertRaises(OSError):s.screensaver_configure(state)
    def test_clock_presentation_is_persisted_and_invalid_updates_are_rejected(self):
        clock = {'locale': 'zh-Hant', 'hour12': True}
        state = dict(s.screensaver_settings(), clock=clock)
        self.assertEqual(s.screensaver_configure(state)['clock'], clock)
        self.assertEqual(s.screensaver_status()['state']['clock'], clock)
        with self.assertRaises(ValueError):
            s.screensaver_configure(dict(state, clock={'locale': 'zh-Hant', 'hour12': 'true'}))
        self.assertEqual(s.screensaver_settings()['clock'], clock)

    def test_integer_generation_and_expired_health_are_required(self):
        for generation in (True,-1,9007199254740992):
            self.intent['generation']=generation;self.assertIsNone(s.screensaver_status()['owner'])
        self.intent['generation']=8
        with patch.object(s,'screensaver_remaining_health_ms',return_value=0):self.assertIsNone(s.screensaver_status()['owner'])
    def test_cli_has_fixed_operations_and_bounded_configuration_input(self):
        import io,cli
        with patch.object(s,'screensaver_entry',return_value={'owner':None}) as entry:
            self.assertEqual(cli.execute('screensaver','status'),{'owner':None})
            entry.assert_called_once_with('status',None)
        with patch.object(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'x'*4097))):
            with self.assertRaises(ValueError):cli.execute('screensaver','configure')

if __name__=='__main__':unittest.main()
