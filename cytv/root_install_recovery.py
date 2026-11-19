"""Execute only packaged, verified recovery support; retained code is data."""
import hashlib
import json
import re
import shlex
from . import package
from .errors import TVCommandError, UserError

RECOVERY_ENTRY = r'''
import json, runpy, sys
sys.path.insert(0, sys.argv.pop(1))
sys.argv.pop(0)
repair = dict(repair_beta_recovery='root_beta_repair_failure',
              repair_root_recovery='root_retained_repair_failure')
key = repair.get(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[0].endswith('/provision.py') else None
stage = 'python-binding'
try:
    from python_binding import verify_binding
    if verify_binding('/var/lib/clean-your-tv-root') != sys.executable:
        raise ValueError('recovery_interpreter_binding_changed')
    stage = 'support-start'
    runpy.run_path(sys.argv[0], run_name='__main__')
except Exception:
    if key is None:
        raise
    print(json.dumps({'returnValue': False, key: {'stage': stage, 'reason': 'failed'}}), flush=True)
    raise SystemExit(1) from None
'''


def recovery_python(remote):
    from .operations import _RETAINED_PYTHON_CHECK
    from .python_runtime import RUNTIME_ROOT, SHA256
    check=_RETAINED_PYTHON_CHECK+'\nprocess.stdout.write(pythonCommand(process.argv[1]));'
    selected=remote.run(shlex.join(['env','-u','NODE_OPTIONS','-u','NODE_PATH','/usr/bin/node','-e',check,
                                   '/var/lib/clean-your-tv-root'])).strip()
    if selected=='/usr/bin/python3':return selected
    if selected=='/var/lib/clean-your-tv-root/python-launcher':
        return RUNTIME_ROOT+'/'+SHA256+'/bin/python3.13'
    raise UserError('Recovery interpreter could not be verified. Recovery data was kept.', reason_code='pending-operation')


def run(installer, stage, script, args, timeout):
    try:
        python=recovery_python(installer.remote)
    except UserError as error:
        if isinstance(error, TVCommandError):
            error.root_boundary='python-select'
        if script == 'provision.py' and args:
            key = {'repair_beta_recovery': 'root_beta_repair_failure',
                   'repair_root_recovery': 'root_retained_repair_failure'}.get(args[0])
            if key:
                setattr(error, key, {'stage': 'python-select', 'reason': 'failed'})
        raise
    invocation=installer._python_command([python,'-I','-B','-c',RECOVERY_ENTRY,stage,stage+'/'+script,*args])
    try:
        raw=installer.remote.run(invocation,timeout=timeout)
    except TVCommandError as error:
        error.root_interpreter='system-python' if python=='/usr/bin/python3' else 'private-python'
        raise
    # Full interpreter inventory was verified by freshly staged python_binding.
    # Subsequent package readback must not run a retained binding module.
    installer._selected_python=python
    return raw


def restore_activation(installer, token):
    if not isinstance(token, str) or not re.fullmatch('[a-f0-9]{32}', token):
        raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.',
                        reason_code='root-operation-unconfirmed')
    package.verify_payload(installer.payload)
    stage = installer.upload_product(installer.payload/'root-c1')
    finished = False
    try:
        raw = run(installer, stage+'/root-updater', 'clean_removal.py',
                  [stage+'/root', '--restore-activation', token], timeout=180)
        finished = True
        reply = json.loads(raw)
        proof = reply.get('native_restored_sha256') if isinstance(reply, dict) else None
        if (not isinstance(reply, dict) or reply.get('returnValue') is not True
                or reply.get('result') != 'restored' or not isinstance(proof, str)
                or not re.fullmatch('[a-f0-9]{64}', proof)):
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.',
                            reason_code='root-operation-unconfirmed')
    except TVCommandError as error:
        finished = error.exit_status is not None and error.exit_status >= 0
        raise
    finally:
        # Leave only the temporary bundle when the child may still be running.
        if finished:
            try:
                installer.remote.run('rm -rf '+shlex.quote(stage))
            except (OSError, RuntimeError):
                pass


def invoke(installer, action, pending, proof=None):
    if action not in ('inspect','remove') or pending.get('action')!='install':
        raise ValueError('Original install required')
    operation=pending.get('product_operation')
    if not isinstance(operation,str) or not re.fullmatch('[a-f0-9]{32}',operation):
        raise ValueError('Original operation required')
    bundle=installer.payload/'root-updater'
    manifest=json.loads((bundle/'bundle.json').read_text())
    files=manifest.get('files',{})
    recovery={name:hashlib.sha256((bundle/name).read_bytes()).hexdigest()
              for name in ('cancel_install.py','cancel_provision.py')}
    if any(files.get(n)!=digest for n,digest in recovery.items()):
        raise UserError('Recovery support code is missing or changed. Use a complete installer build.', reason_code='pending-operation')
    pin=hashlib.sha256(json.dumps({'bundle':manifest,'recovery':recovery},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    stage=installer.coordinator_code(recovery=True)
    args=[action,'--operation',operation,'--code-sha256',pin,'--report-refusal']
    if proof is not None:
        for name in ('candidate_sha256','proof_sha256'):
            if not isinstance(proof.get(name),str) or not re.fullmatch('[a-f0-9]{64}',proof[name]):raise ValueError('Reviewed proof required')
        if proof.get('code_sha256')!=pin or proof.get('operation')!=operation:raise ValueError('Recovery proof changed')
        args+=['--candidate',proof['candidate_sha256']]
        if action=='remove':args+=['--proof-sha256',proof['proof_sha256']]
    elif action=='remove':raise ValueError('Reviewed proof required')
    reply=json.loads(run(installer,stage,'cancel_install.py',args,timeout=180))
    if (not isinstance(reply,dict) or reply.get('operation')!=operation
            or reply.get('code_sha256')!=pin or reply.get('home_changed') is not False):
        raise UserError('Root cancellation could not be verified. Recovery data was kept.', reason_code='pending-operation')
    return reply
