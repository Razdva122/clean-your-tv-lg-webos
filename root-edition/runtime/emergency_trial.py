"""Opt-in bounded emergency-exit trial; permanent activation remains unavailable."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading
import device_adapter as d
import bounded_profile_trial as bounded
from emergency_watchdog import watch

HEARTBEAT_TIMEOUT = 2


class BootInputMissing(RuntimeError):
    """Confirmed boot preference, but a new profile cannot be published yet."""


def record(value, error=False):
    try: print(json.dumps(value),file=sys.stderr if error else sys.stdout,flush=True)
    except Exception: pass  # Diagnostic storage never authorizes or blocks recovery.


def save_ready(transaction, observer, input_state=None):
    value = {'transaction':transaction, 'pid':os.getpid(),
             'start_ticks':d.process_start(os.getpid()), 'observer_pid':observer.pid,
             'observer_start_ticks':d.process_start(observer.pid)}
    if input_state is not None: value['input_state']=input_state
    fd, name = tempfile.mkstemp(dir=d.STATE, prefix='.escape-ready-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f); f.flush(); os.fsync(f.fileno())
        os.replace(name, d.STATE/'escape-ready.json'); d.sync(d.STATE)
    finally:
        if os.path.exists(name): os.unlink(name)


def completed(transaction):
    j = d.safe_json(d.STATE/'profile-trial.json')
    return j['transaction'] != transaction or j['state'] in ('restored','conflict')


def recover(transaction, reason, *, fault_at=None):
    record({'event':'emergency-recovery','transaction':transaction,'reason':reason,
            'pid':os.getpid(),'uptime':time.monotonic()})
    for _ in range(30):
        try:
            from persistent_recovery import bound_exit
            bound = bound_exit(transaction, reason=reason, fault_at=fault_at)
            result = 'restored' if bound is True else d.restore_once(expected_transaction=transaction)
        except (OSError, ValueError, RuntimeError): result = 'recovering'
        if result == 'superseded': return True  # No writes to a later transaction.
        if result == 'restored':
            j = d.safe_json(d.STATE/'profile-trial.json')
            if j['transaction'] != transaction: return True
            # A bound confirmed shutdown retains its pending profile for bootd.
            if bound is True and j['state'] == 'pending': return True
            if d.read() != j['baseline']: return False
            # Routing is already restored even if this optional screen launch fails.
            try: d.sam_transport().call('luna://com.webos.applicationManager/launch', {'id':'com.webos.app.home'})
            except Exception as exc: record({'screen_launch_error':str(exc)})
            return True
        if result == 'conflict': return False
        time.sleep(.2)
    return False  # Independent deadline and boot recovery remain armed.


def startup_deadline(transaction):
    """Leave the existing twenty-second publication/recovery reserve untouched."""
    journal=d.safe_json(d.STATE/'profile-trial.json')
    deadline=journal.get('deadline');now=time.monotonic()
    if (journal.get('transaction')!=transaction or journal.get('state')!='pending'
            or type(deadline) not in (int,float) or not math.isfinite(deadline)
            or not now+20<deadline<=now+90):
        raise ValueError('Invalid or exhausted guarded startup deadline')
    return deadline-20


def supervise(transaction):
    d.trusted_dir(d.STATE)
    j = d.safe_json(d.STATE/'profile-trial.json')
    if j['transaction'] != transaction or j['state'] != 'pending': return
    r, w = os.pipe(); observer = None
    try:
        from persistent_recovery import Coordinator
        from persistent_store import Store
        c=Coordinator(Store(d.STATE))
        bound=os.path.lexists(c.binding) and c.read_binding()['transaction']==transaction
        if bound:
            from boot_gate import waiting
            pending_gate=waiting(transaction)
            from persistent_health import context, require_guardian
            deadline=startup_deadline(transaction)
            # Cold expected-package validation belongs before the input loop.
            # A READY pipe event alone must not start the parent's health wait.
            if not pending_gate: context(transaction)
            while time.monotonic()<deadline:
                try:
                    require_guardian(transaction);break
                except (OSError,ValueError):time.sleep(min(.1,max(0,deadline-time.monotonic())))
            else:raise RuntimeError('Guardian not ready within guarded startup deadline')
        observer = subprocess.Popen([d.current_executable(), str(Path(__file__).with_name('emergency_reader.py')),
                                     str(w), '--recover-profile-input' if bound else '--report-device-gone'],
                                    pass_fds=(w,), stdin=subprocess.DEVNULL, close_fds=True)
        os.close(w); w = None
        sequence = [0]
        health_ready = [False]
        def ping(waiting_since=None):
            started=time.monotonic()
            # Legacy trials have no durable binding and keep their fixed timer.
            from persistent_recovery import Coordinator
            from persistent_store import Store
            c = Coordinator(Store(d.STATE))
            if not os.path.lexists(c.binding): return
            if c.read_binding()['transaction'] != transaction: return
            from persistent_health import publish, require_guardian
            require_guardian(transaction)
            from boot_gate import waiting
            gate=waiting(transaction)
            if not gate:
                sequence[0] += 1
                if waiting_since is None:
                    publish(transaction, sequence[0])
                else:
                    publish(transaction, sequence[0],waiting_since=waiting_since)
            if time.monotonic()-started>=HEARTBEAT_TIMEOUT:
                raise RuntimeError('Input heartbeat validation exceeded watchdog deadline')
            if not health_ready[0]:
                state='boot-gate' if gate else ('active' if waiting_since is None else 'waiting-input')
                save_ready(transaction,observer,state);health_ready[0]=True
        visit = [None]
        def open_lg_home():
            # Luna may take seconds; never block the input health channel.
            if visit[0] is not None and visit[0].is_alive(): return
            def launch():
                try: d.sam_transport().call('luna://com.webos.applicationManager/launch', {'id':'com.webos.app.home'})
                except Exception as exc: record({'screen_launch_error':str(exc)})
            visit[0] = threading.Thread(target=launch, daemon=True)
            visit[0].start()
        fault_at = None
        def device_gone(at):
            nonlocal fault_at
            fault_at = at
        def recover_observer(why):
            if fault_at is None: return recover(transaction, why)
            return recover(transaction, why, fault_at=fault_at)
        reason = watch(r, recover_observer, timeout=HEARTBEAT_TIMEOUT,
                       on_ready=lambda:None if bound else save_ready(transaction, observer),
                       finished=lambda:completed(transaction), on_ping=ping, on_lg_home=open_lg_home,
                       on_device_gone=device_gone,on_wait=ping if bound else None)
        record({'event':'emergency-monitor-ended','reason':reason,'transaction':transaction})
    except Exception as exc:
        try:
            from persistent_health import HealthContextError
            # Record the observed refusal before recovery changes intent/binding.
            # Logging failure must not prevent the independent recovery path.
            if isinstance(exc, HealthContextError):
                record(dict(event='health-context-rejected',reason=exc.reason,
                            pid=os.getpid(),uptime=time.monotonic()),error=True)
        except Exception: pass
        recover(transaction, 'supervisor_error')
        raise
    finally:
        if observer is not None:
            if observer.poll() is None: observer.kill()
            observer.wait()
        os.close(r)
        if w is not None: os.close(w)


def spawn_guarded(transaction, cancelled=lambda:False):
    deadline=startup_deadline(transaction)
    guardian = bounded.spawn(transaction)
    fd = os.open(d.STATE/'emergency.log', os.O_CREAT|os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
    try:
        supervisor = subprocess.Popen([d.current_executable(), str(Path(__file__).resolve()), transaction],
            stdin=subprocess.DEVNULL, stdout=fd, stderr=fd, start_new_session=True, close_fds=True)
    finally: os.close(fd)
    while time.monotonic()<deadline:
        if cancelled(): raise RuntimeError('Guarded startup cancelled')
        try: ready = d.safe_json(d.STATE/'escape-ready.json')
        except FileNotFoundError: ready = {}
        if ready.get('transaction') == transaction and ready.get('pid') == supervisor.pid:
            if (supervisor.poll() is None and guardian.poll() is None
                    and d.process_start(supervisor.pid) == ready.get('start_ticks')
                    and d.process_start(ready['observer_pid']) == ready.get('observer_start_ticks')):
                break
        if supervisor.poll() is not None: raise RuntimeError('Emergency observer failed before activation')
        time.sleep(min(.1,max(0,deadline-time.monotonic())))
    else: raise RuntimeError('Emergency observer not ready; Home was not activated')
    class Guarded:
        pid = guardian.pid
        def poll(self):
            if cancelled() or guardian.poll() is not None or supervisor.poll() is not None: return 1
            try:
                if d.process_start(ready['observer_pid']) != ready['observer_start_ticks']: return 1
                if ready.get('input_state') in ('active','waiting-input'):
                    from persistent_health import require_fresh
                    lease=require_fresh(transaction,allow_wait=True)
                    if lease['state']=='waiting-input': raise BootInputMissing(transaction)
            except (OSError, ValueError): return 1
            return None
    return Guarded()


def start(before_publish=None, *, cancelled=None):
    spawn = spawn_guarded if cancelled is None else lambda tx: spawn_guarded(tx,cancelled)
    if before_publish is None: return bounded.begin(spawn)
    return bounded.begin(spawn, before_publish=before_publish)


def spawn_input_wait(transaction):
    fd=os.open(d.STATE/'emergency.log',os.O_CREAT|os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        subprocess.Popen([d.current_executable(),str(Path(__file__).resolve()),'--wait-boot-input',transaction],
                         stdin=subprocess.DEVNULL,stdout=fd,stderr=fd,start_new_session=True,close_fds=True)
    finally: os.close(fd)


def wait_boot_input(transaction):
    """Stock is already verified. Observe this one deferred boot until Off or fresh input."""
    from boot_gate import observation
    from intent_runtime import coordinator, boot_identity, startup_after_ready
    c=coordinator()
    if c is None: return
    intent=c.store.read()
    binding=c.read_binding()
    if (intent['phase']!='stopping' or not intent['enabled'] or not binding['restored']
            or (binding['transaction'],binding['token'],binding['generation']) !=
               (transaction,intent['token'],intent['generation']) or intent['boot']!=boot_identity()):
        return
    valid_input=False
    handoff=None
    completed_at=None
    errors=[]
    cancelled=threading.Event()

    def same_attempt(current):
        return all(current[key]==intent[key] for key in ('boot','generation','token'))

    def transfer():
        nonlocal completed_at
        try:
            with c.locked(intent):
                if (cancelled.is_set() or c.read_binding()!=binding or c.route(transaction)['state']!='restored'
                        or boot_identity()!=intent['boot'] or observation()!=(True,False)):
                    raise ValueError('Deferred startup no longer owns stock Home')
                starting,_=c.event(intent,'input-ready')
            startup_after_ready(c.restart(starting,cancelled=cancelled.is_set))
            completed_at=time.monotonic()
        except Exception as exc:
            errors.append(exc)

    def ping():
        nonlocal valid_input
        valid_input=True
    def waiting(at):
        nonlocal valid_input
        valid_input=False
    def finished():
        nonlocal handoff
        current=c.store.read()
        if not same_attempt(current) or boot_identity()!=intent['boot']: return True
        if errors: raise errors[0]
        if not current['enabled']: return True
        d.require_home(purpose='live')
        if observation()!=(True,False): raise ValueError('Normal startup revoked')
        if valid_input and handoff is None:
            handoff=threading.Thread(target=transfer)
            handoff.start()
        # A Home gesture can begin on this reader before the new observer
        # starts. Keep both readers until a whole gesture and delivery deadline
        # have elapsed after successful guarded publication.
        return completed_at is not None and time.monotonic()-completed_at>2+HEARTBEAT_TIMEOUT

    def fault(reason):
        cancelled.set()
        if handoff is not None: handoff.join()
        current=c.store.read()
        if same_attempt(current) and boot_identity()==intent['boot'] and current['phase']!='disabled':
            if reason=='escape':
                from update_guard import cancel
                cancel(d.STATE,d.EXPECTED_UID,current)
            c.exit(current,reason='fault',emergency=reason=='escape')
        return True
    r,w=os.pipe();reader=None
    try:
        reader=subprocess.Popen([d.current_executable(),str(Path(__file__).with_name('emergency_reader.py')),
                                 str(w),'--recover-profile-input'],pass_fds=(w,),stdin=subprocess.DEVNULL,close_fds=True)
        os.close(w);w=None
        watch(r,fault,finished=finished,on_ping=ping,on_wait=waiting)
    except Exception:
        fault('supervisor_error')
        raise
    finally:
        cancelled.set()
        if handoff is not None: handoff.join()
        if reader is not None:
            if reader.poll() is None:reader.kill()
            reader.wait()
        os.close(r)
        if w is not None:os.close(w)


if __name__ == '__main__':
    if os.geteuid() != 0: raise SystemExit('Root required')
    if len(sys.argv)==3 and sys.argv[1]=='--wait-boot-input':wait_boot_input(sys.argv[2])
    elif len(sys.argv)==2:supervise(sys.argv[1])
    else:raise SystemExit('Transaction required')
