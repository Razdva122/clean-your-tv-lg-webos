from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import update_guard as guard


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.uid=os.getuid();self.tx='a'*32
        self.intent=dict(version=1,generation=3,phase='active',enabled=True,boot='boot:1',token='old')
        self.saves=[];self.enables=0;self.restores=0
        for name,fn in [('_intent',lambda:dict(self.intent)),('_boot',lambda:'boot:1'),
                        ('_failsafe',lambda:False),('_restore',self.restore),('_enable',self.enable)]:
            p=patch.object(guard,name,fn,create=True);p.start();self.addCleanup(p.stop)
        guard.reserve(self.tx,self.root,self.uid)

    def restore(self):
        self.restores+=1;self.intent.update(phase='disabled',enabled=False)
        return 'restored'

    def enable(self):
        self.enables+=1;self.intent.update(generation=4,phase='active',enabled=True,token='new')
        return {'intent':dict(self.intent),'persistent':True}

    def suspend(self):return guard.suspend(self.tx,self.root,self.uid)
    def finish(self):return guard.finish(self.tx,self.root,self.uid)

    def test_active_resumes_once_and_finish_receipt_survives_restart(self):
        self.assertEqual(self.suspend(),'restored')
        self.assertFalse(self.intent['enabled'])
        self.assertEqual(self.finish(),{'status':'restored'})
        self.assertTrue(self.intent['enabled']);self.assertEqual(self.enables,1)
        self.assertEqual(self.finish(),{'status':'restored'});self.assertEqual(self.enables,1)
        with guard.control(self.root,self.uid):pass

    def boot_cli(self):
        import importlib.util
        import intent_runtime
        source=Path(__file__).resolve().parents[1]/'runtime/cli.py'
        spec=importlib.util.spec_from_file_location('home_resume_boot_cli',source)
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        for target,name,value in ((cli.d,'STATE',self.root),(cli.d,'EXPECTED_UID',self.uid),
                                  (cli.os,'geteuid',lambda:0),(cli,'inhibit',lambda root:None),
                                  (intent_runtime,'restore',self.restore)):
            self.enterContext(patch.object(target,name,value))
        return cli

    def assert_boot_preserves_resume(self,pending=False):
        cli=self.boot_cli();self.suspend()
        original=(self.root/'update-home-resume.json').read_bytes()
        if pending:
            # The update reservation can appear after boot's first path check.
            exists=os.path.lexists
            checked=[]
            def before_reservation(path):
                if path==self.root/'update-block.json' and not checked:
                    checked.append(True);return False
                return exists(path)
            self.enterContext(patch.object(cli.os.path,'lexists',before_reservation))
            self.enterContext(patch.object(guard,'control',side_effect=guard.ProductPending('update started')))
        self.assertEqual(cli.main('boot'),'restored')
        self.assertEqual(cli.main('boot'),'restored')
        self.assertFalse((self.root/'update-home-cancel.json').exists())
        self.assertEqual((self.root/'update-home-resume.json').read_bytes(),original)
        self.assertFalse(self.intent['enabled'])
        self.assertEqual(self.finish(),{'status':'restored'})
        self.assertTrue(self.intent['enabled']);self.assertEqual(self.enables,1)
        self.assertEqual(self.finish(),{'status':'restored'});self.assertEqual(self.enables,1)

    def test_automatic_boot_during_update_preserves_home_resume(self):
        self.assert_boot_preserves_resume()

    def test_automatic_boot_after_product_race_preserves_home_resume(self):
        self.assert_boot_preserves_resume(pending=True)

    def test_automatic_boot_cannot_clear_explicit_cancellation(self):
        cli=self.boot_cli();self.suspend();guard.cancel(self.root,self.uid)
        original=(self.root/'update-home-cancel.json').read_bytes()
        self.assertEqual(cli.main('boot'),'restored')
        self.assertEqual((self.root/'update-home-cancel.json').read_bytes(),original)
        self.assertEqual(self.finish(),{'status':'cancelled'});self.assertEqual(self.enables,0)

    def test_disabled_intent_is_not_enabled(self):
        self.intent.update(enabled=False,phase='disabled')
        self.suspend();self.assertEqual(self.finish(),{'status':'skipped'});self.assertEqual(self.enables,0)

    def test_explicit_off_between_reserve_and_suspend_cancels_resume(self):
        guard.cancel(self.root,self.uid)
        self.suspend()
        self.assertEqual(self.finish(),{'status':'cancelled'});self.assertEqual(self.enables,0)

    def test_cancel_while_disabled_wins(self):
        self.suspend();guard.cancel(self.root,self.uid)
        self.assertEqual(self.finish(),{'status':'cancelled'});self.assertEqual(self.enables,0)

    def test_cancel_during_activation_restores_again(self):
        self.suspend();old=self.enable
        def activate():
            result=old();guard.cancel(self.root,self.uid);return result
        with patch.object(guard,'_enable',activate):self.assertEqual(self.finish(),{'status':'cancelled'})
        self.assertFalse(self.intent['enabled']);self.assertEqual(self.restores,2)

    def test_changed_boot_failsafe_or_intent_skips(self):
        for scenario in ('boot','failsafe','intent'):
            with self.subTest(scenario=scenario):
                # Fresh transaction per subcase; completed receipts are never replayed.
                self.tx={'boot':'b','failsafe':'c','intent':'d'}[scenario]*32
                guard.release('a'*32,self.root,self.uid)
                guard.reserve(self.tx,self.root,self.uid)
                self.intent.update(generation=3,phase='active',enabled=True,token='old');self.suspend()
                if scenario=='intent':self.intent['token']='changed'
                with patch.object(guard,'_boot',lambda:'other' if scenario=='boot' else 'boot:1'),patch.object(guard,'_failsafe',lambda:scenario=='failsafe'):
                    self.assertEqual(self.finish(),{'status':'skipped'})
        self.assertEqual(self.enables,0)

    def test_wrong_transaction_cannot_suspend_finish_or_abort(self):
        self.suspend()
        for fn in (guard.suspend,guard.finish,guard.abort):
            with self.assertRaises(ValueError):fn('b'*32,self.root,self.uid)
        self.assertTrue((self.root/'update-block.json').exists());self.assertEqual(self.enables,0)

    def test_suspend_retry_keeps_original_intent(self):
        self.suspend();self.suspend();self.finish();self.assertEqual(self.enables,1)

    def test_interrupted_suspend_never_resumes(self):
        with patch.object(guard,'_restore',side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):self.suspend()
        self.suspend();self.assertEqual(self.finish(),{'status':'skipped'});self.assertEqual(self.enables,0)

    def test_finish_after_interrupted_suspend_recovers_off_without_enabling(self):
        with patch.object(guard,'_restore',side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):self.suspend()
        self.assertTrue(self.intent['enabled'])
        self.assertEqual(self.finish(),{'status':'skipped'})
        self.assertFalse(self.intent['enabled']);self.assertEqual(self.enables,0)

    def test_interrupted_activation_never_replays_and_restores(self):
        self.suspend()
        def crash():self.enables+=1;raise KeyboardInterrupt()
        with patch.object(guard,'_enable',crash):
            with self.assertRaises(KeyboardInterrupt):self.finish()
        self.assertEqual(self.finish(),{'status':'skipped'});self.assertEqual(self.enables,1)
        self.assertFalse(self.intent['enabled'])

    def test_failed_activation_restores_and_releases(self):
        self.suspend()
        with patch.object(guard,'_enable',side_effect=ValueError('input unavailable')):
            self.assertEqual(self.finish(),{'status':'failed','error':'input unavailable'})
        self.assertFalse(self.intent['enabled'])
        with guard.control(self.root,self.uid):pass

    def test_failed_restore_retains_reservation_and_blocks_enable(self):
        self.suspend()
        with patch.object(guard,'_enable',side_effect=ValueError('not ready')),patch.object(guard,'_restore',side_effect=ValueError('route unresolved')):
            with self.assertRaisesRegex(ValueError,'route unresolved'):self.finish()
        self.assertTrue((self.root/'update-block.json').exists())
        with self.assertRaises(RuntimeError):
            with guard.control(self.root,self.uid):pass

    def test_abort_and_legacy_release_never_enable(self):
        self.assertEqual(guard.finish(self.tx,self.root,self.uid),{'status':'unchanged'})
        self.assertEqual(guard.finish(self.tx,self.root,self.uid),{'status':'unchanged'})
        guard.reserve(self.tx,self.root,self.uid);self.suspend()
        self.assertEqual(guard.abort(self.tx,self.root,self.uid),{'status':'skipped'})
        self.assertEqual(self.finish(),{'status':'skipped'});self.assertEqual(self.enables,0)

    def test_cancel_does_not_take_update_lock(self):
        self.suspend()
        with guard.locked(self.root,self.uid):guard.cancel(self.root,self.uid)
        self.assertEqual(self.finish(),{'status':'cancelled'})

    def test_old_observer_cannot_cancel_another_intent(self):
        self.suspend()
        guard.cancel(self.root,self.uid,dict(self.intent,generation=2,token='stale'))
        self.assertEqual(self.finish(),{'status':'restored'})
    def test_fresh_reservation_same_transaction_starts_new_cycle(self):
        self.suspend();guard.cancel(self.root,self.uid);self.assertEqual(self.finish(),{'status':'cancelled'})
        self.intent.update(phase='active',enabled=True)
        guard.reserve(self.tx,self.root,self.uid);self.suspend()
        self.assertEqual(self.finish(),{'status':'restored'});self.assertEqual(self.enables,1)

    def test_repeated_reservation_does_not_clear_cancellation(self):
        self.suspend();guard.cancel(self.root,self.uid);guard.reserve(self.tx,self.root,self.uid)
        self.assertEqual(self.finish(),{'status':'cancelled'})

    def test_escape_during_new_activation_matches_live_ticket(self):
        self.suspend();old=self.enable
        def activate():
            result=old();guard.cancel(self.root,self.uid,dict(self.intent));return result
        with patch.object(guard,'_enable',activate):self.assertEqual(self.finish(),{'status':'cancelled'})

    def test_unreserved_abort_and_finish_are_unchanged_without_writes(self):
        guard.release(self.tx,self.root,self.uid)
        for fn in (guard.finish,guard.abort):
            self.assertEqual(fn(self.tx,self.root,self.uid),{'status':'unchanged'})
        self.assertFalse((self.root/'update-home-resume.json').exists())

    def test_old_receipt_without_reservation_does_not_block_new_abort(self):
        self.suspend();self.finish()
        before=(self.root/'update-home-resume.json').read_bytes()
        self.assertEqual(guard.abort('b'*32,self.root,self.uid),{'status':'unchanged'})
        self.assertEqual((self.root/'update-home-resume.json').read_bytes(),before)

    def test_corrupt_ticket_fails_closed_and_retains_reservation(self):
        self.suspend()
        path=self.root/'update-home-resume.json';value=json.loads(path.read_text())
        value['desired']='yes';path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):self.finish()
        self.assertTrue((self.root/'update-block.json').exists());self.assertEqual(self.enables,0)


