"""Fixed, explicit System-only replacement using existing verified primitives."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import zlib


REPLACEMENT_SOURCES = {
    '1.2.9': ('1.1.0', '1.1.1'),
    '1.2.10': ('1.1.0', '1.1.1', '1.2.9'),
    '1.2.11': ('1.2.10',),
}


def support_source():
    from .system_rollback_recovery import SCRIPT
    tree=ast.parse(SCRIPT)
    names={'encode','digest','read','original_code','load_sources'}
    return 'import hashlib,json,os,re,stat,sys\nfrom pathlib import Path,PurePosixPath\n'+ f'REPLACEMENT_SOURCES = {REPLACEMENT_SOURCES!r}\n' + '\n'.join(ast.get_source_segment(SCRIPT,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)+'\n'


SCRIPT=r'''
import base64,copy,fcntl,io,shutil,signal,subprocess,tempfile,time,types,uuid,zlib
APP='com.cleanyourtv.system.updater'
SERVICE=APP+'.service'
SYSTEM=Path('/var/lib/clean-your-tv-system-updater')
ROOT_STATE=Path('/var/lib/clean-your-tv-root')
STAGES=('capture','disable','remove','archive','provision','verify','complete')
HOME_OVERRIDE=Path('/var/webos-profile/override/clean-your-tv-root.json')
HOME_FILES=(ROOT_STATE/'persistent-intent.json',HOME_OVERRIDE)

class StockHomeRequired(ValueError):
    pass

def directory(path):
    for parent in (Path(path),*Path(path).parents):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,os.geteuid()) or (info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX):raise ValueError('Unsafe replacement workspace')

def sync_tree(path):
    directory(path)
    for parent,dirs,files in os.walk(path,followlinks=False):
        directory(parent)
        for name in files:
            target=Path(parent)/name;read(target,64*1024*1024)
            fd=os.open(target,os.O_RDONLY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)
    for parent,dirs,files in os.walk(path,topdown=False):
        fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

def preserved_home():
    return {str(path):digest(read(path)) if os.path.lexists(path) else None for path in HOME_FILES}

def require_stock_home(manager):
    stock='com.webos.app.home'
    try:
        status=manager.io.runtime('status')
        intent=status['intent']
        effective=status['effective']
        profiles=effective['profiles']
        idle=profiles['idleApp']
        if ((intent is None or (intent['phase']=='disabled' and intent['enabled'] is False))
                and not os.path.lexists(HOME_OVERRIDE) and idle['support'] is True
                and (effective['sam_home'],profiles['defaultApps']['categories']['home'],idle['appId'])==(stock,stock,stock)):
            return
    except (OSError,subprocess.SubprocessError,ValueError,KeyError,TypeError):
        pass
    raise StockHomeRequired('Return to LG Home before replacing System Updater')

def old_proof(manager,system):
    device=manager.io;device.integrity(enforce=False);device.require_components();device._root_integrity()
    if os.path.lexists(device.root_updater/'transaction.json'):raise ValueError('Existing legacy Root backup requires review before System replacement')
    tx=manager._load()
    profile=None
    if tx is not None:
        if tx['edition']!='root' or tx['phase'] not in ('complete','rolled-back','aborted') or tx.get('homeResumePhase')!=tx['phase']:raise ValueError('Finish the existing System recovery before replacement')
        manager._profile(tx);profile={'name':tx['profile'],'sha256':digest(read(system/(tx['profile']+'.json')))}
    return {'code':original_code(system),'transaction':digest(encode(tx)),'profile':profile,
            'registration':digest(read(system/'registration.json')),'home':preserved_home()}

def baseline_readback(setup,baseline,bundle):
    value=setup.verify_baseline(baseline,bundle)
    for item in value['components']:
        raw=setup.safe(baseline/'cache'/item['sha256'])
        if item['kind']=='ipk':
            for name,data in setup.package_files(raw).items():
                if setup.installed_data(setup.INSTALLED/name,data,setup.INSTALLED,'root')!=data:raise ValueError('Root baseline changed during System replacement')
        else:setup.infrastructure_readback(item,raw)
    return value

def supervisor_absent(installed):
    if any(os.path.lexists(installed/'usr/palm'/kind/name) for kind,name in [('applications',APP),('packages',APP),('services',SERVICE)]):raise ValueError('System Updater package absence not verified')

def remove_system(remove,terminal_removal,installed,store,job):
    evidence=job.get('removal')
    if evidence is None:
        job['removal']={'state':'submitted'};store.write('system-replacement',job)
        terminal=remove(APP,timeout=150)
        if not terminal_removal(terminal,APP):raise ValueError('System removal terminal unknown; do not replay')
        job['removal']={'state':'terminal','evidence':terminal};store.write('system-replacement',job)
    elif evidence.get('state')!='terminal' or not terminal_removal(evidence.get('evidence'),APP):raise ValueError('System removal outcome unknown; do not replay')
    supervisor_absent(installed)

def archive_proof(archive,job):
    if not archive.is_dir() or original_code(archive)!=job['old']['code'] or json.loads(read(archive/'cytv-removal.json')).get('archive')!=job['archive']:raise ValueError('Original System archive proof mismatch')
    if digest(read(archive/'registration.json'))!=job['old']['registration']:raise ValueError('Original System registration proof changed')
    tx=json.loads(read(archive/'transaction.json')) if os.path.lexists(archive/'transaction.json') else None
    if digest(encode(tx))!=job['old']['transaction']:raise ValueError('Original System journal changed')
    profile=job['old']['profile']
    if profile and digest(read(archive/(profile['name']+'.json')))!=profile['sha256']:raise ValueError('Original saved profile backup changed')

def rewritten_service(code,proc=Path('/proc'),node=Path('/usr/bin/node'),uid=0):
    matches=[];code=Path(code).resolve(strict=True)
    node=Path(node).resolve(strict=True)
    for parent in (node,*node.parents):
        info=parent.lstat()
        if info.st_uid not in (0,uid) or info.st_mode&0o022 and not (stat.S_ISDIR(info.st_mode) and info.st_mode&stat.S_ISVTX):raise ValueError('Untrusted Node executable')
    for path in proc.iterdir():
        if not path.name.isdigit() or int(path.name)==os.getpid():continue
        try:
            args=[v for v in (path/'cmdline').read_bytes().split(b'\0') if v]
            if args!=[SERVICE.encode()]:continue
            info=path.stat();exe=(path/'exe').resolve(strict=True);cwd=(path/'cwd').resolve(strict=True)
            start=(path/'stat').read_text().rsplit(')',1)[1].split()[19]
        except (FileNotFoundError,ProcessLookupError):
            if path.exists():raise ValueError('System service identity is unavailable')
            continue
        if info.st_uid!=uid or exe!=node or cwd!=code:raise ValueError('Ambiguous System service process; keep state for inspection')
        matches.append((int(path.name),start))
    if len(matches)>1:raise ValueError('Multiple System service processes; keep state for inspection')
    return matches

def stop_old_service(code,cleanup,registration_sha,proc=Path('/proc')):
    # Cleanup has already authenticated and disabled its owned registration.
    if digest(read(code.parent/'registration.json'))!=registration_sha:raise ValueError('System registration proof changed')
    for pid,start in rewritten_service(code,proc):
        if (pid,start) not in rewritten_service(code,proc):raise ValueError('System service identity changed before stop')
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    cleanup.stop(code)
    end=time.monotonic()+5
    while rewritten_service(code,proc):
        if time.monotonic()>=end:raise ValueError('Original System service did not stop')
        time.sleep(.1)

def completed_bootstrap(lease,job):
    return (isinstance(lease,dict) and lease.get('schema')==1
            and re.fullmatch('[a-f0-9]{32}',lease.get('id','')) is not None
            and lease['id']!=job.get('id') and lease.get('terminal') is True
            and (lease.get('owner'),lease.get('journal'),lease.get('stage'))==('system-bootstrap','bootstrap.json','complete'))

def fresh_bootstrap_proof(setup,cleanup,manager,system,lease):
    from installation import terminal_install
    status=cleanup.operate('status',state=system)
    if (status.get('present') is not True or status.get('bootstrap_complete') is not True
            or status.get('edition')!='root' or status.get('ownership_verified') is not True
            or status.get('disabled') is not False):
        raise ValueError('Live Root supervisor bootstrap ownership could not be verified')
    records={name:read(system/(name+'.json')) for name in
             ('bootstrap','bootstrap-bundle','installed-terminal','installed-package','baseline')}
    bootstrap=json.loads(records['bootstrap'])
    if bootstrap.get('phase')!='complete' or bootstrap.get('edition')!='root' or not terminal_install(json.loads(records['installed-terminal']),APP):
        raise ValueError('Completed Root supervisor bootstrap evidence required')
    # old_proof authenticated the bootstrap binding, private code and exact
    # cache. Recheck the pin and every installed package file before admission.
    pin=json.loads(records['bootstrap-bundle'])['package']
    raw=read(system/'cache'/(pin['sha256']+'.ipk'),32*1024*1024)
    if len(raw)!=pin['size'] or digest(raw)!=pin['sha256']:
        raise ValueError('Live Root supervisor bootstrap cache changed')
    files=setup.package_files(raw)
    owner=manager.io.owner_identity(APP)
    expected={'schema':1,'package':dict(pin,version=owner['version'],local=True),
              'files':{name:digest(data) for name,data in files.items()}}
    if json.loads(records['installed-package'])!=expected:
        raise ValueError('Live Root supervisor bootstrap package proof changed')
    for name,data in files.items():
        if setup.installed_data(setup.INSTALLED/name,data,setup.INSTALLED,'root')!=data:
            raise ValueError('Live Root supervisor bootstrap payload changed')
    return {'lease':lease,'records':{name:digest(raw) for name,raw in records.items()}}

def completed_evidence(job,setup,manager,store,system,terminal_removal,fresh=False):
    root=Path(store.root)/('system-replacement-'+job['id']);directory(root)
    bundle=root/'bundle';manifest=setup.verify_bundle(bundle)
    if digest(read(bundle/'bundle.json'))!=job['bundle_sha256']:raise ValueError('Historical replacement bundle changed')
    if digest(read(root/'baseline/baseline.json'))!=job['baseline_sha256']:raise ValueError('Historical replacement baseline changed')
    # Historical Root bytes can have legitimately advanced since completion.
    # Authenticate that backup without comparing it to today's installed Root.
    setup.verify_baseline(root/'baseline',bundle)
    removal=job.get('removal',{})
    if removal.get('state')!='terminal' or not terminal_removal(removal.get('evidence'),APP):raise ValueError('Historical replacement removal proof required')
    raw=setup.safe(bundle/'system-updater.ipk')
    info=json.loads(setup.package_files(raw)['usr/palm/applications/'+APP+'/appinfo.json'])
    binding=json.loads(read(system/'bootstrap-bundle.json'))
    live_version=manager.io.owner_identity(APP)['version']
    if info.get('id')!=APP:raise ValueError('Historical replacement package identity changed')
    package={'sha256':digest(raw),'size':len(raw)}
    same_binding=binding['bundle']==manifest or binding['package']==package
    archive=Path(job['archive'])
    if not fresh or same_binding or os.path.lexists(archive):
        archive_proof(archive,job)
    if (not fresh or same_binding) and (info.get('version')!=live_version
            or binding['bundle']!=manifest or binding['package']!=package
            or original_code(system)!={n:h for n,h in manifest['files'].items() if n not in ('system-updater.ipk','setup-system-updater.py')}):raise ValueError('Historical replacement does not authenticate the live System Updater owner')
    return root/'completed-replacement.json'


def replace(bundle,setup,cleanup,manager,store,ownership,remove,terminal_removal,pending_journals,system=SYSTEM,source_sha='',refresh=None):
    bundle=Path(bundle);system=Path(system);manifest=setup.verify_bundle(bundle)
    if type(manifest.get('health_lock_wait_seconds')) is not int or manifest['health_lock_wait_seconds']!=10:raise ValueError('Fixed System ownership-wait bundle required')
    bundle_sha=digest(read(bundle/'bundle.json'))
    files=setup.package_files(setup.safe(bundle/'system-updater.ipk'))
    version=json.loads(files['usr/palm/applications/'+APP+'/appinfo.json'])
    target_version=version.get('version')
    if version.get('id')!=APP or target_version not in REPLACEMENT_SOURCES:raise ValueError('This replacement requires a supported System Updater bundle')
    job=store.read('system-replacement');lease=ownership.status();retired=None;bootstrap=None;bootstrap_admission=None
    reserved=(job is not None and lease and not lease['terminal'] and lease['owner']=='system-replace'
              and lease['journal']=='system-replacement.json' and lease['stage']=='reserved' and lease['id']!=job.get('id'))
    fresh=job is not None and completed_bootstrap(lease,job)
    historical=(job is not None and job.get('stage')=='complete'
                and (job.get('bundle_sha256')!=bundle_sha or fresh or reserved))
    if job is not None:
        if (job.get('schema')!=1 or not historical and (job.get('bundle_sha256')!=bundle_sha or job.get('source_sha256')!=source_sha) or not re.fullmatch('[a-f0-9]{32}',job.get('id',''))):raise ValueError('Resume replacement with the same verified installer bundle')
        if job.get('stage') not in STAGES or not isinstance(job.get('archive'),str) or not re.fullmatch(re.escape(str(system))+r'\.archive-[a-f0-9]{32}',job['archive']):raise ValueError('Unknown replacement journal stage or archive')
        if not isinstance(job.get('old'),dict) or set(job['old'])!={'code','transaction','profile','registration','home'} or set(job['old']['home'])!=set(map(str,HOME_FILES)):raise ValueError('Unknown original replacement proofs')
        if any(h is not None and not re.fullmatch('[a-f0-9]{64}',h) for h in job['old']['home'].values()) or not re.fullmatch('[a-f0-9]{64}',job['old']['transaction']) or not re.fullmatch('[a-f0-9]{64}',job['old']['registration']):raise ValueError('Unknown original replacement hashes')
        profile=job['old']['profile']
        if profile is not None and (set(profile)!={'name','sha256'} or not re.fullmatch('profile-[a-f0-9]{32}',profile['name']) or not re.fullmatch('[a-f0-9]{64}',profile['sha256'])):raise ValueError('Unknown saved profile proof')
        if job['stage']!='capture' and not re.fullmatch('[a-f0-9]{64}',job.get('baseline_sha256','')):raise ValueError('Missing captured baseline proof')
        if historical:
            if not re.fullmatch('[a-f0-9]{64}',job.get('bundle_sha256','')) or not re.fullmatch('[a-f0-9]{64}',job.get('source_sha256','')):raise ValueError('Unknown historical replacement pins')
            if not lease or not (lease['terminal'] and lease['stage']=='complete' or reserved):raise ValueError('Historical replacement requires terminal ownership')
            if fresh:
                bootstrap=lease
            elif reserved:
                historical_root=Path(store.root)/('system-replacement-'+job['id'])
                directory(historical_root)
                plan=type(store)(historical_root,uid=manager.io.uid).read('next-replacement')
                if plan is not None and not isinstance(plan,dict):
                    raise ValueError('Unknown historical retirement admission')
                if plan is not None and 'bootstrap' in plan:
                    evidence=plan['bootstrap']
                    bootstrap=evidence.get('lease') if isinstance(evidence,dict) else None
                    if not completed_bootstrap(bootstrap,job):
                        raise ValueError('Unknown reserved Root supervisor bootstrap admission')
            completed_evidence(job,setup,manager,store,system,terminal_removal,fresh=bootstrap is not None)
            retired=job;job=None
        else:
            if not lease or lease['id']!=job['id'] or lease['owner']!='system-replace' or lease['journal']!='system-replacement.json':raise ValueError('Replacement ownership changed')
            resume=job['id']
    if job is None:
        # Inspect every proof before reserving a new operation or disabling code.
        old=old_proof(manager,system)
        if manager.io.owner_identity(APP)['version'] not in REPLACEMENT_SOURCES[target_version]:raise ValueError('Installed System Updater is not supported by this replacement bundle')
        if target_version in ('1.2.10','1.2.11'):require_stock_home(manager)
        if bootstrap is None:cleanup.operate('status',state=system)
        resume=lease['id'] if lease and not lease['terminal'] and lease['owner']=='system-replace' and lease['journal']=='system-replacement.json' and lease['stage']=='reserved' else None
    def eligible():
        nonlocal bootstrap_admission
        pending_journals('system-bootstrap' if job is not None and job['stage']=='provision' else 'system-replace')
        if target_version in ('1.2.10','1.2.11') and (job is None or job['stage']=='capture'):
            require_stock_home(manager)
        if job is not None and job['stage']=='capture' and 'bootstrap_admission' in job:
            admission=job['bootstrap_admission']
            original_lease=admission.get('lease') if isinstance(admission,dict) else None
            if (not completed_bootstrap(original_lease,job) or old_proof(manager,system)!=job['old']
                    or fresh_bootstrap_proof(setup,cleanup,manager,system,original_lease)!=admission):
                raise ValueError('Reserved Root supervisor bootstrap evidence changed')
        if retired is not None:
            # Ownership invokes this under its product lock BEFORE reservation.
            # Bind a new admission even if power fails before a lease is written.
            if ownership.status()!=lease:raise ValueError('Replacement ownership changed before retirement admission')
            if store.read('system-replacement')!=retired or old_proof(manager,system)!=old:raise ValueError('Historical replacement or live state changed before retirement')
            target=completed_evidence(retired,setup,manager,store,system,terminal_removal,fresh=bootstrap is not None)
            raw=read(Path(store.root)/'system-replacement.json')
            plan={'schema':1,'bundle_sha256':bundle_sha,'source_sha256':source_sha,'journal_sha256':digest(raw),'old':old}
            if bootstrap is not None:
                bootstrap_admission=fresh_bootstrap_proof(setup,cleanup,manager,system,bootstrap)
                plan['bootstrap']=bootstrap_admission
            history=type(store)(target.parent,uid=manager.io.uid);previous=history.read('next-replacement')
            if previous is not None and previous!=plan:raise ValueError('Continue historical retirement with the same installer source and bundle')
            if os.path.lexists(target) and (previous is None or read(target)!=raw):raise ValueError('Historical replacement retirement collision')
            if previous is None:history.write('next-replacement',plan)
    with ownership.operation('system-replace','system-replacement.json',resume=resume,check=eligible) as record:
        if job is None:
            root=Path(store.root)/('system-replacement-'+record['id'])
            if root.exists():
                directory(root)
                if set(p.name for p in root.iterdir())-({'pending-replacement.json'} if retired is not None else set()):raise ValueError('Replacement journal missing for existing evidence')
            else:root.mkdir(mode=0o700)
            pending=type(store)(root,uid=manager.io.uid)
            job=pending.read('pending-replacement') if retired is not None else None
            if job is not None:
                fields={'schema','id','bundle_sha256','source_sha256','stage','archive','old'}
                if bootstrap_admission is not None:fields.add('bootstrap_admission')
                if (set(job)!=fields or job.get('bootstrap_admission')!=bootstrap_admission
                        or job['schema']!=1 or job['id']!=record['id'] or job['bundle_sha256']!=bundle_sha or job['source_sha256']!=source_sha
                        or job['stage']!='capture' or job['old']!=old or not re.fullmatch(re.escape(str(system))+r'\.archive-[a-f0-9]{32}',job['archive'])):raise ValueError('Pending historical replacement proof changed')
            else:
                job={'schema':1,'id':record['id'],'bundle_sha256':bundle_sha,'source_sha256':source_sha,'stage':'capture','archive':str(system)+'.archive-'+uuid.uuid4().hex,'old':old}
                if bootstrap_admission is not None:job['bootstrap_admission']=bootstrap_admission
                if retired is not None:pending.write('pending-replacement',job)
            if retired is not None:
                # Preserve exact old bytes durably before atomically replacing
                # the active journal; it never disappears between operations.
                target=completed_evidence(retired,setup,manager,store,system,terminal_removal,fresh=bootstrap is not None)
                raw=read(Path(store.root)/'system-replacement.json')
                if os.path.lexists(target):
                    if read(target)!=raw:raise ValueError('Historical replacement retirement collision')
                else:
                    fd,name=tempfile.mkstemp(prefix='.completed-',dir=target.parent)
                    try:
                        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                        os.rename(name,target)
                    finally:
                        if os.path.lexists(name):os.unlink(name)
                fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(fd)
                finally:os.close(fd)
            store.write('system-replacement',job)
        root=Path(store.root)/('system-replacement-'+job['id']);directory(root);baseline=root/'baseline';saved_bundle=root/'bundle'
        def save(stage):job['stage']=stage;store.write('system-replacement',job);ownership.stage(record,stage,terminal=False)
        if not saved_bundle.exists():
            pending_bundle=root/('bundle-'+uuid.uuid4().hex);pending_bundle.mkdir(mode=0o700)
            for name in (*manifest['files'],'bundle.json'):
                target=pending_bundle/name;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True);target.write_bytes(setup.safe(bundle/name));target.chmod(0o600)
            setup.verify_bundle(pending_bundle);sync_tree(pending_bundle);pending_bundle.rename(saved_bundle);sync_tree(saved_bundle)
        if digest(read(saved_bundle/'bundle.json'))!=bundle_sha:raise ValueError('Replacement bundle changed')
        setup.verify_bundle(saved_bundle)
        archive=Path(job['archive'])
        if job['stage'] in ('provision','verify','complete'):
            archive_proof(archive,job)
        if preserved_home()!=job['old']['home']:raise ValueError('Root Home preference changed; keep replacement evidence')
        if job['stage']=='capture':
            if old_proof(manager,system)!=job['old']:raise ValueError('Original System or Root state changed before baseline capture')
            if not baseline.exists():
                pending=root/('capture-'+uuid.uuid4().hex);setup.snapshot(saved_bundle,'root',pending);setup.verify_baseline(pending,saved_bundle);sync_tree(pending);pending.rename(baseline);sync_tree(baseline)
            job['baseline_sha256']=digest(read(baseline/'baseline.json'));save('disable')
        if digest(read(baseline/'baseline.json'))!=job['baseline_sha256']:raise ValueError('Captured baseline changed')
        baseline_readback(setup,baseline,saved_bundle)
        if job['stage'] in ('disable','remove','archive') and system.exists():
            if original_code(system)!=job['old']['code'] or digest(read(system/'registration.json'))!=job['old']['registration']:raise ValueError('Original System proofs changed before removal')
            current_tx=json.loads(read(system/'transaction.json')) if os.path.lexists(system/'transaction.json') else None
            if digest(encode(current_tx))!=job['old']['transaction']:raise ValueError('Original System journal changed before removal')
        def stop(code):stop_old_service(code,cleanup,job['old']['registration'])
        if job['stage']=='disable':
            result=cleanup.operate('disable',state=system,destination=job['archive'],stop_processes=stop)
            if result.get('disabled') is not True:raise ValueError('Original System disable was not confirmed')
            save('remove')
        if job['stage']=='remove':
            remove_system(remove,terminal_removal,setup.INSTALLED,store,job);save('archive')
        if job['stage']=='archive':
            supervisor_absent(setup.INSTALLED)
            if system.exists():
                result=cleanup.operate('archive',state=system,destination=job['archive'],stop_processes=stop)
                if result.get('removed') is not True:raise ValueError('Original System archive was not confirmed')
            archive_proof(archive,job)
            save('provision')
        if job['stage']=='provision':
            if not system.exists():
                supervisor_absent(setup.INSTALLED);result=setup.provision(saved_bundle,baseline,refresh=refresh)
            else:result=setup.resume(saved_bundle,refresh=refresh)
            if result.get('installed') is not True:raise ValueError('Fixed System provisioning was not confirmed')
            save('verify')
        if job['stage'] not in ('verify','complete'):raise ValueError('Unknown replacement stage')
        baseline_readback(setup,baseline,saved_bundle)
        if preserved_home()!=job['old']['home']:raise ValueError('Root Home preference changed during replacement; retain evidence')
        archive_proof(archive,job)
        if original_code(system)!={n:h for n,h in manifest['files'].items() if n not in ('system-updater.ipk','setup-system-updater.py')}:raise ValueError('Fixed supervisor code/pins mismatch')
        new=type(manager.io)(type(manager.store)(system,uid=manager.io.uid),code=system/'code');new.integrity(enforce=False);new.require_components();new._root_integrity()
        if new.owner_identity(APP)['version']!=target_version:raise ValueError('Fixed System package readback mismatch')
        job['stage']='complete';store.write('system-replacement',job);ownership.stage(record,'complete',terminal=True)
        return {'installed':True,'version':target_version,'root_unchanged':True,'home_unchanged':True,'saved_profile_unchanged':True,'profile_storage_untouched':True,'archive':job['archive']}

def entry():
    if os.geteuid()!=0:raise PermissionError('Root replacement required')
    payload=json.loads(zlib.decompress(base64.b85decode(PAYLOAD)))
    with tempfile.TemporaryDirectory(prefix='cytv-system-replacement-') as temporary:
        bundle=Path(temporary)
        for name,encoded in payload.items():
            relative=PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or str(relative)!=name:raise ValueError('Unsafe replacement payload')
            target=bundle/name;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True);target.write_bytes(base64.b64decode(encoded));target.chmod(0o600)
        metadata=json.loads(read(bundle/'bundle.json'))
        for name,expected in metadata['files'].items():
            if digest(read(bundle/name))!=expected:raise ValueError('Replacement payload integrity mismatch')
        load_sources(bundle,metadata['files'])
        from system_updater.core import Manager
        from system_updater.device import Device
        from system_updater.support.store import Store
        from installation import Ownership,terminal_removal,pending_journals
        from observed_install import remove
        setup=types.ModuleType('verified_system_setup');exec(compile(read(bundle/'setup-system-updater.py'),str(bundle/'setup-system-updater.py'),'exec'),setup.__dict__)
        cleanup=types.ModuleType('verified_system_cleanup');exec(compile(CLEANUP_SOURCE,'<verified System cleanup>','exec'),cleanup.__dict__)
        def refresh():
            ctl=next((p for p in ('/usr/bin/ls-control','/usr/sbin/ls-control') if Path(p).is_file()),None)
            if not ctl:raise ValueError('LS2 scanner unavailable')
            subprocess.run([ctl,'scan-services'],check=True,timeout=15,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        operate=cleanup.operate
        cleanup.operate=lambda action,**kw:operate(action,refresh=refresh,**kw)
        old_store=Store.__new__(Store);old_store.root=str(SYSTEM);old_store.uid=0;device=Device(old_store,code=SYSTEM/'code')
        try:
            result=replace(bundle,setup,cleanup,Manager(old_store,device),Store('/var/lib/clean-your-tv-installation'),Ownership(),remove,terminal_removal,pending_journals,source_sha=SOURCE_SHA,refresh=refresh)
        except StockHomeRequired:
            result={'reason':'stock-home-required'}
        print(json.dumps(result),flush=True)
'''


def program(bundle):
    from .system_updater_remove import SCRIPT as cleanup
    bundle=Path(bundle).resolve();metadata=(bundle/'bundle.json').read_bytes();value=json.loads(metadata)
    if value.get('schema')!=1 or value.get('supervisor')!=1 or type(value.get('health_lock_wait_seconds')) is not int or value['health_lock_wait_seconds']!=10 or not isinstance(value.get('files'),dict) or not {'system-updater.ipk','setup-system-updater.py'}<=set(value['files']):raise ValueError('Invalid System replacement bundle')
    files={'bundle.json':base64.b64encode(metadata).decode()}
    for name,expected in value['files'].items():
        from .package import safe_name
        path=bundle/safe_name(name)
        if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Indirect replacement bundle source')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Replacement source hash mismatch')
        files[name]=base64.b64encode(raw).decode()
    support=support_source();source_sha=hashlib.sha256((support+SCRIPT+cleanup).encode()).hexdigest()
    payload=base64.b85encode(zlib.compress(json.dumps(files).encode(),9)).decode()
    return support+'\nCLEANUP_SOURCE='+repr(cleanup)+'\nPAYLOAD='+repr(payload)+'\nSOURCE_SHA='+repr(source_sha)+'\n'+SCRIPT+'\nentry()\n'
