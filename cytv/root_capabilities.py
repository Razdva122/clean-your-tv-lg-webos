"""Read the existing Root Home contract before preparing new runtime/packages."""
import re

from .errors import UserError, TVRejected

CALLS = {
    'home-settings': ('com.webos.settingsservice/getSystemSettings', {'category':'general','keys':['defaultApps']}),
    'home-profiles': ('com.webos.service.systemprofile/getProfiles', {'names':['defaultApps','idleApp'],'subscribe':False}),
}
REASONS = ('readable', 'rejected', 'invalid-reply', 'unconfirmed', 'not-checked', 'service-absent')


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


# Reading the existing userland shell and Home ELF also works before the TV has
# a usable Python runtime. No input from the TV is interpolated into this command.
NATIVE_HEADERS = """set -e
export LC_ALL=C
home=/usr/bin/com.webos.app.home
test ! -L /usr && test ! -L /usr/bin && test ! -L "$home" && test -f "$home" && test -x "$home" || exit 1
stat -c '%u %h %a %s' "$home"
od -An -v -tu1 -N52 /bin/sh
printf '\nCYTV_HOME_ELF\n'
od -An -v -tu1 -N52 "$home"
"""


def arm32_elf(dump):
    fields = dump.split()
    if len(fields) != 52 or any(not re.fullmatch(r'[0-9]{1,3}', value) for value in fields):
        return False
    header = bytes(int(value) for value in fields)
    return (header[:7] == b'\x7fELF\x01\x01\x01' and header[16:18] in (b'\x02\0', b'\x03\0')
            and header[18:24] == b'\x28\0\x01\0\0\0' and header[40:44] == b'\x34\0\x20\0'
            and int.from_bytes(header[28:32], 'little') >= 52 and header[44:46] != b'\0\0')


def c1_device(remote):
    reply = remote.luna('com.webos.service.tv.systemproperty/getSystemInfo',
                        {'keys':['modelName','firmwareVersion','sdkVersion']}, timeout=5)
    if not isinstance(reply,dict) or reply.get('returnValue') is not True:
        return False
    version = r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:-[A-Za-z0-9.]+)?'
    model, firmware, sdk = (reply.get(k) for k in ('modelName','firmwareVersion','sdkVersion'))
    if (not all(isinstance(v,str) for v in (model,firmware,sdk))
            or not re.fullmatch(r'OLED(?:48|55|65|77|83)C1[A-Z0-9]{2,12}', model)
            or not re.fullmatch(version,firmware) or not re.fullmatch(version,sdk) or not sdk.startswith('6.')):
        return False
    result = remote.run(NATIVE_HEADERS, timeout=5)
    if not isinstance(result,str) or len(result)>2048:
        return False
    metadata, _, headers = result.partition('\n')
    meta = re.fullmatch(r'0 1 ([0-7]{3,4}) ([0-9]{1,10})', metadata)
    if not meta or not 52 <= int(meta[2]) <= 4*1024*1024:
        return False
    mode = int(meta[1],8)
    shell, separator, home = headers.partition('CYTV_HOME_ELF')
    return bool(mode & 0o111 and not mode & 0o022 and separator and arm32_elf(shell) and arm32_elf(home))


def verify(remote, checklist, info, allow_c1=False):
    info.pop('home_backend', None)
    reasons = info['root_capabilities'] = dict.fromkeys(CALLS, 'not-checked')
    requirements = info.setdefault('root_requirements', {})
    codes = info['root_capability_codes'] = {}
    for name in (('home-profiles','home-settings') if allow_c1 else CALLS):
        uri, payload = CALLS[name]
        absent = False
        checklist.update(name, 'running')
        code = None
        try:
            reply = remote.luna(uri, payload, timeout=5)
            if allow_c1 and name == 'home-profiles' and isinstance(reply,dict) and reply.get('returnValue') is False:
                absent = TVRejected('', reply, uri).systemprofile_missing
            code = reply.get('errorCode') if isinstance(reply,dict) else None
            reason = ('readable' if valid(name,reply) else
                      'rejected' if isinstance(reply,dict) and reply.get('returnValue') is False else 'invalid-reply')
        except TVRejected as error:
            reason = 'rejected'
            absent = error.systemprofile_missing
            code = error.luna.get('error_code')
        except Exception:
            reason = 'unconfirmed'
        if type(code) is int and -(2**31)<=code<2**31:
            codes[name] = code
        if allow_c1 and name == 'home-profiles' and absent:
            try:
                supported = c1_device(remote)
            except Exception:
                supported = False
            reasons[name] = 'service-absent'
            if supported:
                for key in CALLS:
                    requirements.pop(key, None)
                checklist.update(name,'unknown','System Profile is absent. Verified the C1 native Home backend.')
                checklist.update('home-settings','unknown','Profile settings are not required by native C1 Home.')
                info['home_backend'] = 'c1-native-gate'
                return info['home_backend']
            requirements[name] = 'fail'
            checklist.update(name,'fail','System Profile is absent and the C1 native Home identity was not verified.')
            raise RootCapabilityError()
        reasons[name] = reason
        status = 'pass' if reason=='readable' else 'unknown' if reason=='unconfirmed' else 'fail'
        requirements[name] = status
        checklist.update(name,status, '' if status=='pass' else
                         'The required Home interface could not be read safely. No repair or routing change was attempted by this check.')
    if any(reason!='readable' for reason in reasons.values()):
        raise RootCapabilityError()
    info['home_backend'] = 'system-profile'
    return info['home_backend']
