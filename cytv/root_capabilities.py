"""Read the existing Root Home contract before preparing new runtime/packages."""
import re
import shlex

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
    'native-home-unavailable', 'native-home-incompatible', 'native-home-script',
)
KEYFILTER_PROBE_STATES = ('timeout', 'rejected', 'unconfirmed', 'invalid-reply', 'not-configured',
                          'incompatible', 'readable', 'service-absent')
RIBBON_PROBE_STATES = ('readable', 'rejected', 'timeout', 'invalid-reply', 'unconfirmed')
LEGACY_RIBBON = 'This TV uses the LG Home ribbon and has no System Profile or KeyFilters support.'
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


class NativeHomeScriptError(RootCapabilityError):
    def __init__(self):
        from .failure_help import NATIVE_HOME_SCRIPT
        super().__init__(NATIVE_HOME_SCRIPT[1])
        self.reason_code = 'native-home-script'


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

NATIVE_HOME_MOUNT_STATES = (
    'absent', 'file-mount', 'stacked-file-mounts', 'file-and-parent-mounts',
    'parent-overlay', 'parent-mount', 'multiple-parent-mounts', 'unknown',
)
NATIVE_HOME_MOUNT_AWK = """'
    {
        if (NR > 8192) { invalid = 1; exit }
        for (sep = 7; sep <= NF && $sep != "-"; sep++) {}
        if (sep + 3 != NF || $1 !~ /^[0-9]+$/ || $2 !~ /^[0-9]+$/ || substr($5, 1, 1) != "/") {
            invalid = 1
            exit
        }
        if ($5 == "/usr/bin/com.webos.app.home") {
            files++
            row = $0
            file_parent = $2
            for (i = 7; i < sep; i++)
                if ($i ~ /^shared:/) shared = 1
        }
        if ($5 == "/") {
            roots++
            root_id = $1
            for (i = 7; i < sep; i++)
                if ($i ~ /^shared:/) shared = 1
            if ($(sep + 1) == "squashfs" && $6 ~ /(^|,)ro(,|$)/ &&
                $(sep + 3) ~ /(^|,)ro(,|$)/) stock_root = 1
        }
        if ($5 == "/usr" || $5 == "/usr/bin") {
            parents++
            if ($(sep + 1) == "overlay") overlay = 1
        }
    }
    END {
        if (mode == "snapshot" || mode == "preview") {
            if (invalid || roots != 1 || files != 1 || file_parent != root_id || parents || shared) exit 1
            if (mode == "preview") sub(/^[0-9]+ +[0-9]+ +/, "", row)
            print row
        }
        else if (mode == "stock") {
            if (invalid || roots != 1 || stock_root != 1 || files || parents) exit 1
        }
        else if (invalid || !NR) print "unknown"
        else if (files > 1) print "stacked-file-mounts"
        else if (files && parents) print "file-and-parent-mounts"
        else if (files) print "file-mount"
        else if (parents > 1) print "multiple-parent-mounts"
        else if (overlay) print "parent-overlay"
        else if (parents) print "parent-mount"
        else print "absent"
    }'"""
NATIVE_HOME_MOUNT_PROBE = 'LC_ALL=C awk ' + NATIVE_HOME_MOUNT_AWK + ' /proc/self/mountinfo'
NATIVE_HOME_MOUNT_SNAPSHOT = 'LC_ALL=C awk -v mode=snapshot ' + NATIVE_HOME_MOUNT_AWK + ' /proc/self/mountinfo'
NATIVE_HOME_STOCK_MOUNT = 'LC_ALL=C awk -v mode=stock ' + NATIVE_HOME_MOUNT_AWK + ' /proc/self/mountinfo'
NATIVE_HOME_PATH = '/usr/bin/com.webos.app.home'
RESTORE_NATIVE_HOME = 'Restore LG Home for Root setup?'


