#!/usr/bin/env python3
"""Shared Root product lifecycle. Package journals retain terminal evidence.

Request IDs are data, never commands. A repeated request only reads its durable
record; even a dead worker cannot authorize replay of an uncertain submission.
"""
import re

from coordinator_inventory import BUNDLED_FILES
from installation import Busy, Ownership, _optional_record, pending_journals, read_journal


def operation_id(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):
        raise ValueError('invalid_operation_uuid')
    return value


def failure_summary(error):
    """Fixed worker categories only; command, output and message stay private."""
    import subprocess
    name=type(error).__name__
    allowed=('CalledProcessError','TimeoutExpired','ValueError','RuntimeError','OSError',
             'PermissionError','FileNotFoundError','TypeError','KeyError')
    result={'exception_type':name if name in allowed else 'unknown'}
    if isinstance(error,subprocess.CalledProcessError) and type(error.returncode) is int and -255<=error.returncode<=255:
        result['exit_status']=error.returncode
    if isinstance(error,OSError) and type(error.errno) is int and 0<=error.errno<=4095:
        result['errno']=error.errno
    return result


def log_failure(device, error):
    try:
        if hasattr(device,'log'): device.log(error)
    except Exception:
        pass  # Private logging must never replace the initiating failure.


class _Recorded(Exception):
    def __init__(self,record): self.record=record


