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
KEYFILTER_PREDICATES = (
    'configs-not-object', 'entries-not-list', 'entry-count-invalid', 'entry-not-object',
    'file-invalid', 'path-outside-contract', 'handler-invalid',
    'system-filter-missing', 'system-filter-duplicate',
)
NATIVE_HOME_PREDICATES = (
    'readable', 'request-failed', 'unavailable', 'invalid-output', 'metadata-invalid',
    'size-out-of-range', 'vendor-filesystem-unverified', 'mode-invalid',
    'shell-header-invalid', 'home-script', 'home-header-invalid',
)
C1_PROBE_STATES = ('admitted', 'request-failed', 'identity-rejected', 'identity-outside-contract',
                   'native-home-rejected')
RIBBON_PROBE_STATES = ('readable', 'rejected', 'timeout', 'invalid-reply', 'unconfirmed')
LEGACY_RIBBON = 'This TV uses the LG Home ribbon and has no System Profile or KeyFilters support.'
NATIVE_HOME_UNAVAILABLE_MESSAGE = 'Root cannot control Home on this TV. You can try No-root using the existing SSH connection.'


def keyfilter_probe(info, state, code=None, *, predicate=None):
    if info is None:
        return
    result = info['root_keyfilters_probe'] = {'state': state}
    if predicate is not None:
        result['predicate'] = predicate
    if type(code) is int and -(2**31) <= code < 2**31:
        result['error_code'] = code


class RootCapabilityError(UserError):
    def __init__(self, message='Required Root Home interfaces could not be verified. Setup stopped; keep recovery data and save the report.'):
        super().__init__(message, reason_code='root-home-interfaces')


class NativeHomeScriptError(RootCapabilityError):
    reason = 'native-home-script'

    def __init__(self):
        from .failure_help import GUIDES
        super().__init__(GUIDES[self.reason][1])
        self.reason_code = self.reason


class ForeignHomeHandoffRequired(NativeHomeScriptError):
    reason = 'foreign-home-handoff-required'


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
UNSUPPORTED_HOME_MOUNTS = {
    'stacked-file-mounts', 'file-and-parent-mounts', 'parent-overlay',
    'parent-mount', 'multiple-parent-mounts',
}


def native_home_script_error(info):
    if info.get('root_native_home_mount') in UNSUPPORTED_HOME_MOUNTS:
        return ForeignHomeHandoffRequired()
    return NativeHomeScriptError()


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


def clear_home_observations(info):
    for name in ('root_capabilities', 'root_capability_codes', 'root_compositor_failure',
                 'root_compositor_observation', 'root_c1_probe', 'root_keyfilters_probe',
                 'root_ribbon_probe', 'root_native_home_probe', 'root_native_home_mode',
                 'root_native_home_mount', 'home_backend', 'home_backend_schema'):
        info.pop(name, None)


def c1_identity(remote):
    reply = remote.luna('com.webos.service.tv.systemproperty/getSystemInfo',
                        {'keys':['modelName','firmwareVersion','sdkVersion']}, timeout=5)
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        return 'identity-rejected'
    version = r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:-[A-Za-z0-9.]+)?'
    model, firmware, sdk = (reply.get(k) for k in ('modelName','firmwareVersion','sdkVersion'))
    if (not all(isinstance(v,str) for v in (model,firmware,sdk))
            or not re.fullmatch(r'OLED(?:48|55|65|77|83)C1[A-Z0-9]{2,12}', model)
            or not re.fullmatch(version,firmware) or not re.fullmatch(version,sdk) or not sdk.startswith('6.')):
        return 'identity-outside-contract'
    return 'match'


