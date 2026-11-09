"""One bounded Luna call with stdin kept open for the firmware client."""
import json
import os
import select
import subprocess
import time


CALLS={
    'com.webos.applicationManager/dev/listApps':'apps-dev',
    'com.webos.applicationManager/listApps':'apps',
    'com.webos.settingsservice/getSystemSettings':'home-settings',
    'com.webos.service.systemprofile/getProfiles':'home-profiles',
    'com.local.nativehome.service/disable':'helper-disable',
    'com.gathin.tvhome.renewal/disable':'home-disable',
    'com.palm.activitymanager/list':'activities-list',
    'com.palm.activitymanager/getActivityInfo':'activities-list',
    'com.palm.activitymanager/cancel':'activity-cancel',
    'com.webos.service.eim/getAllInputStatus':'inputs-list',
    'com.webos.service.eim/deleteDevice':'input-delete'}
REASONS=('negative-reply','permission-denied','service-missing','method-missing',
         'timeout','oversized-reply','malformed-reply','client-start-failed')


def summary(value):
    if not isinstance(value,dict):return {}
    result={'call':value.get('call') if value.get('call') in CALLS.values() else 'other',
            'reason':value.get('reason') if value.get('reason') in REASONS else 'negative-reply'}
    code=value.get('error_code')
    if type(code) is int and -(2**31)<=code<2**31:result['error_code']=code
    return result


def context(error,uri,reason,reply=None):
    # Fixed identifiers only: no URI/payload/error text crosses this boundary.
    value={'call':CALLS.get(uri.removeprefix('luna://'),'other'),'reason':reason}
    if isinstance(reply,dict):
        value['error_code']=reply.get('errorCode')
        text=reply.get('errorText')
        text=text[:1024].lower() if isinstance(text,str) else ''
        if reason=='negative-reply':
            for category,phrases in (
                ('permission-denied',('denied method','permission denied','access denied')),
                ('service-missing',('service does not exist','service is not registered')),
                ('method-missing',('unknown method','method does not exist'))):
                if any(phrase in text for phrase in phrases):value['reason']=category;break
    # Recovery authority must not use the broader diagnostic text categories.
    error.systemprofile_missing=(uri.removeprefix('luna://')=='com.webos.service.systemprofile/getProfiles'
        and reason=='negative-reply' and isinstance(reply,dict) and reply.get('returnValue') is False
        and type(reply.get('errorCode')) is int and reply['errorCode']==-1
        and reply.get('errorText')=='Service does not exist: com.webos.service.systemprofile.')
    error.stopped_launcher=None
    if (uri=='luna://com.webos.applicationManager/closeByAppId' and reason=='negative-reply'
            and isinstance(reply,dict) and reply.get('returnValue') is False
            and type(reply.get('errorCode')) is int and reply['errorCode']==40):
        for app in ('com.cleanyourtv.root.preview','com.gathin.tvhome'):
            if reply.get('errorText')==app+' is not running':error.stopped_launcher=app
    error.luna=summary(value)
    return error


def call(uri,payload,timeout=15,app_id=None):
    limit=2097152 if uri in ('luna://com.palm.activitymanager/list','luna://com.palm.activitymanager/getActivityInfo',
        'luna://com.webos.applicationManager/dev/listApps','luna://com.webos.applicationManager/listApps') else 65536
    identity=[]
    if app_id is not None:
        if app_id!='com.gathin.tvhome' or uri!='luna://com.cleanyourtv.updater.service/status': raise ValueError('Unsupported fixed caller identity')
        identity=['-a',app_id,'-m',app_id+'-cytv']
    try:
        p=subprocess.Popen(['/usr/bin/luna-send',*identity,'-n','1',uri,json.dumps(payload)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except OSError as error:raise context(error,uri,'client-start-failed')
    try:
        end=time.monotonic()+timeout;raw=b''
        while time.monotonic()<end:
            if not select.select([p.stdout],[],[],max(0,end-time.monotonic()))[0]:break
            chunk=os.read(p.stdout.fileno(),4096)
            if not chunk:break
            raw+=chunk
            if len(raw)>limit:raise context(ValueError('Oversized bus reply'),uri,'oversized-reply')
            try:reply=json.loads(raw)
            except ValueError:continue
            if not isinstance(reply,dict) or reply.get('returnValue') is not True:
                reason='negative-reply' if isinstance(reply,dict) and reply.get('returnValue') is False else 'malformed-reply'
                raise context(RuntimeError('Bus operation rejected'),uri,reason,reply)
            return reply
        raise context(TimeoutError('Bus response timed out'),uri,'malformed-reply' if raw else 'timeout')
    finally:
        if p.poll() is None:p.terminate()
        try:p.communicate(timeout=1)
        except subprocess.TimeoutExpired:p.kill();p.communicate()
