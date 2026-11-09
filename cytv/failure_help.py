"""Fixed, phase-bound advice. It never connects, retries, repairs or grants trust."""
import errno
import socket

from .errors import DeveloperKeyError, TVConnectionError, TVRejected, is_storage_full, TV_STORAGE_FULL, COMPUTER_STORAGE_FULL
from .recovery_state import unsubmitted_removal
from .root_action_failure import ACTIVATION_CODES, ACTIVATION_DETAILS

NETWORK = 'Keep the TV on and use the same home network. Review the selected TV address and SSH port, Local Network access and VPN isolation.'
DEVELOPER = 'Leave Developer Mode open with Key Server on. Use the current TV passphrase exactly; do not turn Developer Mode off or delete the saved profile.'
REPORT = 'Save the diagnostic report and keep the saved connection and recovery data. Do not reset the TV or repeat setup to force progress.'
GUIDES = {
    'tv-storage-full': ('Not enough space on the TV', TV_STORAGE_FULL, REPORT, False),
    'computer-storage-full': ('Not enough space on this computer', COMPUTER_STORAGE_FULL, REPORT, False),
    'ssh-access-denied': ('Network access was denied', 'This computer blocked the connection before SSH sign-in.',
        "Review this app's network permissions and firewall or VPN rules, then check the connection again.", True),
    'ssh-refused': ('The TV refused the connection', 'The selected SSH port is not accepting connections.',
        'Check the TV address, edition and SSH port. Root requires existing root SSH; No-root normally uses Developer Mode on port 9922.', True),
    'ssh-timeout': ('The TV did not respond', 'The connection timed out before SSH sign-in.', NETWORK, True),
    'ssh-unreachable': ('Check the TV connection', 'The selected SSH connection could not be reached or timed out.', NETWORK, True),
    'ssh-auth-root': ('SSH sign-in was not confirmed', 'Root sign-in needs your existing trusted SSH access.',
        'Use the existing root SSH password or supported private key. Its key passphrase unlocks the file; it is not the TV password.', True),
    'ssh-auth-no-root': ('SSH sign-in was not confirmed', 'Developer Mode SSH sign-in could not be verified.', DEVELOPER, True),
    'ssh-identity': ('Verify the TV identity before continuing', 'The SSH identity or saved trust record did not pass verification.',
        'Check the change through your existing trusted SSH setup. Do not delete trust records, accept a replacement blindly or disable host verification.', False),
    'ssh-key-file': ('Check the local SSH key', 'The local SSH key or connection data could not be read.',
        'Check the selected key file, its permissions and its passphrase through your existing trusted SSH setup. Keep the saved profile.', True),
    'ssh-protocol': ('SSH negotiation was not confirmed', 'The SSH connection or saved key could not be verified.',
        'Review the selected edition and SSH port against your existing trusted access. Do not weaken SSH security or disable host verification.', True),
    'developer-key-server': ('Check Developer Mode Key Server', 'The TV key could not be obtained from Key Server.', DEVELOPER, True),
    'developer-key-response': ('Check Developer Mode Key Server', 'Key Server returned an unexpected response; it was not accepted.', DEVELOPER, True),
    'developer-key-unlock': ('The TV key could not be unlocked', 'The passphrase or key format could not be verified.', DEVELOPER, True),
    'tv-pairing': ('TV pairing was not confirmed', 'The TV control connection or its pairing response was not confirmed.',
        'Keep the TV awake and review its CYTV pairing request with the remote. Do not reset pairing or reinstall packages to solve a connection check.', True),
    'root-requirements': ('Root prerequisites are not ready', 'SSH access alone does not establish the required TV runtime or Home interfaces.', REPORT, False),
    'installer-runtime-mismatch': ('Root needs the runtime in this installer',
        'The installed Root runtime differs from the verified package in this installer. Home activation has not started.',
        'Choose Set up my TV and confirm Reinstall Root. The installer verifies removal before installing its current packages and runtime.', False),
    'root-home-interfaces': ('Required Root Home interfaces are not verified', 'Root setup requires readable Home settings and Home profiles. The check could not establish that contract.', REPORT, False),
    'recovery-status-rejected': ('TV refused the package status check',
        'Recovery cannot verify the earlier package operation on this TV.', REPORT, False),
    'removal-not-submitted': ('Removal stopped before package deletion',
        'No package removal request was submitted.',
        'Choose Review recovery options for the same saved TV connection. Removal requires a separate confirmation; setup starts separately.', False),
    'pending-operation': ('An earlier operation is unresolved', 'This failure does not prove that the earlier package operation finished.',
        'Save the report and keep the original saved connection and recovery data. Use only verified recovery; do not blindly retry setup, Restore or removal.', False),
    'no-root-recovery': ('Review the original No-root operation',
        'Package outcomes and remaining setup are checked from the original saved evidence.',
        'Choose Review recovery options for the same saved TV connection. Unknown package or setup requests are not repeated.',False),
}


