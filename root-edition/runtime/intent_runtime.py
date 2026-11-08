"""Intent-bound trial, explicit promotion and guarded boot recovery."""
import os
from contextlib import contextmanager, ExitStack
import re
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
    startup_after_ready(result)
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
    from boot_gate import load as continuation_record
    if continuation_record() is not None:
        # An interrupted handoff is recovery-only, never proof of fresh health.
        c.exit(intent, reason='fault')
        return 'restored'
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
    from boot_gate import eligible, start as continue_boot
    if eligible(c, intent, identity):
        result = continue_boot(c, intent, identity)
        startup_after_ready(result)
        return result
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
        startup_after_ready(result)
        return result
    return 'restored'


def confirm(transaction=None):
    c = coordinator()
    if c is None: raise ValueError('No intent-bound trial to confirm')
    if transaction != c.read_binding()['transaction']: raise ValueError('Stale confirmation transaction')
    return c.confirm(c.store.read())


# Native startup policy stays in the pinned runtime inventory for old supervisors.
startup_DEFAULTS = {'tv':True, 'youtube':False}
startup_ROOT_INPUT = {'type':'MVPD_IP', 'appId':d.CANDIDATE}
startup_CHANNEL = 'mgg4.5.channelplus'
startup_YOUTUBE = 'youtube.leanback.v4'


def startup_validate(sources):
    if (not isinstance(sources,dict) or set(sources)!=set(startup_DEFAULTS)
            or any(type(value) is not bool for value in sources.values())):
        raise ValueError('Invalid startup sources')
    return dict(sources)


def startup_load():
    try: value=d.safe_json(d.STATE/'startup-policy.json')
    except FileNotFoundError:return dict(startup_DEFAULTS)
    if (not isinstance(value,dict) or set(value)!={'version','sources'}
            or type(value['version']) is not int or value['version'] not in (1,2)):
        raise ValueError('Invalid startup policy')
    if value['version']==1:
        legacy=value['sources']
        if (not isinstance(legacy,dict) or set(legacy)!={'tv','youtube','hdmi'}
                or any(type(setting) is not bool for setting in legacy.values())):
            raise ValueError('Invalid startup policy')
        # Old HDMI preferences cannot authorize selection; status stays read-only.
        return {key:legacy[key] for key in startup_DEFAULTS}
    return startup_validate(value['sources'])


def startup_status():
    sources=startup_load();c=coordinator();intent=c.store.read() if c is not None else None
    return dict(sources=sources,active=bool(intent and intent['enabled'] and intent['phase']=='active'))


def startup_configure(sources):
    sources=startup_validate(sources);startup_load()  # Do not overwrite unreadable prior evidence.
    c=coordinator()
    if c is None:raise ValueError('Change Home is off')
    intent=c.store.read()
    with c.locked(intent):
        if not intent['enabled'] or intent['phase']!='active':raise ValueError('Change Home is off')
        d.trusted_dir(d.STATE)
        fd,name=tempfile.mkstemp(dir=d.STATE,prefix='.startup-policy-')
        try:
            with os.fdopen(fd,'w') as out:
                json.dump(dict(version=2,sources=sources),out);out.flush();os.fsync(out.fileno())
            os.replace(name,d.STATE/'startup-policy.json');d.sync(d.STATE)
        finally:
            if os.path.lexists(name):os.unlink(name)
    # An explicit setting change may withdraw a previous selection immediately.
    binding=c.read_binding()
    startup_reconcile(binding['transaction'],intent['boot'],event='policy')
    return startup_status()


def startup_call(uri,payload,deadline):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('Native startup deadline')
    return d.sam_transport().call('luna://'+uri,payload,timeout=min(.5,remaining/2))


def startup_source(app,deadline):
    if not isinstance(app,str) or not app:return None
    if app in (d.CANDIDATE,'com.webos.app.home'):return 'home'
    if app=='com.webos.app.livetv':return 'tv'
    if app==startup_YOUTUBE:return 'youtube'
    if re.fullmatch(r'com\.webos\.app\.hdmi[1-4]',app):return 'hdmi'
    if app=='com.webos.app.cpcover':return None
    info=startup_call('com.webos.applicationManager/getAppInfo',{'id':app},deadline).get('appInfo')
    if not isinstance(info,dict) or info.get('id')!=app:return None
    if app==startup_CHANNEL:
        store='/media/cryptofs/apps/usr/palm/applications/'+app
        expected=dict(type='web',vendor='LifeStream ltd.',folderPath=store,activeFolderPath=store)
        if (all(info.get(k)==v for k,v in expected.items())
                and info.get('CPApp') is True and info.get('internalInstallationOnly') is True):return 'tv'
    return 'protected' if info.get('visible') is True else None


