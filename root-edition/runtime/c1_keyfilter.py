"""Schema2 C1 and schema3 capability-admitted experimental compositor routing.

The native guardian owns stop/input/control/broker leases. This interpreter owns
only the configd inverse transaction and conservative lifecycle return hints.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import time
import uuid
try: from . import c1_gate as legacy
except ImportError: import c1_gate as legacy

STATE = legacy.STATE
APP = legacy.APP
BACKEND = legacy.BACKEND
ROUTING = 'compositor-keyfilter-v1'
KEY = 'com.webos.surfacemanager.keyFilters'
STOCK = 'com.webos.app.home'
CARD = '_WEBOS_WINDOW_TYPE_CARD'
STOCK_APPINFO = Path('/usr/palm/applications/com.webos.app.home/appinfo.json')
MOUNTINFO = Path('/proc/self/mountinfo')
INPUT_BINDINGS = Path('/home/root/.config/lginputhook/keybinds.json')
OTHER_HOME_STATE = tuple(Path(p) for p in ('/media/developer/cleanyourtv',
    '/var/lib/tvweb/home-takeover', '/var/lib/luma-home', '/var/lib/webosbrew/homechooser'))
secure = legacy.secure
atomic = legacy.atomic
boot_identity = legacy.boot_identity
verify_ready = legacy.verify_ready


def luna(uri,payload,timeout=5,allow_failure=False):
    # The controller runs as a standalone private runtime script, independently
    # of the provisioning process's package search path and working directory.
    try: from .transport import call
    except ImportError: from transport import call
    if allow_failure:
        return call(uri,payload,timeout=timeout,allow_failure=True)
    return call(uri,payload,timeout=timeout)


def admission_valid(value):
    """A recorded observation, not a compatibility claim or model allowlist."""
    if not isinstance(value,dict) or set(value)!={'model','firmware','webos','target_sha256','target'}:
        return False
    target=value['target']
    return (isinstance(value['model'],str) and re.fullmatch(r'[A-Za-z0-9._-]{1,128}',value['model']) is not None
        and isinstance(value['firmware'],str) and legacy.VERSION.fullmatch(value['firmware']) is not None
        and isinstance(value['webos'],str) and legacy.VERSION.fullmatch(value['webos']) is not None
        and isinstance(value['target_sha256'],str) and legacy.DIGEST.fullmatch(value['target_sha256']) is not None
        and isinstance(target,dict) and set(target)=={'dev','ino','size','mtime_ns'}
        and all(type(v) is int and 0<=v<2**63 for v in target.values()) and target['ino']>0 and target['size']>=52)


def selection(root=STATE, uid=0):
    path = Path(root)/'home-backend.json'
    if not os.path.lexists(path):
        if os.path.lexists(Path(root)/'c1-keyfilter'):
            raise ValueError('Missing compositor selection; retain recovery evidence')
        return None
    value = json.loads(secure(path, uid, 8192))
    if (not isinstance(value, dict) or set(value) != {'schema','backend','experimental','routing','native_sha256','admission'}
            or type(value['schema']) is not int or value['schema'] not in (2,3)
            or value['backend'] != BACKEND or value['routing'] != ROUTING or value['experimental'] is not True
            or not isinstance(value['native_sha256'],str) or not legacy.DIGEST.fullmatch(value['native_sha256'])
            or not (legacy.admission_valid(value['admission']) if value['schema']==2 else admission_valid(value['admission']))):
        raise ValueError('Invalid compositor selection; retain recovery evidence')
    return value


def validate_chain(value):
    if not isinstance(value,list) or len(value)>128:
        raise ValueError('Unknown configd filter chain')
    # Preserve arbitrary bounded JSON fields on foreign entries. Do not coerce
    # strings, missing chains, duplicate ownership, or malformed objects.
    if len(json.dumps(value, allow_nan=False).encode())>16384:
        raise ValueError('Oversized configd filter chain')
    for entry in value:
        if (not isinstance(entry,dict) or not isinstance(entry.get('file'),str)
                or not entry['file'].startswith('/') or len(entry['file'])>1024
                or not isinstance(entry.get('handler'),str)
                or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]{0,127}',entry['handler'])):
            raise ValueError('Malformed configd filter entry')
    return value


def read_chain():
    reply=luna('luna://com.webos.service.config/getConfigs', {'configNames':[KEY]})
    if not isinstance(reply,dict) or reply.get('returnValue') is not True or not isinstance(reply.get('configs'),dict):
        raise ValueError('Cannot read configd filter chain')
    return validate_chain(reply['configs'].get(KEY))


def write_chain(value,volatile=False):
    payload={'configs':{KEY:validate_chain(value)}}
    if volatile: payload['volatile']=True
    reply=luna('luna://com.webos.service.config/setConfigs', payload)
    if not isinstance(reply,dict) or reply.get('returnValue') is not True:
        raise ValueError('Configd did not acknowledge filter write')


def stock_chain(chain):
    chain=validate_chain(chain)
    if (not chain or sum(e['file'].endswith('/systemUi.js') and e['handler']=='handleSystemKeys' for e in chain)!=1
            or any(not re.fullmatch(r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js',e['file']) for e in chain)):
        raise ValueError('Stock Qt Home filter chain not verified')
    return chain


def vendor_script(path):
    # LG commonly aliases /usr/lib/qt5 to /usr/lib. Resolve that alias, then
    # apply the existing ownership/no-symlink checks to the actual vendor tree.
    canonical=Path(path).resolve(strict=True)
    if (canonical.name!=Path(path).name or not re.fullmatch(
            r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js',str(canonical))):
        raise ValueError('Key filter resolves outside the vendor tree')
    return secure(canonical,limit=256*1024)


def require_generic_environment():
    """Read-only admission. Never repair a foreign route, input or vendor file."""
    missing=luna('luna://com.webos.service.systemprofile/getProfiles',
                 {'names':['defaultApps','idleApp'],'subscribe':False},allow_failure=True)
    if (not isinstance(missing,dict) or missing.get('returnValue') is not False
            or type(missing.get('errorCode')) is not int or missing['errorCode']!=-1
            or missing.get('errorText')!='Service does not exist: com.webos.service.systemprofile.'):
        raise ValueError('System Profile absence was not confirmed')
    if any(os.path.lexists(p) for p in OTHER_HOME_STATE):
        raise ValueError('Another Home integration is present; preserve its state')
    if os.path.lexists(INPUT_BINDINGS):
        bindings=json.loads(secure(INPUT_BINDINGS,limit=65536))
        if not isinstance(bindings,dict) or '773' in bindings:
            raise ValueError('Foreign Home input binding; no takeover attempted')
    critical=(str(legacy.TARGET),str(STOCK_APPINFO.parent))
    mounts=MOUNTINFO.read_text()
    if len(mounts)>1024*1024: raise ValueError('Oversized mount table')
    system_image=False
    for line in mounts.splitlines():
        fields=line.split()
        if len(fields)<10 or ' - ' not in line: raise ValueError('Unknown mount topology')
        separator=fields.index('-')
        if separator<6 or len(fields)!=separator+4: raise ValueError('Unknown mount topology')
        target=re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),fields[4])
        if target!='/' and any(p==target or p.startswith(target+'/') for p in critical):
            # webOS can mount its whole immutable /usr image separately. This
            # is not a bind/overlay takeover of Home. Admit only an internal
            # MMC squashfs root, with both Home paths on that exact device;
            # additional covering mounts (including stacked /usr) still refuse.
            if (target=='/usr' and not system_image and fields[3]=='/'
                    and re.fullmatch(r'179:[0-9]+',fields[2])
                    and int(fields[2].split(':')[1])<256
                    and fields[separator+1]=='squashfs'
                    and re.fullmatch(r'/dev/mmcblk[0-9]+p[0-9]+',fields[separator+2])
                    and all('ro' in options.split(',') and 'rw' not in options.split(',')
                            for options in (fields[5],fields[separator+3]))):
                device=tuple(map(int,fields[2].split(':')))
                if all((os.major(s.st_dev),os.minor(s.st_dev))==device
                       for s in (os.stat(p,follow_symlinks=False) for p in critical)):
                    system_image=True
                    continue
            raise ValueError('Native Home is covered by a mount; no takeover attempted')
    app=json.loads(secure(STOCK_APPINFO,limit=65536))
    if (not isinstance(app,dict) or app.get('id')!=STOCK or app.get('type')!='native'
            or app.get('main') not in (str(legacy.TARGET),'file://'+str(legacy.TARGET))):
        raise ValueError('Stock native Home manifest not verified')
    chain=stock_chain(read_chain())
    for entry in chain:
        script=vendor_script(entry['file'])
        if entry['file'].endswith('/systemUi.js') and (
                b'Qt.Key_Super_L' not in script or not re.search(rb'function\s+handleSystemKeys\s*\(',script)):
            raise ValueError('Unknown Qt Home filter contract')
    try: from .emergency_reader import open_remote, query
    except ImportError: from emergency_reader import open_remote, query
    fd=open_remote()
    try:
        keys=query(fd,0x21,128)  # EVIOCGBIT(EV_KEY): advertised Home and Back.
        if any(not keys[code//8] & (1<<(code%8)) for code in (773,412)):
            raise ValueError('Emergency Home/Back input capabilities not verified')
    finally:
        os.close(fd)


def filter_entry(root=STATE):
    return {'file':str(Path(root)/'runtime/c1-home-filter.js'),'handler':'cytvC1HomeKey'}


def reconcile(chain, root, enabled):
    chain=validate_chain(chain)
    own=filter_entry(root)
    related=[entry for entry in chain if entry['file']==own['file'] or entry['handler']==own['handler']]
    if related and related != [own]:
        raise ValueError('Modified or duplicate owned filter; retain evidence')
    rest=[entry for entry in chain if entry != own]
    return [own]+rest if enabled else rest


def filter_present(root):
    chain=read_chain()
    return reconcile(chain,root,False)!=chain


def change_chain(root, enabled, uid=0):
    before=read_chain()
    generic=selection(root,uid)['schema']==3
    if generic and enabled:
        stock_chain(before)
    after=reconcile(before,root,enabled)
    directory=private_directory(root,uid)
    pending=directory/'pending.json'
    if os.path.lexists(pending):
        saved=json.loads(secure(pending,uid,65536))
        if (not isinstance(saved,dict) or set(saved)!={'schema','before','after','entry'}
                or type(saved['schema']) is not int or saved['schema']!=1 or saved['entry']!=filter_entry(root)):
            raise ValueError('Unknown pending filter transaction; retain evidence')
        reconcile(saved['before'],root,False)
        reconcile(saved['after'],root,False)
    if before==after:
        if not enabled and os.path.lexists(pending):
            if read_chain()!=before: raise ValueError('Concurrent filter recovery edit')
            pending.unlink()
        return

    receipt=directory/'ownership.json'
    own=filter_entry(root)
    if own in before:
        try: ownership=json.loads(secure(receipt,uid,4096))
        except FileNotFoundError: raise ValueError('Unknown owned filter; retain evidence')
        if (not isinstance(ownership,dict) or set(ownership)!={'schema','entry','token'}
                or type(ownership['schema']) is not int or ownership['schema']!=1
                or ownership['entry']!=own or not isinstance(ownership['token'],str)
                or not legacy.TOKEN.fullmatch(ownership['token'])):
            raise ValueError('Invalid filter ownership; retain evidence')
    if enabled:
        intent=read_intent(root,uid)
        atomic(receipt,dict(schema=1,entry=own,token=intent['token']),uid)
    pending=directory/'pending.json'
    # Durable inverse precedes every possible configd effect. Never restore an
    # old entire chain: the next operation reconciles the current foreign edits.
    atomic(pending, dict(schema=1,before=before,after=after,entry=filter_entry(root)),uid)
    if read_chain()!=before:
        raise ValueError('Concurrent configd edit; retain pending evidence')
    # Do not silently reinterpret retained schema2 persistent transactions.
    if generic:
        write_chain(after,volatile=True)
    else:
        write_chain(after)
    if read_chain()!=after:
        raise ValueError('Configd readback mismatch; retain pending evidence')
    pending.unlink()


def probe():
    if os.geteuid()!=0 or sys.platform!='linux':
        raise ValueError('Compositor admission requires an existing root TV session')
    # Keep schema2 admission isolated from schema1 checkpoint prerequisites.
    before=legacy.TARGET.stat()
    data=legacy.secure(legacy.TARGET,limit=4*1024*1024)
    info=luna('luna://com.webos.service.tv.systemproperty/getSystemInfo',
              {'keys':['modelName','firmwareVersion','sdkVersion']})
    try:
        value=legacy.admit(info,data)
    except ValueError:
        import struct
        value={key:info.get(field) for key,field in (('model','modelName'),('firmware','firmwareVersion'),('webos','sdkVersion'))} if isinstance(info,dict) else {}
        candidate=dict(value,target_sha256='0'*64,target=dict(dev=0,ino=1,size=len(data),mtime_ns=0))
        if (not isinstance(info,dict) or info.get('returnValue') is not True or struct.calcsize('P')!=4
                or len(data)<52 or data[:7]!=b'\x7fELF\x01\x01\x01' or data[18:20]!=b'\x28\0'
                or not admission_valid(candidate)):
            raise ValueError('Experimental compositor requires verified Qt Home capabilities and ARM32 native Home') from None
    require_generic_environment()
    after=legacy.TARGET.stat()
    identity=lambda st: dict(dev=st.st_dev,ino=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns)
    if identity(before)!=identity(after) or not before.st_mode & 0o111:
        raise ValueError('Native Home changed during compositor admission')
    read_chain()
    return dict(value,target_sha256=hashlib.sha256(data).hexdigest(),target=identity(after))


def private_directory(root, uid=0):
    directory=Path(root)/'c1-keyfilter'
    legacy.trusted_directory(directory,uid)
    info=directory.lstat()
    if info.st_uid!=uid or stat.S_IMODE(info.st_mode)!=0o700:
        raise ValueError('Unsafe compositor state directory')
    return directory


def write_config(root, admission, token, uid=0):
    target=admission['target']
    data=('CYTV-C1-KEYFILTER-1\ntoken '+token+'\nboot '+boot_identity()+'\n'+
          ''.join(key+' '+str(target[key])+'\n' for key in ('dev','ino','size','mtime_ns'))).encode()
    atomic(private_directory(root,uid)/'config',data,uid,raw=True)


def write_intent(root, enabled, token, phase, uid=0):
    value=dict(schema=1,enabled=enabled,token=token,phase=phase,boot=boot_identity())
    atomic(private_directory(root,uid)/'intent.json',value,uid)
    return value


def read_intent(root=STATE, uid=0):
    value=json.loads(secure(private_directory(root,uid)/'intent.json',uid,4096))
    if (not isinstance(value,dict) or set(value)!={'schema','enabled','token','phase','boot'}
            or type(value['schema']) is not int or value['schema']!=1 or type(value['enabled']) is not bool
            or value['phase'] not in ('disabled','starting','active','trial','recovering')
            or not isinstance(value['token'],str) or not legacy.TOKEN.fullmatch(value['token'])
            or not isinstance(value['boot'],str) or str(uuid.UUID(value['boot']))!=value['boot']):
        raise ValueError('Invalid compositor intent')
    return value


def prepare(root, native_sha256, admission, uid=0):
    root=Path(root)
    if (not isinstance(native_sha256,str) or not legacy.DIGEST.fullmatch(native_sha256)
            or not admission_valid(admission)):
        raise ValueError('Invalid compositor admission')
    legacy.trusted_directory(root,uid)
    if any(os.path.lexists(root/name) for name in ('home-backend.json','c1-gate','c1-keyfilter')):
        raise ValueError('Backend already prepared; retain evidence')
    (root/'c1-keyfilter').mkdir(mode=0o700)
    token=uuid.uuid4().hex
    write_config(root,admission,token,uid)
    write_intent(root,False,token,'disabled',uid)
    value=dict(schema=2 if legacy.admission_valid(admission) else 3,backend=BACKEND,experimental=True,routing=ROUTING,
               native_sha256=native_sha256,admission=admission)
    atomic(root/'home-backend.json',value,uid)
    return value


def binary(root=STATE, uid=0):
    saved=selection(root,uid)
    if saved is None: raise ValueError('Compositor backend not selected')
    private_directory(root,uid)
    path=Path(root)/'runtime/c1-keyfilter-guard'
    raw=secure(path,uid,4*1024*1024)
    if hashlib.sha256(raw).hexdigest()!=saved['native_sha256'] or not path.stat().st_mode & 0o111:
        raise ValueError('Verified compositor guardian unavailable')
    return path


def native(args, root=STATE, uid=0, timeout=12):
    reply=subprocess.run([str(binary(root,uid)),*args],stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C'},timeout=timeout,check=False)
    if len(reply.stdout)>16384 or reply.returncode:
        raise ValueError('Native compositor recovery failed; retain evidence')
    value=json.loads(reply.stdout)
    if args==['--selfcheck']:
        expected=dict(returnValue=True,backend=BACKEND,routing=ROUTING,selfcheck=True)
        if not isinstance(value,dict) or value!=expected or value.get('selfcheck') is not True or value.get('returnValue') is not True:
            raise ValueError('Incomplete native compositor selfcheck')
        return value
    return validate_native(value)


def validate_native(value):
    if (not isinstance(value,dict) or set(value)!={'returnValue','backend','routing','state','mounted','healthy','stock_verified','stopped','token','guardian_pid','reason','profiles'}
            or value.get('returnValue') is not True
            or value.get('backend')!=BACKEND or value.get('routing')!=ROUTING or value.get('profiles',{}) is not None
            or value.get('state') not in ('stock','armed','stopped','blocked')
            or any(type(value.get(k)) is not bool for k in ('mounted','healthy','stock_verified','stopped'))
            or value['mounted'] or not isinstance(value.get('token'),str) or not legacy.TOKEN.fullmatch(value['token'])
            or type(value.get('guardian_pid')) is not int or value['guardian_pid']<0
            or not isinstance(value.get('reason'),str) or not re.fullmatch(r'[a-z0-9_-]{0,80}',value['reason'])
            or value['healthy'] and (value['state']!='armed' or value['stopped'] or value['guardian_pid']<=1 or value['stock_verified'])
            or value['stock_verified'] and (value['guardian_pid'] or value['healthy'])
            or value['state']=='armed' and not value['healthy']):
        raise ValueError('Incomplete or inconsistent compositor guardian proof')
    return value


def status(root=STATE, uid=0):
    if selection(root,uid) is None: raise ValueError('Compositor backend not selected')
    value=dict(validate_native(native(['--status'],root,uid)))
    chain=read_chain()
    clean=reconcile(chain,root,False)==chain
    value['stock_verified']=value['stock_verified'] and clean
    value['healthy']=value['healthy'] and not clean
    value['filter_installed']=not clean
    value['routing_active']=value['healthy'] and not value['stopped']
    intent=read_intent(root,uid)
    active=value['healthy'] and not value['stopped'] and intent['token']==value['token'] and intent['phase'] in ('active','trial')
    phase=intent['phase'] if active else 'disabled' if value['stock_verified'] else 'recovering'
    try: recovery=verify_ready()
    except (OSError,ValueError,RuntimeError,ImportError): recovery={'integrity_verified':False}
    return dict(backend=BACKEND,routing=ROUTING,experimental=True,effective=value,
        intent=dict(intent,phase=phase,enabled=bool(active and intent['enabled'])),recovery=recovery,
        candidate=APP,update_home_resume_available=False,persistent_enable_available=recovery.get('integrity_verified') is True)


@contextmanager
def operation(root=STATE,uid=0):
    import fcntl
    path=private_directory(root,uid)/'operation.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode & 0o077:
            raise ValueError('Unsafe compositor operation lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally: os.close(fd)



class ReturnPolicy:
    """A return hint is cancellable and never itself permission to launch."""
    def __init__(self,token):
        self.token=token; self.content=None; self.pending=None; self.generation=0

    def event(self,value,now):
        self.generation+=1
        if (not isinstance(value,dict) or value.get('event') not in ('foreground','stop')
                or not isinstance(value.get('appId'),str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,255}',value['appId'])
                or value.get('windowType')!=CARD):
            self.pending=None; return
        app=value['appId']
        if value['event']=='foreground':
            self.pending=None
            if app==STOCK: self.pending=now+1.0
            elif app!=APP: self.content=app
        elif app==self.content:
            self.pending=now+1.0; self.content=None

    def due(self,now):
        return self.pending is not None and now>=self.pending


def can_return(surfaces,power,proof,token,foreground=None):
    try: validate_native(proof)
    except ValueError: return False
    if (not proof['healthy'] or proof['stopped'] or proof['token']!=token
            or not isinstance(power,dict) or power.get('returnValue') is not True or power.get('state')!='Active'
            or not isinstance(surfaces,dict) or surfaces.get('returnValue') is not True): return False
    if (not isinstance(foreground,dict) or foreground.get('returnValue') is not True
            or not isinstance(foreground.get('appId'),str) or foreground['appId'] not in ('',STOCK)):
        return False
    rows=surfaces.get('foregroundAppInfo')
    if not isinstance(rows,list) or len(rows)>128: return False
    if not rows:
        return isinstance(foreground,dict) and foreground.get('returnValue') is True and foreground.get('appId')==''
    for row in rows:
        if (not isinstance(row,dict) or row.get('displayId',0)!=0 or row.get('windowType')!=CARD
                or row.get('appId')!=STOCK or row.get('pip',False) is not False
                or row.get('multiview',False) is not False or row.get('viewType','normal')!='normal'):
            return False
    return True


def process_start(pid):
    # /proc stat comm may contain spaces and parentheses.
    raw=Path('/proc')/str(pid)/'stat'
    fields=raw.read_text().rsplit(')',1)[1].split()
    return int(fields[19])


def stop_controller(root,uid):
    path=private_directory(root,uid)/'controller.json'
    try: value=json.loads(secure(path,uid,4096))
    except FileNotFoundError: return
    generic=selection(root,uid)['schema']==3
    fields={'pid','start','token','boot'} if generic else {'pid','start','token'}
    if (not isinstance(value,dict) or set(value)!=fields
            or type(value['pid']) is not int or value['pid']<=1 or type(value['start']) is not int
            or not isinstance(value['token'],str) or not legacy.TOKEN.fullmatch(value['token'])):
        raise ValueError('Unknown lifecycle controller identity; retain evidence')
    if generic:
        if not isinstance(value['boot'],str) or str(uuid.UUID(value['boot']))!=value['boot']:
            raise ValueError('Unknown lifecycle controller boot; retain evidence')
        if value['boot']!=boot_identity():
            # Native routing has already stopped. A controller from a previous
            # boot cannot own any current PID; never wait for or signal it.
            path.unlink()
            return
    pid=value['pid']
    try:
        if process_start(pid)!=value['start']:
            raise ValueError('Lifecycle controller PID changed; retain evidence')
        # The native stop latch makes the controller exit on its next bounded
        # status read. Never signal a PID across a check/kill race on old kernels
        # without pidfd; uncertainty keeps the inert filter and recovery record.
        end=time.monotonic()+3
        while time.monotonic()<end:
            try:
                if process_start(pid)!=value['start']: break
                # A zombie no longer executes a launch and may await its parent.
                state=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[0]
                if state=='Z': break
            except FileNotFoundError: break
            time.sleep(.05)
        else: raise ValueError('Lifecycle controller did not retire')
    except ProcessLookupError: pass
    except FileNotFoundError: pass
    path.unlink()


def restore_locked(root,uid):
    native(['--restore'],root,uid)
    after=validate_native(native(['--status'],root,uid))
    generic=selection(root,uid)['schema']==3
    if after['healthy'] or not after['stopped'] or after['guardian_pid'] or (not generic and not after['stock_verified']):
        raise ValueError('Native stop retirement unverified; retain evidence')
    write_intent(root,False,after['token'],'recovering',uid)
    stop_controller(root,uid)
    change_chain(root,False,uid)
    if not after['stock_verified']:
        raise ValueError('Home identity changed; owned filter removed, recovery evidence retained')
    write_intent(root,False,after['token'],'disabled',uid)
    return 'restored'


def read_handshake(fd,expected,children,seconds=8):
    end=time.monotonic()+seconds; response=b''
    while time.monotonic()<end:
        if any(child.poll() is not None for child in children): break
        if select.select([fd],[],[],min(.1,max(0,end-time.monotonic())))[0]:
            chunk=os.read(fd,256)
            if not chunk: break
            response+=chunk
            if len(response)>128 or b'\n' in response: break
    if response!=expected or any(child.poll() is not None for child in children):
        raise ValueError('Independent compositor protection startup unverified')


def start_controller(root,uid,token,control_fd,log):
    from python_binding import command
    ready_read,ready_write=os.pipe()
    child=None
    try:
        child=subprocess.Popen([command(root),str(Path(root)/'runtime/c1_keyfilter.py'),
            '--watch',token,str(control_fd),str(ready_write)],pass_fds=(control_fd,ready_write),
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
        os.close(ready_write); ready_write=None
        record=dict(pid=child.pid,start=process_start(child.pid),token=token)
        if selection(root,uid)['schema']==3: record['boot']=boot_identity()
        atomic(private_directory(root,uid)/'controller.json',record,uid)
        read_handshake(ready_read,('WATCH '+token+'\n').encode(),[child])
        return child
    except BaseException:
        if child is not None and child.poll() is None:
            child.terminate()
            try: child.wait(timeout=2)
            except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=1)
        raise
    finally:
        os.close(ready_read)
        if ready_write is not None: os.close(ready_write)


def enable_locked(root,uid,seconds):
    descriptor=selection(root,uid)
    if descriptor is None: raise ValueError('Compositor backend not selected')
    if verify_ready().get('integrity_verified') is not True:
        raise ValueError('Verified recovery manifest required')
    current=validate_native(native(['--status'],root,uid))
    if current['healthy'] or current['guardian_pid'] or not current['stock_verified']:
        raise ValueError('Restore previous compositor attempt before enabling')
    # Existing own entries, including interrupted attempts, require explicit Off.
    before=read_chain()
    if reconcile(before,root,False)!=before or os.path.lexists(Path(root)/'c1-keyfilter/pending.json'):
        raise ValueError('Restore interrupted filter transaction before enabling')
    if probe()!=descriptor['admission']:
        raise ValueError('C1 admission changed')
    from helper_bridge import require_idle
    require_idle()
    helper=binary(root,uid)
    # Verify the filter is protected before configd is allowed to read it.
    secure(Path(root)/'runtime/c1-home-filter.js',uid,65536)
    token=uuid.uuid4().hex
    write_config(root,descriptor['admission'],token,uid)
    write_intent(root,seconds==0,token,'starting',uid)
    fds=[]; children=[]
    try:
        change_chain(root,True,uid)
        input_read,input_write=os.pipe(); fds.extend([input_read,input_write])
        control_read,control_write=os.pipe(); fds.extend([control_read,control_write])
        ready_read,ready_write=os.pipe(); fds.extend([ready_read,ready_write])
        log=os.open(private_directory(root,uid)/'native.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
        fds.append(log)
        info=os.fstat(log)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode & 0o077:
            raise ValueError('Unsafe compositor recovery log')
        controller=start_controller(root,uid,token,control_write,log); children.append(controller)
        os.close(control_write); fds.remove(control_write)
        from python_binding import command
        observer=subprocess.Popen([command(root),str(Path(root)/'runtime/emergency_reader.py'),str(input_write)],
            pass_fds=(input_write,),stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
        children.append(observer)
        os.close(input_write); fds.remove(input_write)
        guard=subprocess.Popen([str(helper),'--guard',token,str(input_read),str(control_read),str(ready_write),str(seconds)],
            pass_fds=(input_read,control_read,ready_write),stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            env={'PATH':'/usr/bin:/bin','LANG':'C'},start_new_session=True,close_fds=True)
        children.append(guard)
        for fd in (input_read,control_read,ready_write): os.close(fd); fds.remove(fd)
        read_handshake(ready_read,('ARMED '+token+'\n').encode(),children)
        after=validate_native(native(['--status'],root,uid))
        if not after['healthy'] or after['token']!=token:
            raise ValueError('Guardian stopped during activation')
        write_intent(root,seconds==0,token,'trial' if seconds else 'active',uid)
        result=status(root,uid)
        if not result['effective']['healthy']: raise ValueError('Compositor lease not active')
        return result
    except BaseException:
        try: restore_locked(root,uid)
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=1)
        raise
    finally:
        for fd in fds: os.close(fd)


def execute(mode,transaction=None,root=STATE,uid=0):
    if mode=='status': return status(root,uid)
    with operation(root,uid):
        if mode in ('restore','boot'):
            # No failed-attempt retry or same-boot automatic rearm. The filter
            # retains fail-open semantics until an explicit Enable.
            return restore_locked(root,uid)
        if mode in ('enable','trial','intent-trial','emergency-trial'):
            return enable_locked(root,uid,0 if mode=='enable' else 60)
    raise ValueError('Unsupported compositor lifecycle operation')


def return_ready(root,uid,token,changed):
    # Every RPC can deliver a lifecycle change concurrently. Discard the entire
    # delayed hint after any such message, including unknown/partial messages.
    intent=read_intent(root,uid)
    if intent['token']!=token or intent['phase'] not in ('active','trial'): return False
    power=luna('luna://com.webos.service.tvpower/power/getPowerState',{},timeout=.3)
    if changed(): return False
    surfaces=luna('luna://com.webos.surfacemanager/getForegroundAppInfo',{},timeout=.3)
    if changed(): return False
    foreground=luna('luna://com.webos.applicationManager/getForegroundAppInfo',{},timeout=.3)
    if changed(): return False
    proof=validate_native(native(['--status'],root,uid,timeout=.3))
    if changed(): return False
    if selection(root,uid)['schema']==3 and (not filter_present(root) or changed()): return False
    intent=read_intent(root,uid)
    return (intent['token']==token and intent['phase'] in ('active','trial')
            and can_return(surfaces,power,proof,token,foreground))


def launch_return(root,uid,token):
    # Native statelock serializes this fixed Root launch against stop/restore.
    # A stale controller cannot issue a free-standing LS2 launch after Off.
    proof=validate_native(native(['--home',token],root,uid,timeout=2.5))
    if not proof['healthy'] or proof['stopped'] or proof['token']!=token:
        raise ValueError('Lifecycle launch barrier lost the active token')
    return proof


def watch(token,control,ready,root=STATE,uid=0):
    """Persistent LS2 controller; loss of subscription retires CONTROL lease."""
    if not legacy.TOKEN.fullmatch(token): raise ValueError('Invalid controller token')
    # Fixed subscription only; stdin remains open for old luna-send versions.
    child=subprocess.Popen(['/usr/bin/luna-send','-i','luna://com.webos.applicationManager/getAppLifeEvents',
        '{"subscribe":true}'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    os.set_blocking(control,False)
    policy=ReturnPolicy(token); buffer=b''; initialized=False; armed=False; started=time.monotonic()
    def send(data):
        if os.write(control,data)!=len(data): raise ValueError('Partial controller health write')
    try:
        while child.poll() is None:
            now=time.monotonic()
            if not initialized and now-started>5: raise ValueError('Lifecycle subscription timeout')
            if select.select([child.stdout],[],[],.1)[0]:
                data=os.read(child.stdout.fileno(),8192)
                if not data: raise ValueError('Lifecycle subscription ended')
                buffer+=data
                if len(buffer)>65536: raise ValueError('Oversized lifecycle subscription')
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    if not line.strip(): continue
                    value=json.loads(line)
                    if not isinstance(value,dict) or value.get('returnValue') is not True:
                        raise ValueError('Lifecycle subscription failed')
                    if not initialized:
                        if value.get('subscribed') is not True: raise ValueError('Lifecycle subscription not acknowledged')
                        send(b'READY\n')
                        if os.write(ready,('WATCH '+token+'\n').encode())!=len('WATCH '+token+'\n'):
                            raise ValueError('Controller readiness write failed')
                        os.close(ready); ready=None; initialized=True
                    if 'event' in value: policy.event(value,time.monotonic())
            if not initialized: continue
            intent=read_intent(root,uid)
            if intent['token']!=token or intent['phase'] not in ('starting','active','trial'):
                raise ValueError('Lifecycle intent inactive')
            # At most a brief startup grace while the parent starts the guard.
            proof=validate_native(native(['--status'],root,uid,timeout=.3))
            live=proof['token']==token and proof['healthy'] and not proof['stopped']
            if selection(root,uid)['schema']==3 and not filter_present(root):
                raise ValueError('Volatile compositor filter lost; explicit Enable required')
            if live: armed=True
            if not live and (armed or time.monotonic()-started>8):
                raise ValueError('Controller token inactive')
            send(b'PING\n')
            if armed and policy.due(time.monotonic()):
                policy.pending=None
                generation=policy.generation
                changed=lambda: generation!=policy.generation or bool(buffer.strip()) or bool(select.select([child.stdout],[],[],0)[0])
                if return_ready(root,uid,token,changed):
                    send(b'PING\n')
                    launch_return(root,uid,token)
    finally:
        try: send(b'LOST\n')
        except OSError: pass
        os.close(control)
        if ready is not None: os.close(ready)
        if child.poll() is None: child.terminate()
        try: child.communicate(timeout=1)
        except subprocess.TimeoutExpired: child.kill(); child.communicate()


if __name__=='__main__':
    if os.geteuid()!=0 or len(sys.argv)!=5 or sys.argv[1]!='--watch':
        raise SystemExit('Root and private controller channels required')
    watch(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]))