GUIDES.update({
    'root-activation-' + reason: ('Root Home startup stopped', detail,
        'Keep the saved connection and recovery data. Review recovery options in this installer; use its verified removal flow before starting a new installation.', False)
    for reason, detail in ACTIVATION_DETAILS.items()
})


NETWORK_CAUSES = {
    'access-denied': 'ssh-access-denied', 'refused': 'ssh-refused', 'timeout': 'ssh-timeout',
    'host-unreachable': 'ssh-unreachable', 'network-unreachable': 'ssh-unreachable',
    'name-resolution': 'ssh-unreachable', 'unknown': 'ssh-unreachable',
}


def network_failure_causes(error):
    """A bounded set of typed causes, never address keys or exception prose."""
    errors = getattr(error, 'errors', None)
    causes = errors.values() if isinstance(errors, dict) and errors else (error,)
    result = set()
    for cause in causes:
        number = getattr(cause, 'errno', None)
        result.add('name-resolution' if isinstance(cause, socket.gaierror) else
                   'access-denied' if number in (errno.EACCES, errno.EPERM) else
                   'refused' if number == errno.ECONNREFUSED else
                   'timeout' if isinstance(cause, TimeoutError) or number == errno.ETIMEDOUT else
                   'host-unreachable' if number == errno.EHOSTUNREACH else
                   'network-unreachable' if number == errno.ENETUNREACH else 'unknown')
    return sorted(result)


def network_failure_code(error):
    """Mixed causes do not prove a single diagnosis."""
    codes = {NETWORK_CAUSES[cause] for cause in network_failure_causes(error)}
    return codes.pop() if len(codes) == 1 else 'ssh-unreachable'


def for_error(error, phase, profile=None, pending=None):
    if error is None:
        return None
    profile = profile if isinstance(profile,dict) else {}
    edition = profile.get('edition')
    root_ssh = edition == 'root' or profile.get('connection') == 'root-ssh'
    names = {cls.__name__ for cls in type(error).__mro__}
    reason = getattr(error, 'reason_code', None)
    code = None
    if reason == 'installer-runtime-mismatch' and edition == 'root':
        code = reason
    elif reason == 'tv-storage-full':
        code = 'tv-storage-full'
    elif reason == 'computer-storage-full' or is_storage_full(error):
        code = 'computer-storage-full'
    elif (pending and edition == 'no-root' and phase in ('recover', 'uninstall')
            and isinstance(error, TVRejected) and error.luna.get('operation') == 'package-status'):
        code = 'recovery-status-rejected'
    elif reason in ('root-home-interfaces','root-requirements') and edition=='root':
        code = reason
    elif reason in ('ssh-trust-record', 'ssh-identity-unverified') or 'BadHostKeyException' in names:
        code = 'ssh-identity'
    elif isinstance(error, DeveloperKeyError):
        if edition!='no-root' or reason=='unknown':
            return None
        code = ('developer-key-server' if reason=='key-server-unavailable' else
                'developer-key-unlock' if reason=='key-unlock' else 'developer-key-response')
    elif isinstance(error, TVConnectionError) and phase in ('pair-tv','read-inventory'):
        code = 'tv-pairing'
    elif phase == 'ssh-connect':
        if 'AuthenticationException' in names:
            code = 'ssh-auth-root' if root_ssh else 'ssh-auth-no-root'
        elif (isinstance(error,PermissionError) and getattr(error,'filename',None)
              or root_ssh and isinstance(error,(FileNotFoundError,ValueError))):
            code = 'ssh-key-file'
        elif 'SSHException' in names:
            code = 'ssh-protocol'
        elif isinstance(error,(OSError,TimeoutError)) or 'NoValidConnectionsError' in names:
            code = network_failure_code(error)
    if code is None and edition == 'root' and phase in ('activate-root', 'recover') and reason in ACTIVATION_CODES:
        code = reason
    if code is None and isinstance(pending, dict) and pending.get('recovery_protocol') == 'clean-removal-v1':
        return None  # The existing removal plan already explains the safe retry.
    if code is None and pending:
        code = ('no-root-recovery' if edition=='no-root' and pending.get('recovery_protocol')=='no-root-original-stream-v1'
                else 'removal-not-submitted' if phase == 'uninstall' and unsubmitted_removal(profile, pending)
                else 'pending-operation')
    if code is None:
        return None
    title, detail, next_step, edit = GUIDES[code]
    if pending and code.startswith(('ssh-', 'developer-key-')):
        if code in ('ssh-unreachable', 'ssh-timeout', 'ssh-protocol'):
            next_step = 'Keep the TV awake on the same home network. Check network access and VPN isolation using the original trusted connection.'
        next_step += ' Keep the original saved TV connection and recovery data; do not replace or edit the connection to bypass recovery.'
    return {'code':code, 'title':title, 'detail':detail, 'next_step':next_step,
            'pending':bool(pending), 'can_edit_connection':edit and not bool(pending)}


def report_summary(value):
    value = value if type(value) is dict else {}
    code = value.get('code')
    return {'code':code if type(code) is str and code in GUIDES else 'unknown',
            'pending':value.get('pending') is True}
