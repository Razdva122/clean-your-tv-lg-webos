"""Shared bounded recovery wording for desktop and Android; never authority."""

from .errors import ROOT_CLEANUP_ACCESS_REQUIRED, UserError
from .failure_help import AUTH_FAILURES, CONNECTION_FAILURES, transient_connection_failure
from .recovery_state import REMOVAL_FAILURE_PHASES

REMOVAL_STAGES = {
    'requested':'Removal has been requested.',
    'original-writers-fenced':'Previous setup work is stopped.',
    'controls-restored':'Checking the remaining removal steps…',
    'package-removal':'Removing Clean Your TV packages…',
    'private-cleanup':'Removing private setup data…',
    'restart-required':'Restart the TV to finish removal',
    # A saved terminal stage is historical until the adapter checks current state.
    'verified-clean':'Verifying removal…',
}
REMOVAL_BLOCKERS = {
    'removal-requested':'',
    'original-writer-active':'The TV is busy. Wait a moment and try again.',
    'ownership-conflict':'The current TV installer reservation could not be verified.',
    'controls-unverified':'TV controls could not be verified. Review recovery options before continuing.',
    'removal-terminal-unknown':'Review recovery options before trying to remove packages again.',
    'private-cleanup-incomplete':'Final cleanup could not be verified. Review recovery options before continuing.',
    'restart-required':'Restart the TV completely: disconnect it from power, reconnect it, then choose Try again. Standby is not a full restart.',
    'restart-unverified':'The TV restart could not be verified. Save the diagnostic report and keep recovery data.',
    'connection-interrupted':'Connection to the TV was interrupted. Check the connection and try again.',
    'connection-unverified':'Removal could not be verified. Review recovery options before continuing.',
    'root-access-required':ROOT_CLEANUP_ACCESS_REQUIRED,
    'root-worker-busy':'Another Clean Your TV operation is still running. Wait for it to finish, then choose Try again.',
    'removal-failed':'The TV package result could not be verified. Review recovery options before continuing.',
    'cleanup-check-failed':'Removal could not be verified. Review recovery options before continuing.',
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
    """Offer one saved Root connection and its own pin for explicit confirmation."""
    import hashlib
    import paramiko
    from .ssh_identity_review import read_record

    try:
        saved = [profile for profile in store.profiles()
                 if profile['host'] == source['host'] and profile['edition'] == 'root']
        if len(saved) != 1:
            return None
        profile = saved[0]
        known = store.device_path(profile) / 'known_hosts'
        host, port = profile['host'], profile['port']
        name = host if port == 22 else f'[{host}]:{port}'
        pin = hashlib.sha256(read_record(known)).hexdigest()
        if paramiko.HostKeys(str(known)).lookup(name):
            original, pinned = store.connection_profile(profile, expected_pin=pin)
            if pinned and original == profile:
                return original, pin
    except (OSError, UserError, ValueError, paramiko.SSHException, paramiko.hostkeys.InvalidHostKey):
        pass
    return None


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
    if reason == 'root-access-required' and not interrupted and not restart:
        return _removal_action_result('access')
    if (reason == 'original-writer-active' and plan.get('state') == 'waiting'
            and type(actions) is list and 'check' in actions and 'continue-removal' not in actions):
        return _removal_action_result('unverified')
    if reason in ('connection-interrupted', 'root-worker-busy', 'original-writer-active'):
        return _removal_action_result('transient')
    if restart and reason in (None, 'restart-required', 'removal-requested'):
        return _removal_action_result('restart')
    if reason == 'removal-requested' and _saved_failure_phase(plan) is None:
        return _removal_action_result('transient')
    return _removal_action_result('unverified')


def projected_removal_action(plan):
    """Preserve bounded current-failure advice when the plan crosses an adapter."""
    value = plan.get('removal_action')
    if type(value) is dict and type(value.get('requires_change')) is bool:
        condition = value.get('condition')
        if type(condition) is str and condition in _REMOVAL_ACTIONS:
            bounded = _removal_action_result(condition)
            if value == bounded and (condition not in ('access', 'complete') or bounded == removal_action(plan)):
                return bounded
    return removal_action(plan)


def command_outcome(plan):
    """Project machine advice from the same evidence as the recovery actions."""
    state = plan.get('state')
    reason = plan.get('reason')
    if plan.get('disposition') == 'clean-removal':
        condition = projected_removal_action(plan)['condition']
        if condition == 'complete':
            return 'verified-completion', 'none'
        if condition == 'restart':
            return 'owner-input-required', 'restart-tv'
        if condition == 'access':
            return 'owner-input-required', 'connect-root'
        if condition == 'transient' and reason != 'removal-requested':
            return 'retryable-check', 'check'
    if reason in ('removal-failed', 'original-vendor-failure'):
        return 'failed', 'check'
    if state == 'terminal-verified':
        return 'verified-completion', 'none'
    if state in ('ready', 'setup-ready', 'product-ready', 'cancellation-ready'):
        return 'owner-input-required', 'review-recovery'
    if state == 'pre-submission':
        return 'retryable-check', 'check'
    if state in ('waiting', 'blocked', 'cleanup-in-progress', 'review'):
        return 'waiting-for-evidence', 'check'
    return None


def _presentation_condition(plan, failure):
    if failure is None:
        return projected_removal_action(plan)['condition']
    return removal_action(plan, failure)['condition']


def _saved_failure_phase(plan):
    removal = plan.get('removal')
    phase = removal.get('failure_phase') if type(removal) is dict else None
    reason = _removal_reason(plan)
    if reason in (None, 'removal-requested', 'cleanup-check-failed', 'removal-failed', *REMOVAL_FAILURE_PHASES.values()):
        return phase if phase in REMOVAL_FAILURE_PHASES.values() else None
    return None


def _presentation_reason(plan, failure):
    if failure is None:
        reason = _saved_failure_phase(plan) or _removal_reason(plan)
        removal = plan.get('removal')
        if (reason == 'cleanup-check-failed' and type(removal) is dict
                and removal.get('stage') == 'private-cleanup'):
            reason = 'private-cleanup-incomplete'
    else:
        reason = failure.get('code') if type(failure) is dict else None
    return reason if type(reason) is str and reason != 'restart-required' and reason in REMOVAL_BLOCKERS else None


def _saved_removal_presentation(plan, failure):
    if failure is not None or type(plan) is not dict or plan.get('disposition') != 'clean-removal':
        return {}
    value = plan.get('removal_presentation')
    return value if type(value) is dict else {}


def _removal_evidence(plan):
    value = plan.get('removal_evidence')
    return value if type(value) is dict else {}


def observed_stock_surface(evidence):
    if type(evidence) is not dict or evidence.get('stock') != 'stock-observed':
        return None
    surface = evidence.get('stock_surface')
    if surface == 'com.webos.app.home':
        return 'Observed LG Home. Physical remote untested.'
    if surface == 'com.webos.app.livetv':
        return 'Observed Live TV. Physical remote untested.'
    if surface in ('com.webos.app.hdmi1', 'com.webos.app.hdmi2', 'com.webos.app.hdmi3', 'com.webos.app.hdmi4'):
        return 'Observed HDMI {input}. Physical remote untested.'.format(input=surface[-1])
    return None


def removal_milestones(plan, failure=None):
    """Describe readback separately from terminal removal and physical input."""
    if plan.get('disposition') != 'clean-removal' and not plan.get('continue_removal'):
        return ()
    evidence = _removal_evidence(plan)
    complete = removal_action(plan, failure)['condition'] == 'complete'
    stock = evidence.get('stock')
    stock_text = observed_stock_surface(evidence) or {
        'routing-verified':'Home routing was verified. Physical remote untested.',
        'stock-observed':'A stock TV screen was observed. Physical remote untested.',
        'launch-accepted':'The TV accepted a stock app launch. Physical remote untested.',
    }.get(stock if type(stock) is str else None, 'Stock controls are unknown.')
    packages = evidence.get('packages')
    if complete or packages == 'absent':
        package_text = 'Clean Your TV packages are absent.'
    elif packages == 'helper-present':
        package_text = 'Home Helper is still installed.'
    elif packages == 'present':
        package_text = 'Clean Your TV packages are still installed.'
    else:
        package_text = 'Package absence is unknown.'
    cleanup_text = ('Final cleanup is verified.' if complete else
                    'Final cleanup remains to be verified.' if evidence.get('cleanup') == 'pending' else
                    'Final cleanup is unknown.')
    return stock_text, package_text, cleanup_text


def removal_title(plan, failure=None):
    saved = _saved_removal_presentation(plan, failure)
    if type(saved.get('title_text')) is str:
        return saved['title_text']
    if removal_connection_failure(plan, failure):
        return 'Check the TV connection to continue removal'
    condition = _presentation_condition(plan, failure)
    if condition == 'restart':
        return 'Restart the TV to finish removal'
    evidence = _removal_evidence(plan)
    if (evidence.get('stock') in ('routing-verified', 'stock-observed')
            and evidence.get('packages') in ('helper-present', 'present')):
        return 'Removal is partly complete.'
    reason = _presentation_reason(plan, failure)
    if reason == 'controls-unverified':
        return 'TV controls could not be verified.'
    if reason == 'removal-terminal-unknown':
        return 'The TV package result could not be verified.'
    if reason == 'private-cleanup-incomplete':
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
            ('private-cleanup-incomplete', 'root-worker-busy', 'original-writer-active'))


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
    elif reason in ('controls-unverified', 'removal-terminal-unknown', 'removal-failed',
                    'private-cleanup-incomplete', 'cleanup-check-failed'):
        stage = None
    elif stage == 'restart-required':
        stage = None
    return {'stage_text':REMOVAL_STAGES.get(stage, 'Verifying removal…'),
            'blocker_text':REMOVAL_BLOCKERS.get(reason,
                'Removal could not be verified. Review recovery options before continuing.')}
