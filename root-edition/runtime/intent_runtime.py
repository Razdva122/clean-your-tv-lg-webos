"""Intent-bound trial, explicit promotion and guarded boot recovery."""
import os
import fcntl
import stat
import json
import tempfile
import time
from pathlib import Path
import uuid
import device_adapter as d
from persistent_store import Store
from persistent_recovery import Coordinator
from persistent_lifecycle import identifier


def boot_identity(proc=None, session=None):
    # Firmware snapshots can reuse boot_id; btime moves with clock correction.
    # The tested cold-start path clears this private volatile directory.
    from boot_gate import ROOT
    proc = d.PROC if proc is None else Path(proc)
    boot = (proc/'sys/kernel/random/boot_id').read_text().strip()
    if not identifier(boot) or len(boot) > 64: raise ValueError('Invalid kernel boot identity')
    root = ROOT if session is None else Path(session)
    try: root.mkdir(mode=0o700)
    except FileExistsError: pass
    d.trusted_dir(root)
    fd = os.open(root/'session.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != d.EXPECTED_UID
                or info.st_nlink != 1 or info.st_mode & 0o022):
            raise ValueError('Unsafe session lock')
        for attempt in range(50):
            try:
                fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if attempt == 49: raise
                time.sleep(.01)
        try: value = d.safe_json(root/'session.json')
        except FileNotFoundError: value = None
        else:
            if (not isinstance(value,dict) or set(value) != {'version','kernel','token'}
                    or type(value['version']) is not int or value['version'] != 1
                    or not isinstance(value['kernel'],str) or not identifier(value['kernel'])
                    or not isinstance(value['token'],str) or len(value['token']) != 32
                    or any(c not in '0123456789abcdef' for c in value['token'])):
                raise ValueError('Invalid startup session')
        if value is None or value['kernel'] != boot:
            value = dict(version=1,kernel=boot,token=uuid.uuid4().hex)
            temp_fd, name = tempfile.mkstemp(dir=root,prefix='.session-')
            try:
                with os.fdopen(temp_fd,'w') as out: json.dump(value,out)
                os.replace(name,root/'session.json')
            finally:
                if os.path.lexists(name): os.unlink(name)
        return boot+':session-'+value['token']
    finally: os.close(fd)


def coordinator():
    if not os.path.lexists(d.STATE/'persistent-intent.json'): return None
    return Coordinator(Store(d.STATE))


def start():
    from provision import verify
    from helper_bridge import require_idle
    verify(); require_idle()
    c = Coordinator(Store(d.STATE)); intent = c.store.read()
    if intent['phase'] != 'disabled':
        raise ValueError('Restore previous intent before starting another trial')
    return c.start_trial(intent, boot_identity(), str(uuid.uuid4()))


def enable():
    from provision import verify
    from helper_bridge import require_idle
    verify(); require_idle()
    c = Coordinator(Store(d.STATE))
    result=c.enable(c.store.read(), boot_identity(), str(uuid.uuid4()))
    from startup_policy import after_ready
    after_ready(result)
    return result


def later_legacy_trial(c):
    if not os.path.lexists(c.binding) or not os.path.lexists(d.STATE/'profile-trial.json'):
        return False
    from profile_recovery import validate
    binding = c.read_binding()
    journal = d.safe_json(d.STATE/'profile-trial.json'); validate(journal)
    return binding['restored'] and journal.get('transaction') != binding['transaction']


def _legacy_native_recovery(c=None):
    # Without an owned receipt, retain the legacy caller's recovery fallback.
    if not os.path.lexists(d.STATE/'native-input.json'): return None
    c = Coordinator(Store(d.STATE)) if c is None else c
    expected = c.store.read()
    with c.locked(expected):
        if expected['phase'] != 'disabled': expected,_ = c.event(expected,'exit')
        result = d.main('recover')
        if result not in ('restored','absent'): raise ValueError('Routing restoration incomplete')
        if expected['phase'] == 'recovering': c.event(expected,'restored')
        d.native_input_disable()  # A bad EIM receipt may block completion, never route restoration.
        return result


def restore():
    c = coordinator()
    if c is None or later_legacy_trial(c): return _legacy_native_recovery(c)
    intent = c.store.read()
    if intent['phase'] == 'disabled': return _legacy_native_recovery(c)
    result = c.exit(intent)
    return 'restored' if result.get('restored_transaction') else None


def boot():
    if not os.path.lexists(d.STATE/'persistent-intent.json'):
        if os.path.lexists(d.STATE/'profile-trial.json'):
            from profile_recovery import validate
            journal = d.safe_json(d.STATE/'profile-trial.json');validate(journal)
            if d.active_guardian(journal): return None
        return _legacy_native_recovery()
    d.trusted_dir(d.STATE)
    fd=os.open(d.STATE/'boot-dispatch.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != d.EXPECTED_UID
                or info.st_nlink != 1 or info.st_mode & 0o022):
            raise ValueError('Unsafe boot dispatch lock')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 'boot-in-progress'
        try:return _boot()
        except Exception as exc:
            from boot_gate import audit
            audit('boot-error',error=type(exc).__name__+': '+str(exc))
            raise
    finally:os.close(fd)


def _boot():
    c = coordinator()
    if c is None: return _legacy_native_recovery()
    if later_legacy_trial(c): return None
    intent = c.store.read()
    try: identity = boot_identity()
    except (OSError,ValueError):
        c.exit(intent,reason='fault')
        raise
    failsafe = d.FAILSAFE.exists() or not d.home_present()
    if not failsafe and identity == intent['boot']:
        if intent['phase'] == 'stopping':
            c.shutdown(intent)
            return 'shutdown-pending'
        try: journal = d.safe_json(d.STATE/'profile-trial.json')
        except FileNotFoundError: journal = None
        if journal is not None and d.active_guardian(journal): return 'guarded-intent-trial'
        if intent['phase'] == 'disabled':
            _legacy_native_recovery(c)
            return 'restored'
        # Expired trial or interrupted startup in this same boot: disable intent,
        # never infer health from an application merely existing in /proc.
        from boot_gate import audit, observation
        try:
            audit('same-session-fault',phase=intent['phase'],generation=intent['generation'],
                  observation=observation())
        except Exception: pass  # Diagnostic storage must never block fault recovery.
        c.exit(intent, reason='fault')
        return 'restored'
    # Restore first. Normal startup also sets FAILSAFE temporarily; only the
    # current-boot init.d marker plus a cleared flag permits reactivation.
    from boot_gate import audit, observation
    audit('recover-before-gate',prior=intent,boot=identity,observation=observation())
    result = c.boot(intent, identity, str(uuid.uuid4()), False if identity != intent['boot'] else failsafe)
    if result['effect'] == 'start_guarded':
        from boot_gate import wait
        ready = wait()
        audit('gate-complete',prior=intent,boot=identity,ready=ready,observation=observation())
        if not ready:
            c.exit(result['intent'], reason='fault')
            return 'restored'
        result=c.restart(result['intent'])
        from startup_policy import after_ready
        after_ready(result)
        return result
    return 'restored'


def confirm(transaction=None):
    c = coordinator()
    if c is None: raise ValueError('No intent-bound trial to confirm')
    if transaction != c.read_binding()['transaction']: raise ValueError('Stale confirmation transaction')
    return c.confirm(c.store.read())
