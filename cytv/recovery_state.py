"""Local journal classification. Exported summaries are advice, never authority."""

STATES = ('idle', 'pre-submission', 'waiting', 'setup-ready', 'product-ready', 'cancellation-ready', 'terminal-verified', 'blocked')
REASONS = ('no-pending-operation', 'removal-not-submitted', 'terminal-evidence-missing',
           'inherited-operation', 'unsupported-receipt', 'foreign-operation', 'operation-live',
           'packages-verified', 'observation-unverified', 'root-deployment-missing', 'removal-verified', 'activation-verified', 'final-readback-verified', 'cancellation-verified',
           'original-work-remaining', 'original-vendor-failure', 'original-terminal-unknown', 'original-readback-unverified',
           'original-reservation-unverified', 'original-configuration-unknown', 'original-staging-unverified')
ACTIONS = ('check', 'inspect-support', 'continue-product', 'continue-no-root', 'cancel-install', 'continue-setup', 'finish-home-off', 'reconcile', 'retain-evidence', 'continue-removal', 'connect-root')
REMOVAL_STAGES = ('requested', 'original-writers-fenced', 'controls-restored', 'package-removal', 'private-cleanup', 'restart-required', 'verified-clean')
REMOVAL_REASONS = ('removal-requested', 'original-writer-active', 'ownership-conflict', 'controls-unverified',
                   'removal-terminal-unknown', 'private-cleanup-incomplete', 'removal-verified', 'removal-recheck-required', 'restart-required',
                   'root-worker-busy','root-access-required','removal-failed','cleanup-check-failed',
                   'connection-interrupted','connection-unverified')
RESTART_TRIGGERS = ('controller-still-running', 'protected-package-access', 'startup-disable-unverified',
                    'resident-installer-evidence', 'prior-operation-unresolved', 'process-idle-unverified',
                    'invalid-helper-stop-record', 'catalog-helper-stop-unverified', 'package-removal-unverified',
                    'original-configuration-unverified', 'original-package-unverified', 'homebrew-request-unverified')
STATES += ('cleanup-in-progress', 'verified-clean')
REASONS += REMOVAL_REASONS


def removal_summary(pending):
    """Fixed safe projection; neither old success nor this advice grants effects."""
    pending = pending if type(pending) is dict else {}
    stage = pending.get('stage')
    stage = stage if stage in REMOVAL_STAGES else 'requested'
    reason = pending.get('removal_reason')
    previous = pending.get('previous', {})
    outcome = previous.get('state') if type(previous) is dict else None
    if stage == 'verified-clean' and reason == 'removal-verified':
        reason = 'removal-recheck-required'
    result = {'state':'cleanup-in-progress',
            'stage':stage, 'reason':reason if reason in REMOVAL_REASONS else 'removal-requested',
            'original_outcome':outcome if outcome in ('complete', 'recovery_required') else 'unknown'}
    triggers = pending.get('cleanup_restart_triggers')
    if stage == 'restart-required' and type(triggers) is list:
        known = {item for item in triggers if type(item) is str and item in RESTART_TRIGGERS}
        if known:
            result['restart_triggers'] = [item for item in RESTART_TRIGGERS if item in known]
    return result


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
    if type(pending) is dict and pending.get('recovery_protocol') == 'clean-removal-v1':
        removal = removal_summary(pending)
        return result(removal['state'], removal['reason'], 'continue-removal', 'retain-evidence')
    if observation.get('active_operation') is not None:
        return result('blocked', 'foreign-operation', 'check', 'retain-evidence')
    if pending is None:
        return result('idle', 'no-pending-operation')
    if type(pending) is not dict or pending.get('action') not in (
            'install', 'uninstall', 'activate-root', 'setup-root-updater', 'enable-system-updates', 'archive-root-state'):
        return result('blocked', 'unsupported-receipt', 'retain-evidence')
    if 'previous' in pending:
        return result('blocked', 'inherited-operation', 'retain-evidence')
    if pending.get('recovery_protocol')=='no-root-original-stream-v1':
        observer=device.get('observer',{})
        if not isinstance(observer,dict) or observer.get('operation')!=pending.get('observer_operation'):
            return result('blocked','observation-unverified','check','retain-evidence')
        if observation.get('no_root_ready') is True:
            return result('product-ready','original-work-remaining','continue-no-root','retain-evidence')
        reason=observation.get('no_root_reason')
        return result('blocked',reason if reason in REASONS else 'observation-unverified','check','retain-evidence')
    if pending.get('product_operation') and product:
        if product.get('operation') != pending['product_operation']:
            return result('blocked', 'foreign-operation', 'check', 'retain-evidence')
        if product.get('state') == 'pending':
            return result('waiting', 'operation-live', 'check', 'retain-evidence')
    cancellation=observation.get('cancellation')
    if (profile.get('edition')=='root' and pending.get('action')=='install' and pending.get('product_operation')
            and type(cancellation) is dict and cancellation.get('operation')==pending['product_operation']
            and cancellation.get('home_changed') is False
            and cancellation.get('state') in ('admissible','admitted','remove-observed','cancellation-terminal-pending','cancelled-and-removed')):
        return result('cancellation-ready','cancellation-verified','cancel-install','retain-evidence')
    # A native driver may fail before its deployment journal exists. Absence
    # does not prove quiescence, stock Home or that submission had no effects.
    if (profile.get('edition') == 'root' and pending.get('action') == 'install'
            and pending.get('home_backend') == 'c1-native-gate'
            and pending.get('stage') in ('setup', 'verify')
            and not pending.get('product_operation')
            and pending.get('activation_restore_pending') is not True
            and device.get('deployment_stage') == 'absent'
            and observation.get('can_resume_root_setup') is False):
        return result('blocked', 'root-deployment-missing', 'continue-removal', 'retain-evidence')
    if profile.get('edition') == 'root' and device:
        if product.get('can_resume') is True and product.get('resume_reason')=='original_final_readback_verified':
            return result('product-ready','final-readback-verified','continue-product','retain-evidence')
        if (pending.get('action')=='install' and pending.get('stage')=='coordinator-submitted'
                and 'passive' in product):
            return result('blocked','observation-unverified','inspect-support','retain-evidence')
        if observation.get('reconciliation') in ('product-removal-verified', 'root-activation-verified'):
            reason = 'removal-verified' if pending['action'] == 'uninstall' else 'activation-verified'
            return result('terminal-verified', reason, 'reconcile', 'retain-evidence')
        if observation.get('can_resume_root_setup') is True:
            if (pending['action'] == 'uninstall' or
                    (pending['action'] == 'install' and pending.get('product_operation') and
                     (product.get('operation') != pending['product_operation']
                      or product.get('state') != 'complete' or product.get('current') is not True))):
                return result('blocked', 'observation-unverified', 'check', 'retain-evidence')
            return result('setup-ready', 'packages-verified', *_verified_setup_actions(pending), 'retain-evidence')
    if unsubmitted_removal(profile, pending):
        return result('pre-submission', 'removal-not-submitted', 'check', 'retain-evidence')
    return result('blocked', 'terminal-evidence-missing' if profile.get('edition') == 'no-root'
                  else 'observation-unverified', 'check', 'retain-evidence')


