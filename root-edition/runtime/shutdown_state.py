"""Observe bounded, session-bound shutdown evidence before input teardown."""
import json
import os
import stat
import select
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import device_adapter as d
import persistent_health as health


def query():
    try:
        result = subprocess.run(['/usr/bin/systemctl','is-system-running'],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=.5,universal_newlines=True)
        return result.stdout.strip() == 'stopping'
    except (OSError,subprocess.TimeoutExpired): return False


def record(transaction, source="systemd", boot=None):
    from intent_runtime import boot_identity
    current = boot_identity()
    if boot is None: boot = current
    if boot != current: return False
    try:health.ROOT.mkdir(mode=0o700)
    except FileExistsError:pass
    d.trusted_dir(health.ROOT)
    fd,name=tempfile.mkstemp(dir=health.ROOT,prefix='.shutdown-')
    try:
        with os.fdopen(fd,'w') as out:
            json.dump(dict(transaction=transaction,boot=boot,issued=time.monotonic(),source=source),out)
        os.replace(name,health.path(transaction).with_suffix('.power' if source == 'firmware-power' else '.shutdown'))
        return True
    finally:
        if os.path.exists(name):os.unlink(name)


def stopping(transaction=None):
    if transaction is not None:
        try:
            from intent_runtime import boot_identity
            d.trusted_dir(health.ROOT)
            from persistent_lease import finite
            for suffix in ('.shutdown','.power'):
                try: v=d.safe_json(health.path(transaction).with_suffix(suffix))
                except FileNotFoundError: continue
                if (v.get('transaction') == transaction and v.get('boot') == boot_identity()
                        and finite(v.get('issued')) and 0 <= time.monotonic()-v['issued'] < 5):
                    return True
        except (OSError,ValueError):pass
    return query()


class PowerReason:
    """Accept a newly appearing root-owned firmware request, never a stale file."""
    def __init__(self, path=Path('/tmp/poweroff_reason')):
        self.path = path
        self.saw_absent = False
        self.consumed = False

    def poll(self):
        if self.consumed: return False
        try:
            fd = os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as stream:
                info=os.fstat(stream.fileno())
                if (not self.saw_absent or not stat.S_ISREG(info.st_mode)
                        or info.st_uid != d.EXPECTED_UID or info.st_mode & 0o022
                        or info.st_nlink != 1 or info.st_size > 256):
                    self.consumed=True;return False
                value=stream.read(257).strip()
                # The firmware may have created the inode before writing bytes.
                if not value:return False
                self.consumed=True
                return value == b'poweroff_reason=remoteKey'
        except FileNotFoundError:
            self.saw_absent=True;return False
        except OSError:
            self.consumed=True;return False


class PowerState:
    """A live ON -> shutdown transition; initial/reconnected OFF is never proof."""
    def __init__(self, transaction, boot):
        self.transaction = transaction
        self.boot = boot
        self.primed = False
        self.on = False
        self.asleep = False
        self.revision = 0
        self.wake_count = 0
        self.off_count = 0
        self.clear()
        self.diagnose('observing')

    def clear(self):
        try:
            d.trusted_dir(health.ROOT)
            health.path(self.transaction).with_suffix('.power').unlink()
        except FileNotFoundError: pass

    def diagnose(self, event):
        # One bounded volatile snapshot per transaction, never an authority or
        # raw firmware reply. No fsync/flash writes on the power-reader path.
        name = None
        try:
            try: health.ROOT.mkdir(mode=0o700)
            except FileExistsError: pass
            d.trusted_dir(health.ROOT)
            target = health.path(self.transaction).with_suffix('.wake')
            if os.path.lexists(target):
                info = target.lstat()
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != d.EXPECTED_UID
                        or info.st_nlink != 1 or info.st_mode & 0o022): return
            fd,name = tempfile.mkstemp(dir=health.ROOT,prefix='.wake-')
            with os.fdopen(fd,'w') as out:
                json.dump(dict(schema=1,transaction=self.transaction,boot=self.boot,
                    uptime=time.monotonic(),event=event,primed=self.primed,
                    on=self.on,asleep=self.asleep,revision=self.revision,
                    off_count=self.off_count,wake_count=self.wake_count),out)
            os.replace(name,target)
        except Exception: pass  # Diagnostic failure must not affect power policy.
        finally:
            if name is not None:
                try: os.unlink(name)
                except OSError: pass

    def close(self, reason='closed'):
        self.on = False
        self.asleep = False
        self.revision += 1
        self.clear()
        self.diagnose(reason)

    def event(self, value):
        if (not isinstance(value,dict) or value.get('returnValue') is not True
                or not isinstance(value.get('state'),str)
                or 'subscribed' in value and value['subscribed'] is not True
                or not self.primed and value.get('subscribed') is not True):
            self.close('invalid-subscription')
            raise ValueError('Invalid power subscription')
        state=value['state']
        request = None
        diagnostic = None if self.primed else 'initial-state'
        if state == 'Active':
            self.clear()
            if value.get('onOff') == 'off':
                self.close('onoff-off'); diagnostic='onoff-off'
            elif value.get('processing') is True:
                # Keep a proven OFF pending, but revoke an in-flight request.
                self.revision += 1
                diagnostic = 'processing'
            else:
                if not self.on: diagnostic = 'active-observed'
                if self.asleep:
                    self.asleep = False
                    self.revision += 1
                    request = self.revision
                    self.wake_count += 1
                    diagnostic = 'wake-observed'
                self.on = True
        elif state == 'Screen Saver':
            self.close('screen-saver'); self.on=True; diagnostic='screen-saver'
        elif state in ('Active Standby','Power Off'):
            self.revision += 1
            if self.primed and self.on:
                record(self.transaction,source='firmware-power',boot=self.boot)
                if not self.asleep: self.off_count += 1
                self.asleep = True
                diagnostic = 'off-observed'
        else:
            self.close('unknown-state'); diagnostic='unknown-state'
        self.primed=True
        if diagnostic is not None: self.diagnose(diagnostic)
        return request


