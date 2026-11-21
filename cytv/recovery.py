"""An explicit recovery journey; backend receipts remain the only authority."""
import hashlib
import re
from time import monotonic

from . import prompts
from .errors import TVRejected, UserError
from .operations import require_removal_idle
from .outcomes import START_HELPER
from .recovery_state import assess, observation_diagnostics, setup_actions, unsubmitted_removal
from .recovery_ui import observed_stock_surface, removal_action

REVIEW = 'Review recovery options'
SAVED_CONNECTION_PROMPT = 'Review recovery options for this saved connection?'
KEPT = 'Recovery data kept. Installation has not restarted.'
BLOCKED = 'Recovery could not be verified. Save the diagnostic report and keep recovery data. Do not repeat removal.'
SEPARATE = 'Recovery finished. Start a new setup separately when you are ready.'


class _RemovalRestartRequired(UserError):
    removal_restart_required = True


def _assessment(profile, pending, observation):
    from .contract_events import record
    for fact in observation_diagnostics(observation):
        record(fact)
    return assess(profile, pending, observation)


def plan(write, state, summary, next_step=KEPT, actions=None):
    value={'state':state,'summary':summary,'next_step':next_step}
    if actions is not None:value['actions']=actions
    write.recovery_plan(value)


def confirmed_uninstall(pending):
    """Return the identity of a saved explicit Uninstall goal."""
    if (type(pending) is not dict or pending.get('recovery_protocol') != 'clean-removal-v1'
            or pending.get('action') != 'uninstall' or pending.get('full_project') is not True
            or 'root_reinstall_payload' in pending):
        return None
    operation = pending.get('removal_operation')
    return operation if isinstance(operation, str) and re.fullmatch(r'[0-9a-f]{32}', operation) else None


def active_operation_plan(write, profile, *, failure=None):
    from .failure_help import GUIDES

    title, _, next_step, _ = GUIDES['operation-active']
    if write.frontend == 'desktop':
        next_step = 'Check TV status'
        write.recovery(profile)
    if failure is not None:
        write.failure_help(dict(failure, next_step=next_step))
    write.recovery_plan({'state':'waiting', 'disposition':'operation-active', 'summary':title,
                         'next_step':next_step, 'actions':['check']})


def refresh_active_no_root(store, profile, payload, write, connect):
    """Read the supported operation through its saved SSH connection without a writer lock."""
    from .diagnostic_context import status_summary
    from .no_root_observer import PROTOCOL, observe
    from .operations import Installer

    directory = store.device_path(profile)
    pending = store.pending(profile) or {}
    protocol = pending.get('recovery_protocol')
    operation_key = 'observer_operation' if protocol == PROTOCOL else 'removal_operation'
    operation = pending.get(operation_key)
    if protocol not in (PROTOCOL, 'clean-removal-v1') or not operation:
        raise UserError('Another cytv session is using this TV.', reason_code='operation-active')

    def current_receipt():
        receipt = store.pending(profile) or {}
        if (store.device_path(profile) != directory
                or (receipt.get('recovery_protocol'), receipt.get(operation_key)) != (protocol, operation)):
            raise UserError('Recovery evidence changed. Check recovery again; recovery data was kept.',
                            reason_code='pending-operation')
        return receipt

    missing_connection = 'The original saved TV connection and host key are required for recovery. Recovery data was kept.'

    def no_credentials(_):
        raise UserError(missing_connection, reason_code='ssh-identity-unverified')

    saved, recovering = store.connection_profile(profile)
    current_receipt()
    if not recovering:
        raise UserError(missing_connection, reason_code='ssh-identity-unverified')
    remote = connect(saved, directory, no_credentials, lambda *_: False, persist=False)
    try:
        pending = current_receipt()
        installer = Installer(remote, store, saved, payload, {}, write)
        result = observe(installer, pending) if protocol == PROTOCOL else installer.observe_clean_removal(pending)
    finally:
        remote.close()
    current_receipt()
    summary = status_summary(result)
    summary.pop('assessment', None)
    if result.get('package_removal_monitor') in ('busy', 'idle', 'unverified'):
        summary['package_removal_monitor'] = result['package_removal_monitor']
    write.status_result(summary)
    active_operation_plan(write, saved)


