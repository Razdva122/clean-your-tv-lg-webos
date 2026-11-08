"""An explicit recovery journey; backend receipts remain the only authority."""
from . import prompts
from .errors import UserError
from .operations import require_removal_idle
from .recovery_state import assess, unsubmitted_removal

REVIEW = 'Review recovery options'
KEPT = 'Recovery data kept. Installation has not restarted.'
BLOCKED = 'Recovery could not be verified. Save the diagnostic report and keep recovery data. Do not repeat removal.'
SEPARATE = 'Recovery finished. Start a new setup separately when you are ready.'


def plan(write, state, summary, next_step=KEPT, actions=None):
    value={'state':state,'summary':summary,'next_step':next_step}
    if actions is not None:value['actions']=actions
    write.recovery_plan(value)


def offer_install_recovery(write, store, profile):
    pending = store.pending(profile) if profile else None
    if not pending or pending.get('action') not in ('install', 'activate-root'):
        return False
    write.recovery(profile)
    plan(write, 'review', REVIEW, KEPT, actions=['check', 'retain-evidence'])
    return True


def cancelled(write, store, profile, action, phase, tv_info=None, checks=None):
    """Stopping host interaction does not cancel an accepted TV request."""
    pending = store.pending(profile) if profile else None
    if not pending:
        write('Cancelled. Installation has not started.' if action == 'install'
              else 'Cancelled. If an installation was submitted, run cytv status before retrying.')
        return
    write('Cancelled. If an installation was submitted, run cytv status before retrying.')
    if not removal_plan(write, store, profile, state='waiting'):
        offer_install_recovery(write, store, profile)
    from . import diagnostics
    diagnostics.save_result(write, store, action, profile, phase, tv_info, checks=checks)


def remove_before_reinstall(installer, ask, write):
    plan(write, 'ready', 'Finish removing Clean Your TV before installing again. LG Home will be restored and remaining Clean Your TV packages removed.')
    if not prompts.confirm('Remove remaining Clean Your TV packages?', ask, write):
        write(KEPT)
        return
    completed = installer.uninstall_project()
    if completed.get('removed') is True and completed.get('verified_clean') is True and completed.get('restart_required') is not True:
        write.recovery_plan({'state':'complete','disposition':'clean-removal','removed':True,'verified_clean':True,
            'summary':'Clean Your TV removal is verified.','next_step':SEPARATE})
    else:
        removal_plan(write, installer.store, installer.profile, state='waiting')


def removal_plan(write, store, profile, state='blocked', connecting=False, failure=None):
    """Expose only current safe assessment fields, with the selected TV bound."""
    if not profile:return False
    pending=store.pending(profile)
    if not pending or pending.get('recovery_protocol')!='clean-removal-v1':return False
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
        'removal':summary,'actions':assessment['actions'],'reason':summary['reason']}
    from .recovery_ui import removal_connection_failure, removal_details
    if removal_connection_failure(value, failure):
        value.update(summary='Removal is not finished yet.',next_step=removal_details(value, failure)['blocker_text'])
    write.recovery_plan(value)
    return True


def recover(installer, ask, write, non_interactive=False, initial_observation=None):
    """Review first; never implicitly reinstall, erase receipts or retry a mutation."""
    plan(write, 'review', REVIEW)
    if non_interactive:
        raise UserError('Recovery requires interactive confirmation. --yes does not approve recovery.')
    if initial_observation is None:
        write('Checking recovery does not reinstall or remove packages. Root checks may run verified support code.')
        if not prompts.confirm('Check recovery options?', ask, write):
            write(KEPT)
            return
    try:
        pending = installer.store.pending(installer.profile)
        if pending and pending.get('activation_restore_pending') is True:
            if not installer.recover_failed_activation():
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
                remove_before_reinstall(installer, ask, write)
                return
            raise
        installer.tv_info.update(status=result)
        pending = installer.store.pending(installer.profile)
        assessment = assess(installer.profile, pending, result)
        if pending and pending.get('recovery_protocol')=='clean-removal-v1':
            from .recovery_state import removal_summary
            summary=removal_summary(pending)
            write.recovery_plan({'state':'ready','disposition':'clean-removal',
                'summary':'Removal has been requested. Continue the remaining cleanup for this TV.',
                'next_step':'Continue the remaining cleanup for this TV.','removal':summary,'actions':assessment['actions']})
            if prompts.confirm('Continue removing Clean Your TV?',ask,write):
                completed=installer.continue_clean_removal(pending)
                if (completed.get('verified_clean') is not True or completed.get('removed') is not True
                        or completed.get('restart_required') is True):
                    raise UserError('Removal is still in progress. Recovery data and the remaining cleanup step were kept.',reason_code='pending-operation')
                write.recovery_plan({'state':'complete','disposition':'clean-removal',
                                     'removed':completed['removed'],'verified_clean':completed['verified_clean'],'restart_required':False,
                                     'summary':'Clean Your TV removal is verified.','next_step':SEPARATE})
            else:write(KEPT)
            return
        if pending and pending.get('recovery_protocol')=='no-root-original-stream-v1':
            if 'continue-no-root' not in assessment['actions']:
                remove_before_reinstall(installer, ask, write)
                return
            plan(write,'ready','The original No-root operation can continue its verified remaining work. Unknown package requests will not be repeated.',actions=assessment['actions'])
            if prompts.confirm('Continue the original No-root operation?',ask,write):
                installer.continue_no_root(pending)
                plan(write,'complete','Recovery record finished. Original evidence was archived.',SEPARATE)
            else:write(KEPT)
            return
        if 'inspect-support' in assessment['actions']:
            write('The original operation is retained. Verified support code can check continuation or cancellation without changing packages or Home control.')
            if not prompts.confirm('Check the original Root operation using verified support code?', ask, write):
                write(KEPT)
                return
            result=installer.inspect_root_product(pending)
            assessment=assess(installer.profile,pending,result)
        if 'continue-product' in assessment['actions']:
            plan(write,'ready','The original package operation can finish its verified final readback. Home control will stay off until you choose it separately.',actions=assessment['actions'])
            if not prompts.confirm('Continue the original Root operation?',ask,write):
                write(KEPT)
                return
            result=installer.continue_root_product(pending)
            pending=installer.store.pending(installer.profile)
            assessment=assess(installer.profile,pending,result)
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
        if result.get('can_resume_root_setup') is True and installer.profile['edition'] == 'root':
            plan(write, 'ready', 'Root and Root Updater are installed and verified. Continue to stop the old Helper, turn on Home control and open Clean Your TV Home.')
            write.option(0, 'Keep recovery data and exit')
            write.option(1, 'Continue setup and turn on Home control')
            home_off = (pending and pending.get('action') in ('activate-root','install')
                        and pending.get('home_backend') != 'c1-native-gate')
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
        require_removal_idle(installer.remote, installer.profile, pending)
        apps = {app['id'] for app in result.get('device', {}).get('apps', [])}
        removals = pending.get('removals', {})
        if not isinstance(removals, dict) or any(
                app not in ('com.gathin.tvhome', 'com.local.nativehome') or
                value not in ('submitted', 'terminal', 'done') or app in apps
                for app, value in removals.items()):
            raise UserError(BLOCKED, reason_code='pending-operation')
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
        if removal_plan(write,installer.store,installer.profile):raise
        from .failure_help import for_error
        help = for_error(error, 'recover', installer.profile, installer.store.pending(installer.profile))
        if help and help['code'] != 'pending-operation':
            plan(write, 'blocked', help['title'], help['next_step'])
        else:
            plan(write, 'blocked', BLOCKED)
        raise
