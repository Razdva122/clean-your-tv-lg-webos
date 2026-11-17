"""Disk-backed multi-component supervisor recovery tests."""
import copy
import importlib
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'root-edition'))
pkg = types.ModuleType('system_updater'); pkg.__path__ = [str(ROOT/'system-updater')]; sys.modules['system_updater'] = pkg
support = types.ModuleType('system_updater.support'); support.__path__ = [str(ROOT/'root-edition/updater')]; sys.modules['system_updater.support'] = support
from system_updater.support.store import Store

def profile():
    return {'schema':1,'inventory':{'apps':[],'inputs':[]},'config':{'columns':5,'dockApps':[],'hiddenApps':[]},'settings':{}}

def release(version):
    return {'schema':1,'edition':'no-root','release':'v'+version,'supervisor':1,'notes':'Test',
            'components':[{'name':name,'application':app,'version':version,'kind':'ipk','sha256':str(i)*64,'size':10,'local':True}
                          for i,(name,app) in enumerate([('home','com.gathin.tvhome'),('helper','com.local.nativehome'),('updater','com.cleanyourtv.updater')],1)]}

class IO:
    def __init__(self):
        self.time=1000; self.calls=[]; self.current=release('1.0.0'); self.candidate=release('1.1.0'); self.outcomes=[]; self.active=True; self.prepare_error=False
    def require_components(self):pass
    def components_present(self):return True
    def now(self):return self.time
    def offer(self,edition):return {'candidate':copy.deepcopy(self.candidate),'prior':copy.deepcopy(self.current),'canInstall':True}
    def check_legacy(self):self.calls.append('legacy')
    def verify_baseline(self,baseline):return all(self.installed(c['application'])==c['version'] for c in baseline['components'])
    def installed(self,app):return next(c['version'] for c in self.current['components'] if c['application']==app)
    def prepare(self,candidate,prior):
        self.calls.append('cache-all')
        if self.prepare_error:raise ValueError('cache failed')
    def suspend(self,tx):self.calls.append('suspend');self.active=False
    def routing_safe(self):return not self.active
    def install(self,c,on_submit,on_terminal,on_intent):
        on_intent()
        self.calls.append('install:'+c['name']+':'+c['version']);on_submit({'application':c['application']})
        outcome=self.outcomes.pop(0) if self.outcomes else True
        if outcome=='crash':raise KeyboardInterrupt('power loss')
        if outcome is None:return
        if outcome:
            for old in self.current['components']:
                if old['name']==c['name']:old['version']=c['version']
        on_terminal({'success':outcome})
    def verify_installed(self,c):return self.installed(c['application'])==c['version']
    def launch(self,edition):self.calls.append('launch')
    def finish(self,tx):self.calls.append('finish');return {'status':'unchanged'}

class CoreBase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(os.path.realpath(self.tmp.name),uid=os.getuid());self.io=IO()
        try:self.Manager=importlib.import_module('system_updater.core').Manager
        except ModuleNotFoundError:self.fail('independent durable supervisor is missing')
        self.m=self.Manager(self.store,self.io)
    def tearDown(self):self.tmp.cleanup()
    def reserve(self):return self.m.install('no-root','v1.1.0',profile())
    def advance(self,phase,limit=40):
        for _ in range(limit):
            tx=self.m.run()
            if tx['phase']==phase:return tx
        self.fail(tx)