REMOVAL_RECONNECT_INTERVAL = 2
_BOOT_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')


def _removal_reconnect(store, profile, pending):
    operation = confirmed_uninstall(pending)
    if not operation or pending.get('connection_pending') is True:
        return None
    try:
        known = store.device_path(profile) / 'known_hosts'
        if known.is_symlink() or not (key := known.read_bytes()):
            return None
    except (OSError, UserError):
        return None
    proof = pending.get('cleanup_boot_proof')
    boot = pending.get('cleanup_boot_id') or (proof.get('kernel') if isinstance(proof, dict) else None)
    return {'operation':operation, 'pin':hashlib.sha256(key).hexdigest(),
            'boot':boot if isinstance(boot, str) and _BOOT_ID.fullmatch(boot) else None}


def wait_for_removal_tv(store, profile, reconnect, stop, deadline):
    """Observe only the pinned SSH connection and, when available, the boot ID."""
    from paramiko import BadHostKeyException
    from .errors import connection_interrupted
    from .transport import SSH

    def no_credentials(_):
        raise EOFError

    offline = False
    while not stop.is_set() and monotonic() < deadline:
        try:
            if confirmed_uninstall(store.pending(profile)) != reconnect['operation']:
                return 'unavailable'
            saved, _ = store.connection_profile(profile, expected_pin=reconnect['pin'])
            remote = SSH.connect(saved, store.device_path(saved), no_credentials, lambda *_: False, persist=False)
            try:
                if stop.is_set() or monotonic() >= deadline:
                    return 'timeout'
                if reconnect['boot']:
                    boot = remote.run('cat /proc/sys/kernel/random/boot_id', timeout=5).strip()
                    ready = bool(_BOOT_ID.fullmatch(boot) and boot != reconnect['boot'])
                else:
                    # For older records, connectivity alone can offer the existing
                    # check. The continuation still has to verify the restart.
                    ready = offline
                if ready:
                    store.connection_profile(profile, expected_pin=reconnect['pin'])
                    if confirmed_uninstall(store.pending(profile)) == reconnect['operation']:
                        return 'ready'
                    return 'unavailable'
            finally:
                remote.close()
        except BadHostKeyException:
            return 'identity'
        except Exception as error:
            if getattr(error, 'reason_code', None) == 'ssh-identity-unverified':
                return 'identity'
            if not connection_interrupted(error):
                return 'unavailable'
            offline = True
        stop.wait(max(0, min(REMOVAL_RECONNECT_INTERVAL, deadline - monotonic())))
    return 'timeout'


def restored_for_uninstall(write, profile, operation, result, *, evidence=None):
    """A verified Restore can offer to continue the original Uninstall."""
    if result.get('restored') is True or (result.get('returnValue') is True and result.get('result') == 'restored'):
        write.recovery(profile)
        if evidence is None:
            evidence = {'cleanup':'pending'}
            if result.get('returnValue') is True and result.get('result') == 'restored':
                evidence['stock'] = 'routing-verified'
        summary = observed_stock_surface(evidence) or (
            'The TV accepted a stock app launch.' if evidence.get('stock') == 'launch-accepted'
            else 'LG Home is restored.')
        write.recovery_plan({'state':'complete', 'summary':summary, 'removal_evidence':evidence,
            'next_step':'Continue the remaining cleanup for this TV.', 'continue_removal':operation})


