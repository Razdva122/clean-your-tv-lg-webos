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
    'private-cleanup-incomplete':'Some project files remain. Try again to finish removal.',
    'restart-required':'Restart the TV completely: disconnect it from power, reconnect it, then choose Try again. Standby is not a full restart.',
    'connection-interrupted':'Connection to the TV was interrupted. Check the connection and try again.',
    'root-access-required':'Some project files require Root access. Reconnect using Root to finish removal.',
    'root-worker-busy':'Another Clean Your TV operation is still running. Wait for it to finish, then choose Try again.',
    'removal-failed':'The TV could not finish removing a package. Choose Try again.',
    'cleanup-check-failed':'Some Clean Your TV files or settings remain. Choose Try again.',
    'removal-verified':'',
}


def removal_details(plan, failure=None):
    if plan.get('disposition') != 'clean-removal':
        return {}
    value = plan.get('removal') if type(plan.get('removal')) is dict else {}
    stage = value.get('stage') if type(value.get('stage')) is str else None
    reason = value.get('reason') if type(value.get('reason')) is str else None
    if type(plan.get('reason')) is str and plan['reason'] in REMOVAL_BLOCKERS:
        reason = plan['reason']
    if (failure or {}).get('code') in ('ssh-unreachable','ssh-protocol'):
        reason = 'connection-interrupted'
    if plan.get('restart_required') is True or stage == 'restart-required':
        stage = reason = 'restart-required'
    return {'stage_text':REMOVAL_STAGES.get(stage, 'Verifying removal…'),
            'blocker_text':REMOVAL_BLOCKERS.get(reason,
                'Removal could not be confirmed. Check the connection and try again.')}
