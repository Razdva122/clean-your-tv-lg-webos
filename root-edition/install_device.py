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

from installation import classify, device_snapshot, read_journal, _optional_record
from updater.package import safe_bytes, inspect_package, verify_payload, members
from updater.store import Store

ROOT=Path('/var/lib/clean-your-tv-root')
UPDATER=Path('/var/lib/clean-your-tv-root-updater')
SUPERVISOR=Path('/var/lib/clean-your-tv-system-updater')
INSTALLED=Path('/media/developer/apps')
APP='com.cleanyourtv.root.preview'
BUS=Path('/var/luna-service2-dev')
INIT=Path('/var/lib/webosbrew/init.d')
TEMP=Path('/tmp')
SUPPORT_STAGE=re.compile(r'cytv-(?:product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32}')


class InstallerRuntimeMismatch(ValueError):
    """A self-consistent old installation is not the selected installer runtime."""
    reason_code='installer-runtime-mismatch'

    def __init__(self):
        super().__init__('Installed Root runtime differs from this installer; use verified removal and fresh setup')


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
        deploy.verify_bundle(self.payload/'root',allow_experimental=not product)
        verify_bundle(self.payload/'root-updater')
        if options['prepare_supervisor']:
            self.system_setup().verify_bundle(self.payload/'supervisor')
        from python_binding import launcher_bytes
        launcher_bytes(sys.executable)
        self.options=options

    def require_selected_runtime(self, payload):
        """Bind a no-submission handoff to current installer code, not old receipts."""
        import deploy
        selected=Path(payload)/'root'
        manifest=deploy.verify_bundle(selected)
        names=set(deploy.SUPPORT_FILES)|{name for name in manifest['files'] if name.startswith('runtime/')}
        try:
            if any(sha(safe_bytes(ROOT/name,uid=os.geteuid()))!=manifest['files'].get(name) for name in names):
                raise InstallerRuntimeMismatch()
        except (OSError,ValueError):
            raise InstallerRuntimeMismatch() from None

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

    def native_deploy(self, payload):
        # The parent owns the shared product mutex. Execute only this upload's
        # verified driver in isolation, without taking a second deployment lock.
        root=Path(payload)/'root'
        program=('import sys,json;from pathlib import Path\n'
            'sys.path.insert(0,'+repr(str(root))+')\nimport deploy\n'
            'bundle=Path('+repr(str(root))+')\n'
            'release=json.loads(deploy.checked_file(bundle,"release.json"))\n'
            'if release.get("routing")!="compositor-keyfilter-v1":raise ValueError("current_compositor_support_required")\n'
            'admission=deploy.experimental_admission(release["routing"],owned_operation='+repr(self.operation['id'])+')\n'
            'print(json.dumps(deploy.install(bundle,experimental_c1_gate=True,_experimental_admission=admission)))\n')
        result=subprocess.run([sys.executable,'-I','-B','-c',program],check=True,
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1080,
            pass_fds=(self.ownership.fd,))
        return json.loads(result.stdout)

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
        from updater.luna import context
        method='com.webos.applicationManager/dev/listApps'
        try:value=self.rpc(method,{})
        except (RuntimeError,TimeoutError) as error:
            if (str(error) not in ('Bus operation rejected','Bus response timed out')
                    or getattr(error,'luna',{}).get('reason')=='malformed-reply'):raise
            method='com.webos.applicationManager/listApps'
            value=self.rpc(method,{})
        apps=value.get('apps') if isinstance(value,dict) else None
        if not isinstance(apps,list) or not all(isinstance(a,dict) and isinstance(a.get('id'),str) and a['id'] for a in apps):
            raise context(ValueError('invalid_app_inventory'),method,'malformed-reply')
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

    def boot_id(self):
        import deploy
        from clean_removal import boot_format
        root=self.payload/'root'
        deploy.verify_bundle(root,allow_experimental=True)
        program="import sys,json;sys.path.insert(0,%r);from intent_runtime import boot_identity;print(json.dumps({'returnValue':True,'boot':boot_identity()}))"%str(root/'runtime')
        value=deploy.command([sys.executable,'-I','-B','-c',program]).get('boot')
        if boot_format(value)!='session':raise ValueError('boot_id_unavailable')
        return value

    def shared_cleanup(self, action, record, app=None):
        """Current bundled NoRoot namespace cleaner; retained source is never run."""
        name='cleanup_no_root_private.js'
        support=self.payload/'root-updater' if self.payload is not None else Path(__file__).resolve().parent
        raw=safe_bytes(support/name,uid=self.ownership.store.uid)
        manifest=json.loads(safe_bytes(support/'bundle.json',uid=self.ownership.store.uid))
        if sha(raw)!=manifest['files'].get(name):raise ValueError('current_cleanup_support_changed')
        result=subprocess.run(['/usr/bin/node','-e',raw.decode(),json.dumps({'action':action,'app':app,'staging_ids':record.get('cleanup_staging_ids',[])})],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90,
            env={key:value for key,value in os.environ.items() if key not in ('NODE_OPTIONS','NODE_PATH')})
        if result.returncode:raise ValueError('private_cleanup_unconfirmed')
        value=json.loads(result.stdout)
        if value.get('schema')!=1 or not all(isinstance(value.get(k),list) for k in ('present','blocked','root_present')):
            raise ValueError('private_cleanup_unconfirmed')
        if value['blocked']:
            if any(item.get('reason')=='permission-denied' for item in value['blocked']):raise PermissionError('private_cleanup_denied')
            raise ValueError('private_cleanup_unsafe_path')
        return value

    def sweep_package(self, app, record):
        from clean_removal import APPS
        if app not in APPS:raise ValueError('foreign_package')
        result=self.shared_cleanup('root-package',record,app=app)
        if result['present']:raise ValueError('package_remains')

    def clean_remove(self, record, save):
        """Full removal using current support, old snapshots and original locks."""
        from clean_removal import locks, routes, remove_packages, restore_registrations, validate_restored_root_api, boot_format, verified_restart, cleanup_step
        import deploy, provision, startup_hook
        roots=(ROOT,UPDATER,SUPERVISOR)
        uid=self.ownership.store.uid
        with locks(roots,uid):
            restarted=verified_restart(record)
            baseline=record.get('cleanup_boot_id')
            if baseline is not None and not boot_format(baseline):raise ValueError('boot_id_unavailable')
            current_boot=None if restarted else self.boot_id()
            if not restarted:
                if baseline is None or boot_format(baseline)=='kernel':
                    record['cleanup_boot_id']=current_boot
                    record.pop('cleanup_verified_boot_id',None);save(record['stage'])
                restarted=current_boot!=record['cleanup_boot_id']
            if record['stage']=='restart-required' and not restarted:
                return {'removed':False,'verified_clean':False,'restart_required':True}
            self.clean_quiescent(record)
            private=self.shared_cleanup('inventory',record)
            record['cleanup_staging_ids']=private.get('staging_ids',[])
            if private.get('external_update_hint'):record['previous_update_status']=private['external_update_hint']
            restart_first=private.get('resident_installer') or private.get('external_update_hint')
            if 'original-writers-fenced' not in record['done']:
                # A component that held its own lock before our first attempt
                # may have advanced since the initial snapshot. Preserve both
                # observations; only this lock-held one informs absence/drain.
                record['fenced_components']={
                    'deploy':read_journal(ROOT/'deploy.json'),
                    'root-bootstrap':read_journal(UPDATER/'bootstrap.json'),
                    'root-update':read_journal(UPDATER/'transaction.json'),
                    'system-bootstrap':read_journal(SUPERVISOR/'bootstrap.json'),
                    'system-update':read_journal(SUPERVISOR/'transaction.json')}
                latest=record['fenced_components']['deploy'] or {}
                from clean_removal import PRE_ACTIVATION
                record['routing_never_applied']=(latest.get('stage') in PRE_ACTIVATION and not any(
                    os.path.lexists(ROOT/name) for name in ('profile-trial.json','persistent-intent.json','persistent-binding.json','boot-continuation.json',
                        'home-backend.json','c1-gate','c1-keyfilter')))
                self.ownership.store.write('clean-removal-'+record['operation'],record)
                # Original journals remain immutable in the coordinator receipt.
                # These are recognized blocking phases for old entry points.
                for index,root in enumerate(roots):
                    if not os.path.lexists(root):continue
                    store=Store(root,uid=uid)
                    if index==0:
                        store.write('deploy',{'version':1,'app':APP,'stage':'cancellation-admitted'})
                    else:store.write('bootstrap',{'phase':'cancellation-admitted'})
                record['done'].append('original-writers-fenced');save('original-writers-fenced')
            startup_failed=bool(record.get('cleanup_startup_unavailable')) and not restarted
            if 'controls-restored' not in record['done']:
                save('original-writers-fenced')
                with cleanup_step('routing-inverse'):
                    self.preserve_routing_inverse(record)
                if 'profileless_cleanup_eligible' not in record:
                    from clean_removal import ROUTING_EVIDENCE
                    backup=self.ownership.store.read('routing-backup-'+record['operation'])
                    # Capture before restoration can consume inverse records.
                    # Older failed removals already retained their routing backup.
                    record['profileless_cleanup_eligible']=(isinstance(backup,dict)
                        and not any(name.split('/')[0] in ROUTING_EVIDENCE for name in backup)
                        and not any(os.path.lexists(ROOT/name) for name in ROUTING_EVIDENCE)
                        and not os.path.lexists('/var/webos-profile/override/clean-your-tv-root.json')
                        and record.get('routes') is None)
                    save('original-writers-fenced')
                if os.path.lexists(ROOT):
                    # Current verified runtime reads old state as data. Guardian,
                    # key-up and emergency restoration execute before unregister.
                    program=('import sys,json;sys.path.insert(0,'+repr(str(self.payload/'root-updater'))+');'
                             'from clean_removal import runtime_restore;'
                             'print(json.dumps(runtime_restore('+repr(str(self.payload/'root'))+')))')
                    with cleanup_step('runtime-restore'):
                        restored=deploy.command([sys.executable,'-I','-B','-c',program])
                        if restored.get('result') not in ('restored','absent'):raise ValueError('controls_restore_unverified')
                    snapshot=read_journal(ROOT/'ls2-provision-snapshot.json')
                    if snapshot is not None:
                        self.ownership.store.write('owner-backup-'+record['operation'],{'provision':snapshot})
                        with cleanup_step('provision-rollback'):
                            provision.rollback(restored=restored)
                            provision.refresh()
                    else:
                        if any(os.path.lexists(ROOT/name) for name in ('recovery-provision.json','recovery-provision.pending.json')):
                            raise ValueError('provision_snapshot_required')
                        with cleanup_step('startup-hook'):
                            startup_hook.remove(provision.secure)
                # Restore supervisor lockdown before Root updater's original
                # registration. Admit only its authenticated original/installed/
                # restored-SDK chain, never foreign drift.
                if os.path.lexists(SUPERVISOR/'legacy-lockdown.json'):
                    from cleanup_system_updater import lockdown, write
                    with cleanup_step('legacy-lockdown'):
                        entries=lockdown(SUPERVISOR,BUS,check=lambda files:validate_restored_root_api(files,BUS,UPDATER,uid))
                        for name,entry in entries.items():write(Path(name),entry['original'].encode(),entry['mode'])
                for state,app,hookname in ((SUPERVISOR,'com.cleanyourtv.system.updater','52-clean-your-tv-system-updater'),
                                          (UPDATER,'com.cleanyourtv.root.updater','51-clean-your-tv-root-updater')):
                    if not os.path.lexists(state):continue
                    with cleanup_step('registration-restore'):
                        restore_registrations(state,app,BUS,uid)
                        startup_hook.remove_link(provision.secure,state,INIT/hookname,app,startup_hook.owned_legacy(app,state))
                unavailable=set(record.get('cleanup_startup_unavailable',[]))
                for app,service in (('com.local.nativehome','com.local.nativehome.service'),
                                    ('com.gathin.tvhome','com.gathin.tvhome.renewal')):
                    if app not in self.apps() or restarted and service in unavailable:continue
                    try:
                        disabled=self.rpc(service+'/disable',{})
                    except (RuntimeError,TimeoutError) as error:
                        if str(error) not in ('Bus operation rejected','Bus response timed out'):raise
                        disabled={}
                    if service=='com.local.nativehome.service':
                        cancel=disabled.get('cancel',{})
                        confirmed=disabled.get('returnValue') is True and (cancel.get('returnValue') is True or cancel.get('errorCode')==2)
                    else:
                        state=disabled.get('state',{})
                        confirmed=disabled.get('returnValue') is True and state.get('enabled') is False and not state.get('error')
                    if not confirmed:
                        # Broken optional old services cannot gate known-owned
                        # cleanup forever. Cancel fixed jobs below, then boot first.
                        unavailable.add(service);startup_failed=True
                        if restarted:
                            current_boot=current_boot or self.boot_id()
                            record['cleanup_boot_id']=current_boot
                            record.pop('cleanup_verified_boot_id',None)
                            restarted=False
                        record['cleanup_startup_unavailable']=sorted(unavailable)
                        save('original-writers-fenced')
                # Existing precise legacy permission remover restores its own
                # original bytes. No blanket routing setter is used.
                with cleanup_step('legacy-permissions'):
                    self.cleanup('legacy_permissions')
                with cleanup_step('home-readback'):
                    record['routes']=routes(self,record)
                record['done'].append('controls-restored');save('controls-restored')
            # Recheck before destructive work: a retry must not erase newly
            # appeared routing evidence and then use its absence as proof.
            if isinstance(record.get('routes'),dict) and record['routes'].get('mode')=='stock-compositor':
                if not self.compositor_stock_eligible(record) or routes(self,record)!=record['routes']:
                    raise ValueError('routing_evidence_changed')
            if (record.get('routing_never_applied') is True
                    and record.get('profileless_cleanup_eligible') is True
                    and not self.routing_untouched(record)):
                raise ValueError('routing_evidence_changed')
            self.remove_owned_registrations()
            stopped=self.shared_cleanup('stop',record)
            if (stopped.get('controller_running') or startup_failed) and restarted:
                current_boot=current_boot or self.boot_id()
                record['cleanup_boot_id']=current_boot
                record.pop('cleanup_verified_boot_id',None)
                restarted=False
            if stopped.get('controller_running') or startup_failed or restart_first and not restarted:
                save('restart-required')
                return {'removed':False,'verified_clean':False,'restart_required':True}
            save('package-removal')
            package_error=None
            try:
                remove_packages(self,record,save)
                self.cleanup('app_permissions')
            except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:
                package_error=error
            if not package_error and 'package-removal' not in record['done']:record['done'].append('package-removal')
            save('private-cleanup')
            self.shared_cleanup('sweep',record)
            try:
                self.clean_quiescent(record,all_processes=True)
                self.retire_clean_private(record)
            except ValueError as error:
                if restarted or str(error)!='live_original_worker':raise
                # Published Helper may still have a loaded process. Full boot
                # ends it; the final sweep runs afterwards without changing it.
            if package_error:
                record['cleanup_error']='removal-failed'
                raise package_error
            if not restarted:
                save('restart-required')
                return {'removed':False,'verified_clean':False,'restart_required':True}
            if not verified_restart(record):record['cleanup_verified_boot_id']=current_boot
            if 'private-cleanup' not in record['done']:record['done'].append('private-cleanup')
            save('private-cleanup')
        return {'removed':True,'verified_clean':True,'applications_services_startup_removed':True,'private_cleanup_verified':True,
                'temporary_files_retained':bool(record.get('retained_temporary_stages'))}

    def remove_owned_registrations(self):
        devices=self.rpc('com.webos.service.eim/getAllInputStatus',{}).get('devices')
        if not isinstance(devices,list):raise ValueError('input_readback_unverified')
        if any(item.get('id')=='com.gathin.tvhome' or item.get('appId')=='com.gathin.tvhome' for item in devices):
            if self.rpc('com.webos.service.eim/deleteDevice',{'appId':'com.gathin.tvhome'}).get('returnValue') is not True:
                raise ValueError('owned_input_registration_remains')
        from clean_removal import activities as read_activities
        activities=read_activities(self)
        if not isinstance(activities,list):raise ValueError('activity_readback_unverified')
        own={'com.local.nativehome.boot':'luna://com.local.nativehome.service/tick',
             'com.gathin.tvhome.renewal.hourly':'luna://com.gathin.tvhome.renewal/tick',
             'com.cleanyourtv.root.preview.service.recovery':'luna://com.cleanyourtv.root.preview.service/boot'}
        for item in activities:
            if own.get(item.get('name'))!=item.get('callback',{}).get('method') or item.get('name') not in own:continue
            identifier=item.get('activityId')
            if type(identifier) is not int or identifier<0:raise ValueError('owned_activity_unverified')
            result=self.rpc('com.palm.activitymanager/cancel',{'activityId':identifier})
            if result.get('returnValue') is not True and result.get('errorCode')!=2:raise ValueError('owned_activity_remains')

    def retire_clean_private(self, record):
        from clean_removal import retire_tree
        import deploy
        uid=self.ownership.store.uid
        self.retire_temporary_support(record)
        volatile=Path('/tmp/clean-your-tv-root-gate')
        if os.path.lexists(volatile):
            # Current native restore has already verified unmount/stop. Refuse
            # any surviving native process before retiring its private staging.
            self.clean_quiescent(record,all_processes=True)
            retire_tree(volatile,{'gate','gate.empty1','gate.empty2'},uid=uid)
        if 'staging_hashes' not in record:
            hashes=set()
            for root,name in ((ROOT,'bundle'),(UPDATER,'bootstrap-bundle'),(SUPERVISOR,'bootstrap-bundle')):
                if not os.path.lexists(root):continue
                saved=_optional_record(checked_store(root,uid),name)
                if saved is None:continue
                manifest=saved.get('bundle',saved)
                for filename,digest in manifest.get('files',{}).items():
                    if filename.endswith('.ipk') and isinstance(digest,str) and re.fullmatch('[a-f0-9]{64}',digest):hashes.add(digest)
            record['staging_hashes']=sorted(hashes)
            self.ownership.store.write('clean-removal-'+record['operation'],record)
        root_allowed={name.split('/')[0] for name in deploy.SUPPORT_FILES}|{'runtime','service','__pycache__','bundle.json','release.json',
            'deploy.json','install-terminal.json','python-launcher','python-runtime.json',
            'ls2-provision-snapshot.json','recovery-provision.pending.json','recovery-provision.json',
            'recovery-failure.json','run-recovery-service','recovery-service.json','bootstrap.pid',
            'activity-registration.json','startup-hook.json','startup-hook.previous.json',
            'profile-trial.json','profile-trial.lock','persistent-intent.json','persistent-intent.lock',
            'persistent-binding.json','boot-continuation.json','profile-guardian-ready.json','profile-recovery.log',
            'profile-candidate.stage','native-input.json','software-update.lock','update-block.json',
            'update-home-cancel.json','update-home-resume.json','session.lock','boot-dispatch.lock',
            'startup-policy.json','startup-policy.lock','health.log','audio','failsafe',
            'home-backend.json','c1-gate','c1-keyfilter','personalization.json','personalization',
            'state','ssap.json','apps.json','config.json','firmware-permissions.json',
            'theme-receiver-permissions.json','wallpaper-media-permissions.json','weather-permissions.json','audio-recovery',
            'boot-decision.json','session.json','persistent-operation.lock','profile-guardian.log',
            'emergency.log','escape-ready.json','permissions','firmware-permissions.lock','system-permissions.json'}
        updater_allowed={'code','cache','profiles','run-service','python-launcher','python-runtime.json',
            'bootstrap.json','bootstrap-bundle.json','baseline.json','current.json','infrastructure.json',
            'installed-package.json','installed-terminal.json','registration.json','startup-hook.json',
            'startup-hook.previous.json','transaction.json','legacy-lockdown.json','bootstrap.pid',
            'worker.log','daemon.log','removed-registration','cytv-removal.json'}
        def classified(root,index):
            allowed=root_allowed if index==0 else updater_allowed
            if index==2:allowed=allowed|{'current-root.json','current-no-root.json','installer-accepted.json'}
            pattern=r'(?:profile|healthy|healthy-rollback|mutable|helper-resume|renewal-pause)-[a-f0-9]{32}(?:-rollback)?\.json'
            if index==0:
                pattern+=r'|(?:completed-profile-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}|system-rollback-anchor-[a-f0-9]{32})\.json'
            return allowed|{p.name for p in root.iterdir() if re.fullmatch(pattern,p.name)}
        roots=(ROOT,UPDATER,SUPERVISOR)
        for index,root in enumerate(roots):
            if not os.path.lexists(root):continue
            keep={'deploy.json','provision.lock'} if index==0 else {'bootstrap.json','daemon.lock','worker.lock'}
            # Per-transaction data in this private namespace is product-owned;
            # no arbitrary prefix outside it can select a deletion target.
            retire_tree(root,classified(root,index),keep,uid)
        for stage in Path(self.ownership.store.root).iterdir():
            if not re.fullmatch(r'request-[a-f0-9]{32}',stage.name):continue
            identifier=stage.name[8:]
            submitted=_optional_record(self.ownership.store,'submission-'+identifier)
            if not isinstance(submitted,dict) or submitted.get('operation')!=identifier:
                raise ValueError('unclassified_request_staging')
            if _optional_record(self.ownership.store,'request-'+identifier) is None:
                self.ownership.store.write('request-'+identifier,dict(operation=identifier,action=submitted['action'],
                    lease=self.operation['id'],stage='clean-removal-requested',state='recovery_required',code='clean_removal_requested'))
            retire_tree(stage,{'root','root-updater','supervisor','captured-baseline','worker.log'},uid=uid)
        for entry in record.get('support_stages',[]):
            stage=Path(entry['path'])
            if stage==self.payload:continue  # Current tail must remain available until all readbacks.
            if not os.path.lexists(stage):continue
            info=stage.lstat()
            if (info.st_dev,info.st_ino)!=(entry['dev'],entry['ino']):raise ValueError('support_stage_changed')
            retire_tree(stage,{'root','root-updater'},uid=uid)
        from observed_install import STAGING_ROOT
        if os.path.lexists(STAGING_ROOT):
            os.close(checked_store(STAGING_ROOT,uid)._directory())
            for stage in STAGING_ROOT.iterdir():
                if not re.fullmatch(r'cytv-root-install-[A-Za-z0-9_-]+',stage.name):raise ValueError('unclassified_package_staging')
                os.close(checked_store(stage,uid)._directory())
                names={p.name for p in stage.iterdir()}
                if not names:continue
                if names!={'package.ipk'} or sha(safe_bytes(stage/'package.ipk',limit=32*1024*1024,uid=uid)) not in record['staging_hashes']:
                    raise ValueError('unclassified_package_staging')
                retire_tree(stage,{'package.ipk'},uid=uid)
        # Classify by known app/path ownership, never by old success. A matching
        # filename alone is not enough to delete an unknown archive.
        archives=record.get('archives')
        discovered=[]
        for index,root in enumerate(roots):
            for path in sorted(root.parent.iterdir()):
                if not path.name.startswith(root.name+'.archive-'):continue
                if not re.fullmatch(re.escape(root.name)+r'\.archive-[a-f0-9]{32}',path.name):
                    raise ValueError('unclassified_private_archive')
                if archives is not None:
                    if str(path) not in {item['path'] for item in archives}:raise ValueError('unclassified_private_archive')
                    continue
                store=checked_store(path,uid)
                if index==0:
                    proof=_optional_record(store,'deploy')
                    if not isinstance(proof,dict) or proof.get('app')!=APP:
                        raise ValueError('unclassified_private_archive')
                else:
                    proof=_optional_record(store,'cytv-removal')
                    if not isinstance(proof,dict) or proof.get('archive')!=str(path):
                        raise ValueError('unclassified_private_archive')
                info=path.lstat()
                discovered.append({'component':index,'path':str(path),'dev':info.st_dev,'ino':info.st_ino})
        if archives is None:
            archives=record['archives']=discovered
            self.ownership.store.write('clean-removal-'+record['operation'],record)
        for number,item in enumerate(archives):
            index=item['component'];path=Path(item['path'])
            if not os.path.lexists(path):continue
            info=path.lstat()
            if (info.st_dev,info.st_ino)!=(item['dev'],item['ino']):raise ValueError('private_archive_changed')
            store=checked_store(path,uid)
            backup={name:value for name in ('ls2-provision-snapshot','registration','legacy-lockdown','profile-trial')
                    if (value:=_optional_record(store,name)) is not None}
            key='archive-backup-'+record['operation']+'-'+str(number)
            previous=_optional_record(self.ownership.store,key)
            if previous is None:self.ownership.store.write(key,backup)
            # After an interrupted delete, the backup remains the original.
            elif any(previous.get(k)!=v for k,v in backup.items()):raise ValueError('owner_backup_changed')
            allowed=classified(path,index)|{'provision.lock','daemon.lock','worker.lock'}
            retire_tree(path,allowed,uid=uid)
            path.rmdir()
            parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(parent)
            finally:os.close(parent)

    def current_coordinator_reader(self, args):
        """Concurrent polling cannot mutate a product or resume a request."""
        if args[-1:]==[b'']:args=args[:-1]
        try:argv=[arg.decode('utf-8') for arg in args]
        except UnicodeError:return False
        if len(argv)<4 or argv[0] not in (sys.executable,os.path.realpath(sys.executable)) or argv[1]!='-B':return False
        driver=Path(argv[2]);stage=driver.parent
        if (driver.name!='install_driver.py' or stage.parent!=TEMP
                or not re.fullmatch(r'cytv-coordinator-[a-f0-9]{32}',stage.name)):return False
        readonly=argv[3:]==['inspect']
        if (len(argv) in (6,7) and argv[3:5]==['status','--operation']
                and re.fullmatch(r'[a-f0-9]{32}',argv[5])
                and (len(argv)==6 or argv[6]=='--verify-current')):readonly=True
        return readonly and self.current_coordinator_stage(stage)

    def clean_quiescent(self, record, all_processes=False, helpers_only=False):
        snapshot=Path(self.ownership.store.root)/('request-'+record['original']['operation'])
        from clean_removal import APPS
        paths=[ROOT,UPDATER,SUPERVISOR,snapshot,Path('/tmp/clean-your-tv-root-gate')]
        paths.append(Path('/var/lib/clean-your-tv-python'))
        paths.extend(INSTALLED/'usr/palm'/kind/(app+suffix) for app in APPS
                     for kind,suffix in (('applications',''),('services','.renewal' if app=='com.gathin.tvhome' else '.service')))
        paths.extend(Path(item['path']) for item in record.get('archives',[]))
        paths.extend(Path(item['path']) for item in record.get('support_stages',[]))
        paths.extend(path for path in TEMP.iterdir() if SUPPORT_STAGE.fullmatch(path.name))
        if helpers_only:
            paths=[INSTALLED/'usr/palm'/kind/(app+suffix) for app in ('com.local.nativehome','com.gathin.tvhome')
                   for kind,suffix in (('applications',''),('services','.service'),('services','.renewal'))]
            if record.get('helper_lifecycle',{}).get('native_drained') is True:
                paths=[path for path in paths if 'services' not in path.parts]
        # Classifying archive contents happens later; any process using a
        # matching private archive path still prevents cleanup in the meantime.
        prefixes=tuple(str(p).encode()+b'/' for p in paths)
        requests=(str(self.ownership.store.root)+'/request-').encode()
        mutators=(b'deploy.py',b'provision.py',b'install_driver.py',b'setup-updater.py',
                  b'setup-system-updater.py',b'system_setup.py',b'run-updater.py',b'run-system-updater.py')
        for process in PROC.iterdir():
            if not process.name.isdigit() or int(process.name)==os.getpid():continue
            try:args=(process/'cmdline').read_bytes().split(b'\0')
            except FileNotFoundError:continue
            if self.current_coordinator_reader(args):continue
            try:args.append(os.readlink(process/'exe').encode())
            except FileNotFoundError:pass
            if any((any(arg==prefix[:-1] or arg.startswith(prefix) for prefix in prefixes)
                    or not helpers_only and arg.startswith(requests) or any(arg.startswith((str(p)+'.archive-').encode()) for p in (ROOT,UPDATER,SUPERVISOR)))
                   and (all_processes or helpers_only or arg.rsplit(b'/',1)[-1] in mutators) for arg in args):
                raise ValueError('live_original_worker')

    def retire_temporary_support(self, record):
        """Classify discarded installer bundles as data, never by prefix alone."""
        from clean_removal import retire_tree
        uid=self.ownership.store.uid
        inventory=record.setdefault('temporary_stages',[])
        by_path={item['path']:item for item in inventory}
        current=json.loads(safe_bytes(self.payload/'root-updater/bundle.json',uid=uid)) if self.payload else None
        for path in sorted(TEMP.iterdir()):
            if not SUPPORT_STAGE.fullmatch(path.name) or path==self.payload:continue
            if str(path) in {item['path'] for item in record.get('support_stages',[])}:continue
            store=checked_store(path,uid);fd=store._directory()
            try:names=set(os.listdir(fd));info=os.fstat(fd)
            finally:os.close(fd)
            if not names:continue
            saved=by_path.get(str(path))
            if saved:
                if (saved['dev'],saved['ino'])!=(info.st_dev,info.st_ino):raise ValueError('support_stage_changed')
                continue
            if path.name.startswith('cytv-product-'):
                release=json.loads(safe_bytes(path/'root/release.json',uid=uid))
                package=json.loads(safe_bytes(path/'root-updater/package.json',uid=uid))
                if release.get('application_id')!=APP or package.get('name')!='com.cleanyourtv.root.updater.service':raise ValueError('unclassified_support_stage')
                allowed={'root','root-updater'}
            elif path.name.startswith('cytv-coordinator-'):
                package=json.loads(safe_bytes(path/'package.json',uid=uid));services=json.loads(safe_bytes(path/'services.json',uid=uid))
                if package.get('name')!='com.cleanyourtv.root.updater.service' or services.get('id')!=package['name'] or current is None:raise ValueError('unclassified_support_stage')
                allowed={name.split('/')[0] for name in current['files']}|{'bundle.json'}
            elif path.name.startswith('cytv-c1-root-'):
                import deploy
                manifest=deploy.verify_bundle(path,allow_experimental=True)
                release=json.loads(safe_bytes(path/'release.json',uid=uid))
                if release.get('application_id')!=APP:raise ValueError('unclassified_support_stage')
                allowed={name.split('/')[0] for name in manifest['files']}|{'bundle.json'}
            elif path.name.startswith('cytv-system-updater-'):
                manifest=self.system_setup().verify_bundle(path)
                allowed={name.split('/')[0] for name in manifest['files']}|{'bundle.json'}
                retain=bool(names-allowed-{'__pycache__'})
                if '__pycache__' in names:
                    cache=checked_store(path/'__pycache__',uid);cached=cache._directory()
                    try:bytecode=os.listdir(cached)
                    finally:os.close(cached)
                    sources=[name[:-3] for name in manifest['files'] if '/' not in name and name.endswith('.py')]
                    for name in bytecode:
                        if not any(re.fullmatch(re.escape(source)+r'\.cpython-[0-9]{2,3}(?:\.opt-[12])?\.pyc',name) for source in sources):
                            retain=True
                        else:safe_bytes(path/'__pycache__'/name,uid=uid)
                    allowed.add('__pycache__')
                if retain:
                    entry={'path':str(path),'dev':info.st_dev,'ino':info.st_ino}
                    retained=record.setdefault('retained_temporary_stages',[])
                    if entry not in retained:retained.append(entry)
                    continue  # Inert unknown temporary data must not strand removal.
            else:
                # Unrecorded gate-only staging has no product metadata and is
                # not classified from its name or ELF header alone.
                raise ValueError('unclassified_support_stage')
            if names-allowed:raise ValueError('unclassified_support_stage')
            saved={'path':str(path),'dev':info.st_dev,'ino':info.st_ino,'allowed':sorted(allowed)}
            inventory.append(saved);by_path[str(path)]=saved
        self.ownership.store.write('clean-removal-'+record['operation'],record)
        for item in inventory:
            path=Path(item['path'])
            if not os.path.lexists(path):continue
            info=path.lstat()
            if (info.st_dev,info.st_ino)!=(item['dev'],item['ino']):raise ValueError('support_stage_changed')
            retire_tree(path,set(item['allowed']),uid=uid)


    def routing_untouched(self, record):
        """Prove absence of CYTV routing effects, independently of firmware APIs."""
        from clean_removal import PRE_ACTIVATION, ROUTING_EVIDENCE
        deploy=(record.get('fenced_components') or {}).get('deploy') or {}
        if (record.get('routing_never_applied') is not True
                or record.get('profileless_cleanup_eligible') is not True
                or deploy.get('stage') not in PRE_ACTIVATION):return False
        backup=self.ownership.store.read('routing-backup-'+record['operation'])
        return (isinstance(backup,dict)
            and not any(name.split('/')[0] in ROUTING_EVIDENCE for name in backup)
            and not any(os.path.lexists(ROOT/name) for name in ROUTING_EVIDENCE)
            and not os.path.lexists('/var/webos-profile/override/clean-your-tv-root.json'))

    def compositor_stock_eligible(self, record):
        from clean_removal import ROUTING_EVIDENCE
        retained_proof=isinstance(record.get('routes'),dict) and record['routes'].get('mode')=='stock-compositor'
        if (record.get('profileless_cleanup_eligible') is not True or
                not retained_proof and (self.payload is None or not (self.payload/'root/runtime/c1_keyfilter.py').is_file())):return False
        backup=self.ownership.store.read('routing-backup-'+record['operation'])
        return (isinstance(backup,dict)
            and not any(name.split('/')[0] in ROUTING_EVIDENCE for name in backup)
            and not any(os.path.lexists(ROOT/name) for name in ROUTING_EVIDENCE)
            and not os.path.lexists('/var/webos-profile/override/clean-your-tv-root.json'))

    def compositor_stock(self, record):
        import deploy
        if self.payload is None:
            result=subprocess.run(['/usr/bin/node',str(Path(__file__).parent/'cleanup_tail.js'),
                'stock-proof',record['operation'],'-','-1','-1','-1','-',record['removal']],
                check=True,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
            return json.loads(result.stdout)['routes']
        program=('import sys,json;sys.path.insert(0,'+repr(str(self.payload/'root-updater'))+');'
                 'from clean_removal import compositor_stock;'
                 'print(json.dumps({"returnValue":True,"result":compositor_stock('+repr(str(self.payload/'root'))+')}))')
        return deploy.command([sys.executable,'-I','-B','-c',program])['result']

    def preserve_routing_inverse(self, record):
        # Exact finite data-only inverse records, captured before restore can
        # consume them. Credentials, executable trees and mutable preferences
        # are deliberately excluded from these genuine owner backups.
        key='routing-backup-'+record['operation']
        if _optional_record(self.ownership.store,key) is not None:return
        backup={}
        for name in ('profile-trial.json','persistent-intent.json','persistent-binding.json','boot-continuation.json',
                     'profile-candidate.stage','home-backend.json','c1-gate/active',
                     'c1-keyfilter/ownership.json','c1-keyfilter/pending.json',
                     'startup-hook.json','startup-hook.previous.json','system-permissions.json',
                     'firmware-permissions.json','theme-receiver-permissions.json','wallpaper-media-permissions.json','weather-permissions.json'):
            path=ROOT/name
            if os.path.lexists(path):backup[name]=safe_bytes(path,uid=self.ownership.store.uid).decode('utf-8')
        for prefix,root in (('root-updater',UPDATER),('system-updater',SUPERVISOR)):
            for name in ('registration.json','legacy-lockdown.json','startup-hook.json','startup-hook.previous.json'):
                path=root/name
                if os.path.lexists(path):backup[prefix+'/'+name]=safe_bytes(path,uid=self.ownership.store.uid).decode('utf-8')
        self.ownership.store.write(key,backup)

    def retire_current_support(self):
        if self.payload is None:return
        from clean_removal import retire_tree
        retire_tree(self.payload,{'root','root-updater'},uid=self.ownership.store.uid)

    def prepare_clean_install(self, record):
        """Move only verified minimal fences; their original inodes survive.

        Called after the new product lease is durable under the same mutex.
        Historical request tombstones remain at their original lookup paths.
        """
        from clean_removal import locks
        uid=self.ownership.store.uid
        archive=Path(self.ownership.store.root)/('component-fences-'+record['operation'])
        archive.mkdir(mode=0o700,exist_ok=True)
        os.close(checked_store(archive,uid)._directory())
        with locks((ROOT,UPDATER,SUPERVISOR),uid):
            self.verify_clean(record)
            roots=(ROOT,UPDATER,SUPERVISOR)
            key='component-fences-plan-'+record['operation']
            plan=_optional_record(self.ownership.store,key)
            binding=dict(operation=record['operation'],lease=record['lease'],successor=self.operation['id'])
            if plan is None:
                if any(archive.iterdir()):raise ValueError('component_fence_conflict')
                entries={}
                for root in roots:
                    info=root.lstat() if os.path.lexists(root) else None
                    entries[root.name]=[info.st_dev,info.st_ino] if info else None
                plan=dict(binding,entries=entries)
                self.ownership.store.write(key,plan)
            if any(plan.get(k)!=v for k,v in binding.items()) or set(plan.get('entries',{}))!={root.name for root in roots}:
                raise ValueError('component_fence_conflict')
            if {entry.name for entry in archive.iterdir()}-set(plan['entries']):raise ValueError('component_fence_conflict')
            # Validate every remaining source and every previous move before the
            # first rename, allowing the same reservation to finish after a crash.
            for index,root in enumerate(roots):
                target=archive/root.name
                paths=[path for path in (root,target) if os.path.lexists(path)]
                expected=plan['entries'][root.name]
                if len(paths)!=(0 if expected is None else 1):raise ValueError('component_fence_conflict')
                for path in paths:
                    info=path.lstat()
                    if [info.st_dev,info.st_ino]!=expected:raise ValueError('component_fence_changed')
                    os.close(checked_store(path,uid)._directory())
                    allowed={'deploy.json','provision.lock'} if index==0 else {'bootstrap.json','daemon.lock','worker.lock'}
                    if {p.name for p in path.iterdir()}-allowed:raise ValueError('component_fence_changed')
            for root in roots:
                if not os.path.lexists(root):continue
                sourcefd=checked_store(root.parent,uid)._directory()
                destination=checked_store(archive,uid)._directory()
                try:
                    os.rename(root.name,root.name,src_dir_fd=sourcefd,dst_dir_fd=destination)
                    os.fsync(sourcefd);os.fsync(destination)
                finally:os.close(sourcefd);os.close(destination)

    def finish_clean_tail(self, record):
        """Transfer final runtime cleanup to Node with the same inherited flock."""
        saved=_optional_record(self.ownership.store,'clean-removal-'+record['operation'])
        current=self.ownership.status()
        if saved and saved.get('final_fence') is not None:
            # A completed destructive goal has no authority over later files.
            # Its supported retry is the current coordinator/Node readback.
            raise ValueError('completed_removal_readback_required')
        if (not current or current['owner']!='clean-removal'
                or current['journal']!='product-'+record['operation']+'.json'
                or current['id']!=record['lease']):
            raise ValueError('original_removal_required')
        import python_binding, fcntl
        from clean_removal import retire_tree
        runtime=python_binding.MANAGED_ROOT/python_binding.ARCHIVE_SHA256
        directory=checked_store(python_binding.MANAGED_ROOT,self.ownership.store.uid)._directory() if os.path.lexists(python_binding.MANAGED_ROOT) else None
        promotion=None
        try:
            # This is the existing Python promotion mutex, retained across every
            # cleanup/reinstall. Creating its first inode here precedes effects.
            if directory is not None:
                promotion=os.open('.install.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=directory)
                self.ownership.store._check(os.fstat(promotion))
                fcntl.flock(promotion,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.clean_quiescent(record,all_processes=True)
            for name in os.listdir(directory) if directory is not None else ():
                if name in (python_binding.ARCHIVE_SHA256,'.install.lock'):continue
                if not re.fullmatch(r'\.stage-[A-Za-z0-9]{6,32}',name):raise ValueError('unclassified_runtime_staging')
                stage=python_binding.MANAGED_ROOT/name
                retire_tree(stage,{'tree','runtime.tar.gz'},uid=self.ownership.store.uid)
                stage.rmdir();os.fsync(directory)
            # Authenticate the interpreter actually in use. An unused managed
            # tree is owned data to retire, not code we are about to execute.
            if runtime in Path(sys.executable).parents or runtime.resolve() in Path(sys.executable).resolve().parents:
                python_binding._runtime(str(runtime/'bin/python3.13'))
            if 'runtime_cleanup' not in record:
                files={};digest=None
                if os.path.lexists(runtime):
                    raw,inventory=python_binding._runtime_inventory(str(runtime/'bin/python3.13'))
                    files=dict(inventory['files']);files['.cytv-runtime.json']=sha(raw);digest=sha(raw)
                record['runtime_cleanup']={'root':str(runtime),'files':files,'inventory_sha256':digest,'promotion_required':promotion is not None}
            record['runtime_cleanup']['parent_pid']=os.getpid()
            record['stage']='private-cleanup';record['state']='recovery_required'
            record['result']['private_cleanup_verified']=False
            self.ownership.store.write('clean-removal-'+record['operation'],record)
            source=safe_bytes(self.payload/'root-updater/cleanup_tail.js',uid=self.ownership.store.uid)
            self.cleanup_tail_started=True
            descriptors=(self.ownership.fd,promotion if promotion is not None else -1,self.ownership.store.lock_fd)
            gate_hash='-'
            result=subprocess.run(['/usr/bin/node','-','finish',record['operation'],'-',*map(str,descriptors),gate_hash,record['removal']],input=source,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,pass_fds=tuple(fd for fd in descriptors if fd>=0),
                env={key:value for key,value in os.environ.items() if key not in ('NODE_OPTIONS','NODE_PATH')})
            reply=json.loads(result.stdout)
            if reply.get('operation')!=record['operation'] or reply.get('removal')!=record['removal']:raise ValueError('cleanup_tail_unconfirmed')
            if result.returncode:
                code=reply.get('cleanup_error','cleanup-guard-failed')
                if not isinstance(code,str) or not re.fullmatch('[a-z][a-z0-9-]{0,63}',code):code='cleanup-guard-failed'
                sys.stderr.write('CYTV_CLEAN_TAIL: '+code+'\n')
            return reply
        finally:
            if promotion is not None:os.close(promotion)
            if directory is not None:os.close(directory)

    def support_inventory(self, root):
        os.close(checked_store(root,self.ownership.store.uid)._directory())
        result={}
        def scan(directory,prefix=''):
            import stat
            for entry in directory.iterdir():
                name=prefix+entry.name
                info=entry.lstat()
                if stat.S_ISDIR(info.st_mode):
                    os.close(checked_store(entry,self.ownership.store.uid)._directory())
                    result[name+'/']=None
                    scan(entry,name+'/')
                else:result[name]=sha(safe_bytes(entry,uid=self.ownership.store.uid))
        scan(root)
        return result

    def current_product_stage(self, path):
        """Accept an upload only as an exact copy of this authenticated payload."""
        if self.payload is None:return False
        try:
            expected={}
            for component in ('root','root-updater'):
                source=self.payload/component
                raw=safe_bytes(source/'bundle.json',uid=self.ownership.store.uid)
                files=json.loads(raw)['files']
                expected[component+'/']=None
                expected[component+'/bundle.json']=sha(raw)
                for name,digest in files.items():
                    if sha(safe_bytes(source/name,uid=self.ownership.store.uid))!=digest:return False
                    expected[component+'/'+name]=digest
                    for parent in Path(name).parents:
                        if str(parent)!='.':expected[component+'/'+str(parent)+'/']=None
            return self.support_inventory(path)==expected
        except (OSError,ValueError,KeyError,TypeError):return False

    def current_coordinator_stage(self, path):
        """Recognize complete copies of the current host-verified support only."""
        from coordinator_inventory import BUNDLED_FILES
        source=Path(__file__).resolve().parent
        try:
            manifest=source/'bundle.json'
            manifest_digest=None
            if os.path.lexists(manifest):
                raw_manifest=safe_bytes(manifest,uid=self.ownership.store.uid)
                manifest_digest=sha(raw_manifest)
                expected=json.loads(raw_manifest)['files']
                expected={name:digest for name,digest in expected.items() if not name.endswith('.ipk')}
                for name,digest in tuple(expected.items()):
                    if sha(safe_bytes(source/name,uid=self.ownership.store.uid))!=digest:return False
                    for parent in Path(name).parents:
                        if str(parent)!='.':expected[str(parent)+'/']=None
            else:expected=self.support_inventory(source)
            if not set(BUNDLED_FILES)<=set(expected) or any(name.endswith('.ipk') or '__pycache__' in name.split('/') for name in expected):return False
            actual=self.support_inventory(path)
            if actual==expected:return True
            if manifest_digest is not None:
                expected['bundle.json']=manifest_digest
                return actual==expected
            return False
        except (OSError,ValueError,KeyError,TypeError):return False

    def verify_clean(self, record):
        from clean_removal import verified_restart
        if not verified_restart(record):
            raise ValueError('restart_required')
        from clean_removal import validate_package_receipts
        validate_package_receipts(record)
        from clean_removal import APPS, routes
        if self.apps().intersection(APPS):raise ValueError('project_apps_remain')
        for app in APPS:self.absent(app)
        current_routes=routes(self,record)
        if current_routes!=record.get('routes'):
            if current_routes!={'mode':'never-applied'}:raise ValueError('restored_routes_changed')
            # Upgrade older pre-activation readbacks only with fresh no-effect proof.
            record['routes']=current_routes
        for name in ('50-clean-your-tv-root','51-clean-your-tv-root-updater','52-clean-your-tv-system-updater'):
            if os.path.lexists(INIT/name):raise ValueError('startup_remains')
        for name in ('/var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json',
                     '/var/webos-profile/override/clean-your-tv-root.json'):
            if os.path.lexists(name):raise ValueError('owned_registration_remains')
        private=self.shared_cleanup('inventory',record)
        if private['present']:raise ValueError('no_root_private_cleanup_required')
        for path in TEMP.iterdir():
            if SUPPORT_STAGE.fullmatch(path.name) and path!=self.payload:
                if path.name.startswith('cytv-system-updater-'):
                    fd=checked_store(path,self.ownership.store.uid)._directory()
                    try:info=os.fstat(fd)
                    finally:os.close(fd)
                    if {'path':str(path),'dev':info.st_dev,'ino':info.st_ino} in record.get('retained_temporary_stages',[]):continue
                if re.fullmatch(r'cytv-coordinator-[a-f0-9]{32}',path.name) and self.current_coordinator_stage(path):continue
                if re.fullmatch(r'cytv-product-[a-f0-9]{32}',path.name) and self.current_product_stage(path):continue
                fd=checked_store(path,self.ownership.store.uid)._directory()
                try:
                    if os.listdir(fd):raise ValueError('support_stage_remains')
                finally:os.close(fd)
        for folder in ('services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d','groups.d'):
            directory=BUS/folder
            if not os.path.lexists(directory):continue
            os.close(self.ownership.store._walk(str(directory)))
            if any(p.name.startswith(tuple(app+'.' for app in APPS)) for p in directory.iterdir()):
                raise ValueError('owned_registration_remains')
        for index,root in enumerate((ROOT,UPDATER,SUPERVISOR)):
            if not os.path.lexists(root):continue
            allowed={'deploy.json','provision.lock'} if index==0 else {'bootstrap.json','daemon.lock','worker.lock'}
            os.close(checked_store(root,self.ownership.store.uid)._directory())
            if set(p.name for p in root.iterdir())-allowed:raise ValueError('private_members_remain')
        from clean_removal import activities as read_activities
        activities=read_activities(self)
        if (not isinstance(activities,list) or any(not isinstance(item,dict)
                or item.get('name')=='com.cleanyourtv.root.preview.service.recovery'
                or str(item.get('callback',{}).get('method','')).startswith(tuple('luna://'+app+('.renewal/' if app=='com.gathin.tvhome' else '.service/') for app in APPS)) for item in activities)):
            raise ValueError('owned_activity_remains')
        devices=self.rpc('com.webos.service.eim/getAllInputStatus',{}).get('devices')
        if not isinstance(devices,list) or any(d.get('id')=='com.gathin.tvhome' or d.get('appId')=='com.gathin.tvhome' for d in devices):
            raise ValueError('owned_input_registration_remains')
        self.clean_quiescent(record,all_processes=True)
        return True

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
