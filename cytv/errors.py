import errno
import re


TV_STORAGE_FULL = 'The TV reported insufficient storage space. Free space on the affected TV partition; deleting apps may free a different partition.'
COMPUTER_STORAGE_FULL = 'Not enough space on this computer. Free space on the system or temporary drive.'


def is_storage_full(error):
    return isinstance(error, OSError) and error.errno in (errno.ENOSPC, errno.EDQUOT)


def reports_storage_full(data):
    # Recognize fixed OS diagnostics only; never display remote paths or prose.
    return b'No space left on device' in data or b'Disk quota exceeded' in data


class UserError(RuntimeError):
    """An installer-owned message which contains no remote data or credentials."""
    def __init__(self, message, *, reason_code='user-error'):
        super().__init__(message)
        self.reason_code = reason_code


LOCAL_RECOVERY_REASONS = ('directory-owner', 'directory-permissions', 'directory-type',
                          'directory-access', 'storage-unavailable', 'operation-invalid',
                          'capsule-missing', 'capsule-permissions', 'capsule-unsafe',
                          'capsule-changed', 'capsule-invalid', 'capsule-access', 'source-incompatible')


def local_recovery_details(value):
    value = value if type(value) is dict else {}
    result = {key: value.get(key) if type(value.get(key)) is str and value[key] in allowed else 'unknown'
              for key, allowed in (('reason', LOCAL_RECOVERY_REASONS),
                                   ('location', ('profile', 'ancestor', 'capsule', 'operation')))}
    mode = value.get('mode')
    if type(mode) is str and re.fullmatch('[0-7]{4}', mode):
        result['mode'] = mode
    if type(value.get('owner')) is str and value['owner'] in ('root', 'current-user', 'other'):
        result['owner'] = value['owner']
    return result


class LocalRecoveryError(UserError):
    """Fixed local failure categories; no paths, account names or raw exceptions."""
    def __init__(self, reason, location='capsule', *, mode=None, owner=None, storage_full=False):
        self.local_recovery = local_recovery_details(dict(reason=reason, location=location, mode=mode, owner=owner))
        reason = self.local_recovery['reason']
        message = ('Local recovery storage could not be verified.' if reason.startswith('directory-') or reason == 'storage-unavailable' else
                   'The original private recovery file is missing.' if reason == 'capsule-missing' else
                   'The saved recovery operation is incompatible with this installer.' if reason == 'source-incompatible' else
                   'The original private recovery file could not be verified.')
        super().__init__((COMPUTER_STORAGE_FULL if storage_full else message) + ' Recovery data was kept.',
                         reason_code='computer-storage-full' if storage_full else 'pending-operation')


def connection_interrupted(error):
    """Transient transport loss only; credentials and host trust never retry."""
    return (getattr(error, 'reason_code', None) == 'connection-interrupted'
            or isinstance(error, (ConnectionError, TimeoutError))
            or type(error).__name__ in ('SSHException', 'NoValidConnectionsError'))



class PythonCacheError(UserError):
    """Allowlisted host acquisition failure; never carry remote exception text."""
    DOWNLOAD_ERROR = 'The private Python download could not be verified. Check the connection or prepare the Python cache again.'
    CACHE_ERROR = 'The private Python cache is unsafe or damaged. Remove its pinned archive and prepare the cache again.'

    def __init__(self, reason='unknown'):
        self.reason = reason if reason in ('network', 'tls', 'http', 'response-policy',
            'size', 'sha256', 'deadline', 'cache-access', 'cache-replace', 'cache-invalid') else 'unknown'
        super().__init__(self.CACHE_ERROR if self.reason == 'cache-invalid' else self.DOWNLOAD_ERROR)


