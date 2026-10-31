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
    return c.enable(c.store.read(), boot_identity(), str(uuid.uuid4()))


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
        if expected['enabled']: raise ValueError('Native cleanup requires disabled intent')
        result = d.main('recover')
        if result not in ('restored','absent'): raise ValueError('Routing restoration incomplete')
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
        result = c.restart(result['intent'])
        if isinstance(result,dict):
            result['presentation'] = present_boot(c,result)
            try: audit('boot-presentation',outcome=result['presentation'],boot=identity,
                       context=result.get('presentation_context',{}))
            except Exception: pass
        return result
    return 'restored'


def present_boot(c, result):
    """One optional hardware-start request; never retry a launch."""
    return _present_home(c,result)


def present_wake(transaction, boot, cancelled):
    """Called only by a genuine ON/OFF/ON edge in one owned power stream.

    Never recover/rearm here: stale or stopping contexts belong to recovery.
    The caller revokes the edge on OFF, uncertainty, stream loss or teardown.
    """
    outcome = 'unavailable'
    result = {'presentation_context':{'stage':'cancelled'}}
    try:
        if cancelled(): return outcome
        result['presentation_context']['stage'] = 'session'
        if boot_identity() != boot: return outcome
        result['presentation_context']['stage'] = 'intent'
        c = coordinator()
        if c is None: return outcome
        intent = c.store.read()
        if (intent['phase'] != 'active' or intent['enabled'] is not True
                or intent['boot'] != boot): return outcome
        result['presentation_context']['stage'] = 'health-routing'
        if c._healthy(intent) != transaction: return outcome
        result.update(intent=intent,trial=dict(transaction=transaction))
        outcome = _present_home(c,result,cancelled=cancelled,wake=True)
        return outcome
    except Exception:
        return outcome  # Optional presentation never revokes healthy routing.
    finally:
        # Early refusals used to vanish, leaving no distinction between a lost
        # edge and a wake rejected by current intent/health. Never log raw RPCs.
        try:
            from boot_gate import audit
            audit('wake-presentation',outcome=outcome,boot=boot,
                  context=result['presentation_context'])
        except Exception: pass


def _native_channel(sam, app):
    """One observed partner TV surface; never classify arbitrary CP apps."""
    if app != 'mgg4.5.channelplus': return False
    info = sam.call('luna://com.webos.applicationManager/getAppInfo',{'id':app},timeout=.5).get('appInfo')
    if not isinstance(info,dict): return False
    store = '/media/cryptofs/apps/usr/palm/applications/'+app
    expected = dict(id=app,type='web',vendor='LifeStream ltd.',
                    folderPath=store,activeFolderPath=store)
    return (all(info.get(key) == value for key,value in expected.items())
            and info.get('CPApp') is True and info.get('internalInstallationOnly') is True)


def _present_home(c, result, cancelled=lambda:False, wake=False):
    """Shared final checks; foreground/launch are separate platform RPCs."""
    try:
        intent = result['intent']; tx = result['trial']['transaction']
        if intent['phase'] != 'active' or intent['enabled'] is not True: return 'unavailable'
        context = result.setdefault('presentation_context',{})
        context['stage'] = 'startup-setting'
        sam = d.sam_transport()
        settings = sam.call('luna://com.webos.settingsservice/getSystemSettings',
                            {'category':'general','keys':['homeAutoLaunch']},timeout=.5)
        if settings.get('settings',{}).get('homeAutoLaunch') != 'on':
            return 'preserved-startup-setting'
        boot = {}
        if not wake:
            context['stage'] = 'boot-status'
            boot = sam.call('luna://com.webos.bootManager/getBootStatus',{},timeout=.5)
            if (boot.get('bootTarget') != 'hardware' or boot.get('powerStatus') != 'active'
                    or boot.get('bootStatus') != 'normal' or boot.get('firstAppLaunched') is not True):
                return 'preserved-startup-setting'
        from persistent_health import require_fresh
        context['stage'] = 'input-health'
        require_fresh(tx)
        context['stage'] = 'foreground'
        foreground = sam.call('luna://com.webos.applicationManager/getForegroundAppInfo',{},timeout=.5)
        app = foreground.get('appId')
        # Diagnostics carry fixed classes, never private foreground IDs.
        kinds = {'com.webos.app.home':'stock-home','com.webos.app.livetv':'live-tv',d.CANDIDATE:'root'}
        first = boot.get('firstAppId')
        result['presentation_context'] = dict(foreground_kind=kinds.get(app,'other-or-missing'),
                                             first_app_matches=(first == app) if first else None)
        if wake: result['presentation_context']['stage'] = 'foreground'
        if app not in ('com.webos.app.livetv','com.webos.app.home'):
            if wake: result['presentation_context']['stage'] = 'native-metadata'
            if not _native_channel(sam,app): return 'preserved-foreground'
            result['presentation_context']['foreground_kind'] = 'native-channel'
            # Metadata is optional and can be slow. Keep an app selected while
            # it was checked, including a manual Home or a third-party app.
            if wake: result['presentation_context']['stage'] = 'foreground-recheck'
            latest = sam.call('luna://com.webos.applicationManager/getForegroundAppInfo',{},timeout=.5)
            if latest.get('appId') != app:
                result['presentation_context'] = dict(
                    foreground_kind=kinds.get(latest.get('appId'),'other-or-missing'),
                    first_app_matches=(first == latest.get('appId')) if first else None)
                if wake: result['presentation_context']['stage'] = 'foreground-recheck'
                return 'preserved-foreground'
        # Recheck after optional RPCs, which can outlive the two-second lease.
        if wake: result['presentation_context']['stage'] = 'final-input-health'
        require_fresh(tx)
        if wake:
            from persistent_health import require_guardian
            result['presentation_context']['stage'] = 'final-guardian'
            require_guardian(tx)
            result['presentation_context']['stage'] = 'final-intent'
        if cancelled() or c.store.read() != intent or d.FAILSAFE.exists(): return 'unavailable'
        # Never hold the operation lock over optional RPC: an off request must win.
        # Foreground observation and launch are separate platform calls; an app
        # switch after this last observation can still race this single request.
        if wake: result['presentation_context']['stage'] = 'launch'
        sam.call('luna://com.webos.applicationManager/launch',{'id':d.CANDIDATE},timeout=.5)
        return 'launch-requested' if c.store.read() == intent and not cancelled() else 'superseded'
    except Exception:
        # Missing/slow optional APIs must not disable otherwise healthy Home control.
        return 'unavailable'


def confirm(transaction=None):
    c = coordinator()
    if c is None: raise ValueError('No intent-bound trial to confirm')
    if transaction != c.read_binding()['transaction']: raise ValueError('Stale confirmation transaction')
    return c.confirm(c.store.read())
