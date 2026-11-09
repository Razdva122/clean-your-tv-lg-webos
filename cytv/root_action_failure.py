"""Fixed advice from fresh activation observations, never recovery authority."""
from .errors import TVCommandError


ACTIVATION_DETAILS = {
    'transaction-mismatch': 'The Home input monitor belongs to a different startup attempt.',
    'binding-restored': 'Home routing for this startup attempt has already been restored.',
    'generation-mismatch': 'Home control changed after this startup attempt began.',
    'token-mismatch': 'The Home input monitor no longer matches the saved startup attempt.',
    'boot-mismatch': 'The TV restarted after this startup attempt was created.',
    'phase-inactive': 'Home control is no longer active for this startup attempt.',
    'failsafe-present': 'The TV safety stop is active, so Home control was refused.',
}
ACTIVATION_CODES = tuple('root-activation-' + reason for reason in ACTIVATION_DETAILS)


def apply_activation_reason(error, tv_info):
    """Enrich the same command error; history and connection/storage errors win."""
    if not isinstance(error, TVCommandError) or error.reason_code != 'user-error':
        return
    if not isinstance(tv_info, dict):
        return
    snapshot = tv_info.get('root_diagnostics')
    log = snapshot.get('health_log') if isinstance(snapshot, dict) else None
    if not isinstance(log, dict) or log.get('status') != 'read' or log.get('scope') != 'since-enable':
        return
    reason = log.get('health_refusal')
    if isinstance(reason, str) and reason in ACTIVATION_DETAILS:
        error.reason_code = 'root-activation-' + reason