def observe_power(transaction, boot, stop, wake=None):
    # One owned interactive child, no polling process/reconnect loop. Its stdin
    # pipe closes if the guardian dies. Unknown/lost streams revoke their proof.
    power=None;child=None;reason='stopped'
    try:
        power=PowerState(transaction,boot)
        child=subprocess.Popen(['/usr/bin/luna-send','-i',
            'luna://com.webos.service.tvpower/power/getPowerState','{"subscribe":true}'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,close_fds=True)
        data='';opened=time.monotonic()
        while not stop.is_set():
            from intent_runtime import boot_identity
            if boot_identity() != boot:
                reason='session-changed';break
            if not power.primed and time.monotonic()-opened > 5:
                reason='initial-timeout';break
            if not select.select([child.stdout],[],[],.25)[0]:
                if child.poll() is not None:
                    reason='child-exited';break
                continue
            chunk=os.read(child.stdout.fileno(),4096)
            if not chunk:
                reason='eof';break
            data+=chunk.decode('utf8')
            if len(data)>8192:
                reason='oversized-frame';break
            while data.strip():
                data=data.lstrip()
                try: value,end=json.JSONDecoder().raw_decode(data)
                except ValueError:
                    # A partial frame may complete later, but cannot leave a
                    # previous OFF frame authoritative while parsing is uncertain.
                    power.clear()
                    # Framing alone is not an unknown power state: retain a
                    # proven OFF until a complete valid ON, but cancel any
                    # earlier worker while the next frame is incomplete.
                    power.revision += 1
                    power.diagnose('incomplete-frame')
                    break
                data=data[end:]
                revision=power.event(value)
                if revision is not None and wake is not None:
                    wake(lambda revision=revision: stop.is_set() or power.revision != revision)
    except (OSError,ValueError): reason='invalid-or-unavailable-stream'
    finally:
        try:
            if power is not None: power.close(reason)
        finally:
            if child is not None:
                if child.poll() is None: child.terminate()
                try: child.communicate(timeout=1)
                except subprocess.TimeoutExpired: child.kill(); child.communicate(timeout=1)


class Monitor(threading.Event):
    def __init__(self):
        super().__init__()
        self.threads=[]
        self.presentation=None

    def request_wake(self, transaction, boot, cancelled):
        # Optional RPCs must never block the power reader or guardian lease.
        # At most one owned worker, no retries and no queue of stale wake edges.
        if self.is_set() or self.presentation is not None and self.presentation.is_alive(): return
        def present():
            from intent_runtime import present_wake
            present_wake(transaction,boot,lambda:self.is_set() or cancelled())
        self.presentation=threading.Thread(target=present,daemon=True)
        self.presentation.start()

    def close(self):
        self.set()
        for thread in self.threads: thread.join(timeout=2)
        if self.presentation is not None: self.presentation.join(timeout=2)


def monitor(transaction):
    stop=Monitor()
    from intent_runtime import boot_identity
    try: boot=boot_identity()
    except (OSError,ValueError): return stop
    try:
        from persistent_recovery import Coordinator
        from persistent_store import Store
        c=Coordinator(Store(d.STATE))
        if os.path.lexists(c.binding):
            binding=c.read_binding();intent=c.store.read()
            if (binding['transaction'] != transaction or binding['restored']
                    or (binding['generation'],binding['token']) != (intent['generation'],intent['token'])
                    or intent['boot'] != boot): return stop
    except (OSError,ValueError): return stop
    reason=PowerReason()
    reason.poll()  # Establish absence before announcing guardian readiness.
    def power_request():
        pending_until = 0
        while not stop.is_set():
            try:
                if reason.poll(): pending_until=time.monotonic()+1
                if time.monotonic() < pending_until:
                    record(transaction,source='firmware-remoteKey',boot=boot)
                    pending_until=0
                    print(json.dumps(dict(event='shutdown-request-observed',transaction=transaction,uptime=time.monotonic())),flush=True)
            except (OSError,ValueError):pass
            stop.wait(.05)
    def manager():
        while not stop.is_set():
            try:
                if query():record(transaction,boot=boot)
            except (OSError,ValueError):pass
            stop.wait(.25)
    # A stalled systemctl call must not delay the firmware request observer.
    for observe in (power_request,manager,lambda:observe_power(transaction,boot,stop,
            wake=lambda cancelled:stop.request_wake(transaction,boot,cancelled))):
        thread=threading.Thread(target=observe,daemon=True)
        stop.threads.append(thread);thread.start()
    return stop
