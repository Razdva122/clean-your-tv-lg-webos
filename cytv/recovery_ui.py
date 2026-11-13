"""Shared bounded recovery wording for desktop and Android; never authority."""

from .failure_help import AUTH_FAILURES, CONNECTION_FAILURES, transient_connection_failure

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
    'ownership-conflict':'Some project paths changed. Close other installers, then review recovery options.',
    'controls-unverified':'TV controls could not be verified. Review recovery options before continuing.',
    'removal-terminal-unknown':'The TV package result could not be verified. Review recovery options before continuing.',
    'private-cleanup-incomplete':'Final cleanup could not be verified. Review recovery options before continuing.',
    'restart-required':'Restart the TV completely: disconnect it from power, reconnect it, then choose Try again. Standby is not a full restart.',
    'connection-interrupted':'Connection to the TV was interrupted. Check the connection and try again.',
    'connection-unverified':'Removal could not be verified. Review recovery options before continuing.',
    'root-access-required':'Some project files require Root access. Reconnect using Root to finish removal.',
    'root-worker-busy':'Another Clean Your TV operation is still running. Wait for it to finish, then choose Try again.',
    'removal-failed':'The TV package result could not be verified. Review recovery options before continuing.',
    'cleanup-check-failed':'Final cleanup could not be verified. Review recovery options before continuing.',
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


_REMOVAL_ACTIONS = {
    'transient': ('retry-removal', False),
    'unverified': ('check', True),
    'access': ('connect-root', True),
    'restart': ('retry-removal', True),
    'complete': ('none', False),
}


def root_removal_profile(store, source):
    """Choose connection details only; normal Root sign-in/trust still applies."""
    from .state import target
    if source['edition'] == 'root':
        return dict(source)
    saved = [profile for profile in store.profiles()
             if profile['host'] == source['host'] and profile['edition'] == 'root']
    return saved[0] if len(saved) == 1 else target(source['host'], 'root')


def removal_connection_failure(plan, failure=None):
    """Current connection guidance changes presentation, never restart authority."""
    if type(plan) is not dict or plan.get('disposition') != 'clean-removal':
        return False
    code = failure.get('code') if type(failure) is dict else None
    if failure is not None:
        return code in CONNECTION_FAILURES or code == 'connection-interrupted'
    if type(plan.get('connection_failure')) is bool:
        return plan['connection_failure']
    return _removal_reason(plan) in ('connection-interrupted', 'connection-unverified')


def _removal_reason(plan):
    removal = plan.get('removal') if type(plan.get('removal')) is dict else {}
    reason = plan.get('reason')
    if type(reason) is str and reason in REMOVAL_BLOCKERS:
        return reason
    reason = removal.get('reason')
    return reason if type(reason) is str and reason in REMOVAL_BLOCKERS else None


def _removal_action_result(condition):
    action, requires_change = _REMOVAL_ACTIONS[condition]
    return {'action':action, 'condition':condition, 'requires_change':requires_change}


def removal_action(plan, failure=None):
    """Classify fixed evidence for the next user action, without granting effects."""
    if type(plan) is not dict or plan.get('disposition') != 'clean-removal':
        return _removal_action_result('unverified')
    code = failure.get('code') if type(failure) is dict else None
    if failure is not None:
        if transient_connection_failure(failure) or code in ('root-worker-busy', 'original-writer-active'):
            return _removal_action_result('transient')
        if code == 'root-access-required':
            return _removal_action_result('access')
        if code == 'restart-required':
            return _removal_action_result('restart')
        return _removal_action_result('unverified')

    restart = removal_restart_required(plan)
    interrupted = removal_connection_failure(plan)
    if (plan.get('state') == 'complete' and plan.get('removed') is True
            and plan.get('verified_clean') is True and not restart and not interrupted):
        return _removal_action_result('complete')
    reason = _removal_reason(plan)
    actions = plan.get('actions')
    if reason == 'root-access-required' or (type(actions) is list and 'connect-root' in actions):
        return _removal_action_result('access')
    if reason in ('connection-interrupted', 'root-worker-busy', 'original-writer-active'):
        return _removal_action_result('transient')
    if restart and reason in (None, 'restart-required', 'removal-requested'):
        return _removal_action_result('restart')
    if reason == 'removal-requested':
        return _removal_action_result('transient')
    return _removal_action_result('unverified')


