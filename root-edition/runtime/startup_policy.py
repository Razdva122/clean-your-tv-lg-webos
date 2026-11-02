"""Guarded native first-screen choices. Never launches an application."""
import json
import os
import re
import tempfile
import time
import device_adapter as d

DEFAULTS = {'tv':True, 'youtube':False, 'hdmi':False}
ROOT_INPUT = {'type':'MVPD_IP', 'appId':d.CANDIDATE}
CHANNEL = 'mgg4.5.channelplus'
YOUTUBE = 'youtube.leanback.v4'


def validate(sources):
    if (not isinstance(sources,dict) or set(sources)!=set(DEFAULTS)
            or any(type(value) is not bool for value in sources.values())):
        raise ValueError('Invalid startup sources')
    return dict(sources)


def load():
    try: value=d.safe_json(d.STATE/'startup-policy.json')
    except FileNotFoundError:return dict(DEFAULTS)
    if not isinstance(value,dict) or set(value)!={'version','sources'} or type(value['version']) is not int or value['version']!=1:
        raise ValueError('Invalid startup policy')
    return validate(value['sources'])


def status():
    from intent_runtime import coordinator
    sources=load();c=coordinator();intent=c.store.read() if c is not None else None
    return dict(sources=sources,active=bool(intent and intent['enabled'] and intent['phase']=='active'))


def configure(sources):
    from intent_runtime import coordinator
    sources=validate(sources);load()  # Do not overwrite unreadable prior evidence.
    c=coordinator()
    if c is None:raise ValueError('Change Home is off')
    intent=c.store.read()
    with c.locked(intent):
        if not intent['enabled'] or intent['phase']!='active':raise ValueError('Change Home is off')
        d.trusted_dir(d.STATE)
        fd,name=tempfile.mkstemp(dir=d.STATE,prefix='.startup-policy-')
        try:
            with os.fdopen(fd,'w') as out:
                json.dump(dict(version=1,sources=sources),out);out.flush();os.fsync(out.fileno())
            os.replace(name,d.STATE/'startup-policy.json');d.sync(d.STATE)
        finally:
            if os.path.lexists(name):os.unlink(name)
    # An explicit setting change may withdraw a previous selection immediately.
    binding=c.read_binding()
    reconcile(binding['transaction'],intent['boot'],event='policy')
    return status()


def _call(uri,payload,deadline):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('Native startup deadline')
    return d.sam_transport().call('luna://'+uri,payload,timeout=min(.5,remaining/2))


def _source(app,deadline):
    if not isinstance(app,str) or not app:return None
    if app in (d.CANDIDATE,'com.webos.app.home'):return 'home'
    if app=='com.webos.app.livetv':return 'tv'
    if app==YOUTUBE:return 'youtube'
    if re.fullmatch(r'com\.webos\.app\.hdmi[1-4]',app):return 'hdmi'
    if app=='com.webos.app.cpcover':return None
    info=_call('com.webos.applicationManager/getAppInfo',{'id':app},deadline).get('appInfo')
    if not isinstance(info,dict) or info.get('id')!=app:return None
    if app==CHANNEL:
        store='/media/cryptofs/apps/usr/palm/applications/'+app
        expected=dict(type='web',vendor='LifeStream ltd.',folderPath=store,activeFolderPath=store)
        if (all(info.get(k)==v for k,v in expected.items())
                and info.get('CPApp') is True and info.get('internalInstallationOnly') is True):return 'tv'
    return 'protected' if info.get('visible') is True else None


def _matching_input(app,pair):
    if app==CHANNEL:return pair=={'type':'MVPD_IP','appId':CHANNEL}
    if app=='com.webos.app.livetv':return pair=={'type':'DTV','appId':app}
    if re.fullmatch(r'com\.webos\.app\.hdmi[1-4]',app):
        return pair=={'type':'HDMI_'+app[-1],'appId':app}
    return pair.get('appId')==app


