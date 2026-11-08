"""Durable intent policy for future persistent mode; no device calls or activation.

Persist the returned state before executing its effect. Recovery effects must use
an independently recorded routing transaction, never infer a baseline from intent.
Boot identifiers must distinguish snapshot resumes that reset monotonic uptime.
"""
PHASES = ('disabled', 'trial', 'active', 'stopping', 'recovering', 'starting')
FIELDS = {'version', 'generation', 'phase', 'enabled', 'boot', 'token'}
EVENTS = ('enable', 'confirmed', 'boot', 'restored', 'ready', 'exit', 'fault', 'shutdown', 'resume')


def initial():
    return dict(version=1, generation=0, phase='disabled', enabled=False, boot='', token='')


def identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 128 and all(32 < ord(c) < 127 for c in value)


def validate(state):
    if (not isinstance(state, dict) or set(state) != FIELDS
            or type(state['version']) is not int or state['version'] != 1
            or type(state['generation']) is not int or state['generation'] < 0
            or type(state['enabled']) is not bool or state['phase'] not in PHASES
            or not all(isinstance(state[k], str) for k in ('boot', 'token'))):
        raise ValueError('Invalid persistent intent')
    if state['phase'] in ('active', 'starting', 'stopping') and not state['enabled']:
        raise ValueError('Active intent must be enabled')
    if state['phase'] in ('disabled', 'trial') and state['enabled']:
        raise ValueError('Unconfirmed intent cannot be enabled')
    if state['generation'] == 0:
        if state != initial(): raise ValueError('Invalid initial intent')
    elif not identifier(state['boot']) or not identifier(state['token']):
        raise ValueError('Missing lifecycle identity')
    return state


def transition(state, event):
    validate(state)
    if not isinstance(event, dict) or event.get('kind') not in EVENTS:
        raise ValueError('Invalid lifecycle event')
    kind = event['kind']
    if type(event.get('generation')) is not int:
        raise ValueError('Event generation required')
    if event['generation'] != state['generation']: return dict(state), 'none'
    if kind in ('enable', 'boot', 'resume'):
        if not identifier(event.get('boot')) or not identifier(event.get('token')):
            raise ValueError('Boot and attempt identity required')
        if kind == 'boot' and type(event.get('failsafe')) is not bool:
            raise ValueError('Explicit failsafe observation required')
    elif event.get('token') != state['token']:
        return dict(state), 'none'
    new = dict(state)
    if kind == 'enable':
        if state['phase'] != 'disabled': raise ValueError('Recover and disable before enabling')
        new.update(generation=state['generation']+1, phase='trial', enabled=False,
                   boot=event['boot'], token=event['token'])
        effect = 'start_guarded'
    elif kind == 'resume':
        if (state['phase'] not in ('active','stopping') or not state['enabled']
                or state['boot'] == event['boot']):
            raise ValueError('Continuation requires confirmed prior-session intent')
        new.update(generation=state['generation']+1, phase='starting', enabled=True,
                   boot=event['boot'], token=event['token'])
        effect = 'continue_guarded'
    elif kind == 'boot':
        if not event['failsafe'] and event['boot'] == state['boot']:
            return new, 'none'
        resume = state['phase'] in ('active', 'stopping') and state['enabled'] and not event['failsafe']
        new.update(generation=state['generation']+1, phase='recovering', enabled=resume,
                   boot=event['boot'], token=event['token'])
        effect = 'recover'
    elif kind == 'shutdown':
        if state['phase'] not in ('active', 'stopping') or not state['enabled']:
            raise ValueError('Only confirmed mode can enter shutdown')
        new['phase'] = 'stopping'
        effect = 'none'
    elif kind in ('exit', 'fault'):
        if state['phase'] == 'disabled': return new, 'none'
        new.update(enabled=False, phase='recovering')
        effect = 'recover'
    elif kind == 'restored':
        if state['phase'] != 'recovering': raise ValueError('Unexpected recovery result')
        new['phase'] = 'starting' if state['enabled'] else 'disabled'
        effect = 'start_guarded' if state['enabled'] else 'none'
    elif kind == 'confirmed':
        if state['phase'] != 'trial': raise ValueError('Only a healthy trial can be confirmed')
        new.update(phase='active', enabled=True)
        effect = 'none'
    else:  # ready: the boot adapter has checked recovery + observer + guardian.
        if state['phase'] != 'starting': raise ValueError('Unexpected readiness result')
        new['phase'] = 'active'
        effect = 'none'
    validate(new)
    return new, effect
