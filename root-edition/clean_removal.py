"""Removal adapters for the existing product coordinator; retained code is data.

All methods run under Ownership.removal. Package terminal authority remains in
observed_install; this module never infers an old install outcome from absence.
"""
from contextlib import contextmanager, ExitStack
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess

from updater.store import Store
from updater.package import safe_bytes
from installation import _optional_record, terminal_removal

APPS = ('com.cleanyourtv.root.preview', 'com.cleanyourtv.root.updater',
        'com.cleanyourtv.system.updater', 'com.cleanyourtv.updater',
        'com.local.nativehome', 'com.gathin.tvhome')
# Presence (including dangling links) requires the original routing backend.
ROUTING_EVIDENCE=('profile-trial.json','persistent-intent.json','persistent-binding.json','boot-continuation.json',
                  'profile-candidate.stage','home-backend.json','c1-gate','c1-keyfilter')

PRE_ACTIVATION=('prepared','install-submitting','install-accepted','install-observed','payload-verified','personalization-complete')+tuple(
    'provision-'+step+'-'+phase for step in ('apply','resume_pending','refresh','finalize') for phase in ('starting','complete'))


# Diagnostic context only; never used for recovery admission or progress.
@contextmanager
def cleanup_step(name):
    try:
        yield
    except Exception as error:
        error.cleanup_step=name
        raise


def boot_format(value):
    if not isinstance(value,str):return None
    match=re.fullmatch(r'([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})(:session-[a-f0-9]{32})?',value)
    if not match or match[1]=='00000000-0000-0000-0000-000000000000':return None
    return 'session' if match[2] else 'kernel'


def verified_restart(record):
    baseline=record.get('cleanup_boot_id');verified=record.get('cleanup_verified_boot_id')
    return bool(boot_format(baseline) and boot_format(baseline)==boot_format(verified) and baseline!=verified)



def activities(device):
    """Read the complete activity inventory on both retail API generations."""
    payload={'details':True,'subscribers':True,'current':False,'internal':False}
    try:
        reply=device.rpc('com.palm.activitymanager/list',payload)
    except (RuntimeError,TimeoutError) as error:
        if getattr(error,'luna',{}).get('reason') not in ('timeout','service-missing','method-missing','negative-reply'):
            raise
        reply=device.rpc('com.palm.activitymanager/getActivityInfo',payload)
    rows=reply.get('activities') if isinstance(reply,dict) else None
    if (not isinstance(reply,dict) or reply.get('returnValue') is not True or not isinstance(rows,list)
            or any(not isinstance(row,dict) or ('callback' in row and not isinstance(row['callback'],dict)) for row in rows)):
        raise ValueError('Activity inventory could not be verified')
    return rows


def runtime_restore(payload, uid=0):
    """Called in an isolated interpreter with only the current verified bundle.

    Native restore reads its original inverse/inode journal; the executable is
    selected from the current bundle, never a retained file or volatile copy.
    """
    import sys
    import deploy
    payload=Path(payload)
    manifest=deploy.verify_bundle(payload,allow_experimental=True)
    sys.path.insert(0,str(payload/'runtime'))
    import cli
    backend=cli.gate_backend()
    if backend is not None:
        selected=backend.selection(backend.STATE,uid)
        name='c1-home-gate'
        if selected.get('routing')=='compositor-keyfilter-v1':
            import c1_keyfilter
            backend=c1_keyfilter;name='c1-keyfilter-guard'
        path=payload/'runtime'/name
        raw=deploy.checked_file(payload,'runtime/'+name)
        if hashlib.sha256(raw).hexdigest()!=manifest['files'].get('runtime/'+name):
            raise ValueError('current_native_recovery_unverified')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            info=os.fstat(fd)
            if info.st_uid!=uid or info.st_nlink!=1 or not stat.S_ISREG(info.st_mode):raise ValueError('unsafe_current_native_recovery')
            os.fchmod(fd,0o700)
        finally:os.close(fd)
        backend.binary=lambda root,uid:path
    return {'returnValue':True,'result':cli.main('restore')}


def compositor_stock(payload):
    """Fresh stock observation from current verified support, never old code."""
    import sys
    import deploy
    payload=Path(payload)
    deploy.verify_bundle(payload,allow_experimental=True)
    release=json.loads(deploy.checked_file(payload,'release.json'))
    if release.get('routing')!='compositor-keyfilter-v1':
        raise ValueError('current_compositor_support_required')
    sys.path.insert(0,str(payload/'runtime'))
    import c1_keyfilter
    observed=c1_keyfilter.probe()
    return {'mode':'stock-compositor','target':{k:observed['target'][k] for k in ('dev','ino','size')},
            'target_sha256':observed['target_sha256']}


