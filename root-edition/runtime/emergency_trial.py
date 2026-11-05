"""Opt-in bounded emergency-exit trial; permanent activation remains unavailable."""
import json
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


def record(value, error=False):
    try: print(json.dumps(value),file=sys.stderr if error else sys.stdout,flush=True)
    except Exception: pass  # Diagnostic storage never authorizes or blocks recovery.


def save_ready(transaction, observer):
    value = {'transaction':transaction, 'pid':os.getpid(),
             'start_ticks':d.process_start(os.getpid()), 'observer_pid':observer.pid,
             'observer_start_ticks':d.process_start(observer.pid)}
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


def recover(transaction, reason):
    record({'event':'emergency-recovery','transaction':transaction,'reason':reason,
            'pid':os.getpid(),'uptime':time.monotonic()})
    for _ in range(30):
        try:
            from persistent_recovery import bound_exit
            bound = bound_exit(transaction, reason=reason)
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


def supervise(transaction):
    d.trusted_dir(d.STATE)
    j = d.safe_json(d.STATE/'profile-trial.json')
    if j['transaction'] != transaction or j['state'] != 'pending': return
    r, w = os.pipe(); observer = None
    try:
        observer = subprocess.Popen([d.current_executable(), str(Path(__file__).with_name('emergency_reader.py')), str(w)],
                                    pass_fds=(w,), stdin=subprocess.DEVNULL, close_fds=True)
        os.close(w); w = None
        sequence = [0]
        def ping():
            # Legacy trials have no durable binding and keep their fixed timer.
            from persistent_recovery import Coordinator
            from persistent_store import Store
            c = Coordinator(Store(d.STATE))
            if not os.path.lexists(c.binding): return
            if c.read_binding()['transaction'] != transaction: return
            from persistent_health import publish, require_guardian
            require_guardian(transaction)
            sequence[0] += 1
            publish(transaction, sequence[0])
        visit = [None]
        def open_lg_home():
            # Luna may take seconds; never block the input health channel.
            if visit[0] is not None and visit[0].is_alive(): return
            def launch():
                try: d.sam_transport().call('luna://com.webos.applicationManager/launch', {'id':'com.webos.app.home'})
                except Exception as exc: record({'screen_launch_error':str(exc)})
            visit[0] = threading.Thread(target=launch, daemon=True)
            visit[0].start()
        reason = watch(r, lambda why:recover(transaction, why), timeout=2,
                       on_ready=lambda:save_ready(transaction, observer),
                       finished=lambda:completed(transaction), on_ping=ping, on_lg_home=open_lg_home)
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


def start(before_publish=None):
    def spawn(transaction):
        guardian = bounded.spawn(transaction)
        fd = os.open(d.STATE/'emergency.log', os.O_CREAT|os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
        try:
            supervisor = subprocess.Popen([d.current_executable(), str(Path(__file__).resolve()), transaction],
                stdin=subprocess.DEVNULL, stdout=fd, stderr=fd, start_new_session=True, close_fds=True)
        finally: os.close(fd)
        for _ in range(30):
            try: ready = d.safe_json(d.STATE/'escape-ready.json')
            except FileNotFoundError: ready = {}
            if ready.get('transaction') == transaction and ready.get('pid') == supervisor.pid:
                if (supervisor.poll() is None and guardian.poll() is None
                        and d.process_start(supervisor.pid) == ready.get('start_ticks')
                        and d.process_start(ready['observer_pid']) == ready.get('observer_start_ticks')):
                    break
            if supervisor.poll() is not None: raise RuntimeError('Emergency observer failed before activation')
            time.sleep(.1)
        else: raise RuntimeError('Emergency observer not ready; Home was not activated')
        class Guarded:
            pid = guardian.pid
            def poll(self):
                if guardian.poll() is not None or supervisor.poll() is not None: return 1
                try:
                    if d.process_start(ready['observer_pid']) != ready['observer_start_ticks']: return 1
                except (OSError, ValueError): return 1
                return None
        return Guarded()
    if before_publish is None: return bounded.begin(spawn)
    return bounded.begin(spawn, before_publish=before_publish)


if __name__ == '__main__':
    if os.geteuid() != 0 or len(sys.argv) != 2: raise SystemExit('Root and transaction required')
    supervise(sys.argv[1])