class Coordinator:
    def __init__(self, device, ownership=None, read=read_journal):
        self.read=read
        self.device=device
        self.ownership=ownership if ownership is not None else Ownership()
        self.store=self.ownership.store

    def status(self, identifier):
        identifier=operation_id(identifier)
        value=_optional_record(self.store,'request-'+identifier)
        if value is None:
            return dict(operation=identifier,stage='unknown',state='unknown',code='unknown_operation')
        if (not isinstance(value,dict) or value.get('operation')!=identifier
                or value.get('action') not in ('install','remove')
                or value.get('state') not in ('pending','complete','recovery_required')):
            raise ValueError('unknown_product_operation')
        return value

    def inspect(self):
        return self.device.inspect()

    def restore(self):
        # Emergency restoration must work even while another operation is retained.
        return self.device.restore()

    def _run(self, identifier, action, perform):
        identifier=operation_id(identifier)
        previous=self.status(identifier)
        if previous['state']!='unknown':
            if previous['action']!=action: raise ValueError('operation_action_conflict')
            return previous
        def check():
            existing=self.status(identifier)
            if existing['state']!='unknown': raise _Recorded(existing)
            pending_journals('product',self.read)
        try:
            with self.ownership.operation('product', 'product-'+identifier+'.json', check=check) as lease:
                # Check under the lock too: two clients can race their first status.
                previous=self.status(identifier)
                if previous['state']!='unknown': return previous
                record=dict(operation=identifier,lease=lease['id'],action=action,stage='reserved',state='pending',code='operation_pending',home_changed=False)
                submission=_optional_record(self.store,'submission-'+identifier)
                if submission is not None: record['candidate_sha256']=submission['candidate_sha256']
                def checkpoint(stage):
                    record['stage']=stage
                    self.store.write('request-'+identifier,record)
                    self.ownership.stage(lease,stage)
                self.device.operation=lease
                self.device.ownership=self.ownership
                checkpoint('reserved')
                try:
                    result=perform(checkpoint)
                    record.update(stage='complete',state='complete',code='verified',result=result)
                    self.store.write('request-'+identifier,record)
                    self.ownership.stage(lease,'complete',terminal=True)
                except Exception as error:
                    log_failure(self.device,error)
                    # Raw details remain in private logs; retain only fixed failure categories.
                    record.setdefault('failure',failure_summary(error))
                    record.update(state='recovery_required',code='installation_requires_recovery')
                    self.store.write('request-'+identifier,record)
                return record
        except _Recorded as existing:
            if existing.record['action']!=action: raise ValueError('operation_action_conflict')
            return existing.record

    def install(self, identifier, payload, migrate=False, prepare_supervisor=False):
        operation_id(identifier)
        if type(migrate) is not bool or type(prepare_supervisor) is not bool:
            raise ValueError('invalid_install_options')
        # Validate payload/runtime readiness before taking the product lease. A
        # replay never re-enters preflight, provisioning, or package submission.
        previous=self.status(identifier)
        if previous['state']!='unknown':
            if previous['action']!='install': raise ValueError('operation_action_conflict')
            return previous
        options=dict(migrate=migrate,prepare_supervisor=prepare_supervisor)
        self.device.preflight(payload,options)
        def perform(checkpoint):
            state=self.device.inspect()['state']
            if state=='fresh':
                checkpoint('root-deploy')
                self.device.deploy(payload,options)
                checkpoint('root-updater')
                self.device.updater(payload,options)
            elif state!='installed':
                raise ValueError('installation_requires_recovery')
            if prepare_supervisor:
                checkpoint('supervisor')
                self.device.supervisor(payload,options)
            checkpoint('readback')
            return self.device.readback()
        return self._run(identifier,'install',perform)

    def remove(self, identifier):
        def perform(checkpoint):
            return self.device.remove(checkpoint)
        return self._run(identifier,'remove',perform)


    def resume(self, identifier, payload):
        """Explicit continuation: same request/lease, verified snapshot, no replay."""
        identifier=operation_id(identifier)
        submission=_optional_record(self.store,'submission-'+identifier)
        if submission is None: raise ValueError('verified_worker_snapshot_required')
        options=self.device.verify_resume(payload,submission)
        previous=self.status(identifier)
        if previous['state']=='unknown' or (not previous.get('lease') and previous.get('stage')=='blocked'):
            current=self.ownership.status()
            journal='product-'+identifier+'.json'
            if current is not None and current['owner']=='product' and current['journal']==journal:
                if current['terminal']:raise ValueError('completed_request_record_required')
                # The lease itself durably names the request before its first
                # checkpoint. Effects are forbidden until that checkpoint exists.
                with self.ownership.operation('product',journal,resume=current['id']) as lease:
                    if self.status(identifier)['state']=='unknown' or not self.status(identifier).get('lease'):
                        self.store.write('request-'+identifier,dict(operation=identifier,lease=lease['id'],action=submission['action'],stage='reserved',state='pending',code='operation_pending',home_changed=False,candidate_sha256=submission.get('candidate_sha256')))
                previous=self.status(identifier)
            elif previous['state']!='unknown':
                # A blocked record without a reservation is a proved failure
                # before the kernel's first checkpoint, not a package attempt.
                with self.ownership.operation('product',journal,check=lambda:pending_journals('product',self.read)) as lease:
                    self.store.write('request-'+identifier,dict(operation=identifier,lease=lease['id'],action=submission['action'],stage='reserved',state='pending',code='operation_pending',home_changed=False,candidate_sha256=submission.get('candidate_sha256')))
                previous=self.status(identifier)
        if previous['state']=='unknown':
            # Before the first reservation no product effect is possible. The
            # normal kernel atomically deduplicates even a late original worker.
            if submission['action']=='install': return self.install(identifier,payload,**options)
            return self.remove(identifier)
        if previous.get('action')!=submission['action'] or not previous.get('lease'):
            raise ValueError('original_product_lease_required')
        def check():
            current=self.ownership.status()
            if current is None or current['id']!=previous['lease']: raise Busy()
            from installation import JOURNALS
            updates={JOURNALS[name][0] for name in ('root-update','system-update')}
            pending_journals('product',lambda path:self.read(path) if path in updates else None)
        with self.ownership.operation('product','product-'+identifier+'.json',resume=previous['lease'],check=check) as lease:
            record=self.status(identifier)
            self.device.operation=lease;self.device.ownership=self.ownership
            if lease['terminal']:
                # Historical completion is not remaining work. Revalidate only;
                # external drift must not retroactively create a mutation lease.
                try:
                    if not self.device.validate_completion(record['action'],record['lease']):raise ValueError('historical_completion_is_not_current')
                    result=self.device.readback() if record['action']=='install' else record['result']
                    return dict(record,current=True,result=result)
                except Exception as error:
                    log_failure(self.device,error)
                    return dict(record,state='recovery_required',code='historical_completion_is_not_current',current=False)
            def checkpoint(stage):
                record.update(stage=stage,state='pending',code='operation_pending')
                self.store.write('request-'+identifier,record);self.ownership.stage(lease,stage)
            try:
                if record['action']=='install':
                    result=self.device.resume_install(payload,options,record['stage'],checkpoint)
                else:
                    result=self.device.remove(checkpoint,resume=True)
                record.update(stage='complete',state='complete',code='verified',result=result)
                self.store.write('request-'+identifier,record)
                self.ownership.stage(lease,'complete',terminal=True)
            except Exception as error:
                log_failure(self.device,error)
                self.ownership.stage(lease,record['stage'],terminal=False)
                record.setdefault('failure',failure_summary(error))
                record.update(state='recovery_required',code='continuation_requires_recovery')
                self.store.write('request-'+identifier,record)
            return record