def startup_presentation(deadline,event):
    """Fresh compositor guard; unknown context must never imply an input request."""
    value=startup_call('com.webos.surfacemanager/getForegroundAppInfo',{},deadline)
    surfaces=value.get('foregroundAppInfo')
    if value.get('returnValue') is not True or not isinstance(surfaces,list) or len(surfaces)>128:
        return 'unknown-presentation'
    if any(not isinstance(s,dict) or not isinstance(s.get('appId'),str) or not s['appId']
           or not isinstance(s.get('windowType'),str) for s in surfaces):return 'unknown-presentation'
    primary=[s for s in surfaces if s.get('displayId',0)==0]
    overlay=any(s['appId']==d.CANDIDATE and s['windowType']=='_WEBOS_WINDOW_TYPE_OVERLAY' for s in primary)
    content=any(s['appId']!=d.CANDIDATE and s['windowType']=='_WEBOS_WINDOW_TYPE_CARD' for s in primary)
    if overlay and (content or event!='activation'):return 'overlay-visible'
    return None


def startup_matching_input(app,pair):
    if app==startup_CHANNEL:return pair=={'type':'MVPD_IP','appId':startup_CHANNEL}
    if app=='com.webos.app.livetv':return pair=={'type':'DTV','appId':app}
    if re.fullmatch(r'com\.webos\.app\.hdmi[1-4]',app):
        return pair=={'type':'HDMI_'+app[-1],'appId':app}
    return pair.get('appId')==app


def startup_require(c,intent,transaction,boot):
    from persistent_health import require_fresh,require_guardian
    if (not intent['enabled'] or intent['phase']!='active' or intent['boot']!=boot
            or boot_identity()!=boot or c.store.read()!=intent or d.FAILSAFE.exists()):
        raise ValueError('Inactive startup context')
    binding=c.read_binding()
    if (binding['transaction']!=transaction or binding['restored']
            or binding['generation']!=intent['generation'] or binding['token']!=intent['token']):
        raise ValueError('Stale startup binding')
    require_fresh(transaction);require_guardian(transaction)
    if not d.active_guardian(c.route(transaction)):raise ValueError('Inactive guardian')


def startup_active(receipt):
    result=dict(receipt,phase='active');result.pop('pending',None);return result


def startup_observer_mark(transaction,boot,ready):
    """Volatile eligibility belongs to the current guardian process, not intent."""
    from persistent_health import ROOT,path
    target=path(transaction).with_suffix('.startup')
    ticks=d.process_start(os.getpid())
    value=dict(transaction=transaction,boot=boot,pid=os.getpid(),start_ticks=ticks)
    if not ready:
        try:
            if d.safe_json(target)==value:target.unlink()
        except FileNotFoundError:pass
        return
    if boot_identity()!=boot:raise ValueError('Stale startup observer')
    try:ROOT.mkdir(mode=0o700)
    except FileExistsError:pass
    d.trusted_dir(ROOT)
    fd,name=tempfile.mkstemp(dir=ROOT,prefix='.startup-')
    try:
        with os.fdopen(fd,'w') as out:json.dump(value,out)
        os.replace(name,target)
    finally:
        if os.path.lexists(name):os.unlink(name)


def startup_observing(transaction,boot):
    from persistent_health import ROOT,path
    try:
        d.trusted_dir(ROOT)
        value=d.safe_json(path(transaction).with_suffix('.startup'))
        guardian=d.safe_json(d.STATE/'profile-guardian-ready.json')
        pid=guardian['pid'];ticks=guardian['start_ticks']
        return (type(pid) is int and pid>0 and isinstance(ticks,str) and ticks.isdigit()
                and guardian['transaction']==transaction
                and value==dict(transaction=transaction,boot=boot,pid=pid,start_ticks=ticks)
                and d.process_start(pid)==ticks)
    except (OSError,ValueError,KeyError,TypeError):return False


