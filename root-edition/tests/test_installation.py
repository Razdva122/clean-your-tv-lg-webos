import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installation import classify, Ownership, Busy, snapshot, device_operation, JOURNALS
from updater.store import Store


class ClassificationTests(unittest.TestCase):
    def state(self, **changes):
        values = dict(supported=True, packages_match=False, receipts_match=False,
                      pending=False, retained=False, complete=False, migration_supported=False)
        values.update(changes)
        return classify(values)

    def test_all_states_and_fixed_response(self):
        cases = [('unsupported', dict(supported=False)),
                 ('fresh', {}),
                 ('installed', dict(packages_match=True, receipts_match=True, complete=True)),
                 ('migration_required', dict(migration_supported=True)),
                 ('conflict', dict(packages_match=True)),
                 ('recovery_required', dict(retained=True))]
        for state, changes in cases:
            with self.subTest(state=state):
                result = self.state(**changes)
                self.assertEqual(set(result), {'state', 'reason', 'can_install', 'can_maintain'})
                self.assertEqual(result['state'], state)
                self.assertEqual(result['can_install'], state == 'fresh')
                self.assertEqual(result['can_maintain'], state == 'installed')

    def test_pending_matching_packages_are_not_finished(self):
        for marker in ('pending', 'retained'):
            result = self.state(packages_match=True, receipts_match=True, complete=True, **{marker: True})
            self.assertEqual(result['state'], 'recovery_required')
            self.assertFalse(result['can_maintain'])
            self.assertFalse(result['can_install'])

    def test_unknown_missing_and_non_boolean_fields_fail_closed(self):
        for value in ({}, {'supported': True}, dict(supported=True, protocol=2)):
            self.assertEqual(classify(value)['state'], 'conflict')
        self.assertEqual(self.state(pending=0)['state'], 'conflict')


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name).resolve()/'ownership', uid=os.getuid())
        self.owner = Ownership(self.store)

    def test_contention_status_and_restart_never_imply_completion(self):
        with self.owner.operation('deploy', 'deploy.json') as operation:
            identifier = operation['id']
            with self.assertRaises(Busy):
                with Ownership(self.store).operation('system', 'transaction.json'): pass
            self.assertEqual(Ownership(self.store).status()['id'], identifier)
        # A released OS lock (or crashed process) is still a durable reservation.
        with self.assertRaises(Busy):
            with Ownership(self.store).operation('system', 'transaction.json'): pass
        with self.owner.operation('deploy', 'deploy.json', resume=identifier) as operation:
            self.assertEqual(operation['id'], identifier)
            self.owner.stage(operation, 'journal-terminal', terminal=True)
        with self.owner.operation('system', 'transaction.json') as operation:
            self.assertNotEqual(operation['id'], identifier)

    def test_process_death_retains_reservation_without_success(self):
        import subprocess
        code = """import os,sys
sys.path.insert(0,sys.argv[1])
from installation import Ownership
from updater.store import Store
owner=Ownership(Store(sys.argv[2],uid=os.getuid()))
with owner.operation('deploy','deploy.json'):
    os._exit(7)
"""
        result = subprocess.run([sys.executable,'-c',code,str(ROOT),self.store.root])
        self.assertEqual(result.returncode,7)
        self.assertFalse(self.owner.status()['terminal'])
        with self.assertRaises(Busy):
            with self.owner.operation('system','transaction.json'): pass

    def test_resume_requires_exact_owner_journal_and_identifier(self):
        with self.owner.operation('deploy', 'deploy.json') as operation:
            identifier = operation['id']
        for owner, journal, ident in [('system','deploy.json',identifier), ('deploy','other.json',identifier), ('deploy','deploy.json','0'*32)]:
            with self.subTest(owner=owner, journal=journal), self.assertRaises(Busy):
                with self.owner.operation(owner, journal, resume=ident): pass

    def test_unknown_record_is_never_replaced(self):
        self.store.write('operation', {'protocol': 99})
        with self.assertRaises(ValueError):
            with self.owner.operation('deploy', 'deploy.json'): pass
        self.assertEqual(self.store.read('operation'), {'protocol': 99})

    def test_component_guard_keeps_pending_and_requires_routing_receipt(self):
        journals = {}
        read = lambda path: journals.get(path)
        path = JOURNALS['root-update'][0]
        with device_operation('root-update', ownership=self.owner, read=read):
            journals[path] = {'phase':'installing'}
        self.assertFalse(self.owner.status()['terminal'])
        with self.assertRaises(Busy):
            with device_operation('system-update', ownership=self.owner, read=read): pass
        with device_operation('root-update', recovery=True, ownership=self.owner, read=read):
            journals[path] = {'phase':'complete'}
        self.assertFalse(self.owner.status()['terminal'])
        with device_operation('root-update', recovery=True, ownership=self.owner, read=read):
            journals[path]['homeResumePhase'] = 'complete'
        self.assertTrue(self.owner.status()['terminal'])

    def interrupted_second_update(self, component):
        spec = importlib.util.spec_from_file_location('second_update_guard', ROOT/'runtime/update_guard.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        root = Path(self.tmp.name).resolve()/'clean-your-tv-root'
        root.mkdir(mode=0o700)
        owner = Ownership(Store(root.parent/'clean-your-tv-installation', uid=os.getuid()))
        path = JOURNALS[component][0]
        journals = {path: {'phase': 'complete', 'homeResumePhase': 'complete'}}
        read = lambda path: journals.get(path)
        with device_operation(component, recovery=True, ownership=owner, read=read) as first:
            prior = first['id']
        self.assertTrue(owner.status()['terminal'])
        with guard.control(root, os.getuid()):
            pass
        with self.assertRaisesRegex(RuntimeError, 'interrupted preparation'):
            with device_operation(component, recovery=True, ownership=owner, read=read) as second:
                # The next update has persisted its initial transaction, before
                # a routing reservation or context-exit journal mirroring.
                journals[path] = {'phase': 'preparing'}
                raise RuntimeError('interrupted preparation')
        self.assertNotEqual(owner.status()['id'], prior)
        self.assertFalse(owner.status()['terminal'])
        self.assertFalse((root/'update-block.json').exists())
        with self.assertRaises(guard.ProductPending):
            with guard.control(root, os.getuid()):
                self.fail('pending update admitted public activation')
        # A genuine recovery keeps that new pending lease, rather than creating
        # a third update reservation after process/lock release.
        pending = owner.status()['id']
        with device_operation(component, recovery=True, ownership=owner, read=read) as resumed:
            self.assertEqual(resumed['id'], pending)
            journals[path] = {'phase': 'complete', 'homeResumePhase': 'complete'}
        self.assertTrue(owner.status()['terminal'])

    def test_second_root_update_interruption_blocks_public_activation(self):
        self.interrupted_second_update('root-update')

    def test_second_system_update_interruption_blocks_public_activation(self):
        self.interrupted_second_update('system-update')

    def test_bootstrap_readonly_refusals_do_not_publish_ownership(self):
        for component in ('root-bootstrap', 'system-bootstrap'):
            with self.subTest(component=component):
                owner = Ownership(Store(Path(self.tmp.name).resolve()/component, uid=os.getuid()))
                def refused():
                    raise ValueError('readonly eligibility refusal')
                for attempt in range(2):
                    with self.assertRaisesRegex(ValueError, 'eligibility'):
                        with device_operation(component, ownership=owner, read=lambda path: None, check=refused):
                            self.fail('refused setup mutated')
                    self.assertIsNone(owner.status())
                with device_operation('deploy', ownership=owner, read=lambda path: None):
                    pass

    def test_preexisting_foreign_journal_blocks_even_without_global_record(self):
        read = lambda path: {'phase':'installing'} if path == JOURNALS['root-update'][0] else None
        with self.assertRaises(Busy):
            with device_operation('deploy', ownership=self.owner, read=read): pass
        self.assertIsNone(self.owner.status())

    def test_absent_components_cannot_claim_complete_receipts(self):
        observe=lambda name: dict(present=False,packages_match=True,receipts_match=True,
                                  pending=False,retained=False,complete=True,migration_supported=False)
        self.assertEqual(classify(snapshot(True,observe))['state'],'recovery_required')

    def test_snapshot_requires_all_component_receipts_and_retains_partial(self):
        def observe(name):
            return dict(present=True, packages_match=True, receipts_match=name != 'system-updater',
                        pending=False, retained=False, complete=True, migration_supported=False)
        result = snapshot(True, observe)
        self.assertEqual(classify(result)['state'], 'conflict')
        self.assertEqual(classify(snapshot(True, lambda name: {'protocol': 9}))['state'], 'recovery_required')


class RealStoreAbsenceTests(unittest.TestCase):
    def setUp(self):
        import installation
        from unittest.mock import patch
        self.installation=installation
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        uid=os.getuid()
        class FixtureStore(Store):
            # Only inject the fixture UID; traversal, reads and errors are real.
            def _walk(self,path):
                self.uid=uid
                return super()._walk(path)
        self.journals={name:(self.root/name/path.name,field,finished)
                       for name,(path,field,finished) in JOURNALS.items()}
        for attribute,value in [('Store',FixtureStore),('JOURNALS',self.journals),('STATE',self.root/'global')]:
            patcher=patch.object(installation,attribute,value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_real_reader_missing_component_directory_is_absent(self):
        self.assertIsNone(self.installation.read_journal(self.root/'absent'/'bootstrap.json'))
        self.assertFalse((self.root/'absent').exists())

    def test_clean_and_partial_entrypoints_admit_missing_peers(self):
        for owner in ('deploy','root-bootstrap','system-bootstrap'):
            with self.subTest(owner=owner):
                store=Store(self.root/('global-'+owner),uid=os.getuid())
                with device_operation(owner,ownership=Ownership(store)):
                    pass
        path,field,finished=self.journals['deploy']
        Store(path.parent,uid=os.getuid()).write(path.name,{'app':'com.cleanyourtv.root.preview',
                                                          field:'installed-recovery-only'})
        with device_operation('root-update',ownership=Ownership(Store(self.root/'partial-global',uid=os.getuid()))):
            pass

    def test_absent_global_state_does_not_manufacture_retained_evidence(self):
        result=self.installation.device_snapshot()
        self.assertEqual(classify(result)['state'],'fresh')
        self.assertFalse((self.root/'global').exists())

    def test_unsafe_component_paths_and_invalid_receipts_still_block(self):
        symlink=self.root/'symlink';symlink.symlink_to(self.root/'missing',target_is_directory=True)
        writable=self.root/'writable';writable.mkdir();writable.chmod(0o777)
        invalid=self.root/'invalid';invalid.mkdir();(invalid/'bootstrap.json').write_text('{broken')
        for parent in (symlink,writable,invalid):
            with self.subTest(parent=parent.name),self.assertRaises(ValueError):
                self.installation.read_journal(parent/'bootstrap.json')
        with self.assertRaises(ValueError):
            self.installation.read_journal(writable/'missing'/'bootstrap.json')
        foreign=Store.__new__(Store)
        foreign.root,foreign.uid=str(self.root/'foreign'),os.getuid()+1
        (self.root/'foreign').mkdir()
        with self.assertRaises(ValueError):
            self.installation._optional_record(foreign,'bootstrap')
        from unittest.mock import patch
        (invalid/'operation.json').write_text('{"schema":99}')
        for parent in (symlink,writable,invalid):
            with self.subTest(global_parent=parent.name),patch.object(self.installation,'STATE',parent):
                self.assertEqual(classify(self.installation.device_snapshot())['state'],'recovery_required')

    def test_unrelated_value_error_with_absence_cause_is_not_swallowed(self):
        from unittest.mock import patch
        def read(store,name):
            raise ValueError('other failure') from FileNotFoundError('not traversal')
        with patch.object(self.installation.Store,'read',read),self.assertRaisesRegex(ValueError,'other failure'):
            self.installation.read_journal(self.root/'missing'/'bootstrap.json')


class EntryPointTests(unittest.TestCase):
    def test_bootstrap_cli_refusal_is_checked_before_real_reservation(self):
        import installation
        from unittest.mock import patch
        from updater import bootstrap
        for component,filename in (('root-bootstrap','setup_updater.py'),('system-bootstrap','../system-updater/setup.py')):
            spec=importlib.util.spec_from_file_location('bootstrap_entry_'+component,ROOT/filename)
            entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
            with self.subTest(component=component),tempfile.TemporaryDirectory() as tmp:
                owner=Ownership(Store(Path(tmp).resolve()/'global',uid=os.getuid()))
                original=device_operation
                def guarded(name,**kwargs):
                    kwargs.setdefault('ownership',owner)
                    kwargs.setdefault('read',lambda path:None)
                    return original(name,**kwargs)
                target=bootstrap if component=='root-bootstrap' else entry
                args=['setup','--device','--apply','--bundle',tmp,'--baseline',tmp]
                with patch.object(installation,'Ownership',return_value=owner),patch.object(installation,'device_operation',side_effect=guarded),patch.object(target,'preflight',side_effect=FileExistsError('retained setup')),patch.object(os,'geteuid',return_value=os.getuid()),patch.object(Path,'is_file',return_value=True),patch.object(entry.subprocess,'run'):
                    # Model root identity only for the entry-point privilege gate.
                    with patch.object(os,'geteuid',return_value=0):
                        for attempt in range(2):
                            with patch.object(sys,'argv',args),self.assertRaisesRegex(FileExistsError,'retained setup'):entry.main()
                            self.assertIsNone(owner.status())
                        with patch.object(installation,'Ownership',return_value=owner),patch.object(sys,'argv',args+['--resume']),self.assertRaisesRegex(ValueError,'No matching pending'):
                            entry.main()
                        self.assertIsNone(owner.status())
                    with owner.operation(component,'bootstrap.json') as lease:owner.stage(lease,'complete',terminal=True)
                    completed=owner.status()
                    with patch.object(os,'geteuid',return_value=0),patch.object(sys,'argv',args),self.assertRaises(FileExistsError):entry.main()
                    self.assertEqual(owner.status(),completed)
                with owner.operation('deploy','deploy.json'):
                    pass

    def test_idle_reconcile_does_not_reserve_an_installation(self):
        from updater import cli
        import installation
        import io
        from unittest.mock import patch, Mock
        store=Mock()
        store.read.return_value=None
        with patch.object(sys,'argv',['run-updater.py','reconcile']), \
             patch.object(sys,'stdin',type('Input',(),{'buffer':io.BytesIO(b'{}')})()), \
             patch.object(cli.os,'geteuid',return_value=0), patch.object(cli,'Store',return_value=store), \
             patch.object(cli,'Device'), patch.object(cli,'spawn_worker'), \
             patch.object(installation,'device_operation') as guard:
            self.assertIsNone(cli.main())
        guard.assert_not_called()

    def test_updater_reserves_before_mutation_and_wakes_after_unlock(self):
        from updater import cli
        import installation
        import contextlib
        import io
        from unittest.mock import patch
        events=[]
        @contextlib.contextmanager
        def guard(owner,recovery=False):
            events.append(('enter',owner,recovery))
            yield
            events.append('exit')
        def handle(method,payload,store,device,wake):
            events.append('handle')
            wake()
            return {'phase':'preparing'}
        with patch.object(sys,'argv',['run-updater.py','install']), \
             patch.object(sys,'stdin',type('Input',(),{'buffer':io.BytesIO(b'{"version":"1.0.0","profile":{}}')})()), \
             patch.object(cli.os,'geteuid',return_value=0), patch.object(cli,'Store'), patch.object(cli,'Device'), \
             patch.object(installation,'device_operation',guard), patch.object(cli,'handle',handle), \
             patch.object(cli,'spawn_worker',side_effect=lambda:events.append('wake')):
            self.assertEqual(cli.main(),{'phase':'preparing'})
        self.assertEqual(events,[('enter','root-update',True),'handle','exit','wake'])

    def test_device_inspect_exposes_classifier_without_mutation(self):
        import deploy
        import installation
        import contextlib
        import io
        from unittest.mock import patch
        values = dict(supported=True, packages_match=False, receipts_match=False,
                      pending=False, retained=False, complete=False, migration_supported=False)
        output = io.StringIO()
        with patch.object(sys, 'argv', ['deploy.py','inspect']), patch.object(deploy,'require_device'), \
             patch.object(installation,'device_snapshot',return_value=values), contextlib.redirect_stdout(output):
            deploy.main()
        import json
        self.assertEqual(json.loads(output.getvalue())['installation'], classify(values))


if __name__ == '__main__': unittest.main()