def _verified_payload(payload, prepare_supervisor):
    """Copy only authoritative verified component inventories; omit runtime.

    Runtime preparation is the Node/runtime.js contract and precedes this API.
    cytv already prepares Python and must not upload an offline runtime again.
    """
    from pathlib import Path
    import deploy
    from updater.bootstrap import verify_bundle
    payload=Path(payload)
    inventories={'root':deploy.verify_bundle(payload/'root'),
                 'root-updater':verify_bundle(payload/'root-updater')}
    if prepare_supervisor:
        # verify_bundle cannot be imported before its enclosing known bundle is
        # checked. The canonical setup verifier is bundled with the coordinator.
        from system_setup import verify_bundle as verify_system
        inventories['supervisor']=verify_system(payload/'supervisor')
    return inventories


def candidate_digest(payload, inventories):
    import hashlib
    import json
    from pathlib import Path
    from deploy import checked_file
    value={name:hashlib.sha256(checked_file(Path(payload)/name,'bundle.json')).hexdigest() for name in inventories}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def root_review_binding(payload, inventories):
    import hashlib,json
    from pathlib import Path
    from updater.package import inspect_package
    from deploy import checked_file,APP
    root=Path(payload)/'root';manifest=inventories['root'];release=json.loads(checked_file(root,'release.json'))
    raw=checked_file(root,manifest['package'])
    hashes=inspect_package(raw,{'version':release['version'],'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'local':True})
    prefix='usr/palm/applications/'+APP+'/'
    def mutable(name):
        if name in (prefix+'apps.js',prefix+'config.js'):return True
        relative=name[len(prefix):] if name.startswith(prefix) else ''
        return relative.startswith('icons/') and relative.count('/')==1 and relative.lower().endswith(('.png','.jpg','.jpeg','.webp'))
    return {'identity':{'package':manifest['package'],'version':release['version'],'application_id':release['application_id']},
            'code':{name:digest for name,digest in hashes.items() if not mutable(name)}}


def submit(identifier, payload, migrate=False, prepare_supervisor=False, action='install', candidate=None, ownership=None):
    """Persist once, snapshot trusted worker material, then detach.

    The submission receipt precedes Popen. A lost reply or a failed spawn is
    inspect-only and cannot repeat a package operation under the same ID.
    """
    import json
    import os
    import hashlib
    from pathlib import Path
    import subprocess
    import sys
    from install_device import LocalDevice
    operation_id(identifier)
    if type(migrate) is not bool or type(prepare_supervisor) is not bool: raise ValueError('invalid_install_options')
    if action not in ('install','remove'): raise ValueError('invalid_product_action')
    ownership=ownership if ownership is not None else Ownership();store=ownership.store
    with store.lock():
        existing=_optional_record(store,'submission-'+identifier)
        known=request_status(identifier,store)
        if known['state']!='unknown':
            if known.get('action')!=action: raise ValueError('operation_action_conflict')
            return known
        if existing is not None:
            if existing.get('action')!=action: raise ValueError('operation_action_conflict')
            return request_status(identifier,store)
        inventories=_verified_payload(payload,prepare_supervisor)
        actual_candidate=candidate_digest(payload,inventories)
        if candidate is not None and candidate!=actual_candidate: raise ValueError('reviewed_candidate_changed')
        device=LocalDevice();device.preflight(payload,dict(migrate=migrate,prepare_supervisor=prepare_supervisor),product=action=='install')
        receipt=dict(operation=identifier,stage='preparing',state='pending',code='operation_pending',action=action,home_changed=False,candidate_sha256=actual_candidate,options=dict(migrate=migrate,prepare_supervisor=prepare_supervisor),worker_sha256=hashlib.sha256((__import__('pathlib').Path(payload)/'root-updater/bundle.json').read_bytes()).hexdigest(),root_binding=root_review_binding(payload,inventories),root_static={n:d for n,d in inventories['root']['files'].items() if n not in (inventories['root'].get('package'),'release.json','SHA256SUMS')})
        store.write('submission-'+identifier,receipt)
        try:
            root=Path(store.root)/('request-'+identifier)
            root.mkdir(mode=0o700)
            # Clone checked bytes, not a directory tree whose extra/link entries might
            # be executed by a later worker. The updater inventory contains all code.
            for component,manifest in inventories.items():
                for name in (*manifest['files'],'bundle.json'):
                    from deploy import checked_file
                    target=root/component/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                    with target.open('xb') as output:
                        raw=checked_file(Path(payload)/component,name)
                        if name!='bundle.json' and hashlib.sha256(raw).hexdigest()!=manifest['files'][name]:
                            raise ValueError('worker_source_changed')
                        output.write(raw);output.flush();os.fsync(output.fileno())
                    target.chmod(0o600)
            if candidate_digest(root,inventories)!=actual_candidate: raise ValueError('worker_source_changed')
        except (OSError,ValueError):
            receipt.update(state='recovery_required',code='worker_snapshot_unavailable')
            store.write('submission-'+identifier,receipt)
            return receipt
        receipt['stage']='submitted'
        store.write('submission-'+identifier,receipt)
        args=[sys.executable,'-B',str(root/'root-updater/install_driver.py'),action,'--operation',identifier,'--payload',str(root),'--worker']
        if migrate: args.append('--migrate-packaged-home')
        if prepare_supervisor: args.append('--prepare-supervisor')
        log=root/'worker.log'
        with log.open('xb') as output:
            log.chmod(0o600)
            try:
                subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True,close_fds=True,
                                 env={**{k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')},'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'})
            except OSError:
                receipt.update(state='recovery_required',code='worker_submission_unknown')
                store.write('submission-'+identifier,receipt)
        return receipt


def resume_submit(identifier, ownership=None, action=None):
    import os,subprocess,sys
    from pathlib import Path
    from install_device import LocalDevice
    identifier=operation_id(identifier)
    ownership=ownership if ownership is not None else Ownership()
    submission=_optional_record(ownership.store,'submission-'+identifier)
    if submission is None:raise ValueError('verified_worker_snapshot_required')
    if action is not None and submission.get('action')!=action:raise ValueError('operation_action_conflict')
    root=Path(ownership.store.root)/('request-'+identifier)
    LocalDevice().verify_resume(root,submission)
    args=[sys.executable,'-B',str(root/'root-updater/install_driver.py'),submission['action'],'--operation',identifier,'--payload',str(root),'--worker','--resume']
    with (root/'worker.log').open('ab') as output:
        subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True,close_fds=True,
          env={**{k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')},'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1'})
    return dict(request_status(identifier,ownership.store),state='pending',stage='resume-submitted',code='continuation_pending')


def request_status(identifier, store):
    from install_device import LocalDevice
    ownership=Ownership.__new__(Ownership);ownership.store=store
    status=Coordinator(LocalDevice(),ownership).status(identifier)
    if status['state']!='unknown': return status
    return _optional_record(store,'submission-'+operation_id(identifier)) or status



def continuation_status(identifier, store, device=None):
    """Prove a narrow continuation without creating locks, records or workers."""
    import fcntl, os
    from pathlib import Path
    from install_device import LocalDevice
    result=dict(can_resume=False,resume_reason='recovery_evidence_required')
    directory=fd=None
    try:
        identifier=operation_id(identifier)
        owner=Ownership.__new__(Ownership);owner.store=store
        # Opening an existing checked mutex read-only never provisions absent state.
        directory=store._directory()
        fd=os.open('ownership.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        store._check(os.fstat(fd))
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        record=Coordinator(device,owner).status(identifier)
        lease=owner.status()
        if (lease is None or lease['terminal'] or lease['owner']!='product'
                or lease['journal']!='product-'+identifier+'.json' or record.get('lease')!=lease['id']):return result
        submission=_optional_record(store,'submission-'+identifier)
        if (not isinstance(submission,dict) or submission.get('operation')!=identifier
                or submission.get('action')!=record.get('action')):return result
        device=device if device is not None else LocalDevice()
        device.verify_resume(Path(store.root)/('request-'+identifier),submission)
        device.operation=lease;device.ownership=owner
        if device.continuation_ready(record,submission,store) and owner.status()==lease:
            return dict(can_resume=True,resume_reason='original_final_readback_verified')
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):pass
    finally:
        if fd is not None:os.close(fd)
        if directory is not None:os.close(directory)
    return result


def main():
    import argparse
    import json
    from pathlib import Path
    from install_device import LocalDevice, checked_store
    from installation import STATE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','install','status','restore','remove','activate'))
    parser.add_argument('--operation')
    parser.add_argument('--payload',type=Path)
    parser.add_argument('--candidate',help='SHA-256 of the reviewed component bundle manifests')
    parser.add_argument('--migrate-packaged-home',action='store_true')
    parser.add_argument('--prepare-supervisor',action='store_true')
    parser.add_argument('--verify-current',action='store_true',help='Read current completion proof without replay')
    parser.add_argument('--resume',action='store_true',help='Explicitly continue the original verified request; never replay unknown submissions')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.action in ('install','remove','status'): operation_id(args.operation)
    if args.action not in ('install','inspect') and (args.migrate_packaged_home or args.prepare_supervisor): parser.error('install options require install')
    device=LocalDevice()
    if args.action in ('inspect','status','restore','activate'):
        ownership=Ownership.__new__(Ownership);ownership.store=checked_store(STATE)
    else: ownership=Ownership()
    coordinator=Coordinator(device,ownership)
    try:
        if args.resume:
            if args.action not in ('install','remove'):parser.error('--resume requires install or remove')
            if args.worker:result=coordinator.resume(args.operation,args.payload)
            else:result=resume_submit(args.operation,ownership,action=args.action)
        elif args.action=='install':
            if args.payload is None: parser.error('install requires a verified local payload')
            if args.worker:
                result=coordinator.install(args.operation,args.payload,migrate=args.migrate_packaged_home,prepare_supervisor=args.prepare_supervisor)
            else:
                result=submit(args.operation,args.payload,migrate=args.migrate_packaged_home,prepare_supervisor=args.prepare_supervisor,candidate=args.candidate)
        elif args.action=='remove':
            if args.worker: result=coordinator.remove(args.operation)
            else:
                if args.payload is None: parser.error('remove requires a verified local payload')
                result=submit(args.operation,args.payload,action='remove',candidate=args.candidate)
        elif args.action=='status':
            result=request_status(args.operation,ownership.store)
            result=dict(result,**continuation_status(args.operation,ownership.store))
            if args.verify_current:
                result=dict(result,current=False)
                if result['state']=='complete':
                    try:result['current']=device.validate_completion(result['action'],result.get('lease'))
                    except (OSError,ValueError,RuntimeError,KeyError):pass
        elif args.action=='inspect':
            inspected=device.inspect()
            result=dict(operation=None,stage='inspect',state=inspected['state'],code='inspected',installation=inspected)
            try:
                active=ownership.status()
                match=re.fullmatch(r'product-([0-9a-f]{32})\.json',active['journal']) if active and active['owner']=='product' and not active['terminal'] else None
                result['active_operation']=dict(request_status(match.group(1),ownership.store),**continuation_status(match.group(1),ownership.store)) if match else None
            except (OSError,ValueError):result['active_operation']=None
            if args.payload:
                result['candidate_sha256']=candidate_digest(args.payload,_verified_payload(args.payload,args.prepare_supervisor))
        elif args.action=='activate':result=dict(operation=None,stage='activate',state='complete',code='activated',result=device.activate())
        else: result=dict(operation=None,stage='restore',state='complete',code='restored',result=coordinator.restore())
    except Exception as error:
        device.log(error)
        result=dict(operation=args.operation,stage='blocked',state='recovery_required',code='operation_requires_recovery',home_changed=False)
        if args.action in ('install','remove') and not isinstance(error,Busy):
            result['action']=args.action
            if _optional_record(ownership.store,'request-'+args.operation) is None:
                ownership.store.write('request-'+args.operation,result)
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__': main()