@contextmanager
def startup_locked(c,wait):
    deadline=time.monotonic()+2
    while True:
        intent=c.store.read();stack=ExitStack()
        try:stack.enter_context(c.locked(intent))
        except BlockingIOError:
            stack.close()
            if not wait or time.monotonic()>=deadline:raise
            time.sleep(.01);continue
        with stack:yield intent
        return


def startup_reconcile(transaction,boot,cancelled=lambda:False,event='foreground',withdraw=False,wait_lock=False):
    """One fresh observation/effect; a subsequent event is never a blind retry."""
    try:
        if cancelled():return 'canceled'
        c=coordinator()
        if c is None:return 'unavailable'
        with startup_locked(c,wait_lock) as intent:
            startup_require(c,intent,transaction,boot)
            saved=d._native_read()
            if saved is None or saved['phase'] not in ('active','selecting'):return 'unavailable'
            deadline=time.monotonic()+1.5
            withdraw=withdraw or not startup_observing(transaction,boot)
            settings={} if withdraw else startup_call('com.webos.settingsservice/getSystemSettings',
                {'category':'general','keys':['homeAutoLaunch']},deadline)
            withdraw=withdraw or settings.get('settings',{}).get('homeAutoLaunch')!='on'
            if not withdraw:
                presentation=startup_presentation(deadline,event)
                if presentation:return presentation
            if not d._native_entry(deadline):return 'unavailable'
            current=d._native_pair(startup_call('com.webos.service.eim/getLastInput',{},deadline))
            reconciled=False
            if saved['phase']=='selecting':
                target=startup_ROOT_INPUT if saved['pending']=='select' else saved['baseline']
                if current!=target:return 'pending'
                saved=startup_active(saved);d._native_save(saved);reconciled=True
            app=None;source=None
            if not withdraw:
                app=startup_call('com.webos.applicationManager/getForegroundAppInfo',{},deadline).get('appId')
                source=startup_source(app,deadline)
                if source is None:return 'reconciled' if reconciled else 'unknown-foreground'
            sources={} if withdraw else startup_load()
            allowed=(not withdraw and settings.get('settings',{}).get('homeAutoLaunch')=='on'
                     and (source=='home' or sources.get(source) is True))
            if allowed:
                if current==startup_ROOT_INPUT:return 'reconciled' if reconciled else 'already-selected'
                if ((source in ('tv','hdmi') or event=='input') and not startup_matching_input(app,current)):
                    return 'inconsistent-input'
                target=startup_ROOT_INPUT;updated=dict(saved,baseline=current,phase='selecting',pending='select')
                outcome='selected'
            else:
                if current!=startup_ROOT_INPUT:return 'reconciled' if reconciled else 'preserved-input'
                target=saved['baseline'];updated=dict(saved,phase='selecting',pending='restore')
                outcome='withdrawn'
            # EIM and foreground are separate RPCs; reject observed changes.
            if d._native_pair(startup_call('com.webos.service.eim/getLastInput',{},deadline))!=current:
                return 'superseded'
            if app is not None and startup_call('com.webos.applicationManager/getForegroundAppInfo',{},deadline).get('appId')!=app:
                return 'superseded'
            startup_require(c,intent,transaction,boot)
            if cancelled() or allowed and not startup_observing(transaction,boot):return 'canceled'
            if not withdraw:
                presentation=startup_presentation(deadline,event)
                if presentation:return presentation
            d._native_save(updated)  # Persist the inverse before any optional effect.
            try:
                startup_require(c,intent,transaction,boot)
                if cancelled() or allowed and not startup_observing(transaction,boot):
                    d._native_save(saved);return 'canceled'  # No RPC was submitted.
            except Exception:
                d._native_save(saved);raise
            d._native_set(target,deadline)
            # Confirm a submitted effect even if a newer event canceled its work.
            d._native_save(startup_active(updated))
            return outcome
    except Exception:
        return 'unavailable'


def startup_after_ready(result):
    """Initial subscription frames may precede confirmation; apply once ready."""
    try:
        intent=result['intent']
        transaction=result.get('transaction') or result['trial']['transaction']
        return startup_reconcile(transaction,intent['boot'],event='activation')
    except Exception:return 'unavailable'


def startup_entry(args):
    if args==['status']:return startup_status()
    if args==['configure']:
        import sys
        raw=sys.stdin.buffer.read(2049)
        if len(raw)>2048:raise ValueError('Oversized startup sources')
        return startup_configure(json.loads(raw))
    raise ValueError('Unknown startup operation')