def _require(c,intent,transaction,boot):
    from intent_runtime import boot_identity
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


def _active(receipt):
    result=dict(receipt,phase='active');result.pop('pending',None);return result


def reconcile(transaction,boot,cancelled=lambda:False,event='foreground',withdraw=False):
    """One fresh observation/effect; a subsequent event is never a blind retry."""
    try:
        if cancelled():return 'canceled'
        from intent_runtime import coordinator
        c=coordinator()
        if c is None:return 'unavailable'
        intent=c.store.read()
        with c.locked(intent):
            _require(c,intent,transaction,boot)
            saved=d._native_read()
            if saved is None or saved['phase'] not in ('active','selecting'):return 'unavailable'
            deadline=time.monotonic()+1.5
            if not d._native_entry(deadline):return 'unavailable'
            current=d._native_pair(_call('com.webos.service.eim/getLastInput',{},deadline))
            reconciled=False
            if saved['phase']=='selecting':
                target=ROOT_INPUT if saved['pending']=='select' else saved['baseline']
                if current!=target:return 'pending'
                saved=_active(saved);d._native_save(saved);reconciled=True
            settings=_call('com.webos.settingsservice/getSystemSettings',
                {'category':'general','keys':['homeAutoLaunch']},deadline)
            withdraw=withdraw or settings.get('settings',{}).get('homeAutoLaunch')!='on'
            app=None;source=None
            if not withdraw:
                app=_call('com.webos.applicationManager/getForegroundAppInfo',{},deadline).get('appId')
                source=_source(app,deadline)
                if source is None:return 'reconciled' if reconciled else 'unknown-foreground'
            sources={} if withdraw else load()
            allowed=(not withdraw and settings.get('settings',{}).get('homeAutoLaunch')=='on'
                     and (source=='home' or sources.get(source) is True))
            if allowed:
                if current==ROOT_INPUT:return 'reconciled' if reconciled else 'already-selected'
                if ((source in ('tv','hdmi') or event=='input') and not _matching_input(app,current)):
                    return 'inconsistent-input'
                target=ROOT_INPUT;updated=dict(saved,baseline=current,phase='selecting',pending='select')
                outcome='selected'
            else:
                if current!=ROOT_INPUT:return 'reconciled' if reconciled else 'preserved-input'
                target=saved['baseline'];updated=dict(saved,phase='selecting',pending='restore')
                outcome='withdrawn'
            # EIM and foreground are separate RPCs; reject observed changes.
            if d._native_pair(_call('com.webos.service.eim/getLastInput',{},deadline))!=current:
                return 'superseded'
            if app is not None and _call('com.webos.applicationManager/getForegroundAppInfo',{},deadline).get('appId')!=app:
                return 'superseded'
            _require(c,intent,transaction,boot)
            if cancelled():return 'canceled'
            d._native_save(updated)  # Persist the inverse before any optional effect.
            try:
                _require(c,intent,transaction,boot)
                if cancelled():
                    d._native_save(saved);return 'canceled'  # No RPC was submitted.
            except Exception:
                d._native_save(saved);raise
            d._native_set(target,deadline)
            # Confirm a submitted effect even if a newer event canceled its work.
            d._native_save(_active(updated))
            return outcome
    except Exception:
        return 'unavailable'


def after_ready(result):
    """Initial subscription frames may precede confirmation; apply once ready."""
    try:
        intent=result['intent']
        transaction=result.get('transaction') or result['trial']['transaction']
        return reconcile(transaction,intent['boot'],event='activation')
    except Exception:return 'unavailable'


def entry(args):
    if args==['status']:return status()
    if args==['configure']:
        import sys
        raw=sys.stdin.buffer.read(2049)
        if len(raw)>2048:raise ValueError('Oversized startup sources')
        return configure(json.loads(raw))
    raise ValueError('Unknown startup operation')
