"""Verify one C1 gate attempt before opening Home from the common installer."""
import json
import re
import shlex

from . import package
from .errors import UserError
from .root_gate import BACKEND


class RetryRefused(UserError):
    """The TV refused the retry before changing its activation state."""


def retained_retry_receipt(pending, *, pending_restore=False):
    return bool(pending and pending.get('action') == 'activate-root'
                and pending.get('stage') == 'enable' and pending.get('home_backend') == BACKEND
                and pending.get('requires_updater') is False
                and pending.get('migrate') is False
                and pending.get('activation_restore') == ('unverified' if pending_restore else 'verified')
                and pending.get('activation_restore_pending') is pending_restore
                and not any(key in pending for key in
                            ('previous', 'product_operation', 'recovery_protocol', 'home_token'))
                and all(isinstance(pin, str) and re.fullmatch('[a-f0-9]{64}', pin)
                        for pin in (pending.get('release_sha'), pending.get('bundle_sha'))))


def retained_retry_token(device, *, phase='disabled'):
    effective, intent = device.get('effective', {}), device.get('intent', {})
    token = effective.get('token')
    if (effective.get('routing') == 'compositor-keyfilter-v1'
            and effective.get('state') == 'stopped' and effective.get('reason') == 'input_expired'
            and intent.get('phase') == phase and intent.get('token') == token
            and isinstance(token, str) and re.fullmatch('[a-f0-9]{32}', token)):
        return token
    return None


def retained_filter_token(device):
    from .root_gate import native_proof
    effective = native_proof(device)
    if effective is None:
        return None
    intent, recovery = device.get('intent'), device.get('recovery')
    if (effective.get('stopped') is True and effective['guardian_pid'] == 0
            and effective['healthy'] is False and effective['stock_verified'] is False
            and effective.get('routing_active') is False and effective.get('filter_installed') is True
            and isinstance(intent, dict) and intent.get('enabled') is False
            and isinstance(recovery, dict) and recovery.get('integrity_verified') is True):
        return retained_retry_token(device, phase='recovering')
    return None


# The legacy runtime takes its product and compositor operation locks in
# cli.main(). Check the exact stopped attempt at its native config write.
RETRY_ENABLE = r'''
import json
import select
import sys

sys.path.insert(0, '/var/lib/clean-your-tv-root/runtime')
import cli
import c1_keyfilter as gate

expected = sys.argv[1]
write_config = gate.write_config
spawn = gate.subprocess.Popen
started = None

def wait_for_observer(argv, *args, **kwargs):
    if (isinstance(argv, (list, tuple)) and len(argv) == 7
            and argv[0] == str(gate.STATE/'runtime/c1-keyfilter-guard')
            and argv[1] in ('--guard', '--guard-resumable')
            and argv[2] == started and argv[6] == '0'):
        fd = int(argv[3])
        if fd in kwargs.get('pass_fds', ()):
            # Leave the pipe untouched so the old guardian validates READY.
            select.select([fd], [], [], 4)
    return spawn(argv, *args, **kwargs)

def guarded_config(root, admission, token, uid=0):
    global started
    with gate.operation(root, uid, name='lock'):
        directory = gate.private_directory(root, uid)
        boot = gate.boot_identity()
        intent = gate.read_intent(root, uid)
        prefix = ('CYTV-C1-KEYFILTER-1\ntoken ' + expected + '\nboot ' + boot + '\n').encode()
        expired = (expected + ' input_expired\n').encode()
        if (intent['token'] != expected or intent['boot'] != boot
                or intent['enabled'] or intent['phase'] != 'disabled'
                or not gate.secure(directory/'config', uid, 512).startswith(prefix)
                or gate.secure(directory/'stopped', uid, 160) != expired
                or gate.secure(directory/'outcome', uid, 160) != expired):
            raise ValueError('Retained Home attempt changed')
        started = token
        write_config(root, admission, token, uid)

try:
    selected = gate.selection()
    if selected is None or cli.gate_backend() is None:
        raise ValueError('Compositor backend not selected')
    gate.write_config = guarded_config
    gate.subprocess.Popen = wait_for_observer
    result = cli.main('enable')
    if not started:
        raise ValueError('Retained Home activation was not started')
    reply = {'returnValue': True, 'result': result}
except Exception:
    if started:
        # The installer may verify and retire this attempt even without ARMED.
        print(json.dumps({'returnValue': False,
                          'retained_retry_attempt': [expected, started]}), flush=True)
        raise SystemExit(1) from None
    reply = {'returnValue': False, 'retained_retry_refused': True}
finally:
    gate.subprocess.Popen = spawn
print(json.dumps(reply), flush=True)
'''