def c1_device(remote, info=None, *, read_headers=None):
    if info is not None:
        info.pop('root_c1_probe', None)
        clear_native_probe(info)
    try:
        identity = c1_identity(remote)
    except Exception:
        if info is not None:
            info['root_c1_probe'] = 'request-failed'
        raise
    if identity != 'match':
        if info is not None:
            info['root_c1_probe'] = identity
        return False
    try:
        supported = probe_native_home(remote, info, read_headers=read_headers, strict=True,
                                      inspect_mount=False) is None
    except Exception:
        if info is not None:
            info['root_c1_probe'] = 'native-home-rejected'
        raise
    if info is not None:
        info['root_c1_probe'] = 'admitted' if supported else 'native-home-rejected'
    return supported


def clear_native_probe(info):
    for name in ('root_native_home_probe', 'root_native_home_mode', 'root_native_home_mount'):
        info.pop(name, None)


def native_headers_valid(result, info=None):
    return native_header_failure(result, info) is None


def native_header_failure(result, info=None):
    if info is not None:
        clear_native_probe(info)
    predicate = native_header_predicate(result, info)
    if info is not None:
        info['root_native_home_probe'] = predicate
    if predicate == 'readable':
        return None
    return 'native-home-script' if predicate == 'home-script' else 'native-home-incompatible'


def native_header_predicate(result, info):
    if not isinstance(result, str) or len(result) > 2048:
        return 'invalid-output'
    metadata, _, headers = result.partition('\n')
    meta = re.fullmatch(r'(0|1001) 1 ([0-7]{3,4}) ([0-9]{1,10})', metadata)
    if not meta:
        return 'metadata-invalid'
    if not 52 <= int(meta[3]) <= 16*1024*1024:
        return 'size-out-of-range'
    mode = int(meta[2], 8)
    shell, separator, home = headers.partition('CYTV_HOME_ELF')
    home, filesystem_marker, filesystem = home.partition('CYTV_HOME_FS')
    # UID 1001 is a vendor owner only on an immutable SquashFS image.
    if meta[1] == '1001' and (not filesystem_marker or filesystem.strip() != '73717368'):
        return 'vendor-filesystem-unverified'
    if not mode & 0o111 or mode & 0o7022:
        if info is not None:
            info['root_native_home_mode'] = format(mode, '04o')
        return 'mode-invalid'
    if not separator or not arm32_elf(shell):
        return 'shell-header-invalid'
    if home.split()[:2] == ['35', '33']:
        return 'home-script'
    return 'readable' if arm32_elf(home) else 'home-header-invalid'


def probe_native_home(remote, info=None, *, read_headers=None, strict=False, inspect_mount=True,
                      allow_unavailable=False):
    if info is not None:
        clear_native_probe(info)
    try:
        headers = read_headers() if read_headers else remote.run(NATIVE_HEADERS, timeout=5)
    except Exception as error:
        unavailable = isinstance(error, TVCommandError) and error.exit_status == NATIVE_HOME_UNAVAILABLE
        if info is not None:
            info['root_native_home_probe'] = 'unavailable' if unavailable else 'request-failed'
        if strict and not (allow_unavailable and unavailable):
            raise
        return 'native-home-unavailable' if unavailable else 'native-home-request-failed'
    failure = native_header_failure(headers, info)
    if failure == 'native-home-script' and info is not None and inspect_mount:
        try:
            response = remote.run(NATIVE_HOME_MOUNT_PROBE, timeout=5)
            mount = response.strip() if isinstance(response, str) else 'unknown'
        except Exception:
            if strict:
                raise
            mount = 'unknown'
        info['root_native_home_mount'] = mount if mount in NATIVE_HOME_MOUNT_STATES else 'unknown'
    return failure


