"""Read the existing Root Home contract before preparing new runtime/packages."""
import re

from .errors import UserError, TVCommandError, TVRejected

CALLS = {
    'home-settings': ('com.webos.settingsservice/getSystemSettings', {'category':'general','keys':['defaultApps']}),
    'home-profiles': ('com.webos.service.systemprofile/getProfiles', {'names':['defaultApps','idleApp'],'subscribe':False}),
}
REASONS = ('readable', 'rejected', 'invalid-reply', 'unconfirmed', 'not-checked',
           'service-absent', 'setting-not-found')
COMPOSITOR_FAILURES = (
    'c1-probe-failed', 'system-info-request-failed', 'system-info-invalid',
    'keyfilters-request-failed', 'keyfilters-not-configured', 'keyfilters-incompatible', 'keyfilters-service-absent',
    'native-home-request-failed',
    'native-home-unavailable', 'native-home-incompatible',
)
KEYFILTER_PROBE_STATES = ('timeout', 'rejected', 'unconfirmed', 'invalid-reply', 'not-configured',
                          'incompatible', 'readable', 'service-absent')
RIBBON_PROBE_STATES = ('readable', 'rejected', 'timeout', 'invalid-reply', 'unconfirmed')
LEGACY_RIBBON = ('This TV uses the LG Home ribbon and has no System Profile or KeyFilters support. '
                 'Choose No-root to continue.')
NATIVE_HOME_UNAVAILABLE_MESSAGE = 'Root cannot control Home on this TV. You can try No-root using the existing SSH connection.'


def keyfilter_probe(info, state, code=None):
    if info is None:
        return
    result = info['root_keyfilters_probe'] = {'state': state}
    if type(code) is int and -(2**31) <= code < 2**31:
        result['error_code'] = code


class RootCapabilityError(UserError):
    def __init__(self, message='Required Root Home interfaces could not be verified. Setup stopped; keep recovery data and save the report.'):
        super().__init__(message, reason_code='root-home-interfaces')


class NoRootAlternativeError(RootCapabilityError):
    """Root Home is unavailable and setup can offer No-root."""


class LegacyRibbonError(NoRootAlternativeError):
    def __init__(self):
        super().__init__(LEGACY_RIBBON)


def ribbon_probe(remote):
    try:
        reply = remote.luna('com.webos.surfacemanager.home/getCurrentHomeUIState', {},
                            timeout=5, allow_missing_return=True)
    except TVRejected:
        return 'rejected'
    except TimeoutError:
        return 'timeout'
    except Exception:
        return 'unconfirmed'
    if not isinstance(reply, dict):
        return 'invalid-reply'
    if reply.get('returnValue') is False or any(key in reply for key in ('errorCode', 'errorText', 'errorMessage')):
        return 'rejected'
    if reply.get('returnValue', True) is not True:
        return 'invalid-reply'
    entries = reply.get('homeUIState')
    if not isinstance(entries, list):
        return 'invalid-reply'
    home = [item for item in entries if isinstance(item, dict) and item.get('uiType') == 'home']
    return 'readable' if len(home) == 1 and type(home[0].get('visibility')) is bool else 'invalid-reply'



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
NATIVE_HOME_UNAVAILABLE = 42
NATIVE_HEADERS = f"""set -e
export LC_ALL=C
home=/usr/bin/com.webos.app.home
test ! -L /usr && test ! -L /usr/bin && test ! -L "$home" && test -f "$home" && test -x "$home" || exit {NATIVE_HOME_UNAVAILABLE}
stat -c '%u %h %a %s' "$home"
od -An -v -tu1 -N52 /bin/sh
printf '\nCYTV_HOME_ELF\n'
od -An -v -tu1 -N52 "$home"
printf '\nCYTV_HOME_FS\n'
stat -f -c '%t' "$home" 2>/dev/null || printf 'unknown\n'
"""


