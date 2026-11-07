"""Verify one C1 gate attempt before opening Home from the common installer."""
import json
import re
import shlex

from . import package
from .errors import UserError
from .root_gate import BACKEND


def proof(installer, command, active, details=None):
    reply = installer.root_action(command)
    state = reply.get('result') if isinstance(reply,dict) and reply.get('returnValue') is True else None
    effective = state.get('effective') if isinstance(state,dict) else None
    if (not isinstance(effective,dict) or state.get('backend') != BACKEND
            or effective.get('backend') != BACKEND or effective.get('returnValue') is not True
            or effective.get('profiles',{}) is not None or not isinstance(state.get('intent'),dict)
            or not isinstance(state.get('recovery'),dict)):
        raise UserError('C1 native Home proof is incomplete. Keep recovery state and run cytv status.')
    token = effective.get('token')
    if (not isinstance(token,str) or not re.fullmatch('[a-f0-9]{32}',token)
            or state['intent'].get('token') != token):
        raise UserError('C1 Home attempt identity is unconfirmed. Keep recovery state and run cytv status.')
    if active:
        valid = installer.root_active(state)
    else:
        valid = (installer.root_setup_inactive(state) and state['intent'].get('phase') == 'disabled'
                 and effective.get('state') in ('stock','stopped')
                 and effective.get('stopped') is (effective['state'] == 'stopped'))
    if not valid:
        raise UserError('C1 Home routing or recovery readback was not confirmed. Run cytv status or cytv restore.')
    if details is not None: details['routing'] = effective.get('routing')
    return token


def launch_keyfilter(installer, token):
    # A status read followed by raw LS2 launch can cross an explicit Off. The
    # fixed native operation serializes the initial installer launch too.
    raw = installer.remote.run('/var/lib/clean-your-tv-root/runtime/c1-keyfilter-guard --home '+shlex.quote(token), timeout=5)
    try:
        value = json.loads(raw)
        valid = (isinstance(value,dict)
                 and value.get('returnValue') is True and value.get('backend') == BACKEND
                 and value.get('routing') == 'compositor-keyfilter-v1' and value.get('token') == token
                 and value.get('state') == 'armed' and value.get('healthy') is True
                 and value.get('stopped') is False and value.get('mounted') is False
                 and value.get('stock_verified') is False and value.get('profiles',{}) is None
                 and type(value.get('guardian_pid')) is int and value['guardian_pid'] > 1)
    except (ValueError,TypeError): valid=False
    if not valid:
        raise UserError('C1 Home launch was not confirmed. Run cytv status or cytv restore.')
    return value


def activate(installer):
    pending = installer.store.pending(installer.profile) or {}
    if (pending.get('home_backend') != BACKEND or pending.get('action') != 'activate-root'
            or pending.get('stage') != 'stop-helper'):
        raise UserError('C1 activation is already pending or the backend is unconfirmed. Run cytv status or cytv restore.')
    installer.progress('Checking Root recovery…')
    stock_token = proof(installer, 'status', active=False)
    installer.stop_root_helper_for_activation()
    installer.store.checkpoint(installer.profile, stage='enable')
    installer.progress('Turning on Root Home control…')
    try:
        details = {}
        token = proof(installer, 'enable', active=True, details=details)
        if token == stock_token:
            raise UserError('C1 activation did not establish a new Home attempt. Run cytv status or cytv restore.')
        installer.store.checkpoint(installer.profile, stage='launch', home_token=token)
        foreground = installer.remote.luna('com.webos.applicationManager/getForegroundAppInfo', {}, timeout=5)
        app = foreground.get('appId') if isinstance(foreground,dict) and foreground.get('returnValue') is True else None
        if not isinstance(app,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,254}', app):
            raise UserError('C1 foreground is unconfirmed. Run cytv status or cytv restore.')
        requested = app != package.ROOT_APP
        if requested:
            # The foreground probe can take seconds. An escape during that
            # call must stop this installer from launching the candidate.
            if proof(installer, 'status', active=True) != token:
                raise UserError('C1 Home attempt changed before launch. Run cytv status or cytv restore.')
            installer.progress('Opening Clean Your TV Home…')
            installer.store.checkpoint(installer.profile, stage='launch-submitting')
            installer.outcome.launch_submitted()
            launched = (launch_keyfilter(installer, token) if details.get('routing') == 'compositor-keyfilter-v1'
                        else installer.remote.luna('com.webos.applicationManager/launch', {'id':package.ROOT_APP}))
            if not isinstance(launched,dict) or launched.get('returnValue') is not True:
                raise UserError('C1 Home launch was not confirmed. Run cytv status or cytv restore.')
            installer.outcome.launch_accepted()
        installer.store.checkpoint(installer.profile, launch_requested=requested, foreground_observed=not requested)
        if proof(installer, 'status', active=True) != token:
            raise UserError('C1 Home attempt changed during activation. Run cytv status or cytv restore.')
        installer.outcome.startup_observed('root-state-verified')
    except (OSError, RuntimeError, ValueError):
        installer.outcome.startup_observed('unverified')
        try:
            installer.recover_failed_activation()
        except Exception:
            pass  # Retain the original activation failure even if storage is full.
        raise
    installer.store.finish(installer.profile)
    return requested
