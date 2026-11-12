"""Execute only packaged, verified recovery support; retained code is data."""
import hashlib
import json
import re
import shlex
from .errors import TVCommandError, UserError

RECOVERY_ENTRY = r'''
import runpy, sys
sys.path.insert(0, sys.argv.pop(1))
sys.argv.pop(0)
from python_binding import verify_binding
if verify_binding('/var/lib/clean-your-tv-root') != sys.executable:
    raise ValueError('recovery_interpreter_binding_changed')
runpy.run_path(sys.argv[0], run_name='__main__')
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
    except TVCommandError as error:
        error.root_boundary='python-select'
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
