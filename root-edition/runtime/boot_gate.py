"""Normal startup evidence and independently guarded retained-route continuation.

The init.d hook only writes a current-boot marker and returns. Waiting inside
that hook would deadlock: Homebrew clears its flag after run-parts returns.
Continuation rotates health authority while retaining the original Home inverse;
uncertain startup or interrupted authority writes recover through that inverse.
"""
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import uuid
import device_adapter as d
from persistent_lifecycle import transition, validate as validate_intent
from profile_recovery import validate, journal_payload

ROOT = Path('/tmp/clean-your-tv-root-boot')


def mark():
    from intent_runtime import boot_identity
    if os.geteuid() != d.EXPECTED_UID: raise PermissionError('Root required')
    try: ROOT.mkdir(mode=0o700)
    except FileExistsError: pass
    d.trusted_dir(ROOT)
    fd, name = tempfile.mkstemp(dir=ROOT, prefix='.normal-')
    try:
        with os.fdopen(fd,'w') as out:
            json.dump({'version':1,'boot':boot_identity()},out)
        os.replace(name,ROOT/'normal.json')
    finally:
        if os.path.lexists(name): os.unlink(name)


def observation():
    from intent_runtime import boot_identity
    normal = False
    try:
        d.trusted_dir(ROOT)
        value = d.safe_json(ROOT/'normal.json')
        normal = value == {'version':1,'boot':boot_identity()}
    except (OSError,ValueError): pass
    # lexists also fails closed on an unexpected symlink.
    return normal, os.path.lexists(d.FAILSAFE)


def audit(event, **details):
    d.trusted_dir(d.STATE)
    fd, name = tempfile.mkstemp(dir=d.STATE, prefix='.boot-decision-')
    try:
        with os.fdopen(fd,'w') as out:
            json.dump(dict(event=event,uptime=time.monotonic(),**details),out)
            out.flush(); os.fsync(out.fileno())
        os.replace(name,d.STATE/'boot-decision.json')
    finally:
        if os.path.lexists(name):os.unlink(name)


def wait(observe=observation, timeout=35, clock=time.monotonic, sleep=time.sleep):
    deadline = clock()+timeout
    while True:
        normal, flag = observe()
        if normal and not flag: return True
        remaining = deadline-clock()
        if remaining <= 0: return False
        sleep(min(.25, remaining))


NAME = 'boot-continuation.json'