def restore_native_home(remote, mount_state, confirm):
    """Inspect the covered Home in a private mount namespace before restoring it."""
    if mount_state != 'file-mount':
        return False
    home = NATIVE_HOME_PATH
    readback = (f'{NATIVE_HOME_STOCK_MOUNT}\n'
                f"sha256sum {home} | awk '{{print $1}}'\n"
                + NATIVE_HEADERS)
    try:
        snapshot = remote.run(NATIVE_HOME_MOUNT_SNAPSHOT, timeout=5).strip()
        fields = snapshot.split()
        if len(snapshot) > 2048 or '\n' in snapshot or len(fields) < 10 or fields[4] != home:
            return False
        unchanged = f'test "$({NATIVE_HOME_MOUNT_SNAPSHOT})" = {shlex.quote(snapshot)}'
        script = f'''test "$(od -An -v -tu1 -N2 {home} | awk '{{print $1, $2}}')" = '35 33' '''
        regular = f'test ! -L /usr && test ! -L /usr/bin && test ! -L {home} && test -f {home}'
        uncover = f'{regular}\n{script}\numount {home}\n'
        # A cloned namespace can assign new mount IDs to the same filesystems.
        preview_snapshot = NATIVE_HOME_MOUNT_SNAPSHOT.replace('mode=snapshot', 'mode=preview')
        mount_identity = re.sub(r'^[0-9]+ +[0-9]+ +', '', snapshot)
        preview_guard = f'test "$({preview_snapshot})" = {shlex.quote(mount_identity)}'
        preview_command = 'unshare --mount --propagation private /bin/sh -c ' + shlex.quote(
            f'set -e\n{preview_guard}\n{uncover}{readback}')
        preview = remote.run(preview_command, timeout=15)
        digest, _, headers = preview.partition('\n')
        if not re.fullmatch(r'[0-9a-f]{64}', digest) or not native_headers_valid(headers):
            return False
    except (UserError, OSError, TimeoutError):
        return False
    if not confirm():
        return False

    # Match the ELF fingerprint from the private preview before reporting success.
    verify_digest = f"""test "$(sha256sum {home} | awk '{{print $1}}')" = {digest}\n"""
    try:
        reply = remote.run(f'set -e\n{unchanged}\n{uncover}{verify_digest}{readback}', timeout=15)
    except (UserError, OSError, TimeoutError) as error:
        raise UserError('Root operation was not confirmed.', reason_code='root-operation-unconfirmed') from error
    if reply != preview:
        raise UserError('Root operation was not confirmed.', reason_code='root-operation-unconfirmed')
    return True


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
    return native_header_failure(result, info) is None


def native_header_failure(result, info=None):
    if not isinstance(result,str) or len(result)>2048:
        return 'native-home-incompatible'
    metadata, _, headers = result.partition('\n')
    meta = re.fullmatch(r'(0|1001) 1 ([0-7]{3,4}) ([0-9]{1,10})', metadata)
    if not meta or not 52 <= int(meta[3]) <= 16*1024*1024:
        return 'native-home-incompatible'
    mode = int(meta[2],8)
    shell, separator, home = headers.partition('CYTV_HOME_ELF')
    home, filesystem_marker, filesystem = home.partition('CYTV_HOME_FS')
    # UID 1001 is a vendor owner only on an immutable SquashFS image.
    if meta[1] == '1001' and (not filesystem_marker or filesystem.strip() != '73717368'):
        return 'native-home-incompatible'
    if not mode & 0o111 or mode & 0o7022:
        if info is not None:
            info['root_native_home_mode'] = format(mode, '04o')
        return 'native-home-incompatible'
    if not separator or not arm32_elf(shell):
        return 'native-home-incompatible'
    if home.split()[:2] == ['35', '33']:
        return 'native-home-script'
    return None if arm32_elf(home) else 'native-home-incompatible'


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
    failure = native_header_failure(headers, info)
    if failure == 'native-home-script' and info is not None:
        try:
            mount = remote.run(NATIVE_HOME_MOUNT_PROBE, timeout=5).strip()
        except Exception:
            mount = 'unknown'
        info['root_native_home_mount'] = mount if mount in NATIVE_HOME_MOUNT_STATES else 'unknown'
    return failure


def verify(remote, checklist, info, allow_c1=False, allow_compositor=False):
    info.pop('home_backend', None)
    info.pop('home_backend_schema', None)
    info.pop('root_compositor_failure', None)
    info.pop('root_keyfilters_probe', None)
    info.pop('root_ribbon_probe', None)
    info.pop('root_native_home_mode', None)
    info.pop('root_native_home_mount', None)
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
            if failure == 'native-home-script':
                error = NativeHomeScriptError()
                checklist.update(name, 'fail', str(error))
                raise error
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