class Tests(CoreBase):
    def test_no_root_capture_admits_empty_discovery_color_before_storing_profile(self):
        captured=profile()
        captured['inventory']['apps']=[
            {'id':'test.app','title':'Test app','icon':'data:image/png;base64,AAAA','iconColor':''},
            {'id':'test.color','title':'Colored app','icon':'data:image/png;base64,AAAA','iconColor':'#123abc'},
        ]
        tx=self.m.install('no-root','v1.1.0',captured)
        self.advance('verifying')
        apps=self.m.restore_profile('no-root')['profile']['inventory']['apps']
        self.assertNotIn('iconColor',apps[0])
        self.assertEqual(apps[1]['iconColor'],'#123abc')
        self.assertEqual(captured['inventory']['apps'][0]['iconColor'],'')
        self.assertEqual(self.m.status()['id'],tx['id'])

    def test_bootstrap_admits_empty_color_before_engine_reservation(self):
        from system_updater.cli import engine_request
        from system_updater.core import validate_profile

        captured=profile()
        captured['inventory']['apps']=[
            {'id':'test.app','title':'Test app','icon':'data:image/png;base64,AAAA','iconColor':''},
        ]
        checked=engine_request('engine-profile',{'edition':'no-root','profile':captured},self.store,self.io)
        self.assertNotIn('iconColor',checked['inventory']['apps'][0])
        with self.assertRaisesRegex(ValueError,'invalid icon color'):
            validate_profile(captured,'no-root')

    def test_no_root_capture_still_rejects_other_invalid_colors(self):
        captured=profile()
        captured['inventory']['apps']=[
            {'id':'test.app','title':'Test app','icon':'data:image/png;base64,AAAA','iconColor':'red'},
        ]
        with self.assertRaisesRegex(ValueError,'invalid icon color'):
            self.m.install('no-root','v1.1.0',captured)
        self.assertIsNone(self.store.read('transaction'))

    def test_reserves_before_mutation_and_caches_whole_set(self):
        tx=self.reserve();self.assertEqual(tx['phase'],'preparing');self.assertFalse(any(c.startswith('install:') for c in self.io.calls))
        self.advance('verifying');self.assertLess(self.io.calls.index('cache-all'),self.io.calls.index('suspend'))
        self.assertEqual(len([c for c in self.io.calls if c.startswith('install:')]),3)
    def test_interrupted_submission_never_replays_or_rolls_back(self):
        self.reserve();self.io.outcomes=['crash']
        with self.assertRaises(KeyboardInterrupt):self.advance('verifying')
        self.m=self.Manager(self.store,self.io);tx=self.m.run();self.assertEqual(tx['phase'],'recovery-required');self.assertFalse(tx['canRollback'])
        self.m.rollback();self.m.run();self.assertEqual(len([c for c in self.io.calls if c.startswith('install:')]),1)
    def test_failed_cache_leaves_device_untouched(self):
        self.reserve();self.io.prepare_error=True;self.advance('aborted');self.assertNotIn('suspend',self.io.calls)
    def test_health_bound_to_transaction_launcher_version_and_restore(self):
        tx=self.reserve();self.advance('verifying');restored=self.m.restore_profile('no-root');self.assertEqual(restored['profile'],profile());self.assertEqual(restored['version'],'1.1.0')
        with self.assertRaises(ValueError):self.m.healthy('no-root',tx['id'],'1.0.0')
        self.m.healthy('no-root',tx['id'],'1.1.0');self.advance('complete');self.assertEqual(self.store.read('current-no-root')['release'],'v1.1.0')
    def test_timeout_rolls_back_in_reverse_and_requires_rollback_health(self):
        self.reserve();tx=self.advance('verifying');self.io.time+=121;self.advance('verifying-rollback')
        legs=[c for c in self.io.calls if c.startswith('install:')];self.assertEqual(legs[-3:],['install:updater:1.0.0','install:helper:1.0.0','install:home:1.0.0'])
        self.assertEqual(self.m.restore_profile('no-root')['version'],'1.0.0');self.m.healthy('no-root',tx['id'],'1.0.0');self.advance('rolled-back')
    def test_explicit_retained_rollback_after_complete(self):
        self.reserve();tx=self.advance('verifying');self.m.healthy('no-root',tx['id'],'1.1.0');self.advance('complete');self.assertTrue(self.m.status()['canRollback']);self.m.rollback();self.advance('verifying-rollback')
    def test_restart_between_component_intent_and_call_is_unknown(self):
        self.reserve();self.advance('installing');tx=self.store.read('transaction');tx['components'][0]['installEvidence']['intent']=True;self.store.write('transaction',tx)
        self.m=self.Manager(self.store,self.io);self.assertEqual(self.m.run()['phase'],'recovery-required');self.assertFalse(any(c.startswith('install:') for c in self.io.calls))
    def test_profile_digest_and_journal_corruption_block_writes(self):
        self.reserve();tx=self.store.read('transaction');tx['profileDigest']='0'*64;self.store.write('transaction',tx);self.assertEqual(self.m.run()['phase'],'recovery-required');self.assertFalse(any(c.startswith('install:') for c in self.io.calls))
    def test_unknown_second_component_does_not_undo_first(self):
        self.reserve();self.io.outcomes=[True,None];self.advance('recovery-required');self.m.rollback();self.assertEqual(len([c for c in self.io.calls if c.startswith('install:')]),2)
    def test_no_root_profile_retains_bounded_renewal_history(self):
        p=profile();p['renewal']={'enabled':False,'lastRenewedAt':123};self.m.install('no-root','v1.1.0',p);self.advance('verifying');self.assertEqual(self.m.restore_profile('no-root')['profile'],p)

if __name__=='__main__':unittest.main()

class LayoutTests(CoreBase):
    # Reuse the disk-backed contract for layout restoration as well.
    def test_existing_json_layout_roundtrips(self):
        p=profile();p['settings']['tvhome.layout']='{"version":1,"ids":["app"],"hidden":[],"catalog":[]}'
        self.m.install('no-root','v1.1.0',p);self.advance('verifying');self.assertEqual(self.m.restore_profile('no-root')['profile'],p)

class TerminalErrorTests(CoreBase):
    def test_terminal_success_followed_by_registration_failure_triggers_rollback(self):
        install=self.io.install
        def fail_after_receipt(c,submitted,terminal,on_intent):
            install(c,submitted,terminal,on_intent)
            raise ValueError('registration restoration failed')
        self.io.install=fail_after_receipt;self.reserve();self.assertEqual(self.advance('rolling-back')['phase'],'rolling-back')