def _write_removal_plan(write, value, *, pending=None, failure=None, allow_requested=False, restart_observed=False):
    from .recovery_ui import removal_restart_required
    restart = removal_restart_required(value)
    if (restart and not restart_observed
            and (failure or {}).get('code') != 'restart-required'):
        # A persisted request is history, not a fresh instruction to power-cycle.
        # Keep the receipt intact; project only the need to check current state.
        reason = ('restart-unverified' if (failure or {}).get('code') == 'restart-unverified'
                  else 'removal-recheck-required')
        removal = dict(value.get('removal', {}), reason=reason)
        removal.pop('stage', None)
        value = dict(value, removed=False, verified_clean=False, restart_required=False,
                     reason=reason, removal=removal)
        if failure is None:
            message = 'Check the TV state before deciding whether a restart is needed.'
            value.update(summary=REVIEW, next_step=message,
                         removal_presentation={'stage_text':'Verifying removal…', 'blocker_text':message,
                                               'title_text':REVIEW, 'waiting':False})
    evidence = value
    if pending is not None and value['removal']['reason'] == 'removal-requested':
        # The public assessment also uses this reason for missing or unknown
        # journal codes. Only the explicit request gets transient advice.
        if not allow_requested or pending.get('removal_reason') != 'removal-requested':
            evidence = dict(value, reason=None, removal=dict(value['removal'], reason=None))
    if (getattr(write, 'frontend', None) == 'desktop' and (failure or {}).get('code') == 'controls-unverified'
            and not restart and (operation := confirmed_uninstall(pending))):
        value = dict(value, restore_for_removal=operation)
    write.recovery_plan(dict(value, removal_action=removal_action(evidence, failure)))


def verified_removal_plan(write, profile, result, *, evidence=None, next_step=SEPARATE):
    """Publish terminal cleanup proof and bind the optional desktop setup to its TV."""
    if (result.get('removed') is not True or result.get('verified_clean') is not True
            or result.get('restart_required') is True):
        return False
    if write.frontend == 'desktop':
        write.recovery(profile)
    _write_removal_plan(write, {'state': 'complete', 'disposition': 'clean-removal',
        'removed': True, 'verified_clean': True, 'restart_required': False,
        'removal_evidence': evidence, 'summary': 'Clean Your TV removal is verified.', 'next_step': next_step})
    return True


def missing_root_deployment_plan(write, profile, pending, observation):
    """Explain missing evidence without repeating reads or granting recovery."""
    assessment = assess(profile, pending, observation)
    if assessment['reason'] != 'root-deployment-missing':
        return False
    write.recovery_plan(dict(assessment,
        summary='Root setup is unfinished, but its deployment record is missing on the TV.',
        next_step='Choose Review recovery options to remove Clean Your TV, then start setup separately. Full removal also removes No-root Home and Helper; back up preferences first.'))
    return True


def no_root_package_check_plan(write, profile, pending, assessment=None, *, error=None):
    if (not pending or pending.get('action') != 'install'
            or pending.get('recovery_protocol') != 'no-root-original-stream-v1'):
        return False
    if error is not None:
        observer_error = getattr(error, 'no_root_observer', {})
        failure = observer_error.get('failure')
        if (observer_error.get('command') != 'status'
                or failure not in ('connection-interrupted', 'timeout', 'transport-error')):
            return False
        reason = 'connection-interrupted' if failure == 'connection-interrupted' else 'observation-unverified'
        assessment = dict(state='blocked', reason=reason, actions=['check', 'retain-evidence'])
    elif not assessment or assessment['reason'] != 'original-terminal-unknown':
        return False
    write.recovery(profile)
    next_step = 'Keep recovery state and run cytv status.' if write.frontend == 'console' else 'Keep recovery data.'
    write.recovery_plan(dict(assessment, disposition='no-root-package-check',
                            summary='The TV package result could not be verified.', next_step=next_step))
    return True