def arm32_elf(dump):
    fields = dump.split()
    if len(fields) != 52 or any(not re.fullmatch(r'[0-9]{1,3}', value) or int(value) > 255 for value in fields):
        return False
    header = bytes(int(value) for value in fields)
    return (header[:7] == b'\x7fELF\x01\x01\x01' and header[16:18] in (b'\x02\0', b'\x03\0')
            and header[18:24] == b'\x28\0\x01\0\0\0' and header[40:44] == b'\x34\0\x20\0'
            and int.from_bytes(header[28:32], 'little') >= 52 and header[44:46] != b'\0\0')


def c1_device(remote, info=None):
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
    return native_headers_valid(remote.run(NATIVE_HEADERS, timeout=5), info)


def native_headers_valid(result, info=None):
    if not isinstance(result,str) or len(result)>2048:
        return False
    metadata, _, headers = result.partition('\n')
    meta = re.fullmatch(r'(0|1001) 1 ([0-7]{3,4}) ([0-9]{1,10})', metadata)
    if not meta or not 52 <= int(meta[3]) <= 16*1024*1024:
        return False
    mode = int(meta[2],8)
    shell, separator, home = headers.partition('CYTV_HOME_ELF')
    home, filesystem_marker, filesystem = home.partition('CYTV_HOME_FS')
    # UID 1001 is a vendor owner only on an immutable SquashFS image.
    if meta[1] == '1001' and (not filesystem_marker or filesystem.strip() != '73717368'):
        return False
    if not mode & 0o111 or mode & 0o7022:
        if info is not None:
            info['root_native_home_mode'] = format(mode, '04o')
        return False
    return bool(separator and arm32_elf(shell) and arm32_elf(home))