class RootIO(IO):
    def __init__(self):
        super().__init__()
        for release_value in (self.current,self.candidate):
            release_value['edition']='root'
            for c,(name,app) in zip(release_value['components'],[('root','com.cleanyourtv.root.preview'),('root-updater','com.cleanyourtv.root.updater'),('root-infrastructure',None)]):c.update(name=name,application=app,kind='infrastructure' if app is None else 'ipk')
    def verify_baseline(self,baseline):return all(self.verify_installed(c) for c in baseline['components'])
    def verify_installed(self,c):return next(old['version'] for old in self.current['components'] if old['name']==c['name'])==c['version']

class LocalInfrastructureTests(CoreBase):
    def test_interrupted_local_infrastructure_resumes_without_replaying_ipks(self):
        self.io=RootIO();self.m=self.Manager(self.store,self.io);self.m.install('root','v1.1.0',profile());self.io.outcomes=[True,True,'crash']
        with self.assertRaises(KeyboardInterrupt):self.advance('verifying')
        self.io.routing_safe=lambda:self.fail('mixed runtime must not execute during local infrastructure reconciliation')
        self.m=self.Manager(self.store,self.io);tx=self.advance('verifying');self.assertEqual(sum(c=='install:root:1.1.0' for c in self.io.calls),1);self.assertEqual(sum(c=='install:root-infrastructure:1.1.0' for c in self.io.calls),2)
        self.m.healthy('root',tx['id'],'1.1.0');self.advance('complete')

class RollbackPreconditionTests(CoreBase):
    def test_failed_rollback_suspension_blocks_instead_of_retry_loop(self):
        self.reserve();self.advance('verifying');self.io.time+=121;self.advance('rolling-back')
        def fail_suspend(tx):raise ValueError('newer routing intent prevents suspension')
        self.io.suspend=fail_suspend;self.assertEqual(self.m.run()['phase'],'recovery-required');self.assertEqual(self.m.run()['phase'],'recovery-required')

class ComponentVersionTests(CoreBase):
    def test_bootstrap_release_never_allows_component_downgrade(self):
        self.io.current['release']='v0.0.0';self.io.candidate['components'][1]['version']='0.9.0'
        with self.assertRaisesRegex(ValueError,'downgrade'):self.reserve()
        self.assertIsNone(self.store.read('transaction'));self.assertFalse(any(c.startswith('install:') for c in self.io.calls))

class OriginalIntentCallbackTests(CoreBase):
    def test_submission_without_original_intent_callback_is_refused(self):
        self.reserve();self.advance('installing')
        def install(c,submitted,terminal,on_intent):submitted({'application':c['application']})
        self.io.install=install
        result=self.m.run();e=result['components'][0]['installEvidence']
        self.assertEqual(result['phase'],'recovery-required')
        self.assertEqual(e,{'intent':False,'submitted':None,'terminal':None})

    def test_original_intent_callback_cannot_be_invoked_twice(self):
        self.reserve();self.advance('installing')
        def install(c,submitted,terminal,on_intent):
            on_intent();on_intent();submitted({'application':c['application']})
        self.io.install=install
        result=self.m.run();e=result['components'][0]['installEvidence']
        self.assertEqual(result['phase'],'recovery-required')
        self.assertEqual(e,{'intent':True,'submitted':None,'terminal':None})
        self.assertEqual(self.Manager(self.store,self.io).run()['phase'],'recovery-required')

    def test_local_continuation_terminal_requires_this_invocations_intent_callback(self):
        self.io=RootIO();self.m=self.Manager(self.store,self.io)
        self.m.install('root','v1.1.0',profile());self.io.outcomes=[True,True,'crash']
        with self.assertRaises(KeyboardInterrupt):self.advance('verifying')
        def install(c,submitted,terminal,on_intent):terminal({'success':True})
        self.io.install=install
        result=self.Manager(self.store,self.io).run()
        self.assertEqual(result['phase'],'recovery-required')
        self.assertIsNone(result['components'][2]['installEvidence']['terminal'])

class ReservedEngineHandoffTests(CoreBase):
    def test_reserved_profile_survives_crash_before_child_journal(self):
        identifier='e'*32
        self.store.write('profile-'+identifier,profile())
        tx=self.m.install('no-root','v1.1.0',profile(),operation=identifier)
        self.assertEqual(tx['id'],identifier)
        self.assertEqual(tx['profile'],'profile-'+identifier)
        self.assertFalse(any(call.startswith('install:') for call in self.io.calls))
    def test_reserved_handoff_refuses_changed_immutable_profile(self):
        identifier='e'*32
        altered=profile();altered['config']['columns']=6
        self.store.write('profile-'+identifier,altered)
        with self.assertRaises(ValueError):self.m.install('no-root','v1.1.0',profile(),operation=identifier)
        self.assertIsNone(self.store.read('transaction'))
