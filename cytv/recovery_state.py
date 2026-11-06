"""Local journal classification. Exported summaries are advice, never authority."""


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
