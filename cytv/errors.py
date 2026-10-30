import re


class UserError(RuntimeError):
    """An installer-owned message which contains no remote data or credentials."""


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
            if self.wam_session_kib:
                message += '\nWAM Session Storage uses {size} MiB and may contribute to low space. Review the recovery guide before clearing app state.'.format(
                    size=format(self.wam_session_kib / 1024, '.1f').removesuffix('.0'))
            message += '\nYou can cancel and free space yourself. Use the manual cleanup guide and recheck /var/lib; removing apps may free a different partition.'
            message += '\nClose TV apps first. This deletes app session state and may sign you out or lose unsaved work.'
            message += '\nhttps://github.com/Razdva122/clean-your-tv-lg-webos/blob/release/next/docs/WAM-CLEANUP.md'
        else:
            message = messages.get(self.reason, messages['unknown'])
        super().__init__(message)


class TVRejected(UserError):
    """A definite negative TV reply, distinct from an unknown connection outcome."""
    def __init__(self, message, reply=None, uri=None):
        super().__init__(message)
        reply = reply if isinstance(reply, dict) else {}
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
            'state': status if status in ('installing','installed','removing','removed','success','failed','error') else 'unknown',
            'return_value': reply.get('returnValue') if type(reply.get('returnValue')) is bool else None,
        }


class ExistingRoot(UserError):
    """A previous Root deployment needs an explicit reinstall decision."""


class TVCommandError(UserError):
    """A failed SSH command with a numeric status, never remote output."""
    def __init__(self, exit_status):
        super().__init__('TV command failed. Run cytv doctor; retain the operation journal.')
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
