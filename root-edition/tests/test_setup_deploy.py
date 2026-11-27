import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load(name):
    path = ROOT / (name + '.py')
    if not path.exists():
        raise AssertionError('Missing deployment component: ' + name)
    spec = importlib.util.spec_from_file_location('root_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupTests(unittest.TestCase):
    def test_host_rejects_shell_fragments_and_option_aliases(self):
        setup = load('setup')
        for alias in ('-ProxyCommand=bad', 'tv;id', 'tv user', 'root@tv', ''):
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                setup.ssh_options(alias)
        args = setup.ssh_options('living-room')
        self.assertIn('StrictHostKeyChecking=yes', args)
        self.assertIn('BatchMode=yes', args)
        self.assertEqual(args[-1], 'living-room')

    def test_install_uploads_only_verified_bundle_files(self):
        setup = load('setup')
        import deploy
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / 'bundle.json').write_text('{}')
            (source / 'safe').write_text('safe')
            (source / 'private-key').write_text('secret')
            uploads = []
            def run(args, **kwargs):
                if args[0] == 'scp':
                    sources = args[args.index('-r') + 1:-1]
                    self.assertTrue(sources)
                    for source_name in sources:
                        self.assertFalse(source_name.endswith('/.'))
                        uploads.append(Path(source_name).name)
            with patch.object(deploy, 'verify_bundle', return_value={'files': {'safe': 'unused'}}):
                setup.execute('install', 'living-room', source, run=run, component_only=True)
            self.assertEqual(set(uploads), {'safe', 'bundle.json'})

    def test_non_install_has_fixed_remote_command_and_no_upload(self):
        setup = load('setup')
        calls = []
        setup.execute('status', 'living-room', run=lambda args, **kwargs: calls.append(args))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][-1], '/usr/bin/python3 /var/lib/clean-your-tv-root/deploy.py status')
        self.assertEqual(calls[0][0], 'ssh')


