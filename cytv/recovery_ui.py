"""Shared bounded recovery wording for desktop and Android; never authority."""

REMOVAL_STAGES = {
    'requested':'Removal has been requested.',
    'original-writers-fenced':'Previous setup work is stopped.',
    'controls-restored':'TV controls are restored.',
    'package-removal':'Removing Clean Your TV packages…',
    'private-cleanup':'Removing private setup data…',
    'restart-required':'Restart the TV to finish removal',
    # A saved terminal stage is historical until the adapter checks current state.
    'verified-clean':'Verifying removal…',
}
REMOVAL_BLOCKERS = {
    'removal-requested':'',
    'original-writer-active':'The TV is busy. Wait a moment and try again.',
    'ownership-conflict':'Some project paths changed. Close other installers and try again.',
    'controls-unverified':'TV controls could not be verified. Check the error details and try again.',
    'removal-terminal-unknown':'Removal could not be confirmed. Check the connection and try again.',
    'private-cleanup-incomplete':'Final cleanup could not be verified. Choose Try again to check and finish removal.',
    'restart-required':'Restart the TV completely: disconnect it from power, reconnect it, then choose Try again. Standby is not a full restart.',
    'connection-interrupted':'Connection to the TV was interrupted. Check the connection and try again.',
    'root-access-required':'Some project files require Root access. Reconnect using Root to finish removal.',
    'root-worker-busy':'Another Clean Your TV operation is still running. Wait for it to finish, then choose Try again.',
    'removal-failed':'The TV could not finish removing a package. Choose Try again.',
    'cleanup-check-failed':'Final cleanup could not be verified. Choose Try again to check and finish removal.',
    'removal-verified':'',
    'removal-recheck-required':'Connect to the TV to verify the saved removal result.',
}


def removal_restart_required(plan):
    """Recognize only fixed semantic restart signals, never presentation prose."""
    if type(plan) is not dict:
        return False
    removal = plan.get('removal') if type(plan.get('removal')) is dict else {}
    return (plan.get('restart_required') is True or plan.get('reason') == 'restart-required'
            or removal.get('stage') == 'restart-required' or removal.get('reason') == 'restart-required')


NETWORK_FAILURES = ('ssh-unreachable','ssh-protocol','ssh-access-denied','ssh-refused','ssh-timeout')
AUTH_FAILURES = ('ssh-auth-root','ssh-auth-no-root',
                       'ssh-key-file','ssh-identity','developer-key-server','developer-key-unlock','developer-key-response')
CONNECTION_FAILURES = NETWORK_FAILURES + AUTH_FAILURES


def root_removal_profile(store, source):
    """Choose connection details only; normal Root sign-in/trust still applies."""
    from .state import target
    saved = [profile for profile in store.profiles()
             if profile['host'] == source['host'] and profile['edition'] == 'root']
    return saved[0] if len(saved) == 1 else target(source['host'], 'root')


def removal_connection_failure(plan, failure=None):
    """Current connection guidance changes presentation, never restart authority."""
    if type(plan) is not dict or plan.get('disposition') != 'clean-removal':
        return False
    removal = plan.get('removal') if type(plan.get('removal')) is dict else {}
    return ((failure or {}).get('code') in CONNECTION_FAILURES or
            plan.get('reason') == 'connection-interrupted' or removal.get('reason') == 'connection-interrupted')


def _removal_reason(plan):
    removal = plan.get('removal') if type(plan.get('removal')) is dict else {}
    reason = plan.get('reason')
    if type(reason) is str and reason in REMOVAL_BLOCKERS:
        return reason
    reason = removal.get('reason')
    return reason if type(reason) is str and reason in REMOVAL_BLOCKERS else None


def removal_title(plan, failure=None):
    if removal_connection_failure(plan, failure):
        return 'Check the TV connection to continue removal'
    if removal_restart_required(plan):
        return 'Restart the TV to finish removal'
    reason = _removal_reason(plan)
    if reason in ('private-cleanup-incomplete', 'cleanup-check-failed'):
        return 'Finish Clean Your TV cleanup'
    removal = plan.get('removal') if type(plan.get('removal')) is dict else {}
    if reason == 'root-access-required' and removal.get('stage') == 'private-cleanup':
        return 'Cleanup is incomplete.'
    if reason == 'removal-failed':
        return 'The TV could not remove a package'
    return 'Removal is not finished yet.'


def removal_waiting(plan, failure=None):
    if type(plan) is not dict or plan.get('disposition') != 'clean-removal' or removal_connection_failure(plan, failure):
        return False
    return (removal_restart_required(plan) or _removal_reason(plan) in
            ('private-cleanup-incomplete', 'cleanup-check-failed', 'root-worker-busy', 'original-writer-active'))


def removal_details(plan, failure=None):
    if plan.get('disposition') != 'clean-removal':
        return {}
    value = plan.get('removal') if type(plan.get('removal')) is dict else {}
    stage = value.get('stage') if type(value.get('stage')) is str else None
    reason = value.get('reason') if type(value.get('reason')) is str else None
    if type(plan.get('reason')) is str and plan['reason'] in REMOVAL_BLOCKERS:
        reason = plan['reason']
    if removal_connection_failure(plan, failure):
        specific = (failure or {}).get('code') in (*AUTH_FAILURES, 'ssh-access-denied', 'ssh-refused')
        return {'stage_text':'Verifying removal…',
                'blocker_text':failure['next_step'] if specific and type(failure.get('next_step')) is str
                               else REMOVAL_BLOCKERS['connection-interrupted']}
    if removal_restart_required(plan):
        stage = reason = 'restart-required'
    elif reason in ('private-cleanup-incomplete', 'cleanup-check-failed'):
        stage = 'verified-clean'
    return {'stage_text':REMOVAL_STAGES.get(stage, 'Verifying removal…'),
            'blocker_text':REMOVAL_BLOCKERS.get(reason,
                'Removal could not be confirmed. Check the connection and try again.')}