def keyfilters_structure_failure(configs, key):
    if not isinstance(configs, dict):
        return 'configs-not-object'
    entries = configs.get(key)
    if not isinstance(entries, list):
        return 'entries-not-list'
    if not 1 <= len(entries) <= 128:
        return 'entry-count-invalid'
    for entry in entries:
        if not isinstance(entry, dict):
            return 'entry-not-object'
        file, handler = entry.get('file'), entry.get('handler')
        if not isinstance(file, str):
            return 'file-invalid'
        if not re.fullmatch(r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js', file):
            return 'path-outside-contract'
        if not isinstance(handler, str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]{0,127}', handler):
            return 'handler-invalid'
    system_filters = sum(e['file'].endswith('/systemUi.js') and e['handler'] == 'handleSystemKeys' for e in entries)
    if system_filters != 1:
        return 'system-filter-duplicate' if system_filters else 'system-filter-missing'
    return None


def compositor_failure(remote, info=None, *, read_headers=None):
    """Return a diagnostic code for a failed host check, or None on success.

    Model and SDK are observations, not admission lists. Native Home and the
    vendor JS chain are required; the device rechecks their actual contract.
    """
    if info is not None:
        info.pop('root_keyfilters_probe', None)
        clear_native_probe(info)
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
    predicate = keyfilters_structure_failure(configs, key)
    if predicate is not None:
        keyfilter_probe(info, 'incompatible', predicate=predicate)
        return 'keyfilters-incompatible'
    keyfilter_probe(info, 'readable')
    return probe_native_home(remote, info, read_headers=read_headers)


def verify(remote, checklist, info, allow_c1=False, allow_compositor=False, *, diagnose=False, absent_profile_only=False):
    clear_home_observations(info)
    for name in CALLS:
        if name in checklist.results:
            checklist.update(name, 'pending', '')
    admission_error = None
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
            # Doctor can reuse the C1 header observation; setup retains its
            # separate schema-3 read and its C1 exception short circuit.
            header_reads = []

            def read_headers():
                if not header_reads:
                    try:
                        header_reads.append(remote.run(NATIVE_HEADERS, timeout=5))
                    except Exception as caught:
                        header_reads.append(caught)
                if isinstance(header_reads[0], Exception):
                    raise header_reads[0]
                return header_reads[0]

            read = read_headers if diagnose else None
            try:
                supported = c1_device(remote, info, read_headers=read) if diagnose else c1_device(remote, info)
            except Exception:
                supported = False
                if allow_compositor:
                    failure = 'c1-probe-failed'
                    if diagnose:
                        observed = compositor_failure(remote, info, read_headers=read)
                        if observed is not None:
                            info['root_compositor_observation'] = observed
            else:
                if not supported and allow_compositor:
                    failure = compositor_failure(remote, info, read_headers=read)
                    supported = failure is None
                    schema = 3
            if (diagnose and not supported and
                    ('root_native_home_probe' not in info or
                     (info['root_native_home_probe'] == 'home-script' and 'root_native_home_mount' not in info))):
                probe_native_home(remote, info, read_headers=read)
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
                admission_error = native_home_script_error(info)
                checklist.update(name, 'fail', str(admission_error))
            elif failure == 'native-home-unavailable':
                checklist.update(name, 'fail', NATIVE_HOME_UNAVAILABLE_MESSAGE)
                admission_error = NoRootAlternativeError(NATIVE_HOME_UNAVAILABLE_MESSAGE)
            else:
                if failure in ('keyfilters-not-configured', 'keyfilters-service-absent'):
                    info['root_ribbon_probe'] = ribbon_probe(remote)
                if info.get('root_ribbon_probe') == 'readable':
                    checklist.update(name, 'fail', LEGACY_RIBBON)
                    admission_error = LegacyRibbonError()
                else:
                    checklist.update(name,'fail','System Profile is absent and a supported experimental Home backend was not verified.')
                    admission_error = RootCapabilityError()
            if not diagnose:
                raise admission_error
            continue
        reasons[name] = reason
        status = 'pass' if reason=='readable' else 'unknown' if reason=='unconfirmed' else 'fail'
        requirements[name] = status
        checklist.update(name,status, '' if status=='pass' else
                         'The required Home interface could not be read safely. No repair or routing change was attempted by this check.')
        if absent_profile_only and name == 'home-profiles':
            return None
    if admission_error is not None:
        raise admission_error
    if any(reason!='readable' for reason in reasons.values()):
        raise RootCapabilityError()
    info['home_backend'] = 'system-profile'
    return info['home_backend']
