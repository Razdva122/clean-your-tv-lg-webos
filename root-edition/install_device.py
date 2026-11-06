"""Bounded local webOS adapter for the shared product coordinator.

This module executes bundled code only. Retained code is hashed as data before
using its receipts; no module is imported from a retained installation.
"""
import hashlib
import json
import os
import platform
import re
from pathlib import Path
import subprocess
import sys

from installation import classify, device_snapshot, read_journal
from updater.package import safe_bytes, inspect_package, verify_payload, members
from updater.store import Store

ROOT=Path('/var/lib/clean-your-tv-root')
UPDATER=Path('/var/lib/clean-your-tv-root-updater')
SUPERVISOR=Path('/var/lib/clean-your-tv-system-updater')
INSTALLED=Path('/media/developer/apps')
APP='com.cleanyourtv.root.preview'


def checked_store(path, uid=0):
    # Read-only inspection must never provision a state directory.
    store=Store.__new__(Store);store.root=str(path);store.uid=uid
    return store


def sha(raw): return hashlib.sha256(raw).hexdigest()


def verify_package_modes(raw, installed):
    # Archive modes describe deterministic desired package metadata only. SDK
    # ordinary rwx drift cannot authenticate installed bytes or privileged exec.
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(members(raw)['data.tar.gz']),mode='r:gz') as tar:
        for member in tar:
            if member.isfile() and member.mode not in (0o644,0o755):
                raise ValueError('unsafe_archive_executable_mode')


def current_root(root=ROOT, updater=UPDATER, installed=INSTALLED, uid=0):
    """Verify current trusted descriptors and mutable profile separately."""
    from updater.device import Device
    from updater.profile import validate
    from updater.store import encode
    store=checked_store(updater,uid)
    device=Device(store,code=updater/'code',root_state=root,installed=installed)
    device.integrity()
    descriptor=store.read('current')
    device.descriptor(descriptor)
    raw=safe_bytes(device.cached(descriptor),uid=uid)
    verify_payload(installed,inspect_package(raw,descriptor),uid=uid)
    verify_package_modes(raw,installed)
    tx=store.read('transaction')
    if tx is not None:
        if tx.get('phase') not in ('complete','rolled-back','aborted') or tx.get('homeResumePhase')!=tx.get('phase'):
            raise ValueError('root_update_requires_recovery')
        profile=validate(store.read(tx['profile']))
        if sha(encode(profile))!=tx['profileDigest']: raise ValueError('profile_integrity_mismatch')
    return descriptor


def current_updater(updater=UPDATER, installed=INSTALLED, uid=0, hashes=None):
    if hashes is None:
        from package_identity import inventory, ROOT as ROOT_OWNER, UPDATER as UPDATER_OWNER, SYSTEM as SYSTEM_OWNER
        hashes=inventory(UPDATER_OWNER,states={ROOT_OWNER:updater.parent/'clean-your-tv-root',UPDATER_OWNER:updater,SYSTEM_OWNER:updater.parent/'clean-your-tv-system-updater'},uid=uid)
    if not isinstance(hashes,dict) or not hashes:raise ValueError('updater_package_inventory_requires_migration')
    prefixes=('usr/palm/applications/com.cleanyourtv.root.updater/',
              'usr/palm/services/com.cleanyourtv.root.updater.service/')
    for name,digest in hashes.items():
        if not (name.startswith(prefixes) or name=='usr/palm/packages/com.cleanyourtv.root.updater/packageinfo.json'):
            raise ValueError('foreign_updater_package_file')
        from package_data import read_verified
        read_verified(installed/name,sha256=digest,limit=32*1024*1024,installed=installed,uid=uid)
    return True


def _has_inventory(files):
    raw=files.get('usr/palm/applications/'+APP+'/apps.js',b'')
    try:
        value=json.loads(raw.decode().split('=',1)[1].strip().rstrip(';'))
        return isinstance(value,dict) and isinstance(value.get('apps'),list) and bool(value['apps'])
    except (ValueError,IndexError,UnicodeError): return False