class PythonPreflightError(UserError):
    """Fixed reason plus bounded counters; never retain remote error text."""
    def __init__(self, reason='unknown', available_kib=None, required_kib=None, wam_session_kib=None):
        self.reason = reason if reason in ('abi', 'ownership', 'space', 'space-query', 'tools') else 'unknown'
        for key, value in (('available_kib', available_kib), ('required_kib', required_kib), ('wam_session_kib', wam_session_kib)):
            setattr(self, key, value if type(value) is int and 0 <= value <= 2**53 - 1 else None)
        messages = {
            'abi': 'Private Python requires compatible ARM32 soft-float EABI5 userspace. The TV ABI check failed.',
            'ownership': 'Private Python needs real root-owned runtime directories without group or other write access. The directory safety check failed.',
            'space-query': 'Could not read available space in /var/lib. No private Python was installed.',
            'tools': 'Private Python could not verify root access or safe system tools. No runtime was installed.',
            'unknown': 'Private Python compatibility could not be verified. No runtime was installed.',
        }
        if self.reason == 'space' and self.available_kib is not None and self.required_kib is not None:
            message = 'Not enough space for private Python: {available} MiB free in /var/lib; {required} MiB required.'.format(
                available=format((self.available_kib * 10 // 1024) / 10, '.1f').removesuffix('.0'),
                required=format(((self.required_kib * 10 + 1023) // 1024) / 10, '.1f').removesuffix('.0'))
            message += '\nStorage shortfall: {shortfall} MiB.'.format(
                shortfall=format(((max(0, self.required_kib-self.available_kib)*10+1023)//1024)/10, '.1f'))
            if self.wam_session_kib:
                message += '\nWAM Session Storage uses {size} MiB and may contribute to low space. Review the recovery guide before clearing app state.'.format(
                    size=format(self.wam_session_kib / 1024, '.1f').removesuffix('.0'))
            message += '\nYou can cancel and free space yourself. Use the manual cleanup guide and recheck /var/lib; removing apps may free a different partition.'
            message += '\nClose TV apps first. This deletes app session state and may sign you out or lose unsaved work.'
            message += '\nhttps://github.com/Razdva122/clean-your-tv-lg-webos/blob/release/next/docs/WAM-CLEANUP.md'
        else:
            message = messages.get(self.reason, messages['unknown'])
        super().__init__(message)


LUNA_STATES = ('installing', 'installed', 'removing', 'removed', 'success', 'failed', 'error',
               'install failed', 'remove failed')
# Fixed LG OSE installer categories, not arbitrary details.reason text or a retail contract.
PACKAGE_FAILURE_REASONS = ('FAILED_INTERNAL_ERROR', 'FAILED_CREATE_TMP',
                          'FAILED_NOT_ENOUGH_TEMP_SPACE', 'FAILED_NOT_ENOUGH_INSTALL_SPACE',
                          'FAILED_PACKAGEFILE_NOT_FOUND', 'FAILED_PACKAGEFILE_CORRUPT',
                          'FAILED_VERIFY', 'FAILED_IPKG_INSTALL', 'FAILED_INSTALL')


class TVRejected(UserError):
    """A definite negative TV reply, distinct from an unknown connection outcome."""
    def __init__(self, message, reply=None, uri=None):
        super().__init__(message)
        reply = reply if isinstance(reply, dict) else {}
        self.systemprofile_missing = (
            uri == 'com.webos.service.systemprofile/getProfiles'
            and reply.get('returnValue') is False
            and type(reply.get('errorCode')) is int and reply['errorCode'] == -1
            and reply.get('errorText') == 'Service does not exist: com.webos.service.systemprofile.')
        details = reply.get('details')
        details = details if isinstance(details, dict) else {}
        def number(value):
            if isinstance(value, str) and re.fullmatch(r'-?[0-9]{1,10}', value):
                value = int(value)
            return value if type(value) is int and -(2**31) <= value < 2**31 else None
        status = details.get('state')
        status = status.lower() if isinstance(status, str) else 'unknown'
        self.luna = {
            'operation': {'com.webos.appInstallService/dev/install':'package-install',
                          'com.webos.appInstallService/dev/remove':'package-remove',
                          'com.webos.appInstallService/status':'package-status',
                          'com.local.nativehome.service/disable':'helper-disable',
                          'com.webos.service.eim/deleteDevice':'eim-delete-device',
                          'com.webos.applicationManager/launch':'application-launch'}.get(uri, 'luna-call'),
            'error_code': number(reply.get('errorCode')),
            'details_error_code': number(details.get('errorCode')),
            'status_value': number(reply.get('statusValue')),
            'state': status if status in LUNA_STATES else 'unknown',
            'return_value': reply.get('returnValue') if type(reply.get('returnValue')) is bool else None,
        }
        if 'reason' in details:
            reason = details['reason']
            self.luna['reason'] = reason if isinstance(reason, str) and reason in PACKAGE_FAILURE_REASONS else 'unknown'

        if (self.luna['operation'] == 'package-install' and self.luna.get('reason') in
                ('FAILED_NOT_ENOUGH_TEMP_SPACE', 'FAILED_NOT_ENOUGH_INSTALL_SPACE')):
            self.reason_code = 'tv-storage-full'
            self.args = (TV_STORAGE_FULL,)


class ExistingRoot(UserError):
    """A previous Root deployment needs an explicit reinstall decision."""


class TVCommandError(UserError):
    """A failed SSH command with a numeric status, never remote output."""
    def __init__(self, exit_status, *, storage_full=False):
        super().__init__(TV_STORAGE_FULL if storage_full else
                         'TV command failed. Save the diagnostic report and keep recovery data.',
                         reason_code='tv-storage-full' if storage_full else 'user-error')
        self.exit_status = exit_status if type(exit_status) is int and -1 <= exit_status <= 255 else None


class DeveloperKeyError(UserError):
    """A Key Server failure with a fixed reason code, never key material."""
    def __init__(self, message, reason_code):
        super().__init__(message)
        self.reason_code = reason_code if reason_code in (
            'key-server-unavailable', 'response-redirect', 'response-size',
            'response-format', 'key-unlock') else 'unknown'


class TVConnectionError(UserError):
    """An SSAP failure with allowlisted protocol metadata, never remote text."""
    def __init__(self, message, close_code=None, reason_code='connection-closed'):
        super().__init__(message)
        self.close_code = close_code if isinstance(close_code, int) and 1000 <= close_code <= 4999 else None
        self.reason_code = reason_code if reason_code in ('tv-not-ready', 'connection-closed', 'pairing-timeout') else 'connection-closed'


class TVNotReady(TVConnectionError):
    def __init__(self):
        super().__init__('TV is asleep or still starting. Turn it on with the remote and wait for the Home screen.',
                         close_code=1008, reason_code='tv-not-ready')


def root_recovery_details(value):
    """Bounded categories only: device diagnostics are untrusted input."""
    if not isinstance(value, dict) or type(value.get('schema', 1)) is not int or value.get('schema', 1) != 1:
        return {}
    enums = {
        'phase': ('manifest','stock-home','status','register','startup-hook','publish'),
        'reason': ('failed','negative-reply','invalid-reply','oversized-reply','oversized-client-output','client-exited','client-start-failed','timeout'),
        'luna_reason': ('permission-denied','service-missing','method-missing'),
        'startup_state': ('starting','exited','stale','unavailable'),
        'exception_name': ('Error','TypeError','SyntaxError','ReferenceError','RangeError'),
        'exception_code': ('MODULE_NOT_FOUND','ERR_DLOPEN_FAILED','EACCES','EPERM','ENOENT'),
    }
    if value.get('phase') not in enums['phase'] or value.get('reason') not in enums['reason']:
        return {}
    result = {key: value[key] for key, allowed in enums.items() if value.get(key) in allowed}
    for key, low, high in (('luna_error_code', -(2**31), 2**31-1),
                           ('client_exit_status', 0, 255), ('startup_exit_status', 0, 255)):
        number = value.get(key)
        if type(number) is int and low <= number <= high: result[key] = number
    return result


# Fixed runtime categories shared by the trusted launcher and report revalidation.
OBSERVER_EXCEPTION_NAMES = ('Error', 'TypeError', 'SyntaxError', 'ReferenceError', 'RangeError')
OBSERVER_EXCEPTION_CODES = ('MODULE_NOT_FOUND', 'ERR_DLOPEN_FAILED', 'EACCES', 'EPERM',
                            'ENOENT', 'ENOSPC', 'EDQUOT', 'EINVAL', 'ENOTSUP', 'EOPNOTSUPP',
                            'EEXIST', 'ENOTDIR', 'EISDIR', 'ELOOP', 'EROFS', 'EMFILE', 'ENFILE', 'EIO')
OBSERVER_FILESYSTEM_OPERATIONS = ('lstat', 'stat', 'open', 'read', 'write', 'mkdir', 'rmdir',
                                 'link', 'unlink', 'rename', 'scandir', 'readdir', 'fsync',
                                 'fchmod', 'fchown', 'fstat', 'close')
OBSERVER_STORAGE_AREAS = ('private-storage', 'public-staging', 'storage-parent')
OBSERVER_REASONS = (
    'changed-artifact', 'changed-directory', 'changed-file',
    'changed-plan-source', 'changed-public-stage', 'changed-reservation',
    'changed-source', 'changed-upload', 'changed-upload-directory',
    'claimed-artifact-missing', 'configuration-unverified', 'conflicting-terminal',
    'foreign-configuration-result', 'foreign-evidence', 'foreign-reservation',
    'foreign-slot', 'invalid-claim', 'invalid-closure',
    'invalid-configuration-claim', 'invalid-configuration-result', 'invalid-configuration-step',
    'invalid-configuration-upload', 'invalid-plan', 'invalid-readback',
    'invalid-seal', 'invalid-slot', 'invalid-terminal',
    'invalid-terminal-reply', 'invalid-upload', 'missing-public-stage',
    'nonprivate-directory', 'operation-closed', 'operation-not-closed',
    'predecessor-unverified', 'private-public-parent', 'short-read',
    'short-write', 'terminal-unverified', 'unexpected-reservation',
    'unresolved-slot', 'unsafe-config-file', 'unsafe-directory',
    'unsafe-file', 'unsafe-state-owner', 'unsafe-state-parent',
    'unsupported-command', 'unsupported-storage', 'upload-too-large',
    'writable-directory',
)


def no_root_observer_details(value):
    """Revalidate host observer context; never accept remote text or identifiers."""
    if type(value) is not dict:
        return {}
    allowed = {
        'command': ('storage-select', 'storage-check', 'prepare', 'status', 'attach', 'upload-artifact', 'upload-configuration',
                    'artifacts', 'config-claim', 'config-result', 'start', 'worker', 'seal',
                    'readback', 'configured', 'release', 'retire'),
        'failure': ('command-failed', 'connection-interrupted', 'timeout', 'transport-error',
                    'invalid-json', 'invalid-reply', 'foreign-operation', 'invalid-status', 'observer-error'),
    }
    if value.get('failure') == 'observer-error':
        allowed.update(exception_name=OBSERVER_EXCEPTION_NAMES, exception_code=OBSERVER_EXCEPTION_CODES,
                       observer_reason=OBSERVER_REASONS)
        # Optional for older error envelopes and retained diagnostic records.
        for key, choices in (('filesystem_operation', OBSERVER_FILESYSTEM_OPERATIONS),
                             ('storage_area', OBSERVER_STORAGE_AREAS)):
            if key in value:
                allowed[key] = choices
    return {key: value[key] if type(value.get(key)) is str and value[key] in choices else 'unknown'
            for key, choices in allowed.items()}
