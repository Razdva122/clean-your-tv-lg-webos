"""Bounded 60-second activation of the isolated Root candidate."""
import copy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
import device_adapter as d
from profile_plan import CANDIDATE
from profile_recovery import prepare, validate, journal_payload
from staged_publication import publish


def begin(spawn, candidate=CANDIDATE, before_publish=None):
    from provision import verify
    verify()
    from helper_bridge import require_idle
    require_idle()
    d.trusted_dir(d.STATE)
    fd=os.open(d.STATE/'profile-trial.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    armed=False
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Uninstall revokes provisioning under this same lock. A pre-lock
        # check alone could race removal after it had reported readiness.
        verify()
        require_idle()
        d.require_home()
        before=d.read()
        journal=prepare({'returnValue':True,'profiles':before['profiles']},before['sam_home'], candidate)
        payload = journal_payload(journal)
        # Fail closed if an old transaction is unresolved.
        oldpath=d.STATE/'profile-trial.json'
        if oldpath.exists():
            old=d.safe_json(oldpath); validate(old)
            if old['state']!='restored': raise ValueError('Previous transaction not restored')
        if os.path.lexists(d.TARGET) or os.path.lexists(d.STATE/'profile-candidate.stage'):
            raise ValueError('Candidate or staging file already exists')
        info=d.sam_transport().call('luna://com.webos.applicationManager/getAppInfo',{'id':candidate})['appInfo']
        if 'home' not in info.get('appCategory',[]): raise ValueError('Candidate must be registered in the home category')
        if info.get('id')!=candidate or info.get('type')!='web' or not info.get('version'): raise ValueError('Unexpected candidate registration')
        tx=str(uuid.uuid4())
        journal.update(transaction=tx,publication='staged-v1',
                       candidate_identity={'device':0,'inode':0},deadline=time.monotonic()+60)
        if oldpath.exists():
            os.link(oldpath,d.STATE/('completed-profile-'+str(uuid.uuid4())+'.json'))
            oldpath.unlink(); d.sync(d.STATE)
        d.save(journal); armed=True
        if before_publish is not None: before_publish(tx)
        child=spawn(tx)
        for attempt in range(30):
            try: ready=d.safe_json(d.STATE/'profile-guardian-ready.json')
            except FileNotFoundError: ready={}
            if (ready.get('transaction')==tx and ready.get('pid')==child.pid
                    and ready.get('deadline')==journal['deadline'] and child.poll() is None): break
            time.sleep(.1)
        else: raise RuntimeError('Guardian did not acknowledge readiness')
        def remaining():
            d.require_home()
            if time.monotonic()>journal['deadline']-20 or child.poll() is not None:
                raise RuntimeError('Insufficient guarded time')
        def save_identity(identity):
            journal['candidate_identity']=identity; d.save(journal)
        remaining()
        require_idle()
        publish(d.STATE/'profile-candidate.stage',d.TARGET,save_identity,uid=d.EXPECTED_UID,payload=payload)
        remaining()
        d.sam_transport().call('luna://com.webos.service.systemprofile/debug/rescan',{})
        remaining()
        d.write_home(candidate)
        expected=copy.deepcopy(before)
        expected['sam_home']=candidate
        expected['profiles']['defaultApps']['categories']['home']=candidate
        expected['profiles']['idleApp']['appId']=candidate
        actual=d.read()
        if actual!=expected: raise RuntimeError('Candidate readback mismatch: '+json.dumps(actual))
        remaining()
        return {'transaction':tx,'deadline':journal['deadline'],'effective':actual}
    except BaseException:
        if armed:
            # Release before recovery; the independent timer is also still armed.
            os.close(fd); fd=None
            d.restore_once()
        raise
    finally:
        if fd is not None: os.close(fd)


def spawn(transaction):
    fd=os.open(d.STATE/'profile-guardian.log',os.O_CREAT|os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        return subprocess.Popen([d.current_executable(),str(Path(__file__).with_name('guardian_device.py')),transaction],
                                stdin=subprocess.DEVNULL,stdout=fd,stderr=fd,start_new_session=True,close_fds=True)
    finally: os.close(fd)


if __name__=='__main__':
    if os.geteuid()!=0: raise SystemExit('Root required')
    print(json.dumps(begin(spawn)),flush=True)