@contextmanager
def locks(roots, uid):
    """Keep original component lock inodes throughout restoration and cleanup."""
    with ExitStack() as stack:
        for index, root in enumerate(roots):
            if not os.path.lexists(root): continue
            store=Store(root,uid=uid)
            directory=store._directory();stack.callback(os.close,directory)
            for name in (('provision.lock',) if index==0 else ('daemon.lock','worker.lock')):
                fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=directory)
                stack.callback(os.close,fd);store._check(os.fstat(fd))
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def retire_tree(path, allowed, keep=(), uid=0, parent_uid=None):
    """Confined, pinned unlink of classified owned data; no following links.

    Validate the entire inventory before deleting the first member. Missing
    members support a retry after power loss. Changes to owned preferences do
    not need installation-continuation hashes. Foreign shared paths never enter.
    """
    path=Path(path)
    if not os.path.lexists(path):return 0
    store=Store.__new__(Store);store.root=str(path);store.uid=uid
    with ExitStack() as stack:
        if parent_uid is None:
            root=store._directory()
        else:
            parent=Store.__new__(Store);parent.root=str(path.parent);parent.uid=parent_uid
            fd=parent._directory();stack.callback(os.close,fd)
            root=os.open(path.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            info=os.fstat(root)
            if info.st_uid!=uid or info.st_mode&0o022:
                os.close(root);raise ValueError('unsafe_private_member')
        stack.callback(os.close,root)
        plan=[]
        def scan(fd, prefix=''):
            for name in sorted(os.listdir(fd)):
                relative=prefix+name
                if not prefix and name in keep: continue
                if not prefix and name not in allowed: raise ValueError('unclassified_private_member')
                info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if info.st_uid!=uid or (not stat.S_ISLNK(info.st_mode) and info.st_mode&0o022): raise ValueError('unsafe_private_member')
                if stat.S_ISDIR(info.st_mode):
                    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                    stack.callback(os.close,child)
                    if (os.fstat(child).st_dev,os.fstat(child).st_ino)!=(info.st_dev,info.st_ino):
                        raise ValueError('private_member_changed')
                    scan(child,relative+'/');plan.append((fd,name,info,True))
                elif stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode) and info.st_nlink==1:
                    plan.append((fd,name,info,False))
                else: raise ValueError('unsafe_private_member')
        scan(root)
        for fd,name,info,directory in plan:
            current=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if (current.st_dev,current.st_ino,current.st_mode,current.st_uid,current.st_nlink)!=(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_nlink):
                raise ValueError('private_member_changed')
        for fd,name,info,directory in plan:
            current=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if (current.st_dev,current.st_ino)!=(info.st_dev,info.st_ino):raise ValueError('private_member_changed')
            (os.rmdir if directory else os.unlink)(name,dir_fd=fd);os.fsync(fd)
        if set(os.listdir(root))-set(keep):raise ValueError('private_members_remain')
    return len(plan)


def routes(device, record=None):
    if record is not None and device.routing_untouched(record):
        return {'mode':'never-applied'}
    if record is not None and device.compositor_stock_eligible(record):
        return device.compositor_stock(record)
    settings=device.rpc('com.webos.settingsservice/getSystemSettings',{'category':'general','keys':['defaultApps']})
    home=settings.get('settings',{}).get('defaultApps',{}).get('home')
    if settings.get('returnValue') is not True or not isinstance(home,str) or not home or home in APPS:
        raise ValueError('route_readback_unverified')
    never=(record or {}).get('routing_never_applied') is True
    try:reply=device.rpc('com.webos.service.systemprofile/getProfiles',{'names':['defaultApps','idleApp'],'subscribe':False})
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.SubprocessError) as error:
        if never:return {'mode':'never-applied','home':home}
        # Only the firmware's exact missing-service reply admits stock-only
        # verification. A timeout/ACL failure cannot select another backend.
        stock={'mode':'stock-settings','home':'com.webos.app.home'}
        if (getattr(error,'systemprofile_missing',False) is True and home==stock['home']
                and (record or {}).get('profileless_cleanup_eligible') is True
                and (record.get('routes') is None or record['routes']==stock)):
            return stock
        raise
    if reply.get('returnValue') is not True:
        if never:return {'mode':'never-applied','home':home}
        raise ValueError('route_readback_unverified')
    profiles=reply['profiles']
    result=[home,profiles['defaultApps']['categories']['home'],profiles['idleApp']['appId']]
    if any(not isinstance(item,str) or not item or item in APPS for item in result):
        raise ValueError('owned_route_remains')
    if never and isinstance((record or {}).get('routes'),dict):return {'mode':'never-applied','home':home}
    return result


