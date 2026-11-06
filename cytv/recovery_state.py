"""Local journal classification. Exported summaries are advice, never authority."""

STATES = ('idle', 'pre-submission', 'waiting', 'setup-ready', 'terminal-verified', 'blocked')
REASONS = ('no-pending-operation', 'removal-not-submitted', 'terminal-evidence-missing',
           'inherited-operation', 'unsupported-receipt', 'foreign-operation', 'operation-live',
           'packages-verified', 'observation-unverified', 'removal-verified', 'activation-verified')
ACTIONS = ('check', 'continue-setup', 'finish-home-off', 'reconcile', 'retain-evidence')


def assessment_summary(value):
    """Validate persisted/exported advice; this is not an admission credential."""
    value = value if type(value) is dict else {}
    return {'state': value.get('state') if value.get('state') in STATES else 'blocked',
            'reason': value.get('reason') if value.get('reason') in REASONS else 'observation-unverified',
            'actions': [item for item in value.get('actions', []) if type(item) is str and item in ACTIONS]
                       if type(value.get('actions')) is list else ['retain-evidence']}


def assess(profile, pending, observation=None):
    """Pure advice from a full receipt and raw observation, never mutation authority.

    Backend proof methods must re-read evidence after confirmation. Diagnostic
    projections intentionally omit the raw device/operation binding this reads.
    New operation protocols may add branches here; unknown protocols stay blocked.
    """
    profile = profile if type(profile) is dict else {}
    observation = observation if type(observation) is dict else {}
    device = observation.get('device')
    device = device if type(device) is dict else {}
    product = device.get('product')
    product = product if type(product) is dict else {}
    def result(state, reason, *actions):
        return {'state': state, 'reason': reason, 'actions': list(actions)}
    if observation.get('active_operation') is not None:
        return result('blocked', 'foreign-operation', 'check', 'retain-evidence')
    if pending is None:
        return result('idle', 'no-pending-operation')
    if type(pending) is not dict or pending.get('action') not in (
            'install', 'uninstall', 'activate-root', 'setup-root-updater', 'enable-system-updates', 'archive-root-state'):
        return result('blocked', 'unsupported-receipt', 'retain-evidence')
    if 'previous' in pending:
        return result('blocked', 'inherited-operation', 'retain-evidence')
    if pending.get('product_operation') and product:
        if product.get('operation') != pending['product_operation']:
            return result('blocked', 'foreign-operation', 'check', 'retain-evidence')
        if product.get('state') == 'pending':
            return result('waiting', 'operation-live', 'check', 'retain-evidence')
    if profile.get('edition') == 'root' and device:
        if observation.get('reconciliation') in ('product-removal-verified', 'root-activation-verified'):
            reason = 'removal-verified' if pending['action'] == 'uninstall' else 'activation-verified'
            return result('terminal-verified', reason, 'reconcile', 'retain-evidence')
        if observation.get('can_resume_root_setup') is True:
            actions = ['continue-setup']
            if pending['action'] == 'activate-root' and pending.get('home_backend') != 'c1-native-gate':
                actions.append('finish-home-off')
            return result('setup-ready', 'packages-verified', *actions, 'retain-evidence')
    if unsubmitted_removal(profile, pending):
        return result('pre-submission', 'removal-not-submitted', 'check', 'retain-evidence')
    return result('blocked', 'terminal-evidence-missing' if profile.get('edition') == 'no-root'
                  else 'observation-unverified', 'check', 'retain-evidence')


def unsubmitted_removal(profile, pending):
    return (profile.get('edition') == 'no-root' and isinstance(pending, dict)
            and pending.get('action') == 'uninstall' and pending.get('stage') == 'pending'
            and set(pending) <= {'action', 'stage', 'diagnostic_id', 'eim_registered', 'removals'}
            and pending.get('removals', {}) == {})


def summary(profile, pending):
    category = 'unknown-journal'
    removals = pending.get('removals', {}) if isinstance(pending, dict) else {}
    known = {'com.gathin.tvhome': 'home', 'com.local.nativehome': 'helper'}
    valid_removals = (type(removals) is dict and all(
        key in known and value in ('submitted', 'terminal', 'done') for key, value in removals.items()))
    if not pending:
        category = 'none'
    elif (profile.get('edition') == 'root' and isinstance(pending, dict)
          and pending.get('action') == 'activate-root'
          and pending.get('stage') in ('stop-helper', 'enable', 'launch')):
        category = 'root-activation-pending'
    elif profile.get('edition') != 'no-root':
        category = 'other-edition'
    elif isinstance(pending, dict):
        if not valid_removals:
            pass
        elif 'previous' in pending:
            category = 'inherited-operation'
        elif unsubmitted_removal(profile, pending):
            category = 'removal-not-submitted'
        elif pending.get('action') == 'install' and pending.get('stage') == 'pending':
            category = 'interrupted-install'
        elif (pending.get('action') == 'uninstall' and pending.get('stage') == 'removing'
              and set(pending) <= {'action', 'stage', 'diagnostic_id', 'eim_registered', 'removals'}):
            category = 'removal-started'
    return {'category': category,
            'next_action': ('none' if category == 'none' else 'review-recovery'
                            if category in ('removal-not-submitted', 'root-activation-pending') else 'retain-evidence'),
            'removals': {known[key]: value for key, value in removals.items()
                         if key in known and value in ('submitted', 'terminal', 'done')}
                        if type(removals) is dict else {}}