def offer_install_recovery(write, store, profile):
    pending = store.pending(profile) if profile else None
    if not pending or pending.get('action') not in ('install', 'activate-root'):
        return False
    write.recovery(profile)
    plan(write, 'review', REVIEW, KEPT, actions=['check', 'retain-evidence'])
    return True


def cancelled(write, store, profile, action, phase, tv_info=None, checks=None, *, save_report=True):
    """Stopping host interaction does not cancel an accepted TV request."""
    pending = store.pending(profile) if profile else None
    if not pending:
        write('Cancelled. Installation has not started.' if action == 'install'
              else 'Cancelled. If an installation was submitted, run cytv status before retrying.')
        return
    write('Cancelled. If an installation was submitted, run cytv status before retrying.')
    if not removal_plan(write, store, profile, state='waiting', evidence=tv_info.get('removal_evidence') if tv_info else None):
        offer_install_recovery(write, store, profile)
    if save_report:
        from . import diagnostics
        diagnostics.save_result(write, store, action, profile, phase, tv_info, checks=checks)


def remove_before_reinstall(installer, ask, write, *, load_payload=False, next_step=KEPT):
    plan(write, 'ready', 'Finish removing Clean Your TV before installing again. LG Home will be restored and remaining Clean Your TV packages removed.', next_step)
    if installer.profile['edition'] == 'no-root':
        write('LG Home will be restored. Clean Your TV, its updaters, Home Helper and saved preferences will be removed.')
    if not prompts.confirm('Remove remaining Clean Your TV packages?', ask, write):
        write(KEPT)
        return
    if load_payload and not installer.manifest:
        from . import package
        try:
            installer.manifest = package.verify_payload(installer.payload)
        except FileNotFoundError:
            raise UserError('Release payload is missing. Download a built cytv executable or run python scripts/build-cytv.py --payload-only from source.') from None
    completed = installer.uninstall_project()
    evidence = getattr(installer, 'tv_info', {}).get('removal_evidence')
    if not verified_removal_plan(write, installer.profile, completed, evidence=evidence):
        removal_plan(write, installer.store, installer.profile, state='waiting',
                     restart_observed=completed.get('restart_required') is True, evidence=evidence)


def removal_plan(write, store, profile, state='blocked', connecting=False, failure=None, *, error=None, phase='recover',
                 restart_observed=False, evidence=None, restart_instruction=None):
    """Expose only current safe assessment fields, with the selected TV bound."""
    if not profile:return False
    pending=store.pending(profile)
    if not pending or pending.get('recovery_protocol')!='clean-removal-v1':return False
    if error is not None:
        from .failure_help import removal_failure
        failure = removal_failure(error, phase, profile, pending, help=failure)
    from .recovery_state import removal_summary
    summary=removal_summary(pending)
    assessment=assess(profile,pending,None)
    if summary['reason']=='root-access-required' and profile['edition']=='no-root':
        assessment['actions'].insert(0, 'connect-root')
    write.recovery(profile)
    restart=summary['reason']=='restart-required' or summary['stage']=='restart-required'
    value = {'state':state,'disposition':'clean-removal','removed':False,'verified_clean':False,'restart_required':restart,
        'summary':'Restart the TV to finish removal' if restart else 'Removal has been requested. Continue the remaining cleanup for this TV.',
        'next_step':('Restart the TV completely: disconnect it from power, reconnect it, then choose Try again. Standby is not a full restart.' if restart
                     else 'Connect to the TV to continue cleanup.' if connecting else 'Continue the remaining cleanup for this TV.'),
        'removal':summary,'actions':assessment['actions'],'reason':summary['reason'],'removal_evidence':evidence}
    from .recovery_ui import removal_connection_failure, removal_details, removal_title, removal_waiting
    detail = removal_details(value, failure)
    if restart and restart_observed and restart_instruction:
        detail['blocker_text'] = restart_instruction
    value.update(connection_failure=removal_connection_failure(value, failure),
                 removal_presentation={**detail, 'title_text':removal_title(value, failure),
                                       'waiting':removal_waiting(value, failure)})
    if failure is not None or value['connection_failure']:
        value.update(summary=value['removal_presentation']['title_text'],next_step=detail['blocker_text'])
    elif not connecting:
        value.update(summary=value['removal_presentation']['title_text'],
                     next_step=detail['blocker_text'] or value['next_step'])
    if (getattr(write, 'frontend', None) == 'desktop'
            and (restart_observed or (failure or {}).get('code') == 'restart-required')
            and (reconnect := _removal_reconnect(store, profile, pending))):
        value['removal_reconnect'] = reconnect
    _write_removal_plan(write, value, pending=pending, failure=failure, allow_requested=connecting,
                        restart_observed=restart_observed)
    return True


