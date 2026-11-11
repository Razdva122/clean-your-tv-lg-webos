"""Explicit streamed readiness recovery; retained supervisor code stays immutable."""
from .rollback_recovery_sources import SCRIPT as SOURCE_CHECKS


SCRIPT = SOURCE_CHECKS + r'''
STATE=Path('/var/lib/clean-your-tv-system-updater')
ERROR='Launcher profile readiness timed out'

def original_code(state):
    binding=json.loads(read(state/'bootstrap-bundle.json'));receipt=json.loads(read(state/'infrastructure.json'))
    files=binding['bundle']['files'];pin=binding['package']
    if binding.get('schema')!=1 or binding['bundle'].get('schema')!=1 or binding['bundle'].get('supervisor')!=1:raise ValueError('Unknown original supervisor binding')
    expected={n:h for n,h in files.items() if n not in ('system-updater.ipk','setup-system-updater.py')}
    if receipt!={'schema':1,'code':expected} or not {'installation.py','package_identity.py','system_updater/core.py','system_updater/device.py','system_updater/support/store.py'}<=set(expected):raise ValueError('Original supervisor inventory mismatch')
    for name,sha in expected.items():
        path=PurePosixPath(name)
        if path.is_absolute() or str(path)!=name or '..' in path.parts or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Unsafe original supervisor inventory')
        if digest(read(state/'code'/name))!=sha:raise ValueError('Original supervisor code changed')
    if not re.fullmatch('[a-f0-9]{64}',pin['sha256']) or files['system-updater.ipk']!=pin['sha256']:raise ValueError('Original supervisor package pin mismatch')
    raw=read(state/'cache'/(pin['sha256']+'.ipk'),32*1024*1024)
    if digest(raw)!=pin['sha256'] or len(raw)!=pin['size']:raise ValueError('Original supervisor package changed')
    return expected

def immutable(tx):
    return {k:v for k,v in tx.items() if k not in ('phase','updated','error','launched','deadline','homeResume','homeResumePhase')}

def validate(manager,device,tx):
    if tx is None or tx['edition']!='root' or tx['rollbackAttempted'] is not True:raise ValueError('Completed Root rollback required')
    if tx.get('error')!=ERROR:raise ValueError('Only rollback readiness timeout can be recovered')
    if not all(c['phase']=='rolled-back' for c in tx['components']):raise ValueError('Rollback components incomplete')
    for index,c in enumerate(tx['components']):
        for leg,release in [('installEvidence','candidate'),('rollbackEvidence','prior')]:
            e=c[leg];selected=tx[release]['components'][index];app=selected.get('application')
            if e['intent'] is not True or not manager._success(e) or not isinstance(e['submitted'],dict) or e['submitted'].get('sha256')!=selected['sha256']:raise ValueError('Unknown or incomplete installer outcome')
            terminal=e['terminal']
            if c['name']=='root-infrastructure':
                if e['submitted'].get('component')!='root-infrastructure' or terminal.get('sha256')!=selected['sha256']:raise ValueError('Infrastructure completion mismatch')
            else:
                event=terminal.get('event',{});details=event.get('details',{})
                if (e['submitted'].get('application')!=app or event.get('id')!=app or type(event.get('statusValue')) is not int or event['statusValue']!=30 or event.get('returnValue') is False or 'errorCode' in event or details.get('packageId')!=app or 'errorCode' in details or not re.fullmatch(r'com.webos.lunasend-[0-9]+',details.get('client','')) or not re.fullmatch(r'/var/lib/clean-your-tv-installer/cytv-root-install-[A-Za-z0-9_-]+/package.ipk',details.get('ipkFile',''))):raise ValueError('Installer terminal binding mismatch')
    manager._profile(tx)
    device.integrity(enforce=False)
    from package_identity import TransitionUnknown
    try:device.require_components()
    except TransitionUnknown:
        # Original owners_present checks every owner before deferring a touched
        # transition; only this exact authenticated recovery state is eligible.
        if tx['phase']!='recovery-required':raise
    for path in device.legacy_states:
        if not os.path.lexists(path):continue
        value=json.loads(read(path));phase=value.get('phase',value.get('status'))
        if phase not in ('complete','completed','rolled-back','aborted','idle'):raise ValueError('Legacy updater transaction requires recovery')
        if path==device.root_updater/'transaction.json' and value.get('homeResumePhase')!=phase:raise ValueError('Legacy Root Home recovery pending')
    device._root_integrity()
    device._verify_release(tx['prior'],'root')
    if not manager._verify_set(tx['prior']):raise ValueError('Restored components do not match original rollback')

def check_audit(audit,tx,lease,store):
    if (audit.get('schema')!=1 or not re.fullmatch('[a-f0-9]{32}',audit.get('id','')) or audit.get('lease')!=lease['id'] or digest(encode(audit['original']))!=audit.get('original_sha256') or immutable(tx)!=immutable(audit['original']) or audit.get('state') not in ('prepared','waiting','complete','failed')):raise ValueError('Recovery attempt cannot be replaced')
    original=audit['original'];armed=audit['armed'];now=armed.get('launched')
    if original.get('phase')!='recovery-required' or original.get('error')!=ERROR or type(original.get('launched')) not in (int,float) or not math.isfinite(original['launched']) or original.get('deadline')!=original['launched']+120 or audit.get('original_file_sha256')!=audit['original_sha256']:raise ValueError('Original recovery audit changed')
    if (type(now) not in (int,float) or not math.isfinite(now) or now<original['deadline'] or armed.get('deadline')!=now+120):raise ValueError('Invalid recovery attempt deadline')
    updated=armed.get('updated')
    if type(updated) not in (int,float) or not math.isfinite(updated) or not now<=updated<armed['deadline']:raise ValueError('Invalid recovery arm timestamp')
    expected=copy.deepcopy(original);expected.update(phase='verifying-rollback',launched=now,deadline=now+120,updated=updated)
    if armed!=expected:raise ValueError('Recovery attempt journal changed')
    previous=audit.get('previous')
    if previous is not None:
        if set(previous)!={'name','sha256'} or not re.fullmatch('readiness-recovery-history-[a-f0-9]{32}',previous['name']):raise ValueError('Invalid previous recovery archive')
        history=store.read(previous['name'])
        if not history or history.get('schema')!=1 or history.get('sha256')!=previous['sha256'] or digest(encode(history['audit']))!=previous['sha256'] or history['audit'].get('id')!=previous['name'].removeprefix('readiness-recovery-history-'):raise ValueError('Previous recovery archive changed')

def recover(manager,device,store,ownership,mutation,launch,sleep=time.sleep,new_attempt=False):
    if type(new_attempt) is not bool:raise ValueError('Explicit recovery attempt flag must be boolean')
    fd=os.open(Path(store.root)/'daemon.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or info.st_mode&0o022:raise ValueError('Unsafe supervisor worker lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Never reserve a new lease, including when another owner is terminal.
        lease=ownership.status()
        if not lease or lease['owner']!='system-update' or lease['journal']!='transaction.json':raise ValueError('Matching System update ownership required')
        tx=manager._load();validate(manager,device,tx);name='readiness-recovery-'+tx['id'];audit=store.read(name)
        if audit is not None:
            check_audit(audit,tx,lease,store)
            if audit['state']=='complete':
                if not lease['terminal'] or tx['phase']!='rolled-back' or tx.get('homeResumePhase')!='rolled-back' or tx.get('launched')!=audit['armed']['launched'] or tx.get('deadline')!=audit['armed']['deadline']:raise ValueError('Completed recovery evidence changed')
                return tx
        elif lease['terminal']:raise ValueError('Nonterminal matching System update ownership required')
        rollover=audit is not None and new_attempt and manager._now()>=audit['armed']['deadline']
        if audit is not None and audit['state']=='failed' and not rollover:raise ValueError('Failed recovery attempt requires explicit retry after its deadline')
        with mutation() as record:
            if ownership.status()['id']!=lease['id']:raise ValueError('System update ownership changed')
            previous=None
            if rollover:
                # No nested store lock: the original Manager owns its short
                # journal lock and must record the real expired-window result.
                tx=manager._load();validate(manager,device,tx)
                current_audit=store.read(name)
                if current_audit!=audit:raise ValueError('Recovery audit changed before explicit retry')
                check_audit(audit,tx,lease,store)
                if manager._now()<audit['armed']['deadline'] or store.read('healthy-rollback-'+tx['id']) is not None:raise ValueError('Expired recovery without health required')
                before_arm=audit['state']=='prepared' and tx==audit['original']
                if tx['phase']=='verifying-rollback':
                    if tx!=audit['armed']:raise ValueError('Recovery journal changed before explicit retry')
                    manager.run();tx=manager._load()
                if tx['phase']!='recovery-required' or not before_arm and (tx.get('launched'),tx.get('deadline'))!=(audit['armed']['launched'],audit['armed']['deadline']):raise ValueError('Original recovery timeout not confirmed')
                validate(manager,device,tx)
                if store.read('healthy-rollback-'+tx['id']) is not None:raise ValueError('Rollback health appeared before explicit retry')
                history_name='readiness-recovery-history-'+audit['id']
                history={'schema':1,'audit':copy.deepcopy(audit),'sha256':digest(encode(audit))}
                existing=store.read(history_name)
                if existing is not None and existing!=history:raise ValueError('Recovery archive already contains different evidence')
                if existing is None:store.write(history_name,history)
                previous={'name':history_name,'sha256':history['sha256']};audit=None
            with store.lock():
                tx=manager._load();validate(manager,device,tx)
                if audit is None:
                    now=manager._now()
                    if tx['phase']!='recovery-required' or type(tx.get('launched')) not in (int,float) or tx.get('deadline')!=tx['launched']+120 or now<tx['deadline']:raise ValueError('Expired rollback readiness failure required')
                    if store.read('healthy-rollback-'+tx['id']) is not None:raise ValueError('Existing rollback health receipt must be inspected')
                    original=copy.deepcopy(tx);armed=copy.deepcopy(tx);armed.update(phase='verifying-rollback',launched=now,deadline=now+120,updated=now)
                    audit={'schema':1,'id':uuid.uuid4().hex,'lease':lease['id'],'state':'prepared','original':original,'original_sha256':digest(encode(original)),'original_file_sha256':digest(read(Path(store.root)/'transaction.json')),'armed':armed}
                    if previous is not None:audit['previous']=previous
                    store.write(name,audit)
                else:check_audit(audit,tx,lease,store)
                armed=audit['armed']
                if tx['phase']=='rolled-back':
                    if tx.get('launched')!=armed['launched'] or tx.get('deadline')!=armed['deadline']:raise ValueError('Recovery deadline changed')
                elif tx==audit['original'] and audit['state']=='prepared':
                    if not armed['launched']<=manager._now()<armed['deadline']:raise ValueError('Recovery attempt expired; keep evidence')
                    store.write('transaction',armed);tx=armed
                    device.require_components()
                elif tx!=armed:raise ValueError('Recovery journal changed')
                if tx['phase']!='rolled-back':
                    audit['state']='waiting';store.write(name,audit);ownership.stage(record,'verifying-rollback',terminal=False)
        clock_failed=False
        if tx['phase']!='rolled-back':
            now=manager._now();stop=time.monotonic()+max(0,min(120,armed['deadline']-now))
            if armed['launched']<=now<armed['deadline'] and store.read('healthy-rollback-'+tx['id']) is None:
                # No ownership lock here: old Root's one-shot authenticated healthy
                # must be accepted, while daemon.lock excludes its spawned worker.
                try:launch()
                except Exception as error:
                    with mutation() as record:
                        current=manager._load()
                        if ownership.status()['id']!=lease['id'] or current!=armed:raise ValueError('Recovery journal changed during launcher failure')
                        audit.update(state='failed',failure='launcher-error',launcher_error=str(error)[:512]);store.write(name,audit)
                        ownership.stage(record,current['phase'],terminal=False)
                    raise ValueError('Root launcher restart failed; recovery evidence retained') from error
                previous=now
                while store.read('healthy-rollback-'+tx['id']) is None:
                    now=manager._now()
                    if now<previous or now<armed['launched']:clock_failed=True;break
                    if now>=armed['deadline'] or time.monotonic()>=stop:break
                    previous=now;sleep(.1)
            else:clock_failed=now<armed['launched']
        # healthy stores its receipt before releasing ownership. Retry only that
        # short contention, without creating another readiness window.
        end=time.monotonic()+10
        while True:
            try:
                with mutation() as record:
                    if ownership.status()['id']!=lease['id']:raise ValueError('System update ownership changed')
                    current=manager._load()
                    if immutable(current)!=immutable(audit['original']) or current.get('launched')!=armed['launched'] or current.get('deadline')!=armed['deadline']:raise ValueError('Recovery journal changed while waiting')
                    validate(manager,device,current)
                    if current['phase']=='verifying-rollback':
                        receipt=store.read('healthy-rollback-'+current['id'])
                        if clock_failed or receipt is None:
                            result=manager._save(current,'recovery-required',ERROR);audit['state']='failed';audit['failure']='clock-reversed' if clock_failed else 'readiness-timeout';store.write(name,audit);ownership.stage(record,'recovery-required',terminal=False);return result
                        if receipt.get('transaction')!=current['id'] or receipt.get('version')!=manager._launcher_version(current,True) or type(receipt.get('at')) not in (int,float) or not armed['launched']<=receipt['at']<armed['deadline']:raise ValueError('Invalid fresh rollback readiness receipt')
                        current=manager.run()
                    if current['phase']!='rolled-back':raise ValueError('Original rollback completion not confirmed')
                    if current.get('homeResumePhase')!='rolled-back':
                        current['homeResume']=device.finish(current);current['homeResumePhase']='rolled-back';manager._save(current)
                    ownership.stage(record,'rolled-back',terminal=True);audit['state']='complete';store.write(name,audit);return current
            except RuntimeError as error:
                if str(error)!='installation_operation_retained' or time.monotonic()>=end:raise
                sleep(.1)
    finally:os.close(fd)

def restart_launcher(device):
    try:reply=device.rpc('luna://com.webos.applicationManager/closeByAppId',{'id':'com.cleanyourtv.root.preview'})
    except Exception:raise ValueError('Root closeByAppId rejected') from None
    if not isinstance(reply,dict) or reply.get('returnValue') is not True:raise ValueError('Root closeByAppId rejected')
    try:reply=device.launch('root')
    except Exception:raise ValueError('Root launcher relaunch rejected') from None
    if not isinstance(reply,dict) or reply.get('returnValue') is not True:raise ValueError('Root launcher relaunch rejected')

def entry(new_attempt=False):
    if os.geteuid()!=0:raise PermissionError('Root recovery required')
    files=original_code(STATE)
    load_sources(STATE/'code',files)
    from system_updater.core import Manager
    from system_updater.device import Device
    from system_updater.support.store import Store
    from installation import Ownership,pending_journals
    store=Store(STATE);device=Device(store);manager=Manager(store,device);ownership=Ownership()
    lease=ownership.status()
    if not lease or lease['owner']!='system-update' or lease['journal']!='transaction.json':raise ValueError('Matching System update ownership required')
    def mutation():return ownership.operation('system-update','transaction.json',resume=lease['id'],check=lambda:pending_journals('system-update'))
    def launch():restart_launcher(device)
    print(json.dumps({'returnValue':True,'result':recover(manager,device,store,ownership,mutation,launch,new_attempt=new_attempt)}),flush=True)
'''


def program(new_attempt=False):
    if type(new_attempt) is not bool:raise ValueError('Explicit recovery attempt flag must be boolean')
    return SCRIPT+'\nentry(new_attempt='+repr(new_attempt)+')\n'
