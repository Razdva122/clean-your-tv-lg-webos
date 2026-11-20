"""Migration preserves installation data across retries and byte-exact rollback."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
provision_spec = importlib.util.spec_from_file_location('migration_provision', ROOT/'provision.py')
provision = importlib.util.module_from_spec(provision_spec)
provision_spec.loader.exec_module(provision)
migration_spec = importlib.util.spec_from_file_location('device_beta_startup_migration', ROOT/'beta_startup_migration.py')
migration = importlib.util.module_from_spec(migration_spec)
# The host test suite also imports runtime/provision.py under the bare name.
with patch.dict(sys.modules, {'provision': provision}):
    migration_spec.loader.exec_module(migration)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = {'runtime/cli.py': b'old runtime', 'recovery-provision.json': b'old proof',
                         'recovery-provision.pending.json': b'old pending'}
        for name, raw in self.original.items():
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(0o600)
        (self.root/'startup-policy.json').write_text('{"version":2,"sources":{"tv":false,"youtube":true}}')
        self.preferences = (self.root/'startup-policy.json').read_bytes()
        self.targets = {'runtime/cli.py': (b'new runtime', 0o600), 'runtime/new.py': (b'new module', 0o600),
                        'recovery-provision.pending.json': (b'new pending', 0o600),
                        'recovery-provision.json': (b'new proof', 0o600)}
        self.tx = migration.Transaction(self.root, self.targets)
        def read(path):
            path = Path(path)
            if path.is_symlink():
                raise ValueError('Unsafe file')
            return path.read_bytes()
        context = patch.object(migration.p, 'secure', side_effect=read)
        context.start()
        self.addCleanup(context.stop)

    def verify(self):
        for name, (raw, mode) in self.targets.items():
            self.assertEqual((self.root/name).read_bytes(), raw)
            self.assertEqual((self.root/name).stat().st_mode & 0o777, mode)
        self.assertEqual((self.root/'startup-policy.json').read_bytes(), self.preferences)

    def test_publication_is_last_and_completed_retry_only_verifies(self):
        observed = []
        self.tx.apply(self.verify, checkpoint=observed.append)
        self.assertEqual(observed[-1], 'recovery-provision.json')
        with patch.object(migration.p, 'retained_repair_write', side_effect=AssertionError('completed retry wrote')):
            self.tx.apply(self.verify)
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_every_interruption_can_resume_and_rollback_without_changing_settings(self):
        steps = ['readiness-revoked', *[n for n in self.targets if n != 'recovery-provision.json'], 'recovery-provision.json']
        for step in steps:
            def interrupt(current):
                if current == step:
                    raise InterruptedError('modeled process loss')
            with self.assertRaises(InterruptedError):
                self.tx.apply(self.verify, checkpoint=interrupt)
            self.tx.apply(self.verify)
            self.tx.rollback()
            for name, raw in self.original.items():
                self.assertEqual((self.root/name).read_bytes(), raw)
            self.assertFalse((self.root/'runtime/new.py').exists())
            self.assertEqual((self.root/'startup-policy.json').read_bytes(), self.preferences)
            # Fresh fixture for the next independent interruption case.
            import shutil
            shutil.rmtree(self.root/migration.BACKUP)
            (self.root/migration.JOURNAL).unlink()

    def test_explicit_reapply_after_rollback_reuses_the_original_inverse(self):
        self.tx.apply(self.verify)
        original = (self.root/migration.BACKUP/'runtime/cli.py').read_bytes()
        self.tx.rollback()
        self.tx.apply(self.verify)
        self.assertEqual((self.root/migration.BACKUP/'runtime/cli.py').read_bytes(), original)

    def test_live_and_backup_drift_are_rejected_before_publication(self):
        self.tx.prepare()
        for path in (self.root/'runtime/cli.py', self.root/migration.BACKUP/'runtime/cli.py'):
            original = path.read_bytes()
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.tx.apply(self.verify)
            path.write_bytes(original)
        self.assertEqual((self.root/'recovery-provision.json').read_bytes(), b'old proof')

    def test_direct_rollback_accepts_only_authenticated_interrupted_write_prefixes(self):
        value = self.tx.prepare()
        target = self.root/'runtime/cli.py.root-preview-tmp'
        target.write_bytes(b'new runt')
        journal = self.root/(migration.JOURNAL+'.root-preview-tmp')
        journal.write_bytes(migration.p.encoded(dict(value, phase='published'))[:40])
        self.tx.rollback()
        self.assertEqual((self.root/'runtime/cli.py').read_bytes(), b'old runtime')
        self.assertFalse(target.exists())
        self.assertFalse(journal.exists())
        target.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'Interrupted migration member changed'):
            self.tx.rollback()

    def test_backup_crash_before_journal_is_recoverable_and_symlink_is_rejected(self):
        with patch.object(self.tx, 'save', side_effect=InterruptedError()):
            with self.assertRaises(InterruptedError):
                self.tx.prepare()
        self.tx.apply(self.verify)
        self.tx.rollback()
        link = self.root/'runtime/new.py'
        link.symlink_to(self.root/'startup-policy.json')
        with self.assertRaises(ValueError):
            self.tx.apply(self.verify)

class MigrationAdmissionTests(unittest.TestCase):
    def test_unstarted_removal_requires_exact_original_component_state(self):
        from copy import deepcopy
        from unittest.mock import Mock
        lease = {'id':'a'*32,'owner':'clean-removal','journal':'product-'+'b'*32+'.json','terminal':False}
        previous = {'id':'c'*32,'owner':'deploy','journal':'deploy.json','terminal':True}
        from installation import JOURNALS
        components = {name:None for name in JOURNALS}
        record = {'schema':1,'protocol':'clean-removal-v1','operation':'b'*32,'removal':'d'*32,
                  'lease':lease['id'],'stage':'requested','done':[],'packages':{},
                  'original':{'lease':previous,'components':components}}
        owner = Mock()
        owner.store.read.return_value = record
        with patch('installation.read_journal', return_value=None):
            self.assertEqual(migration.unstarted_removal(owner,lease,('b'*32,'d'*32)),record)
            for field,value in (('done',['original-writers-fenced']),('packages',{'app':{}}),
                                ('stage','package-removal'),('archives',[])):
                damaged=deepcopy(record);damaged[field]=value;owner.store.read.return_value=damaged
                with self.subTest(field=field),self.assertRaises(ValueError):
                    migration.unstarted_removal(owner,lease,('b'*32,'d'*32))
        owner.store.write.assert_not_called()

    def test_home_selection_has_one_submission_even_after_uncertain_reply(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(migration.p,'STATE',Path(tmp)), \
                patch.object(migration.p,'secure',side_effect=Path.read_bytes):
            absent={'returnValue':True,'settings':{'defaultApps':{'other':'kept'}}}
            stock={'returnValue':True,'settings':{'defaultApps':{'other':'kept','home':'com.webos.app.home'}}}
            with patch.object(migration.p,'rpc',side_effect=[absent,migration.p.RecoveryRPCError('timeout'),stock]):
                migration.ensure_stock_destination()
            with patch.object(migration.p,'rpc',return_value=stock) as rpc:
                migration.ensure_stock_destination()
                rpc.assert_called_once_with('home-read')
            with patch.object(migration.p,'rpc',return_value=absent) as rpc:
                with self.assertRaisesRegex(ValueError,'unverified'):
                    migration.ensure_stock_destination()
                rpc.assert_called_once_with('home-read')

    def test_wrapper_resumes_between_release_and_bundle_writes_from_original_backup(self):
        from contextlib import nullcontext
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            release={'runtime_variant':'node012-beta','home_backend':'c1-native-gate',
                     'routing':'compositor-keyfilter-v1','native_sha256':'a'*64}
            proof={'files':{},'version':1,'mode':'recovery-only'}
            for name,value in (('release.json',release),('bundle.json',{'old':True}),
                               ('home-backend.json',{}),('deploy.json',{'stage':'installed-recovery-only'}),
                               ('recovery-provision.json',proof)):
                (root/name).write_bytes(migration.p.encoded(value));(root/name).chmod(0o600)
            (root/'provision.lock').touch(mode=0o600)
            from types import SimpleNamespace
            owner=SimpleNamespace(_lock=lambda **kwargs:nullcontext(),status=Mock(),store=Mock())
            current=[{'schema':1,'id':'a'*32,'owner':'deploy','journal':'deploy.json',
                      'stage':'installed-recovery-only','terminal':True}]
            owner.status.side_effect=lambda:dict(current[0])
            owner.store.write.side_effect=lambda name,value:current.__setitem__(0,dict(value)) if name=='operation' else None
            def targets(bundle,original,metadata):
                # Resumption must see exact old source metadata despite live drift.
                self.assertEqual(json.loads((metadata/'bundle.json').read_bytes()),{'old':True})
                self.assertEqual(json.loads((metadata/'release.json').read_bytes()),release)
                return {'release.json':(migration.p.encoded(dict(release,native_sha256='b'*64)),0o600),
                        'bundle.json':(b'{"new":true}',0o600),
                        'recovery-provision.json':(b'{"ready":true}',0o600)}
            original_write=migration.p.retained_repair_write
            failed=[False]
            def interrupted(path,*args,**kwargs):
                result=original_write(path,*args,**kwargs)
                if path==root/'release.json' and not failed[0]:
                    failed[0]=True
                    raise InterruptedError('after release write')
                return result
            with patch.object(migration.p,'STATE',root),patch.object(migration.p,'secure',side_effect=Path.read_bytes), \
                    patch('deploy.require_device'),patch('deploy.require_node'),patch('deploy.verify_payload'), \
                    patch('package_identity.bootstrap_inventory') as inventory,patch('installation.Ownership',return_value=owner), \
                    patch('runtime.c1_keyfilter.operation',return_value=nullcontext()), \
                    patch('runtime.c1_keyfilter.read_intent',return_value={'enabled':False,'phase':'disabled'}), \
                    patch.object(migration.p,'manifest',return_value=proof),patch.object(migration.p,'prepare_stock_home'), \
                    patch.object(migration,'candidate_targets',side_effect=targets), \
                    patch.object(migration,'require_quiescent') as quiet,patch.object(migration,'ensure_stock_destination'), \
                    patch.object(migration,'verify_status'):
                with patch.object(migration.p,'retained_repair_write',side_effect=interrupted):
                    with self.assertRaises(InterruptedError):migration.migrate(root)
                self.assertEqual(migration.migrate(root)['phase'],'complete')
                self.assertEqual(inventory.call_count,1)
                self.assertEqual(quiet.call_count,2)
                self.assertTrue(current[0]['terminal'])
                self.assertNotEqual(current[0]['id'],'a'*32)


if __name__ == '__main__':
    unittest.main()