def _capture_migrated_baseline(bundle):
    """Make rollback match the exact explicitly migrated installed bytes."""
    import io
    import tarfile
    import root_package
    manifest=json.loads(safe_bytes(bundle/'bundle.json'))
    path=bundle/manifest['package'];raw=safe_bytes(path)
    parts=root_package.read_ar(raw);files=root_package.data_files(raw)
    receipt=json.loads(safe_bytes(ROOT/'personalization.json',uid=0))
    for name,digest in receipt['files'].items():
        root_package.safe_name(name)
        target='usr/palm/applications/'+APP+'/'+name
        from package_data import read_verified
        data=read_verified(INSTALLED/target,sha256=digest,limit=32*1024*1024,installed=INSTALLED)
        if sha(data)!=digest: raise ValueError('personalization_changed')
        files[target]=data
    with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']),mode='r:gz') as tar:
        executable={m.name for m in tar if m.isfile() and m.mode&0o111}
    parts['data.tar.gz']=root_package.tgz(files,executable=executable,directories=False)
    raw=root_package.ar(parts);path.write_bytes(raw)
    release=json.loads(safe_bytes(bundle/'release.json'))
    release['files']={n:sha(b) for n,b in files.items()}
    (bundle/'release.json').write_text(json.dumps(release))
    (bundle/'SHA256SUMS').write_text(sha(raw)+'  '+manifest['package']+'\n')
    manifest['files']={name:sha(safe_bytes(bundle/name)) for name in manifest['files']}
    (bundle/'bundle.json').write_text(json.dumps(manifest))


def require_product_abi():
    """Product support is independent of the selected Python interpreter."""
    if sys.platform != 'linux' or platform.machine() not in ('armv7l','armv8l','aarch64'):
        raise RuntimeError('unsupported_product_abi')
    executable=Path('/bin/sh').resolve(strict=True)
    header=safe_bytes(executable,uid=0)[:40]
    if (len(header)!=40 or header[:6]!=b'\x7fELF\x01\x01' or
            int.from_bytes(header[18:20],'little')!=40 or header[37]&4 or header[39]!=5):
        raise RuntimeError('unsupported_product_abi')


PROC=Path('/proc')


