"""Recovery-only device adapter. There is deliberately no activation command."""
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
# Runtime scripts execute directly; the binding helper lives in private state.
sys.path.append(str(Path(__file__).resolve().parents[1]))
import python_binding
from python_binding import current_executable
import time
from profile_plan import snapshot
from profile_recovery import recover, validate, PAYLOAD, DIGEST, payload_for, REAL_HOME, CANDIDATE, STOCK

STATE = Path('/var/lib/clean-your-tv-root')
TARGET = Path('/var/webos-profile/override/clean-your-tv-root.json')
EXPECTED_UID = 0
PROC = Path('/proc')
APPLICATIONS = Path('/media/developer/apps/usr/palm/applications')
FAILSAFE = Path('/var/luna/preferences/webosbrew_failsafe')


def home_present(*,purpose='current'):
    """Ordinary authority and established live health use distinct selectors."""
    try:
        from package_identity import identity
        info=identity(CANDIDATE,purpose=purpose,installed=APPLICATIONS.parents[2],uid=EXPECTED_UID)
        return isinstance(info,dict) and info.get('id')==CANDIDATE and info.get('type')=='web'
    except (OSError,ValueError,TypeError,KeyError):return False


def require_home(*,purpose='current'):
    if not home_present(purpose=purpose):raise ValueError('Root Home package is unavailable')


def process_start(pid):
    fields=(PROC/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
    if fields[0]=='Z': raise ValueError('Exited guardian')
    return fields[19]


def active_guardian(journal):
    # Replayed boot callbacks must not cancel a live bounded trial. A real reboot
    # has no matching guardian process. Failsafe always recovers immediately.
    try:
        if FAILSAFE.exists() or journal['state']!='pending': return False
        ready=safe_json(STATE/'profile-guardian-ready.json')
        pid=ready['pid']; deadline=journal['deadline']
        if type(pid) is not int or pid<=0: return False
        if not time.monotonic()<deadline<=time.monotonic()+90:
            from persistent_health import authorized, require_fresh
            if not authorized(journal['transaction']): return False
            require_fresh(journal['transaction'])
        if ready['transaction']!=journal['transaction'] or ready['deadline']!=deadline: return False
        if (PROC/str(pid)).stat().st_uid!=EXPECTED_UID: return False
        command=(PROC/str(pid)/'cmdline').read_bytes().split(b'\0')
        expected=[current_executable().encode(),str(Path(__file__).with_name('guardian_device.py')).encode(),journal['transaction'].encode(),b'']
        return command==expected and process_start(pid)==ready['start_ticks']
    except (OSError,ValueError,KeyError,TypeError,IndexError): return False


def trusted_dir(path):
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != EXPECTED_UID or st.st_mode & 0o022:
        raise ValueError('Unsafe directory: '+str(path))


def safe_json(path):
    # An atomic publisher may unlink the opened inode before fstat. Never
    # accept that detached snapshot: reopen the current path, boundedly.
    for attempt in range(3):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd) as f:
            st = os.fstat(f.fileno())
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != EXPECTED_UID
                    or st.st_mode & 0o022 or st.st_size > 65536 or st.st_nlink > 1):
                raise ValueError('Unsafe state file')
            if st.st_nlink == 0:
                continue
            return json.load(f)
    raise ValueError('State file repeatedly replaced during read')


def sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def save(journal):
    fd, temp = tempfile.mkstemp(dir=STATE, prefix='.profile-state-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(journal, f); f.flush(); os.fsync(f.fileno())
        os.replace(temp, STATE/'profile-trial.json')
        sync(STATE)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def sam_transport():
    import transport
    return transport


def write_home(target):
    if target not in (STOCK, CANDIDATE, REAL_HOME): raise ValueError('Unsupported Home')
    if target != REAL_HOME: return sam_transport().write(target)
    return sam_transport().call('luna://com.webos.service.applicationmanager/setDefaultApp',
                                {'category':'home','appId':target})


def read():
    sam = sam_transport()
    reply = sam.call('luna://com.webos.service.systemprofile/getProfiles',
                     {'names':['defaultApps','idleApp'], 'subscribe':False})
    return snapshot(reply, sam.read())


def remove_candidate(identity):
    trusted_dir(TARGET.parent)
    try: fd = os.open(TARGET, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError: return 'absent'
    except OSError: return 'conflict'
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != EXPECTED_UID
                or st.st_mode & 0o022 or st.st_nlink != 1 or st.st_size != len(PAYLOAD)
                or (st.st_dev, st.st_ino) != (identity['device'], identity['inode'])):
            return 'conflict'
        data = b''
        while len(data) < len(PAYLOAD):
            chunk = os.read(fd, len(PAYLOAD)-len(data))
            if not chunk: return 'conflict'
            data += chunk
        if hashlib.sha256(data).hexdigest() != DIGEST: return 'conflict'
        now = TARGET.lstat()
        attrs = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if attrs(now) != attrs(st): return 'conflict'
        TARGET.unlink(); sync(TARGET.parent)
        return 'removed'
    finally: os.close(fd)


def restore_once(expected_transaction=None):
    try:
        from cli import inhibit
        inhibit(STATE)
    except Exception: pass  # Emergency Home recovery has priority over optional audio policy.
    trusted_dir(STATE)
    try: (STATE/'profile-trial.json').lstat()
    except FileNotFoundError: return 'absent'
    fd = os.open(STATE/'profile-trial.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        j = safe_json(STATE/'profile-trial.json'); validate(j)
        if expected_transaction is not None and j.get('transaction') != expected_transaction:
            return 'superseded'
        identity = j.get('candidate_identity', {})
        if any(type(identity.get(k)) is not int or identity[k] < 0 for k in ('device','inode')):
            raise ValueError('Missing candidate file identity')
        publication = j.get('publication')
        if publication not in (None, 'staged-v1'): raise ValueError('Unknown publication protocol')
        def remove_owned():
            if publication == 'staged-v1':
                from staged_publication import remove
                return remove(STATE/'profile-candidate.stage', TARGET, identity, EXPECTED_UID, payload=payload_for(j.get('candidate', CANDIDATE)))
            return remove_candidate(identity)
        return recover(j, remove_owned,
                       lambda: sam_transport().call('luna://com.webos.service.systemprofile/debug/rescan', {}),
                       read, lambda target: sam_transport().write(target), save)
    finally: os.close(fd)


def main(mode):
    if mode not in ('status','recover','boot'): raise ValueError('Recovery-only command required')
    trusted_dir(STATE)
    if mode == 'status':
        result = {'effective':read(), 'journal_exists':(STATE/'profile-trial.json').exists()}
        if result['journal_exists']:
            journal = safe_json(STATE/'profile-trial.json'); validate(journal)
            result['journal'] = {k: journal.get(k) for k in ('state','transaction','candidate','deadline')}
            result['guardian_active'] = active_guardian(journal)
        return result
    if mode == 'boot':
        if not (STATE/'profile-trial.json').exists(): return 'absent'
        j = safe_json(STATE/'profile-trial.json'); validate(j)
        if j['state'] not in ('pending','recovering'): return j['state']
        if active_guardian(j): return 'guarded-trial'
        fd = os.open(STATE/'profile-recovery.log',os.O_CREAT|os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        try:
            child = subprocess.Popen([current_executable(),str(Path(__file__).resolve()),'recover'],
                                     stdin=subprocess.DEVNULL,stdout=fd,stderr=fd,
                                     start_new_session=True,close_fds=True)
        finally: os.close(fd)
        return {'recovery_pid':child.pid}
    for attempt in range(12):
        try: result = restore_once()
        except Exception as exc:
            print(type(exc).__name__+': '+str(exc),file=sys.stderr,flush=True); result = 'recovering'
        if result not in ('pending','recovering'): return result
        time.sleep(5)
    return 'recovering'


# Owned EIM presentation uses the existing authenticated runtime destination.
NATIVE_EIM='luna://com.webos.service.eim/'

def _native_call(method,payload,deadline):
 remaining=deadline-time.monotonic()
 if remaining<=0:raise TimeoutError('Native input operation deadline')
 # transport.call may also spend up to timeout reaping its child. Both halves
 # must fit the total budget so emergency recovery can acquire the owner lock.
 uri='luna://com.webos.settingsservice/getSystemSettings' if method=='startupSettings' else NATIVE_EIM+method
 return sam_transport().call(uri,payload,timeout=min(.5,remaining/2))

def _native_pair(value):
 pair={'type':value.get('lastSourceId'),'appId':value.get('lastSourceAppId')}
 _native_validate_pair(pair)
 return pair

def _native_validate_pair(pair):
 if (not isinstance(pair,dict) or set(pair)!={'type','appId'}
     or not isinstance(pair['type'],str) or not re.fullmatch('[A-Z0-9_]{1,64}',pair['type'])
     or not isinstance(pair['appId'],str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',pair['appId'])):
  raise ValueError('Invalid native input baseline')

def _native_entry(deadline):
 devices=_native_call('getAllInputStatus',{},deadline).get('devices')
 if not isinstance(devices,list) or any(not isinstance(x,dict) for x in devices):raise ValueError('Unknown native input inventory')
 matches=[x for x in devices if x.get('appId')==CANDIDATE or x.get('id')=='MVPD_IP-'+CANDIDATE]
 if len(matches)>1 or matches and (matches[0].get('appId')!=CANDIDATE or matches[0].get('id')!='MVPD_IP-'+CANDIDATE):
  raise ValueError('Native input entry changed')
 return bool(matches)

def _native_read():
 path=STATE/'native-input.json'
 try:value=safe_json(path)
 except FileNotFoundError:return None
 if (not isinstance(value,dict) or set(value)!={'schema','appId','phase','baseline'}
     or type(value['schema']) is not int or value['schema']!=1 or value['appId']!=CANDIDATE
     or value['phase'] not in ('adding','active','removing','disabled')):
  raise ValueError('Invalid native input receipt')
 _native_validate_pair(value['baseline'])
 if value['baseline']['appId']==CANDIDATE:raise ValueError('Native input baseline cannot be Root')
 return value

def _native_save(value):
 trusted_dir(STATE)
 fd,name=tempfile.mkstemp(prefix='.native-input-',dir=STATE)
 try:
  with os.fdopen(fd,'w') as out:
   json.dump(value,out,sort_keys=True);out.flush();os.fsync(out.fileno())
  os.replace(name,STATE/'native-input.json');sync(STATE)
 finally:
  if os.path.lexists(name):os.unlink(name)

def _native_set(pair,deadline):
 _native_call('setLastInput',pair,deadline)
 # NATIVE_EIM updates its own state synchronously, settings persistence may lag.
 for attempt in range(5):
  if _native_pair(_native_call('getLastInput',{},deadline))==pair:return
  if attempt<4:time.sleep(.05)
 raise ValueError('Native remembered input was not verified')

def native_input_enable():
 """Explicit healthy enable only; uncertain operations must recover first."""
 deadline=time.monotonic()+1.5
 saved=_native_read();present=_native_entry(deadline)
 if saved is not None and saved['phase']=='active':
  if not present:raise ValueError('Native input entry changed')
  return 'active'  # Never overwrite an input selected after enable.
 if saved is not None and saved['phase']!='disabled':raise ValueError('Native input recovery required')
 if present:raise ValueError('Refusing unowned native input')
 startup=_native_call('startupSettings',{'category':'general','keys':['homeAutoLaunch']},deadline)
 if startup.get('settings',{}).get('homeAutoLaunch')!='on':return 'preserved-startup-setting'
 baseline=_native_pair(_native_call('getLastInput',{},deadline))
 if baseline['appId']==CANDIDATE:raise ValueError('Unowned remembered Root input')
 saved=dict(schema=1,appId=CANDIDATE,phase='adding',baseline=baseline)
 _native_save(saved)  # A timeout is uncertainty, not permission to replay addDevice.
 _native_call('addDevice',{'appId':CANDIDATE,'pigImage':'','mvpdIcon':''},deadline)
 if not _native_entry(deadline):raise ValueError('Native input registration was not verified')
 _native_set({'type':'MVPD_IP','appId':CANDIDATE},deadline)
 _native_save(dict(saved,phase='active'))
 return 'active'

def native_input_disable():
 """Retarget only our remembered input, then remove only our owned entry."""
 deadline=time.monotonic()+1.5
 saved=_native_read()
 if saved is None:return 'absent'
 if saved['phase']=='disabled':return 'disabled'
 _native_save(dict(saved,phase='removing'))
 present=_native_entry(deadline)
 if _native_pair(_native_call('getLastInput',{},deadline))['appId']==CANDIDATE:
  _native_set(saved['baseline'],deadline)
 if present:_native_call('deleteDevice',{'appId':CANDIDATE},deadline)
 if _native_entry(deadline) or _native_pair(_native_call('getLastInput',{},deadline))['appId']==CANDIDATE:
  raise ValueError('Native input cleanup was not verified')
 _native_save(dict(saved,phase='disabled'))
 return 'disabled'


if __name__ == '__main__':
    if os.geteuid() != 0: raise SystemExit('Root recovery service required')
    print(json.dumps(main(sys.argv[1] if len(sys.argv)==2 else '')),flush=True)
