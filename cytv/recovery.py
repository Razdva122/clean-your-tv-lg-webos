"""An explicit recovery journey; backend receipts remain the only authority."""
from . import prompts
from .errors import UserError

REVIEW = 'Review recovery options'
KEPT = 'Recovery data kept. Installation has not restarted.'
BLOCKED = 'Recovery could not be verified. Save the diagnostic report and keep recovery data. Do not repeat removal.'
SEPARATE = 'Recovery finished. Start a new setup separately when you are ready.'


def plan(write, state, summary, next_step=KEPT):
    write.recovery_plan({'state': state, 'summary': summary, 'next_step': next_step})


def recover(installer, ask, write, non_interactive=False):
    """Review first; never implicitly reinstall, erase receipts or retry a mutation."""
    plan(write, 'review', REVIEW)
    if non_interactive:
        raise UserError('Recovery requires interactive confirmation. --yes does not approve recovery.')
    write('Checking recovery does not reinstall or remove packages. Root checks may run verified support code.')
    if not prompts.confirm('Check recovery options?', ask, write):
        write(KEPT)
        return
    try:
        result = installer.status()
        installer.tv_info.update(status=result)
        pending = installer.store.pending(installer.profile)
        if result.get('active_operation') is not None:
            raise UserError(BLOCKED, reason_code='pending-operation')
        if result.get('can_resume_root_setup') is True and installer.profile['edition'] == 'root':
            plan(write, 'ready', 'Root and Root Updater are installed and verified. Continue to stop the old Helper, turn on Home control and open Clean Your TV Home.')
            if prompts.confirm('Finish Root setup?', ask, write):
                # Re-reads status and verifies the updater before Home activation.
                installer.resume_root_setup()
                plan(write, 'complete', 'Root is ready', 'Check controls on the TV after installation.')
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
        idle = installer.remote.luna('com.webos.appInstallService/status', {'subscribe': True}, timeout=10)
        if (not isinstance(idle, dict) or idle.get('returnValue') is not True or
                not isinstance(idle.get('status'), dict) or idle['status'].get('apps') != []):
            raise UserError('TV installer is not confirmed idle. Keep the receipt and run cytv status before removal.', reason_code='pending-operation')
        apps = {app['id'] for app in result.get('device', {}).get('apps', [])}
        removals = pending.get('removals', {})
        if not isinstance(removals, dict) or any(
                app not in ('com.gathin.tvhome', 'com.local.nativehome') or
                value not in ('submitted', 'terminal', 'done') or app in apps
                for app, value in removals.items()):
            raise UserError(BLOCKED, reason_code='pending-operation')
        plan(write, 'ready', 'Finish removing Clean Your TV before installing again. LG Home will be restored and remaining Clean Your TV packages removed.')
        write('Removal may reset Home preferences. Reinstallation will not start automatically.')
        if not prompts.confirm('Remove remaining Clean Your TV packages?', ask, write):
            write(KEPT)
            return
        # The existing removal implementation revalidates its idle/receipt guards.
        installer.uninstall()
        if installer.store.pending(installer.profile):
            raise UserError(BLOCKED, reason_code='pending-operation')
        plan(write, 'complete', 'Finished', SEPARATE)
    except Exception:
        plan(write, 'blocked', BLOCKED)
        raise