def restore_registrations(state, app, base, uid=0):
    """Restore an interrupted bootstrap's fixed original/installed snapshot."""
    from cancel_provision import write_registration
    state,base=Path(state),Path(base)
    store=Store(state,uid=uid)
    saved=_optional_record(store,'registration')
    paths={str(base/folder/(app+'.service'+suffix)) for folder,suffix in (
        ('services.d','.service'),('roles.d','.service.json'),
        ('client-permissions.d','.service.json'),('api-permissions.d','.api.json'))}
    if saved is None:
        # No snapshot means bootstrap never replaced registrations. Reject any
        # private runner reference; SDK-generated bytes stay with package remove.
        for name in paths:
            if os.path.lexists(name) and str(state).encode() in safe_bytes(name,uid=uid):
                raise ValueError('unowned_private_registration')
        return
    if not isinstance(saved,dict) or set(saved.get('files',{}))!=paths:
        raise ValueError('registration_ownership_conflict')
    plan=[]
    for name in sorted(paths):
        entry=saved['files'][name]
        if (not isinstance(entry,dict) or set(entry) not in ({'original','installed'},{'original','installed','mode','uid','gid'})
                or not all(isinstance(entry[k],str) for k in ('original','installed'))):
            raise ValueError('registration_ownership_conflict')
        path=Path(name);raw=safe_bytes(path,uid=uid);info=path.lstat()
        if raw not in (entry['original'].encode(),entry['installed'].encode()):
            raise ValueError('registration_ownership_conflict')
        metadata=dict(mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid)
        if 'mode' in entry:
            recorded={key:entry[key] for key in ('mode','uid','gid')}
            if (any(type(value) is not int or value<0 for value in recorded.values())
                    or recorded['uid']!=uid or recorded['mode']>0o777 or recorded['mode']&0o022
                    or recorded!=metadata):raise ValueError('registration_metadata_conflict')
            metadata=recorded
        # Legacy snapshots prove bytes only. Preserve CURRENT metadata without
        # claiming it was original; these dedicated app registrations are next
        # removed by their package, and final absence is mandatory.
        plan.append((path,dict(original=entry['original'],**metadata)))
    for path,entry in plan:write_registration(path,entry)
    for path,entry in plan:
        if safe_bytes(path,uid=uid)!=entry['original'].encode():raise ValueError('registration_restore_unverified')


def validate_restored_root_api(files,base,root_updater,uid=0):
    """Authenticate the final SDK API state in the two original owner snapshots."""
    from cleanup_system_updater import read
    api=base/'api-permissions.d/com.cleanyourtv.root.updater.service.api.json'
    raw=read(api)
    registration=Path(root_updater)/'registration.json';proof=files.get(str(registration))
    if not isinstance(proof,dict) or set(proof)!={'original','disabled','mode'} or not all(isinstance(proof[k],str) for k in ('original','disabled')):raise ValueError('Legacy lockdown file changed')
    if read(registration) not in (proof['original'].encode(),proof['disabled'].encode()):raise ValueError('Legacy lockdown file changed')
    original=json.loads(proof['original']);disabled=json.loads(proof['disabled'])
    paths={str(base/folder/('com.cleanyourtv.root.updater.service'+suffix)) for folder,suffix in (('services.d','.service'),('roles.d','.service.json'),('client-permissions.d','.service.json'),('api-permissions.d','.api.json'))}
    if not isinstance(original,dict) or set(original)!={'files'} or not isinstance(original['files'],dict) or set(original['files'])!=paths:raise ValueError('Legacy lockdown file changed')
    for entry in original['files'].values():
        if not isinstance(entry,dict) or set(entry) not in ({'original','installed'},{'original','installed','mode','uid','gid'}) or not all(isinstance(entry[k],str) for k in ('original','installed')):raise ValueError('Legacy lockdown file changed')
    entry=original['files'][str(api)]
    if entry['installed']!=files[str(api)]['original'] or raw!=entry['original'].encode():raise ValueError('Legacy lockdown file changed')
    if 'mode' in entry:
        info=api.lstat();metadata={key:entry[key] for key in ('mode','uid','gid')}
        if (any(type(v) is not int or v<0 for v in metadata.values()) or metadata['uid']!=uid
                or metadata['mode']>0o777 or metadata['mode']&0o022
                or metadata!={'mode':stat.S_IMODE(info.st_mode),'uid':info.st_uid,'gid':info.st_gid}):raise ValueError('Legacy lockdown file changed')
    # The only authenticated transition is the System lockdown's API substitution.
    entry['installed']=files[str(api)]['disabled']
    if original!=disabled:raise ValueError('Legacy lockdown file changed')



def validate_package_receipts(record):
    packages=record.get('packages')
    if not isinstance(packages,dict) or set(packages)!=set(APPS):raise ValueError('incomplete_removal_receipts')
    for app,item in packages.items():
        if not isinstance(item,dict) or item.get('state')!='absent' or item.get('readback')!={'app':app,'absent':True}:
            raise ValueError('package_absence_unverified')


