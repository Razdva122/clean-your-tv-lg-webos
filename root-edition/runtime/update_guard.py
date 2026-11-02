"""Serialize activation with updater reservation; explicit recovery stays available."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

STATE = Path('/var/lib/clean-your-tv-root')
HOME_RESUME_PROTOCOL = 1


@contextmanager
def locked(root,uid):
    for p in (root,*root.parents):
        st=p.lstat()
        # Ancestors such as /tmp may be sticky. The private state itself may not.
        if not stat.S_ISDIR(st.st_mode) or (p==root and (st.st_uid!=uid or st.st_mode & 0o022)):
            raise ValueError('Unsafe routing lock directory')
    fd=os.open(root/'software-update.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=uid or st.st_nlink!=1 or st.st_mode & 0o022:raise ValueError('Unsafe routing lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:os.close(fd)


class ProductPending(RuntimeError):
    pass


@contextmanager
def product_control(root, uid):
    """Use the coordinator's mutex, without a second durable reservation.

    Pure activation does not run under deploy's package lease. Updater Home
    resume invokes its independently verified _enable path and never enters
    this public activation gate. Status and emergency restore bypass this gate.
    """
    state=Path(root).parent/'clean-your-tv-installation'
    for parent in (state.parent,*state.parent.parents):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,uid) or (info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX):
            raise ValueError('Unsafe installation ancestor')
    try: state.mkdir(mode=0o700)
    except FileExistsError: pass
    info=state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=uid or info.st_mode&0o022:
        raise ValueError('Unsafe installation directory')
    fd=os.open(state/'ownership.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode&0o022:
            raise ValueError('Unsafe installation lock')
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ProductPending('Product setup or removal is running; restore remains available') from None
        path=state/'operation.json'
        if os.path.lexists(path):
            value=read(path,uid)
            if (not isinstance(value,dict) or set(value)!={'schema','id','owner','journal','stage','terminal'}
                    or type(value.get('schema')) is not int or value['schema']!=1 or type(value.get('terminal')) is not bool
                    or not isinstance(value.get('id'),str) or not re.fullmatch('[a-f0-9]{32}',value['id'])
                    or any(not isinstance(value.get(k),str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',value[k]) for k in ('owner','journal','stage'))):
                raise ProductPending('Unknown product operation; retain recovery evidence')
            if not value['terminal']: raise ProductPending('Product setup or removal needs recovery; restore remains available')
        yield
    finally: os.close(fd)


@contextmanager
def control(root=STATE,uid=0):
    root=Path(root)
    with product_control(root,uid), locked(root,uid):
        if os.path.lexists(root/'update-block.json'):raise RuntimeError('Software update pending; use Root Updater Recovery before enabling Root')
        yield


def read(path,uid,limit=1024):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=uid or st.st_nlink!=1 or st.st_size>limit or st.st_mode & 0o022:raise ValueError('Unsafe reservation')
        return json.load(f)


def sync(root):
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def reserve(transaction,root=STATE,uid=0):
    if not isinstance(transaction,str) or not re.fullmatch('[a-f0-9]{32}',transaction):raise ValueError('Invalid update identity')
    root=Path(root)
    with locked(root,uid):
        p=root/'update-block.json';value={'transaction':transaction}
        if os.path.lexists(p):
            if read(p,uid)!=value:raise ValueError('Another update owns routing')
            return
        # A fresh reservation starts a new cycle, including rollback of the same update.
        # Remove the old receipt before publishing the reservation, never on retry.
        for name in ('update-home-resume.json','update-home-cancel.json'):
            old=root/name
            if os.path.lexists(old):old.unlink()
        sync(root)
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
        sync(root)


def release(transaction,root=STATE,uid=0):
    root=Path(root)
    with locked(root,uid):
        p=root/'update-block.json'
        if not os.path.lexists(p):return
        if read(p,uid)!={'transaction':transaction}:raise ValueError('Reservation owner mismatch')
        p.unlink();sync(root)


def identity(transaction):
    if not isinstance(transaction,str) or not re.fullmatch('[a-f0-9]{32}',transaction):
        raise ValueError('Invalid update identity')


def atomic(path,value):
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.update-home-')
    try:
        with os.fdopen(fd,'w') as out:
            json.dump(value,out,sort_keys=True);out.flush();os.fsync(out.fileno())
        os.replace(temp,path);sync(path.parent)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def reservation(transaction,root,uid,required=True):
    identity(transaction)
    try:value=read(root/'update-block.json',uid)
    except FileNotFoundError:
        if required:raise ValueError('No update reservation')
        return False
    if value!={'transaction':transaction}:raise ValueError('Reservation owner mismatch')
    return True


def ticket(root,uid):
    from persistent_lifecycle import identifier, validate
    try:t=read(root/'update-home-resume.json',uid,16384)
    except FileNotFoundError:return None
    if not isinstance(t,dict) or not {'transaction','ticket'} <= set(t):
        raise ValueError('Invalid update Home ticket')
    identity(t['transaction']);identity(t['ticket'])
    receipt={'transaction','ticket','outcome'}
    fields={'transaction','ticket','boot','before','desired','suspended','attempted'}
    if set(t)!=receipt:
        if not fields <= set(t) or set(t)-fields-{'suspend_result','outcome'}:
            raise ValueError('Invalid update Home ticket fields')
        if not identifier(t['boot']) or type(t['desired']) is not bool or type(t['attempted']) is not bool:
            raise ValueError('Invalid update Home ticket state')
        for key in ('before','suspended'):
            if t[key] is not None:validate(t[key])
        if not disabled(t['suspended']) or (t['desired'] and (t['before'] is None or t['before']['phase']!='active' or not t['before']['enabled'])):
            raise ValueError('Invalid update Home intent snapshots')
        if t['attempted'] and t['suspended'] is None:
            raise ValueError('Unverified update Home activation')
        if 'suspend_result' in t and t['suspend_result'] not in ('restored','absent'):
            raise ValueError('Invalid update Home suspension result')
    if 'outcome' in t:
        outcome=t['outcome']
        if (not isinstance(outcome,dict) or not {'status'} <= set(outcome) or set(outcome)-{'status','error'}
                or outcome['status'] not in ('restored','skipped','cancelled','failed','unchanged')
                or ('error' in outcome and not isinstance(outcome['error'],str))):
            raise ValueError('Invalid update Home outcome')
    return t


def _intent():
    from intent_runtime import coordinator
    c=coordinator()
    return c.store.read() if c is not None else None


def _boot():
    from intent_runtime import boot_identity
    return boot_identity()


def _failsafe():
    import device_adapter as d
    return os.path.lexists(d.FAILSAFE)


def _restore():
    from intent_runtime import restore
    import device_adapter as d
    result=restore()
    result=d.main('recover') if result is None else result
    if result not in ('restored','absent'):raise ValueError('Home restoration incomplete: '+str(result))
    return result


def _enable():
    from intent_runtime import enable
    return enable()


def disabled(intent):
    return intent is None or (intent['phase']=='disabled' and intent['enabled'] is False)


def cancel(root=STATE,uid=0,expected=None):
    """Explicit off wins without waiting for the activation/update lock.

    Emergency observers pass their current bound intent, so old observers cannot
    cancel a different update or a newer lifecycle attempt.
    """
    root=Path(root);t=ticket(root,uid)
    if t is None:
        if expected is not None:return
        try:block=read(root/'update-block.json',uid)
        except FileNotFoundError:return
        if not isinstance(block,dict) or set(block)!={'transaction'}:raise ValueError('Invalid update reservation')
        identity(block['transaction'])
        # Explicit off in the reserve/suspend gap applies to this fresh cycle.
        atomic(root/'update-home-cancel.json',dict(transaction=block['transaction'],ticket=None))
        return
    if 'outcome' in t:return
    if not reservation(t['transaction'],root,uid,required=False):return
    if expected is not None:
        before=t['before'];suspended=t.get('suspended')
        same=before is not None and (expected['generation'],expected['token'])==(before['generation'],before['token'])
        activating=(t.get('attempted') and suspended is not None
                    and expected['generation']==suspended['generation']+1 and expected['boot']==t['boot'])
        if not (same or activating):return
    atomic(root/'update-home-cancel.json',dict(transaction=t['transaction'],ticket=t['ticket']))


def cancelled(t,root,uid):
    try:value=read(root/'update-home-cancel.json',uid)
    except FileNotFoundError:return False
    if not isinstance(value,dict) or set(value)!={'transaction','ticket'}:raise ValueError('Invalid update Home cancellation')
    identity(value['transaction'])
    if value['ticket'] is not None:identity(value['ticket'])
    return value['transaction']==t['transaction'] and value['ticket'] in (None,t['ticket'])


def _anchor_bytes(path,uid,limit=4*1024*1024):
    """Private data only; this gate must authenticate code before importing it."""
    for parent in path.parents:
        info=parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,uid)
                or info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX):
            raise ValueError('Unsafe rollback anchor ancestor')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as source:
        info=os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1
                or info.st_mode&0o022 or info.st_size>limit):
            raise ValueError('Unsafe rollback anchor file')
        raw=source.read(limit+1)
        if len(raw)>limit:raise ValueError('Oversized rollback anchor file')
        return raw


def _anchor_lock_held(path,uid):
    # These locks belong to the parent System worker. Never wait on them here.
    _anchor_bytes(path,uid,1024)
    fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        fcntl.flock(fd,fcntl.LOCK_UN)
        raise ValueError('System rollback owner lock is not held')
    finally:os.close(fd)


INSTALLED=Path('/media/developer/apps')


def stage_system_rollback_anchor(transaction,root=STATE,uid=0):
    """Keep the original supervisor's prior anchor valid during retained rollback.

    The active System journal still selects the candidate until an independently
    observed rollback terminal selects the prior. This writes no installer proof.
    The caller holds the routing lock, System journal lock and product lease.
    """
    import hashlib
    import importlib
    import importlib.abc
    import importlib.util
    import sys
    import types
    root=Path(root);identity(transaction)
    system=root.parent/'clean-your-tv-system-updater'
    if not os.path.lexists(system):return
    tx_path=system/'transaction.json'
    if not os.path.lexists(tx_path):return
    tx=json.loads(_anchor_bytes(tx_path,uid))
    if not isinstance(tx,dict):raise ValueError('Invalid System rollback transaction')
    if tx.get('phase')!='rolling-back' or tx.get('resumeCycle')!='rollback':return
    if (tx.get('id')!=transaction or tx.get('edition')!='root' or tx.get('homeResumePhase')!='complete'
            or tx.get('rollbackAttempted') is not False):
        raise ValueError('Original completed System rollback required')
    reservation(transaction,root,uid)
    ownership=root.parent/'clean-your-tv-installation'
    operation=json.loads(_anchor_bytes(ownership/'operation.json',uid))
    if (not isinstance(operation,dict) or set(operation)!={'schema','id','owner','journal','stage','terminal'}
            or type(operation.get('schema')) is not int or operation.get('schema')!=1 or operation.get('owner')!='system-update'
            or operation.get('journal')!='transaction.json' or operation.get('terminal') is not False
            or not isinstance(operation.get('id'),str) or not re.fullmatch('[a-f0-9]{32}',operation['id'])
            or not isinstance(operation.get('stage'),str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',operation['stage'])):
        raise ValueError('Exclusive System rollback lease required')
    _anchor_lock_held(ownership/'ownership.lock',uid)
    _anchor_lock_held(system/'worker.lock',uid)
    updater=root.parent/'clean-your-tv-root-updater';code=system/'code'
    receipt=json.loads(_anchor_bytes(system/'infrastructure.json',uid))
    inventory=receipt.get('code') if isinstance(receipt,dict) and receipt.get('schema')==1 else None
    required={'package_identity.py','package_data.py','installation.py','python_binding.py'}|{'system_updater/'+n for n in ('__init__.py','core.py','device.py','support/__init__.py','support/store.py','support/package.py','support/profile.py','support/luna.py','policy.js','release-public.pem')}
    if not isinstance(inventory,dict) or not required<=set(inventory):
        raise ValueError('Authenticated supervisor code required')
    sources={}
    for name,digest in inventory.items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or str(path)!=name or not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):
            raise ValueError('Unsafe supervisor rollback inventory')
        raw=_anchor_bytes(code/name,uid)
        if hashlib.sha256(raw).hexdigest()!=digest:
            raise ValueError('Supervisor rollback code changed')
        sources[str(code/name)]=raw
    # Execute the captured verified source, never an adjacent bytecode cache.
    # Absolute helper imports are confined to the same authenticated supervisor;
    # ambient Root modules and sys.path do not choose this gate's byte authority.
    alias='_cytv_rollback_'+uuid.uuid4().hex
    helpers={name:str(code/(name+'.py')) for name in ('package_identity','package_data','installation','python_binding')}
    helpers.update({'updater.store':str(code/'system_updater/support/store.py'),'updater.package':str(code/'system_updater/support/package.py')})
    class VerifiedSource(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,name,path=None,target=None):
            package=False
            if name in helpers:filename=helpers[name]
            elif name==alias or name.startswith(alias+'.'):
                relative=name[len(alias):].lstrip('.').replace('.','/')
                filename=str(code/'system_updater'/(relative+'.py'))
                if filename not in sources:
                    filename=str(code/'system_updater'/relative/'__init__.py');package=True
            else:return None
            if filename not in sources:raise ImportError('Unverified supervisor module '+name)
            return importlib.util.spec_from_loader(name,self,origin=filename,is_package=package)
        def create_module(self,spec):return None
        def exec_module(self,module):
            module.__file__=module.__spec__.origin
            exec(compile(sources[module.__file__],module.__file__,'exec'),module.__dict__)
    missing=object();saved={name:sys.modules.get(name,missing) for name in ('updater',*helpers)}
    for name in saved:sys.modules.pop(name,None)
    updater_namespace=types.ModuleType('updater');updater_namespace.__path__=[]
    sys.modules['updater']=updater_namespace
    finder=VerifiedSource();sys.meta_path.insert(0,finder)
    try:
        importlib.import_module(alias)
        device_module=importlib.import_module(alias+'.device')
        core_module=importlib.import_module(alias+'.core')
        store_module=importlib.import_module(alias+'.support.store')
        store=store_module.Store.__new__(store_module.Store);store.root=str(system);store.uid=uid
        device=device_module.Device(store,code=code,root_state=root,root_updater=updater,installed=INSTALLED,uid=uid)
        checked=core_module.Manager(store,device)._load()
        if checked!=tx:raise ValueError('System rollback transaction changed')
        for component in checked['components']:
            install=component['installEvidence'];rollback=component['rollbackEvidence']
            if (install['terminal'] is None or install['terminal'].get('success') is not True
                    or rollback!={'intent':False,'submitted':None,'terminal':None}):
                raise ValueError('Untouched rollback of a completed release required')
        device.integrity(enforce=False)
        candidate=device._verify_release(checked['candidate'],'root')
        prior=device._verify_release(checked['prior'],'root')
        if 'proof' not in candidate or device._baseline('root')!=candidate:
            raise ValueError('Original signed System publication required')
        device.require_components();device._root_integrity()
        if not all(device.verify_installed(c) for c in candidate['components']):
            raise ValueError('Completed System release changed')
        for c in prior['components']:device.inspect(device.cache_bytes(c),c)
        current_path=updater/'current.json';raw=_anchor_bytes(current_path,uid)
        current=json.loads(raw)
        def anchor(component):
            return dict(version=component['version'],sha256=component['sha256'],size=component['size'],local=True,writer={'owner':'system-update','id':transaction})
        original=anchor(candidate['components'][0]);target=anchor(prior['components'][0])
        ticket_path=root/('system-rollback-anchor-'+transaction+'.json')
        ticket=dict(schema=1,transaction=transaction,lease=operation['id'],candidate=original,prior=target)
        if os.path.lexists(ticket_path):
            if json.loads(_anchor_bytes(ticket_path,uid))!=ticket:
                raise ValueError('Conflicting System rollback anchor receipt')
            if current not in (original,target):raise ValueError('System rollback anchor changed')
        elif current!=original:raise ValueError('Original completed System current required')
        # A current descriptor always has an independently checked private cache.
        component=prior['components'][0];prior_raw=device.cache_bytes(component)
        cache=updater/'cache'/(component['sha256']+'.ipk')
        if os.path.lexists(cache):
            if _anchor_bytes(cache,uid,64*1024*1024)!=prior_raw:raise ValueError('Prior rollback cache conflict')
        else:device.atomic(cache,prior_raw,exclusive=True)
        if not os.path.lexists(ticket_path):atomic(ticket_path,ticket)
        if current!=target:device.atomic(current_path,json.dumps(target,sort_keys=True,separators=(',',':')).encode())
    finally:
        sys.meta_path.remove(finder)
        for name in list(sys.modules):
            if name==alias or name.startswith(alias+'.'):sys.modules.pop(name,None)
        for name,value in saved.items():
            if value is missing:sys.modules.pop(name,None)
            else:sys.modules[name]=value


def suspend(transaction,root=STATE,uid=0):
    root=Path(root)
    with locked(root,uid):
        reservation(transaction,root,uid)
        path=root/'update-home-resume.json';t=ticket(root,uid)
        if t is not None and t['transaction']!=transaction:raise ValueError('Resume ticket owner mismatch')
        if t is None:
            before=_intent()
            t=dict(transaction=transaction,ticket=uuid.uuid4().hex,boot=_boot(),before=before,
                   desired=before is not None and before['phase']=='active' and before['enabled'] is True,
                   suspended=None,attempted=False)
            atomic(path,t)
            fresh=True
        else:
            if 'outcome' in t:raise ValueError('Update Home suspension already finished')
            fresh=False
        result=_restore()
        # Capture the owner's preference and restore routing before the retained
        # rollback anchor changes package authority. Active health must not see
        # an intentionally retargeted current descriptor before ticket capture.
        stage_system_rollback_anchor(transaction,root,uid)
        after=_intent()
        if not disabled(after):raise ValueError('Persistent intent was not disabled')
        # An interrupted suspension has no verified post-restore snapshot. Retrying
        # can recover stock Home but must not infer permission to enable again.
        if t['suspended'] is None:
            t.update(suspended=after,desired=t['desired'] and fresh,suspend_result=result)
            atomic(path,t)
        return result


def finish(transaction,root=STATE,uid=0,resume=True):
    root=Path(root)
    with locked(root,uid):
        owned=reservation(transaction,root,uid,required=False)
        path=root/'update-home-resume.json';t=ticket(root,uid)
        if not owned and (t is None or t['transaction']!=transaction):return dict(status='unchanged')
        if t is not None and t['transaction']!=transaction:raise ValueError('Resume ticket owner mismatch')
        if t is not None and 'outcome' in t:
            if owned:(root/'update-block.json').unlink();sync(root)
            return t['outcome']
        if not owned:raise ValueError('No update reservation')
        outcome=dict(status='unchanged')
        if t is not None:
            outcome=dict(status='skipped')
            if cancelled(t,root,uid):outcome=dict(status='cancelled')
            elif resume and t['desired'] and not t['attempted'] and t.get('suspended') is not None and _boot()==t['boot'] and not _failsafe() and _intent()==t['suspended']:
                # Persist BEFORE activation. An uncertain attempt is recovered off,
                # never replayed, even when the updater process is restarted.
                t['attempted']=True;atomic(path,t)
                try:
                    if cancelled(t,root,uid):outcome=dict(status='cancelled')
                    else:
                        result=_enable();current=_intent()
                        if not isinstance(result,dict) or result.get('intent')!=current or current['phase']!='active' or current['enabled'] is not True:
                            raise ValueError('Persistent Home activation not confirmed')
                        outcome=dict(status='restored')
                except Exception as exc:outcome=dict(status='failed',error=str(exc))
                if cancelled(t,root,uid):outcome=dict(status='cancelled')
            if outcome['status']!='restored' and (t['attempted'] or not disabled(_intent())):
                _restore()
                if not disabled(_intent()):raise ValueError('Persistent intent was not disabled')
            # A cancellation arriving after enable must also win before release.
            if cancelled(t,root,uid) and outcome['status']=='restored':
                _restore()
                if not disabled(_intent()):raise ValueError('Persistent intent was not disabled')
                outcome=dict(status='cancelled')
            t['outcome']=outcome;atomic(path,t)
        else:
            atomic(path,dict(transaction=transaction,ticket=uuid.uuid4().hex,outcome=outcome))
        (root/'update-block.json').unlink();sync(root)
        return outcome


def abort(transaction,root=STATE,uid=0):
    return finish(transaction,root,uid,resume=False)