def projected_removal_action(plan):
    """Preserve bounded current-failure advice when the plan crosses an adapter."""
    value = plan.get('removal_action')
    if type(value) is dict and type(value.get('requires_change')) is bool:
        condition = value.get('condition')
        if type(condition) is str and condition in _REMOVAL_ACTIONS:
            bounded = _removal_action_result(condition)
            if value == bounded and (condition != 'complete' or bounded == removal_action(plan)):
                return bounded
    return removal_action(plan)


def _presentation_condition(plan, failure):
    if failure is None:
        return projected_removal_action(plan)['condition']
    return removal_action(plan, failure)['condition']


def _presentation_reason(plan, failure):
    if failure is None:
        reason = _removal_reason(plan)
    else:
        reason = failure.get('code') if type(failure) is dict else None
    return reason if type(reason) is str and reason != 'restart-required' and reason in REMOVAL_BLOCKERS else None


def _saved_removal_presentation(plan, failure):
    if failure is not None or type(plan) is not dict or plan.get('disposition') != 'clean-removal':
        return {}
    value = plan.get('removal_presentation')
    return value if type(value) is dict else {}


def removal_title(plan, failure=None):
    saved = _saved_removal_presentation(plan, failure)
    if type(saved.get('title_text')) is str:
        return saved['title_text']
    if removal_connection_failure(plan, failure):
        return 'Check the TV connection to continue removal'
    condition = _presentation_condition(plan, failure)
    if condition == 'restart':
        return 'Restart the TV to finish removal'
    reason = _presentation_reason(plan, failure)
    if reason in ('private-cleanup-incomplete', 'cleanup-check-failed'):
        return 'Finish Clean Your TV cleanup'
    removal = plan.get('removal') if type(plan.get('removal')) is dict else {}
    if condition == 'access' and removal.get('stage') == 'private-cleanup':
        return 'Cleanup is incomplete.'
    if reason == 'removal-failed':
        return 'The TV could not remove a package'
    return 'Removal is not finished yet.'


def removal_waiting(plan, failure=None):
    if type(plan) is not dict or plan.get('disposition') != 'clean-removal' or removal_connection_failure(plan, failure):
        return False
    saved = _saved_removal_presentation(plan, failure)
    if type(saved.get('waiting')) is bool:
        return saved['waiting']
    return (_presentation_condition(plan, failure) == 'restart' or _presentation_reason(plan, failure) in
            ('private-cleanup-incomplete', 'cleanup-check-failed', 'root-worker-busy', 'original-writer-active'))


def removal_details(plan, failure=None):
    if plan.get('disposition') != 'clean-removal':
        return {}
    saved = _saved_removal_presentation(plan, failure)
    if type(saved.get('stage_text')) is str and type(saved.get('blocker_text')) is str:
        return {key:saved[key] for key in ('stage_text', 'blocker_text')}
    value = plan.get('removal') if type(plan.get('removal')) is dict else {}
    stage = value.get('stage') if type(value.get('stage')) is str else None
    reason = _presentation_reason(plan, failure)
    if removal_connection_failure(plan, failure):
        if failure is None and reason == 'connection-unverified':
            return {'stage_text':'Verifying removal…','blocker_text':REMOVAL_BLOCKERS[reason]}
        unverified = _presentation_condition(plan, failure) == 'unverified'
        failure = failure if type(failure) is dict else {}
        specific = unverified or failure.get('code') in (*AUTH_FAILURES, 'ssh-access-denied', 'ssh-refused')
        fallback = ('Removal could not be verified. Review recovery options before continuing.' if unverified
                    else REMOVAL_BLOCKERS['connection-interrupted'])
        return {'stage_text':'Verifying removal…',
                'blocker_text':failure['next_step'] if specific and type(failure.get('next_step')) is str
                               else fallback}
    condition = _presentation_condition(plan, failure)
    if condition == 'restart':
        stage = reason = 'restart-required'
    elif condition == 'access':
        reason = 'root-access-required'
        if stage == 'restart-required':
            stage = 'private-cleanup'
    elif reason in ('private-cleanup-incomplete', 'cleanup-check-failed'):
        stage = 'verified-clean'
    elif stage == 'restart-required':
        stage = None
    return {'stage_text':REMOVAL_STAGES.get(stage, 'Verifying removal…'),
            'blocker_text':REMOVAL_BLOCKERS.get(reason,
                'Removal could not be verified. Review recovery options before continuing.')}
