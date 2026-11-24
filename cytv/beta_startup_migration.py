"""Explicit migration entry point, separate from recovery and package removal."""
import json
import shlex
from pathlib import PurePosixPath

from . import package, prompts, root_staging
from .errors import UserError
from .state import private_write


def run(installer, ask, write, *, rollback=False):
    if installer.profile.get('edition') != 'root' or installer.profile.get('root_variant') != 'node012-beta':
        raise UserError('Startup migration requires the saved Root Beta SSH connection.')
    pending = installer.store.pending(installer.profile)
    preserved = None
    if pending:
        if (pending.get('recovery_protocol') != 'clean-removal-v1'
                or pending.get('stage') != 'requested'):
            raise UserError('The saved operation cannot be migrated in place. Keep recovery data.', reason_code='pending-operation')
        operation = pending.get('removal_target_operation') or pending.get('product_operation')
        intent = pending.get('removal_operation')
        if not all(isinstance(v, str) and len(v) == 32 and all(c in '0123456789abcdef' for c in v)
                   for v in (operation, intent)):
            raise UserError('The original removal selection is missing. Keep recovery data.', reason_code='pending-operation')
        preserved = operation, intent
    write('The existing application and preferences will be kept. Change Home must be off before migration.')
    if preserved:
        write('The selected removal may be abandoned only if the TV verifies that its cleanup has not started.')
    question = 'Roll back the private Root Beta startup migration?' if rollback else 'Migrate the existing Root Beta startup runtime?'
    if not prompts.confirm(question, ask, write, default=False):
        return None
    # This checks the packaged source before staging any executable support.
    from .root_gate import source_bundle
    from .root_install_recovery import run as device_run
    data = source_bundle(installer, resolution='1920x1080')
    script = 'beta_startup_migration.py'
    if script not in data:
        raise UserError('Root runtime support is missing or changed. Use a complete installer build.')
    stage = root_staging.create(installer.remote, 'c1-root', required=sum(map(len,data.values())))
    for name, raw in data.items():
        target = stage+'/'+package.safe_name(name)
        installer.remote.run('umask 077; mkdir -p '+shlex.quote(str(PurePosixPath(target).parent)))
        installer.remote.upload(target, raw, mode=0o700 if name == 'runtime/c1-keyfilter-guard' else 0o600)
    args = [stage]
    if rollback:
        args.append('--rollback')
    if preserved:
        args += ['--preserve-removal', *preserved]
    from .root_passive import collect_beta
    try:
        reply = json.loads(device_run(installer, stage, script, args, timeout=180))
    finally:
        installer.tv_info['root_beta_state'] = collect_beta(installer.remote)
    expected = 'rolled-back' if rollback else 'complete'
    if (not isinstance(reply, dict) or reply.get('returnValue') is not True or reply.get('phase') != expected
            or any(reply.get(key) is not True for key in ('application_preserved', 'preferences_preserved'))
            or reply.get('home_changed') is not False):
        raise UserError('Root Beta migration completion could not be verified. Keep recovery data.', reason_code='pending-operation')
    if pending:
        if installer.store.pending(installer.profile) != pending:
            raise UserError('The saved operation changed. Keep recovery data.', reason_code='pending-operation')
        directory = installer.store.device_dir(installer.profile)
        original = directory/'operation.json'
        private_write(directory/('beta-startup-preserved-'+preserved[1]+'.json'), original.read_bytes())
        installer.store.finish(installer.profile)
    root_staging.retire(installer.remote, stage, data)
    # The device retains its inverse and authenticated transaction for retry.
    # Staged bytes remain available if the SSH response is lost.
    write('Root Beta startup runtime migration completed. The application and preferences were preserved.')
    return reply