def save(value):
    fd, name = tempfile.mkstemp(dir=d.STATE, prefix='.boot-continuation-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out); out.flush(); os.fsync(out.fileno())
        os.replace(name, d.STATE/NAME); d.sync(d.STATE)
    finally:
        if os.path.exists(name): os.unlink(name)


def load():
    if not os.path.lexists(d.STATE/NAME): return None
    try: value = d.safe_json(d.STATE/NAME)
    except FileNotFoundError: return None
    if (not isinstance(value, dict) or set(value) != {'version','phase','prior','intent','previous','binding','old_route','route'}
            or type(value['version']) is not int or value['version'] != 1
            or value['phase'] not in ('waiting','released')):
        raise ValueError('Invalid boot continuation')
    return validate_record(value)


def validate_record(value):
    if (not isinstance(value, dict) or set(value) != {'version','phase','prior','intent','previous','binding','old_route','route'}
            or type(value['version']) is not int or value['version'] != 1
            or value['phase'] not in ('waiting','released')):
        raise ValueError('Invalid boot continuation')
    prior = validate_intent(value['prior']); intent = validate_intent(value['intent'])
    expected, effect = transition(prior, dict(kind='resume', generation=prior['generation'],
                                            token=intent['token'], boot=intent['boot']))
    if intent != expected or effect != 'continue_guarded': raise ValueError('Invalid continuation intent')
    old = value['old_route']; new = value['route']; validate(old); validate(new)
    deadline = new.get('deadline')
    if (old.get('state') != 'pending' or new.get('state') != 'pending'
            or type(deadline) not in (int,float) or not math.isfinite(deadline)
            or new.get('transaction') == old.get('transaction')
            or dict(new, transaction=old.get('transaction'), deadline=old.get('deadline')) != old):
        raise ValueError('Invalid continuation route')
    for key, state, route in (('previous',prior,old), ('binding',intent,new)):
        if value[key] != dict(version=1,generation=state['generation'],token=state['token'],
                              transaction=route.get('transaction'),restored=False):
            raise ValueError('Invalid continuation binding')
    return value


def predecessor_absent(transaction):
    # Start ticks are checked independently of boot identity: a snapshot may
    # preserve processes despite resetting uptime and reusing the kernel ID.
    for name, fields in (('profile-guardian-ready.json', (('pid','start_ticks'),)),
                         ('escape-ready.json', (('pid','start_ticks'),('observer_pid','observer_start_ticks')))):
        ready = d.safe_json(d.STATE/name)
        if ready.get('transaction') != transaction: return False
        for pid_key, ticks_key in fields:
            pid = ready.get(pid_key); ticks = ready.get(ticks_key)
            if type(pid) is not int or pid <= 0 or not isinstance(ticks,str) or not ticks:
                return False
            try: current = d.process_start(pid)
            except FileNotFoundError: continue
            if current == ticks: return False
    return True


def owned(route):
    payload = journal_payload(route); identity = route.get('candidate_identity', {})
    fd = os.open(d.TARGET, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != d.EXPECTED_UID
                or info.st_mode & 0o022 or info.st_nlink != 1 or info.st_size != len(payload)
                or any(type(identity.get(k)) is not int for k in ('device','inode'))
                or (info.st_dev,info.st_ino) != (identity['device'],identity['inode'])
                or source.read(len(payload)+1) != payload
                or tuple(getattr(d.TARGET.lstat(),k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns'))
                   != tuple(getattr(info,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns'))):
            raise ValueError('Retained Home profile ownership changed')
    if os.path.lexists(d.STATE/'profile-candidate.stage'):
        raise ValueError('Unfinished profile publication')
    expected = copy.deepcopy(route['baseline']); candidate = route['candidate']
    expected['sam_home'] = candidate
    expected['profiles']['defaultApps']['categories']['home'] = candidate
    expected['profiles']['idleApp']['appId'] = candidate
    if d.read() != expected: raise ValueError('Retained Home route changed')


def eligible(c, prior, boot):
    if (prior['phase'] not in ('active','stopping') or not prior['enabled']
            or prior['boot'] == boot or os.path.lexists(d.STATE/NAME)):
        return False
    try:
        binding = c.read_binding(); route = c.route(binding['transaction'])
        if (binding != dict(version=1,generation=prior['generation'],token=prior['token'],
                            transaction=route['transaction'],restored=False)
                or route['state'] != 'pending' or not predecessor_absent(route['transaction'])): return False
        owned(route)
        return True
    except (OSError,ValueError,TypeError,KeyError): return False


def repair(c):
    """Recovery-only: repair a torn binding using the authenticated saved tuple.

    Caller holds the operation lock. This never promotes intent or routes; all
    surviving combinations proceed through ordinary original-baseline recovery.
    """
    value = load()
    if value is None: return
    intent = c.store.read()
    if not any(all(intent[k] == state[k] for k in ('generation','token','boot'))
               for state in (value['prior'], value['intent'])):
        raise ValueError('Continuation belongs to another lifecycle')
    route = d.safe_json(d.STATE/'profile-trial.json'); validate(route)
    original = next((x for x in (value['old_route'],value['route'])
                     if x['transaction'] == route.get('transaction')), None)
    if original is None or route['baseline'] != original['baseline']:
        raise ValueError('Continuation recovery route changed')
    # Recovery may already have durably advanced the journal or converted a
    # completed v2 record to v1. The normal validator checks that terminal form.
    expected = dict(original,state=route['state'])
    if original['version'] == 2 and route['state'] == 'restored':
        from profile_recovery import DIGEST
        expected.update(version=1,payload_sha256=DIGEST,completed_payload_sha256=original['payload_sha256'])
    if route != expected: raise ValueError('Continuation recovery authority changed')
    c.write_binding(dict(version=1,generation=intent['generation'],token=intent['token'],
                         transaction=route['transaction'],restored=route['state']=='restored'))


def waiting(transaction):
    value = load()
    if value is None or value['route']['transaction'] != transaction: return False
    from persistent_recovery import Coordinator
    from persistent_store import Store
    c = Coordinator(Store(d.STATE)); intent = c.store.read()
    matching = intent == value['intent'] or (value['phase'] == 'released'
                and intent == dict(value['intent'],phase='active'))
    d.require_home(purpose='live')
    if (not matching or c.read_binding() != value['binding']
            or c.route(transaction) != value['route']
            or time.monotonic() >= value['route']['deadline']-20):
        raise ValueError('Boot continuation is no longer pending')
    return value['phase'] == 'waiting'


def remove():
    (d.STATE/NAME).unlink(); d.sync(d.STATE)


def prepare(c, prior, boot):
    """Caller recovers any uncertain durable write before reporting a failure."""
    from provision import verify
    from helper_bridge import require_idle
    from intent_runtime import boot_identity
    verify(); require_idle()
    with c.locked(prior):
        fd = os.open(d.STATE/'profile-trial.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if boot_identity() != boot or not eligible(c,prior,boot):
                raise ValueError('Retained Home cannot be continued')
            d.require_home()
            old_binding = c.read_binding(); old = c.route(old_binding['transaction'])
            token = str(uuid.uuid4())
            intent, _ = transition(prior,dict(kind='resume',generation=prior['generation'],token=token,boot=boot))
            route = dict(old, transaction=str(uuid.uuid4()), deadline=time.monotonic()+60)
            binding = dict(version=1,generation=intent['generation'],token=token,
                           transaction=route['transaction'],restored=False)
            value = dict(version=1,phase='waiting',prior=prior,intent=intent,
                         previous=old_binding,binding=binding,old_route=old,route=route)
            monitor = arm_bootstrap(value)
            try:
                save(value)  # Before changing any authority; repair handles every prefix.
                c.event(prior,'resume',boot=boot,token=token)
                d.save(route)
                c.write_binding(binding)
            except BaseException:
                monitor.close()
                raise
        finally: os.close(fd)
    return value, monitor


def start(c, prior, boot):
    """Keep routing, rotate authority, then arm fresh independent protection."""
    import emergency_trial
    try:
        value, monitor = prepare(c,prior,boot)
    except BaseException:
        current = c.store.read()
        if current == prior or load() is not None:
            c.exit(current,reason='fault')
        raise
    intent = value['intent']; route = value['route']
    # The operation lock is released so ESCAPE/LOST can recover immediately.
    # The fixed guardian deadline is never reset after waiting for the boot gate.
    try:
        child = emergency_trial.spawn_guarded(route['transaction'])
        monitor.disarm()
        from boot_gate import wait
        remaining = route['deadline']-20-time.monotonic()
        if remaining <= 0 or not wait(timeout=min(35,remaining)):
            raise RuntimeError('Normal startup was not verified')
        with c.locked(intent):
            if child.poll() is not None or not waiting(route['transaction']):
                raise ValueError('Continuation protection stopped')
            from boot_gate import observation
            if observation() != (True,False): raise ValueError('Normal startup changed')
            owned(route)
            save(dict(value,phase='released'))
        from persistent_health import require_fresh
        while time.monotonic() < route['deadline']-20:
            try: require_fresh(route['transaction']); break
            except (OSError,ValueError):
                if child.poll() is not None: raise RuntimeError('Continuation observer exited')
                time.sleep(.1)
        with c.locked(intent):
            c._healthy(intent)
            updated, effect = c.event(intent,'ready')
            remove()
        return dict(intent=updated,effect=effect,transaction=route['transaction'],persistent=True)
    except BaseException:
        current = c.store.read()
        if (current['generation'],current['token']) == (intent['generation'],intent['token']):
            c.exit(current,reason='fault')
        raise
    finally:
        monitor.close()


class BootstrapMonitor:
    def __init__(self, process, fd):
        self.process = process; self.fd = fd

    def close(self):
        if self.fd is not None:
            os.close(self.fd); self.fd = None
        if self.process.poll() is not None: self.process.wait()

    def disarm(self):
        if self.process.poll() is not None: raise RuntimeError('Bootstrap recovery monitor exited')
        os.write(self.fd,b'ARMED\n'); self.close()
        if self.process.wait(timeout=2) != 0:
            raise RuntimeError('Bootstrap protection transfer failed')


def arm_bootstrap(value):
    """Independent recovery deadline + parent-death pipe before durable changes."""
    import select
    import subprocess
    read_fd, write_fd = os.pipe(); ack_read, ack_write = os.pipe(); process = None
    try:
        process = subprocess.Popen([d.current_executable(),str(Path(__file__).resolve()),
                                    'bootstrap',str(read_fd),str(ack_write)],
            pass_fds=(read_fd,ack_write),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)
        os.close(read_fd); read_fd = None
        os.close(ack_write); ack_write = None
        data = (json.dumps(value)+'\n').encode()
        if len(data) > 65536: raise ValueError('Oversized bootstrap recovery record')
        while data:
            count = os.write(write_fd,data); data = data[count:]
        if not select.select([ack_read],[],[],min(5,max(0,value['route']['deadline']-time.monotonic())))[0]:
            raise RuntimeError('Bootstrap recovery monitor not ready')
        if os.read(ack_read,16) != b'READY\n' or process.poll() is not None:
            raise RuntimeError('Bootstrap recovery monitor refused startup')
        monitor = BootstrapMonitor(process,write_fd); write_fd = None
        return monitor
    finally:
        for fd in (read_fd,write_fd,ack_read,ack_write):
            if fd is not None: os.close(fd)


def watch_bootstrap(fd, deadline, recover):
    import select
    data = b''
    while time.monotonic() < deadline:
        if not select.select([fd],[],[],min(.25,max(0,deadline-time.monotonic())))[0]: continue
        chunk = os.read(fd,16)
        if not chunk: break
        data += chunk
        if data == b'ARMED\n': return 'armed'
        if len(data) > 16 or b'\n' in data: break
    recover()
    return 'recovered'


def bootstrap(read_fd, ready_fd):
    from persistent_recovery import Coordinator
    from persistent_store import Store
    if os.geteuid() != d.EXPECTED_UID: raise PermissionError('Root bootstrap required')
    with os.fdopen(read_fd,'rb',buffering=0) as source:
        value = validate_record(json.loads(source.readline(65537)))
        c = Coordinator(Store(d.STATE)); prior = value['prior']; intent = value['intent']
        if c.store.read() != prior or c.read_binding() != value['previous']:
            raise ValueError('Bootstrap recovery source changed')
        if not time.monotonic() < value['route']['deadline'] <= time.monotonic()+60:
            raise ValueError('Invalid bootstrap recovery deadline')
        def recover():
            for attempt in range(120):
                current = c.store.read()
                if not any(all(current[k] == x[k] for k in ('generation','boot','token'))
                           for x in (prior,intent)): return
                try:
                    c.exit(current,reason='fault'); return
                except (OSError,ValueError,RuntimeError): time.sleep(.25)
            raise RuntimeError('Bootstrap recovery remains incomplete')
        os.write(ready_fd,b'READY\n'); os.close(ready_fd)
        return watch_bootstrap(source.fileno(),value['route']['deadline'],recover)


if __name__ == '__main__':
    if sys.argv[1:] == ['mark']: mark()
    elif len(sys.argv) == 4 and sys.argv[1] == 'bootstrap':
        bootstrap(int(sys.argv[2]),int(sys.argv[3]))
    else: raise ValueError('Expected mark or bootstrap')