class DeployTests(unittest.TestCase):
    def setUp(self):
        provision=load('provision')
        modules=patch.dict(sys.modules,{'provision':provision})
        modules.start();self.addCleanup(modules.stop)
        def bus(method):
            if method=='home-read':return {'returnValue':True,'settings':{'defaultApps':{'home':'com.webos.app.home'}}}
            if method=='home-profiles':return {'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home','support':True}}}
            self.fail('Unexpected bus mutation: '+method)
        context=patch.object(provision,'rpc',side_effect=bus)
        context.start();self.addCleanup(context.stop)

    def test_device_node_probe_rejects_legacy_runtime(self):
        import subprocess
        deploy = load('deploy')
        real_run = subprocess.run
        for version, supported in [('0.12.14', False), ('8.12.0', True), ('10.24.1', True)]:
            def execute(args, **kwargs):
                self.assertEqual(args[:2], ['/usr/bin/node', '-e'])
                return real_run(['node', '-e',
                    "Object.defineProperty(process.versions,'node',{value:"+json.dumps(version)+"});"+args[2]], **kwargs)
            with self.subTest(version=version), patch.object(deploy.subprocess, 'run', side_effect=execute):
                if supported: deploy.require_node()
                else:
                    with self.assertRaisesRegex(RuntimeError, 'Node.js 8'): deploy.require_node()

    def test_old_python_is_rejected_before_install_mutations(self):
        deploy = load('deploy')
        with patch.object(deploy.sys, 'version_info', (3, 8, 10)), \
             patch.object(deploy, 'verify_bundle', side_effect=AssertionError('must reject runtime before bundle/mutations')) as verify:
            with self.assertRaisesRegex(RuntimeError, 'Python 3.9'):
                deploy.install(Path('/unused'))
            verify.assert_not_called()

    def test_recovery_commands_allow_the_bounded_recovery_deadline(self):
        deploy = load('deploy')
        from types import SimpleNamespace
        calls = []
        def run(args, **kwargs):
            calls.append(kwargs['timeout'])
            return SimpleNamespace(stdout=b'{"returnValue":true}')
        with patch.object(deploy.subprocess, 'run', side_effect=run):
            for mode in ('restore', 'rollback', 'status'):
                deploy.command(['/usr/bin/python3', '/fixed/driver.py', mode])
        self.assertEqual(calls, [700, 700, 100])

    def test_wrong_device_fails_before_mutation(self):
        deploy = load('deploy')
        with patch.object(deploy.os, 'geteuid', return_value=1000):
            with self.assertRaises(PermissionError):
                deploy.require_device()

    def test_existing_install_is_never_overwritten(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'state'
            state.mkdir()
            (state / 'keep').write_text('owned')
            with patch.object(deploy, 'STATE', state):
                with self.assertRaises(FileExistsError):
                    deploy.install(Path(tmp))
            self.assertEqual((state / 'keep').read_text(), 'owned')

    def test_payload_hash_drift_is_rejected(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = root / 'usr/palm/applications/com.cleanyourtv.root.preview/app.js'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'changed')
            with patch.object(deploy, 'INSTALLED', root):
                with self.assertRaises(ValueError):
                    deploy.verify_payload({'files': {'usr/palm/applications/com.cleanyourtv.root.preview/app.js': '0' * 64}})

    def test_unknown_install_keeps_journal_and_never_provisions(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            builder = load('build')
            bundle = root / 'bundle'
            builder.build(bundle)
            events = []
            from package_data import read_verified as package_reader
            def observe(app, path, **kwargs):
                kwargs['on_ready']()
                raise deploy.OutcomeUnknown('No terminal evidence')
            with patch.object(deploy, 'STATE', root / 'state'), patch.object(deploy, 'INSTALLED', root / 'installed'):
                with self.assertRaises(deploy.OutcomeUnknown):
                    deploy.install(bundle, run=lambda args: events.append(args), observe=observe)
            self.assertTrue((root / 'state/deploy.py').is_file())
            self.assertTrue((root / 'state/runtime/helper_bridge.py').is_file())
            self.assertEqual(events, [])
            self.assertEqual(json.loads((root / 'state/deploy.json').read_text())['stage'], 'install-submitting')

    def test_explicit_migration_preserves_source_and_records_destination_hashes(self):
        deploy = load('deploy')
        self.assertTrue(hasattr(deploy, 'migrate_packaged_home'), 'Explicit packaged migration is missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state = root / 'state'; state.mkdir()
            installed = root / 'installed'
            source = installed / 'usr/palm/applications/com.gathin.tvhome'
            source.mkdir(parents=True)
            (source / 'apps.js').write_text('window.TV_APPS = {apps: [], inputs: []};')
            (source / 'config.js').write_text('window.CONFIG = {columns: 7};')
            original = {p.name:p.read_bytes() for p in source.iterdir()}
            target = installed / ('usr/palm/applications/' + deploy.APP)
            target.mkdir()
            (target / 'config.js').write_text('window.CONFIG = {};')
            with patch.object(deploy, 'STATE', state), patch.object(deploy, 'INSTALLED', installed):
                deploy.migrate_packaged_home()
            self.assertEqual({p.name:p.read_bytes() for p in source.iterdir()}, original)
            self.assertIn(b'columns: 7', (target / 'config.js').read_bytes())
            record = json.loads((state / 'personalization.json').read_text())
            import hashlib
            self.assertEqual(record['files']['config.js'], hashlib.sha256((target / 'config.js').read_bytes()).hexdigest())

    def test_missing_migration_source_fails_before_state_or_package_install(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bundle = root / 'bundle'
            load('build').build(bundle)
            with patch.object(deploy, 'STATE', root/'state'), patch.object(deploy, 'INSTALLED', root/'installed'), patch.object(deploy, 'observed_install') as observe:
                with self.assertRaisesRegex(ValueError, 'migration source'):
                    deploy.install(bundle, migrate=True, observe=observe)
                observe.assert_not_called()
            self.assertFalse((root/'state').exists())

    def test_homebrew_settings_appear_after_submission_no_package_or_product_state_created(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bundle = root / 'bundle'
            load('build').build(bundle)
            installed = root / 'installed'
            profile = installed/'usr/palm/services/com.cleanyourtv.updater.service/state/profile.json'
            profile.parent.mkdir(parents=True)
            data = dict(schema=1, inventory=dict(apps=[], inputs=[]), config=dict(columns=4, dockApps=[], hiddenApps=[]))
            profile.write_text(json.dumps(data))
            with patch.object(deploy,'STATE',root/'state'), patch.object(deploy,'INSTALLED',installed), \
                 patch.object(deploy,'observed_install') as observe:
                with self.assertRaisesRegex(ValueError, 'Reviewed Home settings changed'):
                    deploy.install(bundle, migrate=False, homebrew_settings='absent', observe=observe)
                observe.assert_not_called()
            self.assertFalse((root/'state').exists())

    def test_preprovision_uninstall_skips_rollback_and_preserves_proof_on_resume(self):
        deploy = load('deploy')
        import observed_install
        stages = ('payload-verified', 'personalization-starting', 'personalization-complete', 'provision-apply-starting')
        for stage in stages:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                state = root/'state';state.mkdir()
                calls = []
                def run(args):
                    calls.append(args[-1])
                    return {'returnValue':True,'result':'absent'}
                real_write=deploy.write_stage
                def interrupted(stage,**extra):
                    if stage=='remove-submitting':raise OSError('interrupted before removal submission')
                    real_write(stage,**extra)
                with patch.object(deploy, 'STATE', state), patch.object(deploy, 'INSTALLED', root/'installed'), patch.object(observed_install, 'remove', return_value={'completed':True}) as remove:
                    deploy.write_stage(stage)
                    with patch.object(deploy,'write_stage',side_effect=interrupted):
                        with self.assertRaises(OSError):deploy.uninstall(run=run)
                    remove.assert_not_called()
                    calls.clear()
                    def resume(args):
                        calls.append(args[-1]);return {'returnValue':True,'result':'absent'}
                    deploy.uninstall(run=resume)
                    self.assertEqual(calls,['restore'])
                    self.assertIs(json.loads((state/'deploy.json').read_text())['provisioning_not_started'],True)

    def test_preprovision_cleanup_refuses_conflicting_readiness_or_snapshot_links(self):
        deploy = load('deploy')
        import observed_install
        for name in ('recovery-provision.pending.json','recovery-provision.json','ls2-provision-snapshot.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                state=Path(tmp).resolve()
                (state/name).symlink_to(state/'missing')
                with patch.object(deploy,'STATE',state),patch.object(observed_install,'remove') as remove:
                    deploy.write_stage('payload-verified')
                    with self.assertRaises(ValueError):deploy.uninstall(run=lambda args: {'returnValue':True,'result':'absent'})
                    remove.assert_not_called()

    def test_preprovision_cleanup_refuses_an_active_provision_lock(self):
        import fcntl, observed_install
        deploy=load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp).resolve()
            with patch.object(deploy,'STATE',state):
                deploy.write_stage('provision-apply-starting')
                with (state/'provision.lock').open('w') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with patch.object(deploy,'restore') as restore,patch.object(observed_install,'remove',return_value={'completed':True}):
                        with self.assertRaises(BlockingIOError):deploy.uninstall(run=lambda args: None)
                        restore.assert_not_called()

    def test_preprovision_cleanup_rechecks_evidence_after_restore(self):
        deploy=load('deploy')
        import observed_install
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp).resolve()
            def run(args):
                (state/'ls2-provision-snapshot.json').write_text('{}')
                return {'returnValue':True,'result':'absent'}
            with patch.object(deploy,'STATE',state),patch.object(observed_install,'remove',return_value={'completed':True}) as remove:
                deploy.write_stage('provision-apply-starting')
                with self.assertRaises(ValueError):deploy.uninstall(run=run)
                remove.assert_not_called()

    def test_install_success_requires_payload_then_orders_provision(self):
        deploy = load('deploy')
        builder = load('build')
        from test_build_root import ar_members
        import io, tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bundle = root / 'bundle'
            package = builder.build(bundle)
            installed = root / 'installed'
            calls = []
            from package_data import read_verified as package_reader
            def observe(app, path, **kwargs):
                kwargs['on_ready']()
                with tarfile.open(fileobj=io.BytesIO(ar_members(Path(path).read_bytes())['data.tar.gz'])) as archive:
                    for member in archive:
                        if member.isdir():continue
                        target = installed / member.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(archive.extractfile(member).read())
                return {'completed':True,'event':{'id':app,'statusValue':30,'details':{
                    'packageId': app, 'client':'com.webos.lunasend-123',
                    'ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-test/package.ipk',
                }}}
            with patch.object(deploy, 'STATE', root / 'state'), patch.object(deploy, 'INSTALLED', installed), patch('package_data.read_verified',side_effect=lambda path,**kw: package_reader(path,**{**kw,'uid':__import__('os').getuid()})):
                result = deploy.install(bundle, run=lambda args: calls.append(args[-1]), observe=observe)
            self.assertTrue(result['returnValue'])
            self.assertFalse(result['home_changed'])
            self.assertEqual(calls, ['apply', 'refresh', 'finalize'])
            self.assertEqual(json.loads((root / 'state/deploy.json').read_text())['stage'], 'installed-recovery-only')

    def test_remove_terminal_without_absence_keeps_state(self):
        deploy = load('deploy')
        import observed_install
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state = root / 'state'; state.mkdir()
            installed = root / 'installed'
            app = installed / ('usr/palm/applications/' + deploy.APP)
            app.mkdir(parents=True)
            with patch.object(deploy, 'STATE', state), patch.object(deploy, 'INSTALLED', installed), patch.object(observed_install, 'remove', return_value={'completed':True}):
                with self.assertRaises(deploy.OutcomeUnknown):
                    deploy.uninstall(run=lambda args: {'returnValue':True,'result':'restored'})
            self.assertTrue(state.exists())
            self.assertEqual(json.loads((state / 'deploy.json').read_text())['stage'], 'remove-observed')

    def test_empty_package_remnant_requires_matching_terminal(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            installed = Path(tmp).resolve()
            package = installed / ('usr/palm/packages/' + deploy.APP)
            package.mkdir(parents=True)
            evidence = {'completed':True,'event':{'id':deploy.APP,'statusValue':31,
                'details':{'packageId':deploy.APP,'state':'removed'}}}
            with patch.object(deploy, 'INSTALLED', installed):
                with self.assertRaises(deploy.OutcomeUnknown):
                    deploy.verify_removed({'completed':True})
                self.assertTrue(package.exists())
                (package / 'unexpected').write_text('retain')
                with self.assertRaises(deploy.OutcomeUnknown):
                    deploy.verify_removed(evidence)
                self.assertTrue((package / 'unexpected').exists())
                (package / 'unexpected').unlink()
                deploy.verify_removed(evidence)
                self.assertFalse(package.exists())
                other = installed / 'other'; other.mkdir()
                package.symlink_to(other, target_is_directory=True)
                with self.assertRaises(deploy.OutcomeUnknown):
                    deploy.verify_removed(evidence)
                self.assertTrue(package.is_symlink())
                self.assertTrue(other.exists())

    def test_uncertain_removal_is_not_resubmitted(self):
        deploy = load('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp).resolve()
            (state / 'deploy.json').write_text(json.dumps({'stage':'remove-submitting'}))
            calls = []
            with patch.object(deploy, 'STATE', state):
                with self.assertRaises(deploy.OutcomeUnknown):
                    deploy.uninstall(run=lambda args: calls.append(args))
            self.assertEqual(calls, [])

    def test_restore_conflict_prevents_uninstall(self):
        deploy = load('deploy')
        calls = []
        def run(args):
            calls.append(args)
            return {'returnValue': True, 'result': 'conflict'}
        with self.assertRaises(ValueError):
            deploy.uninstall(run=run)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()

class SharedSetupEntryTests(unittest.TestCase):
    def fixture(self):
        import hashlib
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve()
        for name in ('root','updater'):
            folder=root/name;folder.mkdir();(folder/'install_driver.py').write_bytes(b'trusted driver')
            (folder/'bundle.json').write_text(json.dumps({'files':{'install_driver.py':hashlib.sha256(b'trusted driver').hexdigest()}}))
        return root/'root',root/'updater'

    def test_host_setup_install_uses_shared_request_and_candidate(self):
        setup=load('setup');root,updater=self.fixture();calls=[]
        setup.execute('install','living-room',root,updater_bundle=updater,operation='a'*32,run=lambda args,**kwargs:calls.append(args))
        command=calls[-1][-1]
        self.assertIn('/root-updater/install_driver.py install --payload ',command)
        self.assertIn('--operation '+'a'*32,command);self.assertIn('--candidate ',command)
        self.assertNotIn('deploy.py install',command)

    def test_documented_shared_status_requests_current_proof(self):
        setup=load('setup');root,updater=self.fixture();calls=[]
        setup.execute('status','living-room',root,updater_bundle=updater,operation='a'*32,run=lambda args,**kwargs:calls.append(args))
        self.assertIn('--verify-current',calls[-1][-1])
        self.assertIn('--operation '+'a'*32,calls[-1][-1])

    def test_component_install_requires_explicit_low_level_flag(self):
        setup=load('setup');root,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'component-only'):
            setup.execute('install','living-room',root,run=lambda *a,**k:self.fail('SSH before complete bundle validation'))

    def test_updater_host_apply_routes_to_product_unless_explicit_component_recovery(self):
        import sys
        updater=load('setup_updater');root,bundle=self.fixture()
        with patch('updater.bootstrap.verify_bundle',return_value={'files':{}}),patch('deploy.verify_bundle',return_value={'package':'baseline.ipk','files':{}}),patch('setup.execute_product') as product,patch.object(sys,'argv',['setup-updater','--bundle',str(bundle),'--baseline',str(root),'--ssh','living-room','--apply','--operation','a'*32]):
            updater.main()
        self.assertEqual(product.call_args.args[:4],('install','living-room',root,bundle))
        self.assertEqual(product.call_args.kwargs['operation'],'a'*32)
