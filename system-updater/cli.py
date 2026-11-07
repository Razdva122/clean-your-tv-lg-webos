"""Fixed operation CLI. JSON input cannot select paths, URLs or commands."""
from contextlib import contextmanager, ExitStack
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from .core import Manager, SETS, FINISHED, version
from .device import Device, STATE
from .support.store import Store, prune_peer_caches
LEGACY_NODE_BETA = False

FIELDS={'check':{'edition'},'status':set(),'install':{'edition','release','profile'},'restoreProfile':{'edition'},'healthy':{'edition','transaction','version'},'rollback':set(),'reconcile':set()}


def validate_request(method,payload):
    if method not in FIELDS or not isinstance(payload,dict) or set(payload)!=FIELDS[method]:raise ValueError('Invalid system updater request')
    if 'edition' in payload and payload['edition'] not in SETS:raise ValueError('Invalid edition')
    if 'version' in payload:version(payload['version'])
    if 'release' in payload:
        if not isinstance(payload['release'],str) or not payload['release'].startswith('v'):raise ValueError('Invalid release')
        version(payload['release'][1:])
    if 'transaction' in payload and (not isinstance(payload['transaction'],str) or not re.fullmatch('[a-f0-9]{32}',payload['transaction'])):raise ValueError('Invalid transaction')
    return payload


def spawn_worker():
    subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'run-system-updater.py'),'worker'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)


def handle(method,payload,store,device,wake=spawn_worker):
    if LEGACY_NODE_BETA and method in ('check','install'):
        raise ValueError('Root Beta automatic updates are unavailable; use the computer installer.')
    p=validate_request(method,payload);manager=Manager(store,device)
    device.integrity()
    if method=='status':return manager.status()
    if method=='restoreProfile':return manager.restore_profile(p['edition'])
    device.require_components()
    if method=='check':return device.check(p['edition'])
    if method=='install':result=manager.install(p['edition'],p['release'],p['profile'])
    elif method=='healthy':result=manager.healthy(p['edition'],p['transaction'],p['version'])
    elif method=='rollback':result=manager.rollback()
    else:result=manager.status()
    wake();return result


def worker(store,device):
    # Lifetime lock is independent of the short journal lock, allowing health
    # receipts and status while the detached installer is waiting on the bus.
    fd=os.open(Path(store.root)/'daemon.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or st.st_mode & 0o022:raise ValueError('Unsafe worker lock')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        device.integrity();manager=Manager(store,device)
        while True:
            if store.read('transaction') is None:return
            from installation import device_operation
            with device_operation('system-update', recovery=True):
                from package_identity import TransitionUnknown
                try:present=device.components_present()
                except TransitionUnknown:present=True  # Every owner was checked; only the original touched leg remains uncertain.
                if not present:
                    manager.component_removed();return
                tx=manager.run()
                if tx is None or tx['phase']=='recovery-required':return
                if tx['phase'] in FINISHED:
                    if tx.get('homeResumePhase')!=tx['phase']:
                        with store.lock():
                            current=store.read('transaction')
                            if current and (current['id'],current['phase'])==(tx['id'],tx['phase']):
                                try:
                                    current['homeResume']=device.finish(current);current['homeResumePhase']=current['phase']
                                except Exception as error:
                                    current['homeResume']={'status':'failed','error':str(error)[:512]};current['error']=str(error)[:1024]
                                store.write('transaction',current)
                    prune_peer_caches(store, device.root_updater)
                    return
            time.sleep(1 if tx['phase'] in ('verifying','verifying-rollback') else .05)
    finally:os.close(fd)


@contextmanager
def healthy_operation(payload,store,device):
    """Wait only for context acquisition; never replay a handler or context exit."""
    from installation import Ownership, Busy, device_operation, pending_journals
    ownership=Ownership();lease=ownership.status();manager=Manager(store,device)
    if not lease or lease['terminal'] or (lease['owner'],lease['journal'])!=('system-update','transaction.json'):
        raise ValueError('Matching active System update ownership required')
    stop=time.monotonic()+10;health=None
    def eligible():
        nonlocal health
        current=ownership.status();tx=manager._load()
        if not current or current['id']!=lease['id'] or current['terminal'] or (current['owner'],current['journal'])!=('system-update','transaction.json'):
            raise ValueError('System update ownership changed')
        if not tx or tx['phase'] not in ('verifying','verifying-rollback') or (tx['id'],tx['edition'])!=(payload['transaction'],payload['edition']):
            raise ValueError('Stale health transaction')
        if manager._launcher_version(tx,tx['phase']=='verifying-rollback')!=payload['version']:
            raise ValueError('Stale health version')
        observed=(tx['id'],tx['edition'],tx['phase'],payload['version'],tx['launched'],tx['deadline'])
        if health is None:health=observed
        elif health!=observed:raise ValueError('Health window changed during ownership wait')
        now=manager._now()
        if not tx['launched']<=now<tx['deadline']:raise ValueError('Stale health deadline')
        pending_journals('system-update')  # Foreign journals never grant a wait.
        return tx['deadline']-now
    while True:
        remaining=eligible()
        if time.monotonic()>=stop:raise Busy()
        stack=ExitStack()
        try:stack.enter_context(device_operation('system-update',recovery=True))
        except Busy:
            stack.close();remaining=eligible()
            delay=min(.05,remaining,max(0,stop-time.monotonic()))
            if delay<=0:raise
            time.sleep(delay)
            continue
        with stack:
            eligible()
            if time.monotonic()>=stop:raise Busy()
            yield
        return


def main():
    if os.geteuid()!=0:raise PermissionError('Root System Updater service required')
    if len(sys.argv)!=2:raise ValueError('Expected one supervisor operation')
    store=Store(STATE);device=Device(store);method=sys.argv[1]
    if method=='worker':return worker(store,device)
    raw=sys.stdin.buffer.read(4*1024*1024+1)
    if len(raw)>4*1024*1024:raise ValueError('Request too large')
    payload=json.loads(raw or b'{}')
    validate_request(method,payload)
    if method in ('status','check','restoreProfile'):
        return handle(method,payload,store,device)
    if method != 'install' and store.read('transaction') is None:
        if method in ('rollback','reconcile'):return None
        raise ValueError('Stale health signal')
    from installation import device_operation
    operation=healthy_operation(payload,store,device) if method=='healthy' else device_operation('system-update',recovery=True)
    with operation:
        result=handle(method,payload,store,device,wake=lambda:None)
    spawn_worker()
    return result


def entry():
    try:print(json.dumps({'returnValue':True,'result':main()},allow_nan=False),flush=True)
    except Exception as error:
        print(json.dumps({'returnValue':False,'errorText':str(error)[:512]}),flush=True);sys.exit(1)