def remove_packages(device, record, save):
    """Retry explicit removal against current presence, keeping old outcomes separate."""
    from observed_install import remove
    errors=[]
    for app in APPS:
        try:
            if app in device.apps():
                record['packages'][app]={'state':'removing'};save('package-removal')
                terminal=remove(app,timeout=150)
                if not terminal_removal(terminal,app):raise ValueError('package_removal_unconfirmed')
            if getattr(type(device),'sweep_package',None) is not None:device.sweep_package(app,record)
            device.absent(app)
            if app in device.apps():raise ValueError('package_still_registered')
            record['packages'][app]={'state':'absent','readback':{'app':app,'absent':True}};save('package-removal')
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:
            errors.append(error)
    if errors:raise errors[0]


def compact_audit(record, store):
    """Retain old outcomes/fences and digests, never private product payloads.

    Host original receipts remain immutable. Once TV private cleanup succeeds,
    old workers only need the same request ID/action/state/lease to be refused.
    Raw nested transaction errors/configuration must not survive under 'audit'.
    """
    import re
    def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    phases=set(PRE_ACTIVATION)|{'unknown','pending','prepared','installing-updater','installing-supervisor','reserved','blocked','root-deploy','root-updater','supervisor',
        'readback','complete','submitted','preparing','provisioning','installed-recovery-only','cancellation-admitted',
        'uninstalled-state-retained','remove-submitting','remove-observed','clean-removal-requested','recovery-required',
        'backed-up','installing','awaiting-launch','verifying','rolling-back','rolled-back','aborted','disabled'}
    def safe(value):
        if not isinstance(value,dict):return None
        result={}
        for key,item in value.items():
            if key in ('operation','lease','id') and isinstance(item,str) and re.fullmatch('[a-f0-9]{32}',item):result[key]=item
            elif key in ('candidate_sha256','worker_sha256','profileDigest') and isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item):result[key]=item
            elif key=='action' and item in ('install','remove'):result[key]=item
            elif key in ('stage','phase') and isinstance(item,str):result[key]=item if item in phases else 'unknown'
            elif key=='state' and item in ('pending','complete','recovery_required','unknown'):result[key]=item
            elif key=='code' and item in ('verified','operation_pending','unknown_operation','installation_requires_recovery','clean_removal_requested','continuation_requires_recovery'):result[key]=item
            elif key in ('schema','version') and type(item) is int and 0<=item<=2:result[key]=item
            elif key in ('home_changed','terminal') and type(item) is bool:result[key]=item
            elif key=='failure' and isinstance(item,dict):
                result[key]={k:v for k,v in item.items() if (k=='exception_type' and v in ('CalledProcessError','TimeoutExpired','ValueError','RuntimeError','OSError','PermissionError','FileNotFoundError','TypeError','KeyError','unknown'))
                    or (k in ('exit_status','errno') and type(v) is int and -255<=v<=4095)}
        return result
    if record.get('audit_compacted') is True:return
    original=record['original']
    hashes={key:digest(value) for key,value in original.items() if value is not None}
    for key in ('request','submission'):
        value=original.get(key)
        if value is not None:
            original[key]=safe(value)
            store.write(key+'-'+original['operation'],original[key])
    original['components']={key:safe(value) for key,value in original.get('components',{}).items()}
    if original.get('removal') is not None:original['removal']=safe(original['removal'])
    if 'fenced_components' in record:
        record['fenced_component_digests']={key:digest(value) for key,value in record['fenced_components'].items() if value is not None}
        record['fenced_components']={key:safe(value) for key,value in record['fenced_components'].items()}
    for app,item in record['packages'].items():
        if item.get('state')=='terminal':
            proof=item['terminal']
            if not terminal_removal(proof,app):raise ValueError('removal_terminal_unknown')
            event=proof['event'];details=event['details']
            bounded={'details':{'state':details['state']}}
            if 'id' in event:bounded['id']=event['id']
            if 'packageId' in details:bounded['details']['packageId']=details['packageId']
            if type(event.get('returnValue')) is bool:bounded['returnValue']=event['returnValue']
            item['terminal_sha256']=digest(proof);item['terminal']={'completed':True,'event':bounded}
    record['original_digests']=hashes;record['audit_compacted']=True
    # Prior generations can also contain raw worker errors or stale inventories.
    # Their compact request/lease bindings continue to reject delayed workers.
    for path in Path(store.root).iterdir():
        if re.fullmatch(r'(?:request|submission|removal)-[a-f0-9]{32}\.json',path.name):
            value=store.read(path.name)
            if isinstance(value,dict):store.write(path.name,safe(value))