def proof(installer, command, active, details=None, *, retry_token=None):
    reply = installer.root_action(command, **({'retry_token': retry_token} if retry_token is not None else {}))
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
    if details is not None:
        details['routing'] = effective.get('routing')
        details['session_only'] = (effective.get('routing') == 'compositor-keyfilter-v1'
                                   and 'session' not in state['intent'])
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


def activate(installer, *, retry_token=None):
    pending = installer.store.pending(installer.profile) or {}
    if (pending.get('home_backend') != BACKEND or pending.get('action') != 'activate-root'
            or pending.get('stage') != ('enable' if retry_token is not None else 'stop-helper')):
        raise UserError('C1 activation is already pending or the backend is unconfirmed. Run cytv status or cytv restore.')
    installer.progress('Checking Root recovery…')
    stock_token = proof(installer, 'status', active=False)
    if retry_token is not None and stock_token != retry_token:
        raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.', reason_code='pending-operation')
    installer.stop_root_helper_for_activation()
    if retry_token is not None:
        installer.store.checkpoint(installer.profile, activation_restore_pending=True, activation_restore='unverified')
    else:
        installer.store.checkpoint(installer.profile, stage='enable')
    installer.progress('Turning on Root Home control…')
    token = None
    home_may_be_open = False
    try:
        details = {}
        token = proof(installer, 'enable', active=True, details=details, retry_token=retry_token)
        if token == stock_token:
            token = None
            raise UserError('C1 activation did not establish a new Home attempt. Run cytv status or cytv restore.')
        foreground = installer.remote.luna('com.webos.applicationManager/getForegroundAppInfo', {}, timeout=5)
        app = foreground.get('appId') if isinstance(foreground,dict) and foreground.get('returnValue') is True else None
        if not isinstance(app,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,254}', app):
            raise UserError('C1 foreground is unconfirmed. Run cytv status or cytv restore.')
        requested = app != package.ROOT_APP
        home_may_be_open = not requested
        # A status read after the foreground probe keeps an intervening
        # emergency stop authoritative before we authorize the launch.
        if requested and proof(installer, 'status', active=True) != token:
            raise UserError('C1 Home attempt changed before launch. Run cytv status or cytv restore.')
        installer.store.checkpoint(installer.profile, stage='launch', home_token=token)
        if requested:
            installer.progress('Opening Clean Your TV Home…')
            installer.store.checkpoint(installer.profile, stage='launch-submitting')
            installer.outcome.launch_submitted()
            home_may_be_open = True
            launched = (launch_keyfilter(installer, token) if details.get('routing') == 'compositor-keyfilter-v1'
                        else installer.remote.luna('com.webos.applicationManager/launch', {'id':package.ROOT_APP}))
            if not isinstance(launched,dict) or launched.get('returnValue') is not True:
                raise UserError('C1 Home launch was not confirmed. Run cytv status or cytv restore.')
            installer.outcome.launch_accepted()
        installer.store.checkpoint(installer.profile, launch_requested=requested, foreground_observed=not requested)
        if proof(installer, 'status', active=True, details=details) != token:
            raise UserError('C1 Home attempt changed during activation. Run cytv status or cytv restore.')
        installer.outcome.startup_observed('root-state-verified')
        if details['session_only']:
            installer.outcome.root_home_session_only()
    except RetryRefused:
        installer.store.checkpoint(installer.profile, activation_restore_pending=False, activation_restore='verified')
        raise
    except (OSError, RuntimeError, ValueError) as error:
        installer.outcome.startup_observed('unverified')
        try:
            if retry_token is None:
                installer.recover_failed_activation()
            else:
                # An interrupted SSH reply cannot authorize a routing write.
                failed_attempt = getattr(error, '_retained_retry_attempt', None)
                if token is None and failed_attempt is not None and failed_attempt[0] == retry_token:
                    token = failed_attempt[1]
                if token is not None and not home_may_be_open:
                    installer.recover_failed_activation(verified_support=True, expected_token=token, routing_only=True)
                else:
                    installer.recover_failed_activation(verified_support=True, expected_token=token,
                                                        stock_only=token is None)
        except Exception:
            pass  # Retain the original activation failure even if storage is full.
        raise
    installer.store.finish(installer.profile)
    return requested
