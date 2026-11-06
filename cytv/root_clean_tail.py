"""Reconnect to final Root cleanup without requiring the retired Python runtime."""
import hashlib
import json
import re
import shlex
import uuid

from .errors import UserError, TVCommandError


def gate_bytes(installer):
    name='installer-support/lifecycle-gate';path=installer.payload/name
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if any(p.is_symlink() for p in (path,*path.parents)) or digest!=installer.manifest.get('files',{}).get(name):
        raise UserError('Recovery support code is missing or changed. Use a complete installer build.',reason_code='pending-operation')
    return raw,digest


def resume(installer, pending):
    bundle=installer.payload/'root-updater'
    manifest=json.loads((bundle/'bundle.json').read_text()).get('files',{})
    if 'cleanup_tail.js' not in manifest:return None
    path=bundle/'cleanup_tail.js'
    source=path.read_bytes()
    if any(p.is_symlink() for p in (path,*path.parents)) or hashlib.sha256(source).hexdigest()!=manifest['cleanup_tail.js']:
        raise UserError('Recovery support code is missing or changed. Use a complete installer build.',reason_code='pending-operation')
    operation=pending.get('removal_target_operation',pending['product_operation'])
    if not re.fullmatch('[a-f0-9]{32}',operation):raise ValueError('Invalid cleanup operation')
    removal=pending['removal_operation']
    if not isinstance(removal,str) or not re.fullmatch('[a-f0-9]{32}',removal):raise ValueError('Invalid cleanup removal intent')
    node=['env','-u','NODE_OPTIONS','-u','NODE_PATH','/usr/bin/node','-']
    observation=json.loads(installer.remote.run(shlex.join([*node,'inspect',operation,'-','0','-1','-1','-',removal]),data=source,timeout=30))
    if observation.get('operation')!=operation or observation.get('removal')!=removal:raise UserError('Removal evidence changed. Recovery data was kept.')
    if observation.get('state')=='not-ready':return None
    if observation.get('state')!='tail-ready':
        raise UserError('Removal is still in progress. Recovery data and the remaining cleanup step were kept.',reason_code='pending-operation')
    raw,digest=gate_bytes(installer)
    stage='/tmp/cytv-root-tail-'+uuid.uuid4().hex
    stages=list(pending.get('root_tail_stages',[]))
    if any(not isinstance(item,str) or not re.fullmatch(r'/tmp/cytv-root-tail-[a-f0-9]{32}',item) for item in stages):
        raise UserError('Removal evidence changed. Recovery data was kept.')
    stages.append(stage)
    installer.store.checkpoint(installer.profile,root_tail_stages=stages)
    installer.remote.run('umask 077; mkdir '+stage)
    installer.remote.upload(stage+'/gate',raw,mode=0o755)
    command=['env','-u','NODE_OPTIONS','-u','NODE_PATH',stage+'/gate','root-clean-lock','/usr/bin/node','-',
             'finish',operation,','.join(stages),'3','4','5',digest,removal]
    # Native gate opens only the existing Root ownership inode; a fresh UUID
    # identifies this disposable support directory, never an operation lease.
    try:reply=json.loads(installer.remote.run(shlex.join(command),data=source,timeout=180))
    except TVCommandError:
        if pending.get('stage')=='verified-clean':return None
        raise
    if reply.get('operation')!=operation or reply.get('removal')!=removal:raise UserError('Removal evidence changed. Recovery data was kept.')
    # A completed receipt is only a fast current readback. Reappeared owned
    # files use the ordinary current-support sweep on explicit Remove/Retry.
    if pending.get('stage')=='verified-clean' and reply.get('state')!='complete':return None
    return reply