class IntegrationTests(unittest.TestCase):
    def test_cli_internal_suspend_does_not_cancel_but_explicit_restore_always_does(self):
        import importlib.util
        source=Path(__file__).resolve().parents[1]/'runtime/cli.py'
        spec=importlib.util.spec_from_file_location('home_resume_cli',source)
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        import intent_runtime
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();uid=os.getuid();tx='a'*32
            guard.reserve(tx,root,uid)
            intent=dict(version=1,generation=1,phase='active',enabled=True,boot='boot:1',token='a')
            def restore():
                if intent['phase']=='disabled':return None
                intent.update(phase='disabled',enabled=False);return 'restored'
            with patch.object(cli.d,'main',return_value='absent'),patch.object(cli.d,'STATE',root),patch.object(cli.d,'EXPECTED_UID',uid),patch.object(cli.os,'geteuid',return_value=0),patch.object(guard,'_intent',lambda:dict(intent)),patch.object(guard,'_boot',lambda:'boot:1'),patch.object(intent_runtime,'restore',restore):
                self.assertEqual(cli.main('suspend-update',tx),'restored')
                self.assertFalse((root/'update-home-cancel.json').exists())
                self.assertEqual(cli.main('restore'),'absent')
                self.assertTrue((root/'update-home-cancel.json').exists())
                self.assertEqual(cli.main('finish-update',tx),{'status':'cancelled'})

    def test_explicit_restore_still_recovers_when_cancellation_file_is_corrupt(self):
        import importlib.util
        import intent_runtime
        source=Path(__file__).resolve().parents[1]/'runtime/cli.py'
        spec=importlib.util.spec_from_file_location('home_resume_cli_corrupt',source)
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        restored=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();uid=os.getuid();guard.reserve('a'*32,root,uid)
            (root/'update-home-resume.json').write_text('{}')
            with patch.object(cli.d,'STATE',root),patch.object(cli.d,'EXPECTED_UID',uid),patch.object(cli.os,'geteuid',return_value=0),patch.object(intent_runtime,'restore',lambda:restored.append(True) or 'restored'):
                with self.assertRaises(ValueError):cli.main('restore')
        self.assertEqual(restored,[True])

    def test_update_commands_are_root_only(self):
        import importlib.util
        source=Path(__file__).resolve().parents[1]/'runtime/cli.py'
        spec=importlib.util.spec_from_file_location('home_resume_cli_root',source)
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        with patch.object(cli.os,'geteuid',return_value=1000):
            for mode in ('suspend-update','finish-update','abort-update'):
                with self.assertRaises(PermissionError):cli.main(mode,'a'*32)



    def test_emergency_exit_cancels_only_current_binding(self):
        import persistent_recovery as recovery
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();uid=os.getuid();tx='a'*32
            intent=dict(version=1,generation=3,phase='active',enabled=True,boot='boot:1',token='old')
            guard.reserve(tx,root,uid)
            def restore():intent.update(phase='disabled',enabled=False);return 'restored'
            with patch.object(guard,'_intent',lambda:dict(intent)),patch.object(guard,'_boot',lambda:'boot:1'),patch.object(guard,'_restore',restore):
                guard.suspend(tx,root,uid)
            binding=root/'persistent-binding.json';binding.write_text('{}')
            c=SimpleNamespace(binding=binding,store=SimpleNamespace(read=lambda:dict(intent)),
                read_binding=lambda:dict(transaction='route',generation=3,token='old'),
                exit=lambda value,reason:dict(restored_transaction='route'))
            with patch.object(recovery.d,'STATE',root),patch.object(recovery.d,'EXPECTED_UID',uid),patch.object(recovery,'Coordinator',return_value=c):
                recovery.bound_exit('stale-route','escape')
                self.assertFalse((root/'update-home-cancel.json').exists())
                recovery.bound_exit('route','fault')
                self.assertFalse((root/'update-home-cancel.json').exists())
                recovery.bound_exit('route','escape')
                self.assertTrue((root/'update-home-cancel.json').exists())


if __name__=='__main__':unittest.main()