def _verified_setup_actions(pending):
    actions = ['continue-setup']
    if pending['action'] in ('install', 'activate-root') and pending.get('home_backend') != 'c1-native-gate':
        actions.append('finish-home-off')
    return actions


def setup_actions(profile, pending, observation=None):
    """Project setup advice only after all assessment priorities have applied."""
    return [action for action in assess(profile, pending, observation)['actions']
            if action in ('continue-setup', 'finish-home-off')]


def observation_diagnostics(observation):
    """Pure fixed facts about malformed optional inputs; never raw values or I/O."""
    from .contract_events import describe
    if observation is None:
        return []
    facts = []
    def check(field, value, expected_type, rule):
        if type(value) is not expected_type:
            facts.append({'schema':1, 'component':'recovery', 'operation':'recover',
                          'phase':'assessment', 'field':field, 'expected':rule,
                          'actual':describe(value), 'decision':'retain'})
    check('observation', observation, dict, 'observation-object')
    if type(observation) is dict:
        if 'device' in observation:
            device = observation['device']
            check('device', device, dict, 'device-object')
            if type(device) is dict:
                for key in ('product', 'observer'):
                    if key in device:
                        check('device.' + key, device[key], dict, 'proof-object')
                product = device.get('product')
                if (type(product) is dict and observation.get('can_resume_root_setup') is True
                        and (product.get('state') != 'complete' or product.get('current') is not True)):
                    facts.append({'schema':1, 'component':'recovery', 'operation':'recover',
                                  'phase':'assessment', 'field':'device.product',
                                  'expected':'setup-product-current-complete',
                                  'actual':dict(describe(product), category='mismatch'), 'decision':'retain'})
        for key in ('can_resume_root_setup', 'no_root_ready'):
            if key in observation:
                check(key, observation[key], bool, 'readiness-boolean')
    return facts


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
        elif pending.get('recovery_protocol')=='no-root-original-stream-v1':
            category = 'no-root-original-stream'
        elif unsubmitted_removal(profile, pending):
            category = 'removal-not-submitted'
        elif pending.get('action') == 'install' and pending.get('stage') == 'pending':
            category = 'interrupted-install'
        elif (pending.get('action') == 'uninstall' and pending.get('stage') == 'removing'
              and set(pending) <= {'action', 'stage', 'diagnostic_id', 'eim_registered', 'removals'}):
            category = 'removal-started'
    return {'category': category,
            'next_action': ('none' if category == 'none' else 'review-recovery'
                            if category in ('removal-not-submitted', 'root-activation-pending','no-root-original-stream') else 'retain-evidence'),
            'removals': {known[key]: value for key, value in removals.items()
                         if key in known and value in ('submitted', 'terminal', 'done')}
                        if type(removals) is dict else {}}
