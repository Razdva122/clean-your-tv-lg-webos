"""Read the existing Root Home contract before preparing new runtime/packages."""
from .errors import UserError, TVRejected

CALLS = {
    'home-settings': ('com.webos.settingsservice/getSystemSettings', {'category':'general','keys':['defaultApps']}),
    'home-profiles': ('com.webos.service.systemprofile/getProfiles', {'names':['defaultApps','idleApp'],'subscribe':False}),
}
REASONS = ('readable', 'rejected', 'invalid-reply', 'unconfirmed', 'not-checked')


class RootCapabilityError(UserError):
    def __init__(self):
        super().__init__('Required Root Home interfaces could not be verified. Setup stopped; keep recovery data and save the report.',
                         reason_code='root-home-interfaces')


def valid(name, reply):
    try:
        if not isinstance(reply, dict) or reply.get('returnValue') is not True:
            return False
        if name == 'home-settings':
            defaults = reply['settings']['defaultApps']
            return isinstance(defaults,dict) and ('home' not in defaults or route(defaults['home']))
        profiles = reply['profiles']
        return (type(profiles['idleApp']['support']) is bool and
                route(profiles['defaultApps']['categories']['home']) and route(profiles['idleApp']['appId']))
    except (KeyError, TypeError):
        return False


def route(value):
    return isinstance(value,str) and bool(value) and value.strip()==value


def verify(remote, checklist, info):
    reasons = info['root_capabilities'] = dict.fromkeys(CALLS, 'not-checked')
    requirements = info.setdefault('root_requirements', {})
    codes = info['root_capability_codes'] = {}
    for name, (uri, payload) in CALLS.items():
        checklist.update(name, 'running')
        code = None
        try:
            reply = remote.luna(uri, payload, timeout=5)
            code = reply.get('errorCode') if isinstance(reply,dict) else None
            reason = ('readable' if valid(name,reply) else
                      'rejected' if isinstance(reply,dict) and reply.get('returnValue') is False else 'invalid-reply')
        except TVRejected as error:
            reason = 'rejected'
            code = error.luna.get('error_code')
        except Exception:
            reason = 'unconfirmed'
        if type(code) is int and -(2**31)<=code<2**31:
            codes[name] = code
        reasons[name] = reason
        status = 'pass' if reason=='readable' else 'unknown' if reason=='unconfirmed' else 'fail'
        requirements[name] = status
        checklist.update(name,status, '' if status=='pass' else
                         'The required Home interface could not be read safely. No repair or routing change was attempted by this check.')
    if any(reason!='readable' for reason in reasons.values()):
        raise RootCapabilityError()