def recover(installer, ask, write, non_interactive=False, initial_observation=None, *, review_confirmed=False):
    """Review first; never implicitly reinstall, erase receipts or retry a mutation."""
    plan(write, 'review', REVIEW)
    if non_interactive:
        raise UserError('Recovery requires interactive confirmation. --yes does not approve recovery.')
    if initial_observation is None and not review_confirmed:
        write('Checking recovery does not reinstall or remove packages. Root checks may run verified support code.')
        if not prompts.confirm('Check recovery options?', ask, write):
            write(KEPT)
            return
    try:
        from .root_activation import retained_retry_receipt
        pending = installer.store.pending(installer.profile)
        activation_restore = pending and pending.get('activation_restore_pending') is True
        if (initial_observation is None and pending and pending.get('home_backend') == 'c1-native-gate'
                and (activation_restore or pending.get('activation_restore') == 'verified')
                and not retained_retry_receipt(pending)):
            if not installer.recover_failed_activation(verified_support=True):
                raise UserError(BLOCKED, reason_code='pending-operation')
            plan(write, 'complete', 'LG Home is restored.', 'Save diagnostic report…')
            return
        if activation_restore and not installer.recover_failed_activation():
            raise UserError(BLOCKED, reason_code='pending-operation')
        try:
            result = installer.observe_recovery() if initial_observation is None else initial_observation
        except Exception as error:
            if (installer.profile['edition'] == 'no-root' and pending
                    and pending.get('recovery_protocol') == 'no-root-original-stream-v1'):
                # Cleanup reads current presence independently of a damaged or
                # incomplete old observer. Its separate confirmation is required.
                from . import diagnostics
                try:
                    diagnostics.create_report(installer.store, 'recover', installer.profile, 'recover', error)
                except (OSError, ValueError, TypeError):
                    pass
                if no_root_package_check_plan(write, installer.profile, pending, error=error):
                    return
                next_step = KEPT
                if (pending.get('action') == 'install' and installer.profile.get('connection') != 'root-ssh'
                        and getattr(error, 'local_recovery', {}).get('reason') == 'capsule-missing'):
                    from .no_root_cleanup import inspect_binding
                    from .recovery_ui import REMOVAL_BLOCKERS

                    # Review the original evidence before recording a removal request.
                    binding = inspect_binding(installer, pending={'previous': pending})
                    installer.tv_info['status'] = {'removal_binding': binding}
                    if binding['reservation'] in ('conflict', 'unverified'):
                        plan(write, 'blocked', REMOVAL_BLOCKERS['ownership-conflict'], 'Save diagnostic report…')
                        return
                    if binding['reservation'] == 'matched':
                        next_step = 'Continue the remaining cleanup for this TV.'
                remove_before_reinstall(installer, ask, write, next_step=next_step)
                return
            raise
        installer.tv_info.update(status=result)
        pending = installer.store.pending(installer.profile)
        if retained_retry_receipt(pending):
            token = installer.retained_activation_token(pending, result)
            if not token:
                token = installer.retained_activation_token(pending, result, routing_restore=True)
                if not token:
                    raise UserError(BLOCKED, reason_code='pending-operation')
                if not prompts.confirm('Restore LG Home?', ask, write):
                    write(KEPT)
                    return
                if not installer.restore_retained_activation_routing(pending, token):
                    raise UserError(BLOCKED, reason_code='pending-operation')
            plan(write, 'ready', 'LG Home is restored.')
            if prompts.confirm('Finish Root setup and turn on Home control?', ask, write):
                installer.resume_retained_activation(pending, token)
                installer.outcome.review_home(ask, write)
                plan(write, 'complete', 'Review TV checks', 'Save diagnostic report…')
            else:
                write(KEPT)
            return
        from .root_gate import beta_repair_available, repair_beta_recovery
        if (pending is None and installer.profile.get('root_variant') == 'node012-beta'
                and beta_repair_available(installer, result)):
            from .root_runtime import require_idle

            require_idle(installer.store, installer.profile)
            write('Repair the existing Root Beta recovery service and check its status. The app stays installed and LG Home stays selected.')
            if prompts.confirm('Repair the existing Root Beta recovery service?', ask, write):
                repair_beta_recovery(installer)
                installer.tv_info['status'] = {'deployment_stage': 'installed-recovery-only'}
                write('Root Beta recovery service answered and its integrity was verified.')
            return
        assessment = _assessment(installer.profile, pending, result)
        if assessment['reason'] == 'root-deployment-missing':
            write('This removes Root, Root Updater, their services and startup hooks, plus any installed No-root Home, Helper and Updater.')
            write('Removal may reset Home preferences. Reinstallation will not start automatically.')
            remove_before_reinstall(installer, ask, write)
            return
        if pending and pending.get('recovery_protocol')=='clean-removal-v1':
            from .recovery_state import removal_summary
            summary = dict(result.get('removal') or removal_summary(pending))
            blocked = 'continue-removal' not in assessment['actions']
            if blocked:
                summary['reason'] = assessment['reason']
                from .recovery_ui import REMOVAL_BLOCKERS
                message = REMOVAL_BLOCKERS[summary['reason']]
                binding = result.get('removal_binding', {})
                waiting = assessment['state'] == 'waiting'
                next_step = message if 'connect-root' in assessment['actions'] else (
                    'Choose Review recovery options for the same saved TV connection.'
                    if waiting or binding.get('capsule') != 'verified' else KEPT)
                _write_removal_plan(write, {'state':'waiting' if waiting else 'blocked', 'disposition':'clean-removal',
                    'summary':message, 'next_step':next_step, 'removal':summary, 'actions':assessment['actions']},
                    pending=pending)
                write(message)
                write(next_step)
                return
            if summary['reason']=='root-access-required' and installer.profile['edition']=='no-root':
                assessment['actions'].insert(0, 'connect-root')
            _write_removal_plan(write, {'state':'ready','disposition':'clean-removal',
                'summary':'Removal has been requested. Continue the remaining cleanup for this TV.',
                'next_step':'Continue the remaining cleanup for this TV.','removal':summary,'actions':assessment['actions']},
                pending=pending, allow_requested=True)
            if prompts.confirm('Continue removing Clean Your TV?',ask,write):
                completed=installer.continue_clean_removal(pending)
                if not verified_removal_plan(write, installer.profile, completed,
                                             evidence=installer.tv_info.get('removal_evidence')):
                    error_type = _RemovalRestartRequired if completed.get('restart_required') is True else UserError
                    raise error_type('Removal is still in progress. Recovery data and the remaining cleanup step were kept.',
                                     reason_code='pending-operation')
            else:write(KEPT)
            return
        if pending and pending.get('recovery_protocol')=='no-root-original-stream-v1':
            if no_root_package_check_plan(write, installer.profile, pending, assessment):
                return
            if 'continue-no-root' not in assessment['actions']:
                remove_before_reinstall(installer, ask, write)
                return
            if result.get('no_root_configuration_remaining') is True:
                plan(write, 'ready', 'Installed No-root packages are verified.',
                     'Finish configuration using the installed packages.', actions=assessment['actions'])
                question = 'Finish No-root configuration?'
            else:
                plan(write,'ready','The original No-root operation can continue its verified remaining work. Unknown package requests will not be repeated.',actions=assessment['actions'])
                question = 'Continue the original No-root operation?'
            if prompts.confirm(question, ask, write):
                completed = installer.continue_no_root(pending)
                next_step = START_HELPER if completed.get('activation_cancelled') is True else SEPARATE
                plan(write, 'complete', 'Recovery record finished. Original evidence was archived.', next_step)
            else:write(KEPT)
            return
        if 'inspect-support' in assessment['actions']:
            write('The original operation is retained. Verified support code can check continuation or cancellation without changing packages or Home control.')
            if not prompts.confirm('Check the original Root operation using verified support code?', ask, write):
                write(KEPT)
                return
            result=installer.inspect_root_product(pending)
            assessment=_assessment(installer.profile,pending,result)
        if 'continue-product' in assessment['actions']:
            plan(write,'ready','The original package operation can finish its verified final readback. Home control will stay off until you choose it separately.',actions=assessment['actions'])
            if not prompts.confirm('Continue the original Root operation?',ask,write):
                write(KEPT)
                return
            result=installer.continue_root_product(pending)
            pending=installer.store.pending(installer.profile)
            assessment=_assessment(installer.profile,pending,result)
        if (installer.profile['edition']=='root' and pending and pending.get('action')=='install'
                and pending.get('product_operation') and result.get('can_resume_root_setup') is not True
                and assessment['state']=='blocked'
                and 'passive' not in result.get('device',{}).get('product',{})):
            # This is reached only after the separately approved trusted check.
            proof=installer.inspect_root_cancellation(pending)
            if proof.get('state') not in ('admissible','admitted','remove-observed','cancellation-terminal-pending','cancelled-and-removed'):
                raise UserError(BLOCKED,reason_code='pending-operation')
            plan(write,'ready','The original failed Root installation can be cancelled using verified evidence. A new installation will not start.',actions=assessment['actions'])
            if proof.get('state')!='cancelled-and-removed' and not prompts.confirm('Are LG Home and the normal remote controls working now?',ask,write):
                write(KEPT)
                return
            if prompts.confirm('Cancel the original Root installation and finish verified removal?',ask,write):
                installer.cancel_root_product(pending,proof)
                plan(write,'complete','The original Root installation was cancelled and removal was verified.',SEPARATE)
            else:write(KEPT)
            return
        if assessment['actions'] == ['retain-evidence']:
            raise UserError(BLOCKED, reason_code='pending-operation')
        if result.get('active_operation') is not None:
            raise UserError(BLOCKED, reason_code='pending-operation')
        if 'reconcile' in assessment['actions']:
            plan(write, 'ready', 'Completion is verified. Keep the original receipt in an archive and finish the local recovery record.')
            if prompts.confirm('Finish the verified recovery record?', ask, write):
                installer.reconcile_recovery(pending)
                plan(write, 'complete', 'Recovery record finished. Original evidence was archived.', SEPARATE)
            else:
                write(KEPT)
            return
        actions = setup_actions(installer.profile, pending, result)
        if 'continue-setup' in actions:
            plan(write, 'ready', 'Root and Root Updater are installed and verified. Continue to stop the old Helper, turn on Home control and open Clean Your TV Home.', actions=assessment['actions'])
            write.option(0, 'Keep recovery data and exit')
            write.option(1, 'Continue setup and turn on Home control')
            home_off = 'finish-home-off' in actions
            if home_off:
                write.option(2, 'Finish setup with LG Home and Home control off')
            choice = prompts.number(ask, write, 'Recovery action [0]: ', 0, 2 if home_off else 1, default=0)
            if choice == 0:
                write(KEPT)
            elif choice == 1 and prompts.confirm('Finish Root setup?', ask, write):
                # Re-reads status and verifies the updater before Home activation.
                installer.resume_root_setup(expected_pending=pending)
                installer.outcome.review_home(ask, write)
                plan(write, 'complete', 'Review TV checks', 'Save diagnostic report…')
            elif choice == 2:
                write('Home control will stay off. Installed packages and recovery data will be kept.')
                if prompts.confirm('Finish Root setup with Home control off?', ask, write):
                    installer.finish_root_setup_disabled(expected_pending=pending)
                    write.recovery_plan({'state':'complete','disposition':'home-off',
                        'summary':'Root setup finished with LG Home and Home control off.',
                        'next_step':'Prepare updates for all TV components separately, then open Software updates. Compatibility and rollback checks still apply.'})
            return
        if not pending:
            verified_removal = (result.get('reconciled') == 'product-removal-verified' and
                                result.get('device', {}).get('product', {}).get('state') == 'complete' and
                                result.get('device', {}).get('product', {}).get('current') is True)
            if (installer.profile['edition'] == 'root' and not verified_removal and result.get('deployment_stage') not in
                    ('absent', 'installed-recovery-only', 'uninstalled-state-retained')):
                raise UserError(BLOCKED, reason_code='pending-operation')
            plan(write, 'complete', 'No unfinished operation was found. Installation has not started.', 'Save diagnostic report…')
            return
        if (installer.profile['edition'] != 'no-root' or
                pending.get('action') not in ('install', 'uninstall') or
                (pending.get('action') == 'uninstall' and pending.get('stage') not in ('pending', 'removing')) or
                (pending.get('action') == 'install' and pending.get('stage') != 'pending')):
            raise UserError(BLOCKED, reason_code='pending-operation')
        apps = {app['id'] for app in result.get('device', {}).get('apps', [])}
        removals = pending.get('removals', {})
        if not isinstance(removals, dict) or any(
                app not in ('com.gathin.tvhome', 'com.local.nativehome') or
                value not in ('submitted', 'terminal', 'done') or app in apps
                for app, value in removals.items()):
            raise UserError(BLOCKED, reason_code='pending-operation')
        try:
            require_removal_idle(installer.remote, installer.profile, pending)
        except TVRejected as error:
            if (pending['action'] != 'install' or 'recovery_protocol' in pending
                    or not error.package_status_denied):
                raise
            # Developer Mode may deny the global monitor. Treat this as a
            # separate clean-removal goal with its own checks and confirmation.
            remove_before_reinstall(installer, ask, write, load_payload=True)
            return
        summary = ('No package removal was submitted. Finish removal before installing again.'
                   if unsubmitted_removal(installer.profile, pending) else
                   'Finish removing Clean Your TV before installing again. LG Home will be restored and remaining Clean Your TV packages removed.')
        plan(write, 'ready', summary)
        write('Removal may reset Home preferences. Reinstallation will not start automatically.')
        if not prompts.confirm('Remove remaining Clean Your TV packages?', ask, write):
            write(KEPT)
            return
        # The existing removal implementation revalidates its idle/receipt guards.
        installer.uninstall()
        if installer.store.pending(installer.profile):
            raise UserError(BLOCKED, reason_code='pending-operation')
        plan(write, 'complete', 'Finished', SEPARATE)
    except Exception as error:
        if removal_plan(write,installer.store,installer.profile,error=error,
                        evidence=getattr(installer, 'tv_info', {}).get('removal_evidence')):raise
        from .failure_help import for_error
        help = for_error(error, 'recover', installer.profile, installer.store.pending(installer.profile))
        if help and help['code'] != 'pending-operation':
            plan(write, 'blocked', help['title'], help['next_step'])
        else:
            plan(write, 'blocked', BLOCKED)
        raise