def compositor_failure(remote, info=None):
    """Return a diagnostic code for a failed host check, or None on success.

    Model and SDK are observations, not admission lists. Native Home and the
    vendor JS chain are required; the device rechecks their actual contract.
    """
    try:
        reply = remote.luna('com.webos.service.tv.systemproperty/getSystemInfo',
                            {'keys':['modelName','firmwareVersion','sdkVersion']}, timeout=5)
    except Exception:
        return 'system-info-request-failed'
    if isinstance(reply, dict) and reply.get('returnValue') is False:
        return 'system-info-request-failed'
    if (not isinstance(reply,dict) or reply.get('returnValue') is not True
            or not all(isinstance(reply.get(k),str) for k in ('modelName','firmwareVersion','sdkVersion'))
            or not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', str(reply.get('modelName','')))
            or not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[A-Za-z0-9.]+)?',str(reply.get('firmwareVersion','')))
            or not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[A-Za-z0-9.]+)?',str(reply.get('sdkVersion','')))):
        return 'system-info-invalid'
    key = 'com.webos.surfacemanager.keyFilters'
    uri = 'com.webos.service.config/getConfigs'
    try:
        chain = remote.luna(uri, {'configNames':[key]}, timeout=5)
        if isinstance(chain, dict) and chain.get('returnValue') is False:
            raise TVRejected('', chain, uri)
    except TVRejected as error:
        if error.config_service_missing:
            keyfilter_probe(info, 'service-absent', error.luna.get('error_code'))
            return 'keyfilters-service-absent'
        keyfilter_probe(info, 'rejected', error.luna.get('error_code'))
        return 'keyfilters-request-failed'
    except TimeoutError:
        keyfilter_probe(info, 'timeout')
        return 'keyfilters-request-failed'
    except Exception:
        keyfilter_probe(info, 'unconfirmed')
        return 'keyfilters-request-failed'
    if not isinstance(chain, dict) or chain.get('returnValue') is not True:
        keyfilter_probe(info, 'invalid-reply')
        return 'keyfilters-request-failed'
    configs = chain.get('configs')
    entries = configs.get(key) if isinstance(configs, dict) else None
    if isinstance(configs, dict) and (key not in configs or entries == []):
        keyfilter_probe(info, 'not-configured')
        return 'keyfilters-not-configured'
    if (not isinstance(entries,list) or not 1 <= len(entries) <= 128
            or not all(isinstance(e,dict) and isinstance(e.get('file'),str)
                and re.fullmatch(r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js',e['file'])
                and isinstance(e.get('handler'),str) and re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]{0,127}',e['handler']) for e in entries)
            or sum(e['file'].endswith('/systemUi.js') and e['handler']=='handleSystemKeys' for e in entries) != 1):
        keyfilter_probe(info, 'incompatible')
        return 'keyfilters-incompatible'
    keyfilter_probe(info, 'readable')
    try:
        headers = remote.run(NATIVE_HEADERS, timeout=5)
    except TVCommandError as error:
        if error.exit_status == NATIVE_HOME_UNAVAILABLE:
            return 'native-home-unavailable'
        return 'native-home-request-failed'
    except Exception:
        return 'native-home-request-failed'
    return None if native_headers_valid(headers, info) else 'native-home-incompatible'


def verify(remote, checklist, info, allow_c1=False, allow_compositor=False):
    info.pop('home_backend', None)
    info.pop('home_backend_schema', None)
    info.pop('root_compositor_failure', None)
    info.pop('root_keyfilters_probe', None)
    info.pop('root_ribbon_probe', None)
    info.pop('root_native_home_mode', None)
    reasons = info['root_capabilities'] = dict.fromkeys(CALLS, 'not-checked')
    requirements = info.setdefault('root_requirements', {})
    codes = info['root_capability_codes'] = {}
    for name in (('home-profiles','home-settings') if allow_c1 else CALLS):
        uri, payload = CALLS[name]
        rejection = None
        checklist.update(name, 'running')
        code = None
        try:
            reply = remote.luna(uri, payload, timeout=5)
            code = reply.get('errorCode') if isinstance(reply,dict) else None
            if isinstance(reply, dict) and reply.get('returnValue') is False:
                rejection = TVRejected('', reply, uri)
            reason = 'readable' if valid(name, reply) else 'invalid-reply'
        except TVRejected as error:
            rejection = error
            code = error.luna.get('error_code')
        except Exception:
            reason = 'unconfirmed'
        if rejection is not None:
            if name == 'home-profiles' and rejection.systemprofile_missing:
                reason = 'service-absent'
            elif name == 'home-settings' and rejection.system_setting_not_found:
                reason = 'setting-not-found'
            else:
                reason = 'rejected'
        if type(code) is int and -(2**31)<=code<2**31:
            codes[name] = code
        if allow_c1 and reason == 'service-absent':
            failure = None
            schema = 2
            try:
                supported = c1_device(remote, info)
            except Exception:
                supported = False
                if allow_compositor:
                    failure = 'c1-probe-failed'
            else:
                if not supported and allow_compositor:
                    failure = compositor_failure(remote, info)
                    supported = failure is None
                    schema = 3
            reasons[name] = reason
            if supported:
                info.pop('root_native_home_mode', None)
                for key in CALLS:
                    requirements.pop(key, None)
                checklist.update(name,'unknown','System Profile is absent. Experimental compositor Home prerequisites passed; physical controls are unverified.')
                checklist.update('home-settings','unknown','Profile settings are not required by compositor Home.')
                info['home_backend'] = 'c1-native-gate'
                info['home_backend_schema'] = schema
                return info['home_backend']
            if failure is not None:
                info['root_compositor_failure'] = failure
            requirements[name] = 'fail'
            if failure == 'native-home-unavailable':
                checklist.update(name, 'fail', NATIVE_HOME_UNAVAILABLE_MESSAGE)
                raise NoRootAlternativeError(NATIVE_HOME_UNAVAILABLE_MESSAGE)
            if failure in ('keyfilters-not-configured', 'keyfilters-service-absent'):
                info['root_ribbon_probe'] = ribbon_probe(remote)
                if info['root_ribbon_probe'] == 'readable':
                    checklist.update(name, 'fail', LEGACY_RIBBON)
                    raise LegacyRibbonError()
            checklist.update(name,'fail','System Profile is absent and a supported experimental Home backend was not verified.')
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
