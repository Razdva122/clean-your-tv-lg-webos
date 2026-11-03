"""Fixed, phase-bound advice. It never connects, retries, repairs or grants trust."""
from .errors import DeveloperKeyError, TVConnectionError, TVRejected
from .recovery_state import unsubmitted_removal

NETWORK = 'Keep the TV on and use the same home network. Review the selected TV address and SSH port, Local Network access and VPN isolation.'
DEVELOPER = 'Leave Developer Mode open with Key Server on. Use the current TV passphrase exactly; do not turn Developer Mode off or delete the saved profile.'
REPORT = 'Save the diagnostic report and keep the saved connection and recovery data. Do not reset the TV or repeat setup to force progress.'
GUIDES = {
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
    'root-home-interfaces': ('Required Root Home interfaces are not verified', 'Root setup requires readable Home settings and Home profiles. The check could not establish that contract.', REPORT, False),
    'recovery-status-rejected': ('TV refused the package status check',
        'Recovery cannot verify the earlier package operation on this TV.', REPORT, False),
    'removal-not-submitted': ('Removal stopped before package deletion',
        'No package removal request was submitted.',
        'Choose Review recovery options for the same saved TV connection. Removal requires a separate confirmation; setup starts separately.', False),
    'pending-operation': ('An earlier operation is unresolved', 'This failure does not prove that the earlier package operation finished.',
        'Save the report and keep the original saved connection and recovery data. Use only verified recovery; do not blindly retry setup, Restore or removal.', False),
}


def for_error(error, phase, profile=None, pending=None):
    if error is None:
        return None
    profile = profile if isinstance(profile,dict) else {}
    edition = profile.get('edition')
    names = {cls.__name__ for cls in type(error).__mro__}
    reason = getattr(error, 'reason_code', None)
    code = None
    if (pending and edition == 'no-root' and phase in ('recover', 'uninstall')
            and isinstance(error, TVRejected) and error.luna.get('operation') == 'package-status'):
        code = 'recovery-status-rejected'
    elif pending and phase == 'uninstall' and unsubmitted_removal(profile, pending):
        code = 'removal-not-submitted'
    elif pending:
        code = 'pending-operation'
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
            code = 'ssh-auth-root' if edition=='root' else 'ssh-auth-no-root'
        elif edition=='root' and (isinstance(error,(FileNotFoundError,ValueError)) or
                                  (isinstance(error,PermissionError) and getattr(error,'filename',None))):
            code = 'ssh-key-file'
        elif 'SSHException' in names:
            code = 'ssh-protocol'
        elif isinstance(error,(OSError,TimeoutError)) or 'NoValidConnectionsError' in names:
            code = 'ssh-unreachable'
    if code is None:
        return None
    title, detail, next_step, edit = GUIDES[code]
    return {'code':code, 'title':title, 'detail':detail, 'next_step':next_step,
            'pending':bool(pending), 'can_edit_connection':edit and not bool(pending)}


def report_summary(value):
    value = value if type(value) is dict else {}
    code = value.get('code')
    return {'code':code if type(code) is str and code in GUIDES else 'unknown',
            'pending':value.get('pending') is True}
