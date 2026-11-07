"""Fixed Root Updater CLI; stdin JSON is data, never a command line fragment."""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

from updater.core import Manager
from updater.device import Device, STATE
from updater.store import Store
LEGACY_NODE_BETA = False

FIELDS={'check':set(),'status':set(),'install':{'version','profile'},'restoreProfile':set(),
        'ready':{'transaction','version'},'confirm':{'transaction','version'},
        'reconcile':set(),'rollback':set()}


def validate_request(method,payload):
    if method not in FIELDS or not isinstance(payload,dict) or set(payload)!=FIELDS[method]:raise ValueError('Invalid updater request')
    if 'version' in payload and (not isinstance(payload['version'],str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',payload['version'])):raise ValueError('Invalid version')
    if 'transaction' in payload and (not isinstance(payload['transaction'],str) or not re.fullmatch('[a-f0-9]{32}',payload['transaction'])):raise ValueError('Invalid transaction')
    return payload


def spawn_worker():
    subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'run-updater.py'),'worker'],
                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                     start_new_session=True,close_fds=True)


def handle(method,payload,store,device,wake=spawn_worker):
    if LEGACY_NODE_BETA and method in ('check','install'):
        raise ValueError('Root Beta automatic updates are unavailable; use the computer installer.')
    p=validate_request(method,payload);manager=Manager(store,device)
    if method=='status':return manager.status()
    if method=='restoreProfile':return manager.restore_profile()
    device.integrity()
    device.require_components()
    if method=='check':return device.offer()
    if method=='install':value=manager.install(p['version'],p['profile'])
    elif method=='ready':value=manager.ready(p['transaction'],p['version'])
    elif method=='confirm':value=manager.confirm(p['transaction'],p['version'])
    elif method=='rollback':value=manager.rollback()
    else:value=manager.status()
    wake();return value


def worker(store,device):
    # Worker lifetime lock is separate from short transaction mutations and UI
    # receipts; another worker exits without stealing a pending installation.
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
            with device_operation('root-update', recovery=True):
                from package_identity import TransitionUnknown
                try:present=device.components_present()
                except TransitionUnknown:present=True  # Every owner was checked; only the original touched leg remains uncertain.
                if not present:
                    manager.component_removed();return
                tx=manager.run()
                if not tx:return
                if tx['phase'] in ('complete','rolled-back','aborted'):
                    device.finish(tx);return
                if tx['phase']=='recovery-required':return
            time.sleep(1 if tx['phase']=='verifying' else 0.05)
    finally:os.close(fd)


def main():
    if os.geteuid()!=0:raise PermissionError('Root updater service required')
    if len(sys.argv)!=2:raise ValueError('Expected one updater operation')
    method=sys.argv[1];store=Store(STATE);device=Device(store)
    if method=='worker':worker(store,device);return None
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
    with device_operation('root-update', recovery=True):
        result=handle(method,payload,store,device,wake=lambda:None)
    spawn_worker()
    return result


def entry():
    try:print(json.dumps({'returnValue':True,'result':main()},allow_nan=False),flush=True)
    except Exception as error:
        print(json.dumps({'returnValue':False,'errorText':str(error)[:512]}),flush=True);sys.exit(1)