class LocalDevice:
    def __init__(self):
        self.payload=None

    def preflight(self, payload, options, product=True):
        import deploy
        from updater.bootstrap import verify_bundle
        deploy.require_device();deploy.require_node()
        if product:
            require_product_abi()
            from provision import require_home_interfaces
            require_home_interfaces()
        self.payload=Path(payload)
        deploy.verify_bundle(self.payload/'root')
        verify_bundle(self.payload/'root-updater')
        if options['prepare_supervisor']:
            self.system_setup().verify_bundle(self.payload/'supervisor')
        from python_binding import launcher_bytes
        launcher_bytes(sys.executable)
        self.options=options

    def system_setup(self):
        import system_setup
        return system_setup

    def inspect(self):
        import deploy
        try:
            deploy.require_device();deploy.require_node();require_product_abi()
            if sys.version_info<(3,9): raise RuntimeError('unsupported_python')
        except (OSError,PermissionError,RuntimeError,ValueError):
            return classify(dict(supported=False,packages_match=False,receipts_match=False,pending=False,retained=False,complete=False,migration_supported=False))
        versions=None
        operation=getattr(self,'operation',None)
        values=device_snapshot(owned_operation=operation['id'] if operation else None)
        # device_snapshot intentionally refuses to bless lifecycle markers alone.
        # Complete descriptor/profile readback adds the missing package evidence.
        if not any(values[k] for k in ('pending','retained')) and os.path.lexists(ROOT) and os.path.lexists(UPDATER):
            try:
                if os.path.lexists(SUPERVISOR): self.verify_supervisor()
                current_updater(UPDATER,INSTALLED,hashes=getattr(self,'supervisor_updater',None))
                descriptor=current_root(ROOT,UPDATER,INSTALLED)
                # Only display versions after exact current package/code readback.
                from package_identity import identity
                info=identity('com.cleanyourtv.root.updater',installed=INSTALLED)
                if info.get('id')!='com.cleanyourtv.root.updater':raise ValueError('updater_identity_mismatch')
                versions={'root':descriptor['version'],'root-updater':info['version']}
                if any(not isinstance(v,str) or not __import__('re').fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',v) for v in versions.values()):raise ValueError('invalid_installed_version')
                values.update(packages_match=True,receipts_match=True,complete=True)
            except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.SubprocessError):
                values['retained']=True;versions=None
        result=classify(values)
        if result['state']=='installed' and versions is not None:result['versions']=versions
        return result

    def verify_snapshot(self, payload, submission, *, inventories=None):
        """Authenticate retained bytes without admitting installation effects."""
        from install_driver import _verified_payload,root_review_binding
        options=submission.get('options')
        if not isinstance(options,dict) or set(options)!={'migrate','prepare_supervisor'} or any(type(v) is not bool for v in options.values()):raise ValueError('unknown_snapshot_options')
        payload=Path(payload)
        if inventories is None:inventories=_verified_payload(payload,options['prepare_supervisor'])
        if submission.get('action') not in ('install','remove'):raise ValueError('unknown_snapshot_action')
        if root_review_binding(payload,inventories)!=submission.get('root_binding'):raise ValueError('reviewed_root_code_changed')
        if sha(safe_bytes(payload/'root-updater/bundle.json',uid=os.geteuid()))!=submission.get('worker_sha256'):raise ValueError('worker_snapshot_changed')
        static=submission.get('root_static')
        expected=set(inventories['root']['files'])-{inventories['root']['package'],'release.json','SHA256SUMS'}
        if not isinstance(static,dict) or set(static)!=expected:raise ValueError('static_snapshot_required')
        for name,digest in static.items():
            if sha(safe_bytes(payload/'root'/name,uid=os.geteuid()))!=digest:raise ValueError('static_snapshot_changed')
        return options

    def verify_resume(self, payload, submission):
        options=self.verify_snapshot(payload,submission)
        self.preflight(Path(payload),options,product=submission['action']=='install')
        return options

    def continuation_ready(self, record, submission, store):
        """Read-only final-stage proof; uncertain package submissions stay blocked."""
        if record.get('action')=='install':
            if record.get('stage') not in ('readback','complete'):return False
            if self.inspect()['state']!='installed':return False
            return self.readback().get('verified') is True
        if record.get('action')!='remove' or record.get('stage') not in ('removal-readback','removal-verified','complete'):return False
        from installation import terminal_removal
        journal=store.read('removal-'+record['lease'])
        if not isinstance(journal,dict) or journal.get('schema')!=1:return False
        initial=journal.get('initial_apps')
        if not isinstance(initial,list) or not isinstance(journal.get('removals'),dict):return False
        for app in ('com.cleanyourtv.root.updater','com.cleanyourtv.updater','com.local.nativehome','com.gathin.tvhome','com.cleanyourtv.system.updater'):
            receipt=journal['removals'].get(app)
            if not isinstance(receipt,dict):return False
            if app in initial:
                if receipt.get('state')!='terminal' or not terminal_removal(receipt.get('evidence'),app):return False
            elif receipt.get('state')!='absent-before-submission':return False
        if APP in initial:
            proof=self.root_journal()
            if not isinstance(proof,dict) or not terminal_removal(proof.get('evidence'),APP):return False
        self.verify_removed()
        if os.path.lexists(ROOT) and self.cleanup('root_archive','inspect').get('busy') is not False:return False
        return True

    def continuation_quiescent(self, snapshot):
        """No surviving original mutator may race the final readback."""
        prefixes=tuple(str(p).encode()+b'/' for p in (ROOT,UPDATER,SUPERVISOR,Path(snapshot)))
        mutators=(b'deploy.py',b'provision.py',b'install_driver.py',b'setup-updater.py',b'system_setup.py')
        for process in PROC.iterdir():
            if not process.name.isdigit() or int(process.name)==os.getpid():continue
            try:args=(process/'cmdline').read_bytes().split(b'\0')
            except FileNotFoundError:continue
            if any(arg.startswith(prefixes) and arg.rsplit(b'/',1)[-1] in mutators for arg in args):
                raise ValueError('live_original_worker')

    def resume_install(self, payload, options, stage, checkpoint):
        import deploy
        root=Path(payload)/'root'
        current=self.inspect()['state']
        if current=='fresh' and stage in ('reserved','root-deploy','blocked'):
            checkpoint('root-deploy');self.deploy(payload,options)
        elif current!='installed':
            journal=read_journal(ROOT/'deploy.json')
            if not isinstance(journal,dict):raise ValueError('root_submission_requires_recovery')
            phase=journal.get('stage')
            if phase!='installed-recovery-only':
                from installation import terminal_install
                allowed={'install-observed','payload-verified','personalization-complete'}|{'provision-'+step+'-'+state for step in ('apply','resume_pending','refresh','finalize') for state in ('starting','complete')}
                if phase not in allowed or not terminal_install(read_journal(ROOT/'install-terminal.json'),APP):raise ValueError('root_submission_requires_recovery')
                if options['migrate'] and read_journal(ROOT/'personalization.json') is None:raise ValueError('migration_snapshot_requires_recovery')
                self.validate_root_driver()
                if options['migrate']:_capture_migrated_baseline(root)
                deploy.verify_payload(json.loads(safe_bytes(root/'release.json')))
                steps=['refresh','finalize']
                if read_journal(ROOT/'recovery-provision.json') is None:
                    steps.insert(0,'resume_pending' if read_journal(ROOT/'ls2-provision-snapshot.json') is not None else 'apply')
                for step in steps:
                    deploy.write_stage('provision-'+step+'-starting')
                    deploy.command([deploy.python_command(ROOT),str(ROOT/'provision.py'),step])
                    deploy.write_stage('provision-'+step+'-complete')
                deploy.write_stage('installed-recovery-only')
            if options['migrate']:_capture_migrated_baseline(root)
            deploy.verify_payload(json.loads(safe_bytes(root/'release.json')))
            verify_package_modes(safe_bytes(root/json.loads(safe_bytes(root/'bundle.json'))['package']),INSTALLED)
        if not os.path.lexists(UPDATER):
            # Bootstrap always writes private state before submission. Also reject
            # foreign/externally retained package and bus artifacts before setup.
            app='com.cleanyourtv.root.updater'
            self.absent(app)
            paths=[Path('/var/lib/webosbrew/init.d/51-clean-your-tv-root-updater')]
            paths += [Path('/var/luna-service2-dev')/folder/(app+'.service'+suffix) for folder,suffix in (('services.d','.service'),('roles.d','.service.json'),('client-permissions.d','.service.json'),('api-permissions.d','.api.json'))]
            if any(os.path.lexists(p) for p in paths):raise ValueError('retained_updater_artifacts')
            checkpoint('root-updater');self.updater(payload,options)
        else:
            bootstrap=read_journal(UPDATER/'bootstrap.json')
            if not isinstance(bootstrap,dict):raise ValueError('updater_submission_requires_recovery')
            if bootstrap.get('phase')!='complete':
                from updater.bootstrap import resume
                checkpoint('root-updater');resume(Path(payload)/'root-updater')
        if options['prepare_supervisor']:
            if os.path.lexists(SUPERVISOR):
                bootstrap=read_journal(SUPERVISOR/'bootstrap.json')
                if not isinstance(bootstrap,dict):raise ValueError('supervisor_submission_requires_recovery')
                if bootstrap.get('phase')!='complete':
                    checkpoint('supervisor');self.system_setup().resume(Path(payload)/'supervisor')
                else:self.verify_supervisor()
            else:
                checkpoint('supervisor');self.supervisor(payload,options)
        checkpoint('readback')
        return self.readback()

    def validate_completion(self, action, lease_id):
        from installation import Ownership,pending_journals,STATE
        owner=Ownership.__new__(Ownership);owner.store=checked_store(STATE)
        lease=owner.status()
        if lease is None or lease['id']!=lease_id or lease['owner']!='product' or not lease['terminal']:return False
        pending_journals('product')
        if action=='install':
            if self.inspect()['state']!='installed':return False
        else:
            self.verify_removed()
            if os.path.lexists(ROOT) and self.cleanup('root_archive','inspect').get('busy') is not False:return False
        return owner.status()==lease

    def deploy(self, payload, options):
        import deploy
        root=Path(payload)/'root'
        if not options['migrate']:
            import root_package
            manifest=json.loads(safe_bytes(root/'bundle.json'))
            files=root_package.data_files(safe_bytes(root/manifest['package']))
            # Host cytv provides its inventory; a generic offline Root has the
            # empty placeholder and must discover apps locally before deployment.
            if b'window.TV_APPS = {apps:[],inputs:[]}' in files.get('usr/palm/applications/'+APP+'/apps.js',b'') or not _has_inventory(files):
                result=subprocess.run(['/usr/bin/node','-e',"require(process.argv[1])().then(function(a){process.stdout.write(JSON.stringify(a));},function(){process.exit(1);});",str(Path(__file__).parent/'app-inventory.js')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
                apps=json.loads(result.stdout)
                inventory={'apps':[{k:a[k] for k in ('id','title','icon','iconColor')} for a in apps if not a.get('hidden') and isinstance(a.get('id'),str) and isinstance(a.get('title'),str)],'inputs':[]}
                root_package.personalize_root(root,inventory)
        result=deploy.install(root,migrate=options['migrate'])
        if options['migrate']: _capture_migrated_baseline(root)
        return result

    def updater(self, payload, options):
        from updater.bootstrap import apply
        return apply(Path(payload)/'root-updater',Path(payload)/'root')

    def supervisor(self, payload, options):
        if os.path.lexists(SUPERVISOR): return self.verify_supervisor()
        setup=self.system_setup()
        baseline=Path(payload)/'captured-baseline'
        # Exact personalized installed bytes, never the generic offline baseline.
        setup.snapshot(Path(payload)/'supervisor','root',baseline)
        return setup.provision(Path(payload)/'supervisor',baseline)

    def verify_supervisor(self):
        # Import the trusted bundled implementation, never the retained worker.
        source=Path(__file__).parent/'system_updater/device.py'
        if not source.is_file(): raise ValueError('supervisor_inspector_unavailable')
        from system_updater.device import Device
        store=checked_store(SUPERVISOR)
        device=Device(store,code=SUPERVISOR/'code',root_state=ROOT,root_updater=UPDATER,installed=INSTALLED)
        receipt=store.read('infrastructure')
        if not isinstance(receipt,dict) or receipt.get('schema')!=1 or not isinstance(receipt.get('code'),dict) or not receipt['code']:
            raise ValueError('supervisor_infrastructure_unknown')
        for name,digest in receipt['code'].items():
            from pathlib import PurePosixPath
            relative=PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or str(relative)!=name or sha(safe_bytes(SUPERVISOR/'code'/name,uid=0))!=digest:
                raise ValueError('supervisor_infrastructure_mismatch')
        lockdown=store.read('legacy-lockdown')
        if not isinstance(lockdown,dict) or lockdown.get('schema')!=1: raise ValueError('supervisor_lockdown_unknown')
        for name,entry in lockdown['files'].items():
            if name not in device._legacy_lockdown_paths() or safe_bytes(name,uid=0)!=entry['disabled'].encode():
                raise ValueError('supervisor_lockdown_mismatch')
        from system_updater.core import Manager
        tx=Manager(store,device)._load()
        if tx is not None and (tx['phase'] not in ('complete','rolled-back','aborted') or tx.get('homeResumePhase')!=tx['phase']):
            raise ValueError('system_update_requires_recovery')
        self.supervisor_transaction=tx
        baseline=device._baseline('root')
        # Standalone Root publication is separately proved by current_root(); a
        # historical System Root component cannot override that current writer.
        if not all(device.verify_installed(c) for c in baseline['components'] if c['name']!='root'):raise ValueError('supervisor_baseline_mismatch')
        from package_identity import identity
        identity('com.cleanyourtv.system.updater',installed=INSTALLED,full=True)
        updater=next(item for item in baseline['components'] if item['name']=='root-updater')
        raw=device.cache_bytes(updater)
        self.supervisor_updater=device.inspect(raw,updater)
        infrastructure=next(item for item in baseline['components'] if item['name']=='root-infrastructure')
        self.supervisor_infrastructure=device.inspect(device.cache_bytes(infrastructure),infrastructure)
        verify_package_modes(raw,INSTALLED)
        return baseline

    def readback(self):
        if os.path.lexists(SUPERVISOR): self.verify_supervisor()
        current_updater(UPDATER,INSTALLED,hashes=getattr(self,'supervisor_updater',None));descriptor=current_root(ROOT,UPDATER,INSTALLED)
        return {'verified':True,'installed':APP,'home_changed':False,'baseline_sha':descriptor['sha256']}

    @staticmethod
    def log(error):
        import traceback
        traceback.print_exception(type(error),error,error.__traceback__,file=sys.stderr)

    def validate_root_driver(self):
        """Hash retained executable support/runtime as data before spawning it."""
        import deploy
        from updater.device import Device
        if not os.path.lexists(ROOT): return
        bundle=read_journal(ROOT/'bundle.json')
        if not isinstance(bundle,dict) or not isinstance(bundle.get('files'),dict):
            raise ValueError('root_recovery_requires_existing_cytv_recovery')
        files=bundle['files']
        support=('provision.py','startup_hook.py','activity.py','python_binding.py','system_permissions.py')
        support+=tuple(name for name in ('package_data.py','package_identity.py','startup_guard.py') if name in files)
        release_raw=safe_bytes(ROOT/'release.json',limit=65536,uid=0)
        if files.get('release.json')!=sha(release_raw):
            raise ValueError('root_recovery_release_mismatch')
        release=json.loads(release_raw)
        version=release.get('version') if isinstance(release,dict) else None
        if (not isinstance(version,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',version)
                or release.get('application_id')!=APP
                or bundle.get('package')!=APP+'_'+version+'_all.ipk'
                or bundle['package'] not in files):
            raise ValueError('root_recovery_release_identity_mismatch')
        expected=set(deploy.RUNTIME_FILES)
        layout=release.get('runtime_layout')
        if layout is None and version=='0.5.0':
            expected.add('audio_recovery.py')
        elif layout not in (None,'inline-audio-v1'):
            raise ValueError('root_recovery_runtime_inventory_mismatch')
        runtime_names={name[len('runtime/'):] for name in files if name.startswith('runtime/')}
        if runtime_names!=expected:
            raise ValueError('root_recovery_runtime_inventory_mismatch')
        proof=read_journal(ROOT/'recovery-provision.json')
        if proof is not None:
            if proof.get('version')!=1 or proof.get('mode')!='recovery-only' or not isinstance(proof.get('files'),dict):
                raise ValueError('root_recovery_protocol_unknown')
            prefix=str(ROOT/'runtime')+'/'
            if {name[len(prefix):] for name in proof['files'] if name.startswith(prefix)}!=expected:
                raise ValueError('root_recovery_runtime_inventory_mismatch')
            runtime={name:proof['files'].get(str(ROOT/'runtime'/name)) for name in expected}
        else:
            runtime={name:files.get('runtime/'+name) for name in expected}
        changed=any(files.get(name)!=sha(safe_bytes(ROOT/name,uid=0)) for name in support)
        changed=changed or any(digest!=files.get('runtime/'+name) for name,digest in runtime.items())
        infrastructure={}
        if changed:
            if proof is None or not os.path.lexists(SUPERVISOR):
                raise ValueError('root_recovery_current_provenance_required')
            baseline=self.verify_supervisor()
            # Signed bytes alone do not establish a completed writer. The
            # resumed terminal journal must select this exact verified release.
            tx=self.supervisor_transaction
            selected=tx['candidate' if tx['phase']=='complete' else 'prior'] if tx else None
            if 'proof' not in baseline or selected!=baseline:
                raise ValueError('root_recovery_current_provenance_required')
            current_root(ROOT,UPDATER,INSTALLED)
            infrastructure=self.supervisor_infrastructure
            if {name[len('runtime/'):] for name in infrastructure if name.startswith('runtime/')}!=expected:
                raise ValueError('root_recovery_runtime_inventory_mismatch')
            from system_updater.device import Device as SystemDevice
            device=SystemDevice(checked_store(SUPERVISOR),code=SUPERVISOR/'code',root_state=ROOT,root_updater=UPDATER,installed=INSTALLED)
            device.require_components()
            device._root_integrity()
        for name in support:
            original=files.get(name)
            current=sha(safe_bytes(ROOT/name,uid=0))
            if current!=original and (infrastructure.get('support/'+name)!=current or proof['files'].get(str(ROOT/name))!=current):
                raise ValueError('root_recovery_support_mismatch')
        for name,digest in runtime.items():
            expected_digest=infrastructure.get('runtime/'+name) if changed else files.get('runtime/'+name)
            if digest!=expected_digest or digest!=sha(safe_bytes(ROOT/'runtime'/name,uid=0)):
                raise ValueError('root_recovery_runtime_mismatch')
        Device.require_home_resume_runtime(ROOT)

    def activate(self):
        import deploy
        if self.inspect()['state']!='installed':raise ValueError('current_installation_required')
        self.validate_root_driver()
        # The existing public runtime gate owns the mutex, emergency/off and input checks.
        return deploy.runtime('enable')

    def restore(self):
        import deploy
        self.validate_root_driver()
        return deploy.restore()

    @staticmethod
    def rpc(method, payload):
        from updater.luna import call
        return call('luna://'+method,payload)

    @staticmethod
    def cleanup(name, *args):
        if name not in ('root_updater','system_updater','legacy_permissions','app_permissions','root_archive'):
            raise ValueError('unsupported_cleanup')
        result=subprocess.run([sys.executable,str(Path(__file__).parent/('cleanup_'+name+'.py')),*args],
                              check=True,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
        if name in ('legacy_permissions','app_permissions'):
            expected={'legacy_permissions':b'CYTV_LEGACY_PERMISSIONS_REMOVED','app_permissions':b'CYTV_APP_PERMISSIONS_REMOVED'}[name]
            if result.stdout.strip()!=expected: raise ValueError('cleanup_unconfirmed')
            return True
        return json.loads(result.stdout)

    @staticmethod
    def legacy_status():
        from updater.luna import call
        return call('luna://com.cleanyourtv.updater.service/status',{},app_id='com.gathin.tvhome')

    def apps(self):
        value=self.rpc('com.webos.applicationManager/dev/listApps',{})
        apps=value.get('apps')
        if not isinstance(apps,list) or not all(isinstance(a,dict) and isinstance(a.get('id'),str) for a in apps):
            raise ValueError('invalid_app_inventory')
        return {a['id'] for a in apps}

    @staticmethod
    def package_paths(app):
        service=app+'.renewal' if app=='com.gathin.tvhome' else app+'.service'
        return [INSTALLED/'usr/palm'/folder/name for folder,name in (
            ('applications',app),('packages',app),('services',service))]

    def absent(self, app, terminal=None):
        paths=self.package_paths(app)
        package=paths[1]
        # Empty package remainders are removed only with a saved subscribed
        # terminal for this request. Absence never manufactures terminal proof.
        if terminal and terminal.get('completed') is True and os.path.lexists(package):
            if package.is_symlink() or not package.is_dir(): raise ValueError('unsafe_package_remainder')
            package.rmdir()
        if any(os.path.lexists(p) for p in paths): raise ValueError('package_remains')

    def root_journal(self):return read_journal(ROOT/'deploy.json')

    def archive_proof(self,path):
        value=read_journal(Path(path)/'cytv-removal.json')
        return isinstance(value,dict) and value.get('phase')=='disabled' and value.get('archive')==path

    def remove(self, checkpoint, resume=False):
        import deploy,time,uuid
        from observed_install import remove
        ownership=self.ownership;lease=ownership.status()
        if lease is None or lease['owner']!='product' or lease['id']!=self.operation['id']:raise ValueError('product_lease_required')
        journal=ownership.store;name='removal-'+lease['id'];record=journal.read(name)
        if record is not None and not resume:raise ValueError('removal_already_started')
        if record is None:
            record={'schema':1,'root_updater_archive':str(UPDATER)+'.archive-'+uuid.uuid4().hex,
                    'system_updater_archive':str(SUPERVISOR)+'.archive-'+uuid.uuid4().hex,'removals':{},'done':[]}
            journal.write(name,record)
        if record.get('schema')!=1 or not isinstance(record.get('done'),list) or not isinstance(record.get('removals'),dict):raise ValueError('unknown_removal_journal')
        def save(stage):record['stage']=stage;journal.write(name,record);checkpoint(stage)
        def step(label,fn):
            if label not in record['done']:
                save(label);result=fn();record['done'].append(label);journal.write(name,record);return result
        idle=self.rpc('com.webos.appInstallService/status',{'subscribe':True})
        if idle.get('status',{}).get('apps')!=[]:raise ValueError('installer_not_idle')
        current=self.apps();legacy='com.cleanyourtv.updater';home='com.gathin.tvhome';helper='com.local.nativehome';supervisor='com.cleanyourtv.system.updater'
        if 'initial_apps' not in record:
            record['initial_apps']=sorted(current);record['system_needed']=supervisor in current or os.path.lexists(SUPERVISOR);journal.write(name,record)
        apps=set(record['initial_apps'])
        # Authenticate the retained executable closure before disabling updaters.
        # root_remove validates it again immediately before invocation.
        if APP in current:self.validate_root_driver()
        if legacy in current:
            status=self.legacy_status().get('result')
            if not isinstance(status,dict) or 'transaction' not in status:raise ValueError('legacy_updater_unknown')
            tx=status['transaction']
            if tx is not None and (not isinstance(tx,dict) or tx.get('status') not in ('complete','rolled-back')):raise ValueError('legacy_update_pending')
        def system_disable():
            if not os.path.lexists(SUPERVISOR) and self.archive_proof(record['system_updater_archive']):return
            self.cleanup('system_updater','status',record['system_updater_archive'])
            if self.cleanup('system_updater','disable',record['system_updater_archive']).get('disabled') is not True:raise ValueError('supervisor_disable_unconfirmed')
        if record['system_needed']:step('supervisor-disable',system_disable)
        def root_updater_disable():
            if self.cleanup('root_updater','disable',record['root_updater_archive']).get('disabled') is not True:raise ValueError('root_updater_disable_unconfirmed')
        step('root-updater-disable',root_updater_disable)
        def root_remove():
            if APP not in apps:self.absent(APP);return
            proof=self.root_journal()
            phase=proof.get('stage') if isinstance(proof,dict) else None
            if phase=='uninstalled-state-retained':
                self.absent(APP);return
            if phase=='remove-observed':
                from installation import terminal_removal
                evidence=proof.get('evidence')
                if proof.get('app')!=APP or proof.get('version')!=1 or not terminal_removal(evidence,APP):raise ValueError('root_removal_terminal_unknown')
                deploy.verify_removed(evidence)
                deploy.write_stage('uninstalled-state-retained',evidence=evidence,**({'provisioning_not_started':True} if proof.get('provisioning_not_started') is True else {}));return
            if phase=='remove-submitting':raise ValueError('root_removal_terminal_unknown')
            self.validate_root_driver()
            result=deploy.uninstall()
            if result.get('removed')!=APP:raise ValueError('root_remove_unconfirmed')
        step('root-remove-submitting',root_remove);self.absent(APP)
        if helper in current:step('helper-disable',lambda:self.rpc(helper+'.service/disable',{}))
        def restore_home():
            if home in current:
                self.rpc('com.webos.service.eim/deleteDevice',{'appId':home})
                devices=self.rpc('com.webos.service.eim/getAllInputStatus',{}).get('devices')
                if not isinstance(devices,list) or any(d.get('id')==home or d.get('appId')==home for d in devices):raise ValueError('legacy_input_registration_remains')
            self.rpc('com.webos.applicationManager/launch',{'id':'com.webos.app.home'})
        step('restore-home',restore_home);step('legacy-permissions',lambda:self.cleanup('legacy_permissions'))
        for app in ('com.cleanyourtv.root.updater',legacy,helper,home,supervisor):
            previous=record['removals'].get(app)
            if previous is not None:
                if previous.get('state')=='submitted':raise ValueError('package_removal_terminal_unknown')
                if previous.get('state') not in ('terminal','absent-before-submission'):raise ValueError('unknown_package_removal_receipt')
                if previous['state']=='terminal':
                    from installation import terminal_removal
                    if not terminal_removal(previous.get('evidence'),app):raise ValueError('package_removal_terminal_unknown')
                self.absent(app,previous.get('evidence'));continue
            if app in apps:
                record['removals'][app]={'state':'submitted'};save('package-remove-submitting')
                terminal=remove(app,timeout=150)
                record['removals'][app]={'state':'terminal','evidence':terminal};save('package-remove-terminal')
                self.absent(app,terminal)
            else:
                self.absent(app);record['removals'][app]={'state':'absent-before-submission'};journal.write(name,record)
        step('app-permissions',lambda:self.cleanup('app_permissions'))
        def root_archive():
            result=self.cleanup('root_updater','finalize',record['root_updater_archive'])
            if result.get('removed') is not True:raise ValueError('root_updater_cleanup_incomplete')
            record['updater_archive']=result.get('archive');journal.write(name,record)
        step('root-updater-archive',root_archive)
        def system_archive():
            if not os.path.lexists(SUPERVISOR) and self.archive_proof(record['system_updater_archive']):return
            if self.cleanup('system_updater','archive',record['system_updater_archive']).get('removed') is not True:raise ValueError('supervisor_cleanup_incomplete')
        if record['system_needed']:step('supervisor-archive',system_archive)
        save('removal-readback');self.verify_removed()
        if os.path.lexists(ROOT):
            deadline=time.monotonic()+60
            while self.cleanup('root_archive','inspect').get('busy') is not False:
                if time.monotonic()>=deadline:raise ValueError('old_root_processes_running_restart_required')
                time.sleep(1)
        save('removal-verified')
        return {'removed':True,'applications_services_startup_removed':True,'recovery_retained':str(ROOT),'updater_archive':record.get('updater_archive'),'system_updater_archive':record['system_updater_archive'] if record['system_needed'] else None}

    def verify_removed(self):
        apps=(APP,'com.cleanyourtv.root.updater','com.cleanyourtv.updater','com.gathin.tvhome','com.local.nativehome','com.cleanyourtv.system.updater')
        if self.apps().intersection(apps): raise ValueError('project_apps_remain')
        for app in apps: self.absent(app)
        paths=['/var/lib/webosbrew/init.d/'+n for n in ('50-clean-your-tv-root','51-clean-your-tv-root-updater','52-clean-your-tv-system-updater')]
        paths+=['/var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json','/var/webos-profile/override/clean-your-tv-root.json']
        if any(os.path.lexists(p) for p in paths): raise ValueError('project_routing_remains')
        for folder in ('services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d'):
            if any(p.name.startswith(tuple(a+'.' for a in apps)) for p in (Path('/var/luna-service2-dev')/folder).iterdir()):
                raise ValueError('project_bus_registration_remains')
        settings=self.rpc('com.webos.settingsservice/getSystemSettings',{'category':'general','keys':['defaultApps']})
        profiles=self.rpc('com.webos.service.systemprofile/getProfiles',{'names':['defaultApps','idleApp'],'subscribe':False})['profiles']
        routes=(settings['settings']['defaultApps']['home'],profiles['defaultApps']['categories']['home'],profiles['idleApp']['appId'])
        if routes!=('com.webos.app.home',)*3: raise ValueError('lg_home_routing_unconfirmed')
