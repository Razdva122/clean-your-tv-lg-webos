#!/usr/bin/env python3
"""Shared Root product lifecycle. Package journals retain terminal evidence.

Request IDs are data, never commands. A repeated request only reads its durable
record; even a dead worker cannot authorize replay of an uncertain submission.
"""
import re

from installation import Busy, Ownership, _optional_record, pending_journals, read_journal


def operation_id(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):
        raise ValueError('invalid_operation_uuid')
    return value


def failure_summary(error):
    """Fixed worker categories only; command, output and message stay private."""
    import subprocess
    name=type(error).__name__
    if name=='InstallerRuntimeMismatch':name='ValueError'
    allowed=('CalledProcessError','TimeoutExpired','ValueError','RuntimeError','OSError',
             'PermissionError','FileNotFoundError','TypeError','KeyError','TimeoutError')
    result={'exception_type':name if name in allowed else 'unknown'}
    if isinstance(error,subprocess.CalledProcessError) and type(error.returncode) is int and -255<=error.returncode<=255:
        result['exit_status']=error.returncode
    if isinstance(error,OSError) and type(error.errno) is int and 0<=error.errno<=4095:
        result['errno']=error.errno
    step=getattr(error,'cleanup_step',None)
    if isinstance(step,str) and step in ('routing-inverse','runtime-restore','provision-rollback','startup-hook',
            'legacy-lockdown','registration-restore','legacy-permissions','home-readback'):result['cleanup_step']=step
    from updater.luna import summary
    detail=summary(getattr(error,'luna',None))
    if detail:result['luna']=detail
    return result


def log_failure(device, error):
    try:
        if hasattr(device,'log'): device.log(error)
    except Exception:
        pass  # Private logging must never replace the initiating failure.


def cleanup_failure(error):
    if isinstance(error,PermissionError):return 'root-access-required'
    if isinstance(error,(Busy,BlockingIOError)) or str(error)=='live_original_worker':return 'root-worker-busy'
    if type(error).__name__=='OutcomeUnknown':return 'removal-failed'
    return 'cleanup-check-failed'


def retire_staging(store, identifier, ownership):
    """Only the completed request's matching terminal product lease may retire it.

    Historical requests without a sealed staging inventory remain inspect-only.
    The caller holds Ownership.operation, excluding other cooperative writers.
    """
    from updater.store import Store, retire_verified_files, prune_update_caches, retention_summary, retention_reason
    removed=0
    try:
        identifier=operation_id(identifier)
        request=store.read('request-'+identifier);submission=store.read('submission-'+identifier)
        lease=ownership.status()
        if (not isinstance(request,dict) or not isinstance(submission,dict) or not isinstance(lease,dict)
                or request.get('operation')!=identifier or submission.get('operation')!=identifier
                or request.get('stage')!='complete' or request.get('state')!='complete' or request.get('code')!='verified'
                or request.get('action') not in ('install','remove') or request['action']!=submission.get('action')
                or submission.get('stage')!='submitted' or lease.get('terminal') is not True or lease.get('stage')!='complete'
                or lease.get('owner')!='product' or lease.get('journal')!='product-'+identifier+'.json'
                or request.get('lease')!=lease.get('id')):
            retention_summary('staging','admission-refused');return 0
        result=request.get('result')
        if not isinstance(result,dict) or result.get('verified' if request['action']=='install' else 'removed') is not True:
            retention_summary('staging','admission-refused');return 0
        files=submission.get('staging')
        if not isinstance(files,dict) or not files:
            retention_summary('staging','missing-inventory');return 0
        if any(not isinstance(name,str) or name.split('/')[0] not in ('root','root-updater','supervisor') for name in files):
            retention_summary('staging','admission-refused');return 0
        stable=lambda: (store.read('request-'+identifier)==request and store.read('submission-'+identifier)==submission and ownership.status()==lease)
        removed=retire_verified_files(store,'request-'+identifier,files,stable)
        # Product maintenance can seed newer baselines without an OTA journal.
        # Its exact final readback and terminal lease above authorize this boundary.
        import os
        from install_device import UPDATER, SUPERVISOR
        peers=[Store(path,uid=store.uid) for path in (UPDATER,SUPERVISOR) if os.path.lexists(path)]
        if peers and stable():prune_update_caches(peers,product_complete=True)
        return removed
    except (OSError,ValueError,TypeError,KeyError) as error:
        retention_summary('staging',retention_reason(error),removed)
        return removed


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

    def _clean_record(self, lease):
        identifier=operation_id(lease['journal'][8:-5])
        record=_optional_record(self.store,'clean-removal-'+identifier)
        if (lease['journal']!='product-'+identifier+'.json' or lease['terminal']
                or not isinstance(record,dict) or record.get('schema')!=1
                or record.get('protocol')!='clean-removal-v1' or record.get('operation')!=identifier
                or not isinstance(record.get('lease'),str) or not re.fullmatch('[a-f0-9]{32}',record['lease'])
                or record.get('final_fence',record.get('lease'))!=lease['id'] or record.get('stage')!='verified-clean'
                or (record.get('final_fence') is not None and record.get('final_original_lease')!=record.get('lease'))
                or record.get('state')!='complete' or record.get('current') is not True
                or record.get('result',{}).get('private_cleanup_verified') is not True):raise Busy()
        self.device.ownership=self.ownership
        if self.device.verify_clean(record) is not True:raise Busy()
        return record

    def _finish_clean(self, record, lease):
        """Retire destructive authority before publishing successful absence."""
        import uuid
        final=record.setdefault('final_fence',uuid.uuid4().hex)
        if not isinstance(final,str) or not re.fullmatch('[a-f0-9]{32}',final) or final==record['lease']:raise Busy()
        record.update(stage='private-cleanup',state='recovery_required',current=False)
        record['final_original_lease']=record['lease']
        self.store.write('clean-removal-'+record['operation'],record)
        lease.update(id=final,stage='final-fence-pending')
        self.store.write('operation',lease)
        record.update(stage='verified-clean',state='complete',reason='removal-verified',current=True)
        self.store.write('clean-removal-'+record['operation'],record)
        self.ownership.stage(lease,'verified-clean')
        return record

    def inspect(self):
        lease=self.ownership.status()
        if lease and lease['owner']=='clean-removal' and lease['stage']=='verified-clean':
            # Resume the same reservation only to acquire its original mutex.
            # Inspection never releases the durable old-worker fence.
            with self.ownership.operation('clean-removal',lease['journal'],resume=lease['id']) as current:
                if current!=lease:raise Busy()
                self._clean_record(current)
                return dict(state='fresh',reason='verified_clean_removal',can_install=True,
                            can_maintain=False,clean_removal_verified=True)
        return self.device.inspect()

    def restore(self):
        # Emergency restoration must work even while another operation is retained.
        lease=self.ownership.status()
        if lease and lease['owner']=='clean-removal' and lease['stage']=='verified-clean':
            if self.inspect().get('clean_removal_verified') is True:
                return dict(restored=True,already_removed=True)
        return self.device.restore()

    def _run(self, identifier, action, perform):
        identifier=operation_id(identifier)
        previous=self.status(identifier)
        if previous['state']!='unknown':
            if previous['action']!=action: raise ValueError('operation_action_conflict')
            return previous
        cleaned=[]
        def check():
            existing=self.status(identifier)
            if existing['state']!='unknown': raise _Recorded(existing)
            previous=self.ownership.status()
            if action=='install' and previous and previous['owner']=='clean-removal' and previous['stage']=='verified-clean':
                old=previous['journal'][8:-5]
                if old==identifier:raise Busy()
                record=self._clean_record(previous)
                cleaned.append((previous,record))
                return
            pending_journals('product',self.read)
        try:
            with self.ownership.operation('product', 'product-'+identifier+'.json', check=check,
                    handoff=lambda previous:bool(cleaned and cleaned[0][0]==previous)) as lease:
                # Check under the lock too: two clients can race their first status.
                previous=self.status(identifier)
                if previous['state']!='unknown': return previous
                record=dict(operation=identifier,lease=lease['id'],action=action,stage='reserved',state='pending',code='operation_pending',home_changed=False)
                if cleaned:record['clean_predecessor']=cleaned[0][1]['operation']
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
                    if cleaned:self.device.prepare_clean_install(cleaned[0][1])
                    result=perform(checkpoint)
                    record.update(stage='complete',state='complete',code='verified',result=result)
                    self.store.write('request-'+identifier,record)
                    self.ownership.stage(lease,'complete',terminal=True)
                    retire_staging(self.store,identifier,self.ownership)
                except Exception as error:
                    log_failure(self.device,error)
                    # Raw details remain in private logs; retain only fixed failure categories.
                    record.setdefault('failure',failure_summary(error))
                    code='installer-runtime-mismatch' if getattr(error,'reason_code',None)=='installer-runtime-mismatch' else 'installation_requires_recovery'
                    record.update(state='recovery_required',code=code)
                    self.store.write('request-'+identifier,record)
                return record
        except _Recorded as existing:
            if existing.record['action']!=action: raise ValueError('operation_action_conflict')
            return existing.record

    def native_install(self, identifier, payload):
        """Fresh experimental install, including a verified clean predecessor.

        Reuses the product mutex/fence handoff, without installing an updater
        or replaying a recorded native request through normal product resume.
        """
        identifier=operation_id(identifier)
        previous=self.status(identifier)
        if previous['state']!='unknown':
            if previous['action']!='install':raise ValueError('operation_action_conflict')
            return previous
        self.device.preflight(payload,dict(migrate=False,prepare_supervisor=False),product=False)
        def perform(checkpoint):
            checkpoint('root-deploy')
            return self.device.native_deploy(payload)
        return self._run(identifier,'install',perform)

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
            elif state=='installed':
                self.device.require_selected_runtime(payload)
            else:
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

    def removal_target(self, identifier):
        """Read current TV ownership without changing the retained host history."""
        identifier=operation_id(identifier)
        lease=self.ownership.status()
        match=re.fullmatch(r'product-([a-f0-9]{32})\.json',lease['journal']) if lease and lease['owner'] in ('product','clean-removal') else None
        selected=match.group(1) if match else identifier
        goal=None
        if lease and lease['owner']=='clean-removal':
            record=_optional_record(self.store,'clean-removal-'+selected)
            if record is not None:
                if (record.get('schema')!=1 or record.get('protocol')!='clean-removal-v1'
                        or record.get('operation')!=selected):raise Busy()
                if record.get('final_fence')==lease['id']:
                    # A distinct user-approved Remove gets a new goal. The old
                    # completed target can only be retried as a readback.
                    if (lease['stage']=='verified-clean' and record.get('stage')=='verified-clean'
                            and record.get('state')=='complete' and record.get('current') is True):
                        selected=identifier
                    else:goal=operation_id(record.get('removal'))
                elif record.get('lease')==lease['id']:
                    goal=operation_id(record.get('removal'))
                else:raise Busy()
        return dict(operation=identifier,state='fresh',target_operation=selected,
                    target_lease=lease['id'] if lease else None,target_removal=goal)

    def clean_remove(self, identifier, intent=None, expected_lease=None):
        """Explicit desired absence, distinct from an old unknown installation."""
        identifier = operation_id(identifier)
        intent=operation_id(intent if intent is not None else identifier)
        name = 'clean-removal-'+identifier
        with self.store.lock(blocking=False), self.ownership.removal(identifier,expected=expected_lease) as (lease, original_lease):
            record = _optional_record(self.store, name)
            if (record is not None and record.get('final_fence') is not None
                    and lease['id'] in (record.get('lease'),record.get('final_fence'))):
                if (record.get('schema')!=1 or record.get('protocol')!='clean-removal-v1'
                        or record.get('operation')!=identifier or record.get('removal')!=intent
                        or record.get('final_original_lease')!=record.get('lease')
                        or lease['owner']!='clean-removal' or lease['journal']!='product-'+identifier+'.json'
                        or record.get('result',{}).get('private_cleanup_verified') is not True):raise Busy()
                self.device.operation=lease;self.device.ownership=self.ownership
                if self.device.verify_clean(record) is not True:raise Busy()
                if record.get('stage')=='verified-clean' and lease['stage']=='verified-clean' and record['final_fence']==lease['id']:return record
                if lease['stage']!='final-fence-pending' and not (lease['id']==record['lease'] and record.get('current') is False):raise Busy()
                return self._finish_clean(record,lease)
            if record is None:
                if lease['owner'] == 'clean-removal':
                    # Fresh reservation may have crashed before the first write;
                    # a different removal selector must never take it over.
                    if lease['journal'] != 'product-'+identifier+'.json':
                        match=re.fullmatch(r'product-([a-f0-9]{32})\.json',lease['journal'])
                        completed=_optional_record(self.store,'clean-removal-'+match.group(1)) if match else None
                        if (not completed or completed.get('final_fence')!=lease['id']
                                or completed.get('stage')!='verified-clean' or lease['stage']!='verified-clean'
                                or completed.get('state')!='complete' or completed.get('current') is not True
                                or intent==completed.get('removal') or identifier==completed.get('operation')):raise Busy()
                elif lease['owner'] == 'product' and lease['journal'] != 'product-'+identifier+'.json' and not lease['terminal']:
                    raise Busy()
                elif lease['owner']=='no-root':
                    if not re.fullmatch(r'no-root-[a-f0-9]{32}\.json',lease['journal']):raise Busy()
                    binding=_optional_record(self.store,lease['journal'][:-5])
                    if (not binding or binding.get('schema')!=1 or binding.get('protocol')!='no-root-root-handoff-v1'
                            or binding.get('lease')!=lease['id'] or binding.get('operation')!=lease['journal'][8:-5]
                            or not re.fullmatch('[a-f0-9]{64}',str(binding.get('plan_sha256','')))
                            or identifier==binding['operation']):raise Busy()
                elif lease['owner'] not in ('product','deploy','root-bootstrap','root-update','system-bootstrap','system-update'):
                    raise Busy()
                from installation import JOURNALS
                original_id = lease['journal'][8:-5] if lease['owner']=='product' and re.fullmatch(r'product-[a-f0-9]{32}\.json',lease['journal']) else identifier
                record = dict(schema=1, protocol='clean-removal-v1', operation=identifier,
                              removal=intent,lease=lease['id'], stage='requested', state='recovery_required',
                              reason='removal-requested', done=[], packages={},
                              original={'lease':original_lease,'operation':original_id,
                                        'request':_optional_record(self.store,'request-'+original_id),
                                        'submission':_optional_record(self.store,'submission-'+original_id),
                                        'removal':_optional_record(self.store,'removal-'+lease['id']),
                                        'components':{key:self.read(path) for key,(path,_,_) in JOURNALS.items()}})
                self.store.write(name, record)
            if (record.get('protocol') != 'clean-removal-v1' or record.get('operation') != identifier
                    or record.get('lease') != lease['id'] or record.get('removal')!=intent): raise Busy()
            # This changes no original request/submission. Every prior resume
            # compares owner+journal+lease under this same mutex and is refused.
            lease.update(owner='clean-removal', journal='product-'+identifier+'.json', terminal=False)
            self.store.write('operation', lease)
            original_id=record['original']['operation']
            if record['original']['request'] is None and _optional_record(self.store,'request-'+original_id) is None:
                self.store.write('request-'+original_id,dict(operation=original_id,action='install',lease=lease['id'],
                    stage='clean-removal-requested',state='recovery_required',code='clean_removal_requested'))
            self.device.operation=lease; self.device.ownership=self.ownership
            support=record.setdefault('support_stages',[])
            from pathlib import Path
            import os
            stages=list(getattr(self.device,'previous_stages',()))
            if getattr(self.device,'payload',None) is not None:stages.append(self.device.payload)
            for path in stages:
                path=Path(path)
                if str(path) in {item['path'] for item in support} or not os.path.lexists(path):continue
                os.close(self.store._walk(str(path)))
                info=path.lstat()
                support.append({'path':str(path),'dev':info.st_dev,'ino':info.st_ino})
            self.store.write(name,record)
            def save(stage):
                record.update(stage=stage,state='recovery_required')
                self.store.write(name,record)
                self.ownership.stage(lease,stage)
            try:
                record.pop('cleanup_error',None)
                if record['stage']=='verified-clean':record.pop('runtime_cleanup',None)
                record['result'] = self.device.clean_remove(record, save)
                if record['result'].get('restart_required'):
                    record.update(stage='restart-required',reason='restart-required',current=False)
                    self.store.write(name,record)
                    return record
                if self.device.verify_clean(record) is not True: raise ValueError('clean_readback_unverified')
                from clean_removal import compact_audit
                compact_audit(record,self.store)
                self.store.write(name,record)
                if hasattr(self.device,'finish_clean_tail'):
                    tail=self.device.finish_clean_tail(record)
                    if tail is not None:return dict(record,**tail)
                if hasattr(self.device,'retire_current_support'):self.device.retire_current_support()
                self._finish_clean(record,lease)
            except Exception as error:
                log_failure(self.device,error)
                if getattr(self.device,'cleanup_tail_started',False):
                    # The independent child owns this receipt after interpreter
                    # retirement starts. Parent errors cannot overwrite its proof.
                    return dict(record,state='recovery_required',current=False,reason='private-cleanup-incomplete')
                record['last_failure']=dict(failure_summary(error),stage=record['stage'])
                record.setdefault('failure',record['last_failure'])
                record.setdefault('cleanup_error',cleanup_failure(error))
                reasons={'requested':'original-writer-active','original-writers-fenced':'controls-unverified',
                         'controls-restored':'controls-unverified','package-removal':'removal-terminal-unknown',
                         'private-cleanup':'private-cleanup-incomplete','verified-clean':'ownership-conflict','restart-required':'restart-required'}
                record.update(state='recovery_required',current=False,reason=reasons[record['stage']])
                self.store.write(name,record)
            return record


    def resume(self, identifier, payload, final_readback_only=False):
        """Explicit continuation: same request/lease, verified snapshot, no replay."""
        identifier=operation_id(identifier)
        submission=_optional_record(self.store,'submission-'+identifier)
        if submission is None: raise ValueError('verified_worker_snapshot_required')
        options=self.device.verify_resume(payload,submission)
        previous=self.status(identifier)
        if final_readback_only and (previous.get('action')!='install' or not previous.get('lease')
                                   or previous.get('stage') not in ('readback','complete')):
            raise ValueError('package-terminal-unverified')
        if final_readback_only:
            if (previous.get('candidate_sha256')!=submission.get('candidate_sha256')
                    or candidate_digest(payload,_verified_payload(payload,options['prepare_supervisor']))!=submission.get('candidate_sha256')):
                raise ValueError('original_candidate_changed')
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
            if final_readback_only:
                if (record.get('operation')!=identifier or submission.get('operation')!=identifier
                        or record.get('action')!='install' or record.get('action')!=submission.get('action')
                        or record.get('lease')!=lease['id'] or lease['id']!=previous.get('lease')
                        or lease.get('owner')!='product' or lease.get('journal')!='product-'+identifier+'.json'
                        or record.get('candidate_sha256')!=submission.get('candidate_sha256')):
                    raise ValueError('original_product_binding_changed')
                if _optional_record(self.store,'submission-'+identifier)!=submission:
                    raise ValueError('original_candidate_changed')
                options=self.device.verify_resume(payload,submission)
                if candidate_digest(payload,_verified_payload(payload,options['prepare_supervisor']))!=submission.get('candidate_sha256'):
                    raise ValueError('original_candidate_changed')
                self.device.continuation_quiescent(payload)
                if record.get('candidate_sha256')!=previous.get('candidate_sha256'):
                    raise ValueError('original_candidate_changed')
            if final_readback_only and not self.device.continuation_ready(record,submission,self.store):
                raise ValueError('current-package-files-unverified')
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
                if final_readback_only:
                    result=self.device.readback()
                elif record['action']=='install':
                    if record.get('clean_predecessor') and record['stage']=='reserved':
                        clean=_optional_record(self.store,'clean-removal-'+operation_id(record['clean_predecessor']))
                        if not isinstance(clean,dict) or clean.get('stage')!='verified-clean':raise ValueError('clean_predecessor_required')
                        self.device.prepare_clean_install(clean)
                    result=self.device.resume_install(payload,options,record['stage'],checkpoint)
                else:
                    result=self.device.remove(checkpoint,resume=True)
                record.update(stage='complete',state='complete',code='verified',result=result)
                self.store.write('request-'+identifier,record)
                self.ownership.stage(lease,'complete',terminal=True)
                retire_staging(self.store,identifier,self.ownership)
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
            staging={}
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
                        staging[component+'/'+name]=hashlib.sha256(raw).hexdigest()
                        output.write(raw);output.flush();os.fsync(output.fileno())
                    target.chmod(0o600)
            if candidate_digest(root,inventories)!=actual_candidate: raise ValueError('worker_source_changed')
        except (OSError,ValueError):
            receipt.update(state='recovery_required',code='worker_snapshot_unavailable')
            store.write('submission-'+identifier,receipt)
            return receipt
        # Persist every directory entry from leaves through the request parent
        # before sealing the durable worker snapshot.
        from install_device import checked_store
        for directory in sorted((root,*(p for p in root.rglob('*') if p.is_dir())),key=lambda p:len(p.parts),reverse=True):
            fd=checked_store(directory,store.uid)._directory()
            try:os.fsync(fd)
            finally:os.close(fd)
        fd=store._directory()
        try:os.fsync(fd)
        finally:os.close(fd)
        receipt['staging']=staging
        receipt['stage']='submitted'
        store.write('submission-'+identifier,receipt)
        args=[sys.executable,'-B',str(root/'root-updater/install_driver.py'),action,'--operation',identifier,'--payload',str(root),'--worker','--submission-parent',str(os.getpid())]
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


def resume_submit(identifier, ownership=None, action=None, final_readback_only=False):
    import os,subprocess,sys
    from pathlib import Path
    from install_device import LocalDevice
    identifier=operation_id(identifier)
    ownership=ownership if ownership is not None else Ownership()
    if final_readback_only and continuation_status(identifier,ownership.store).get('can_resume') is not True:
        raise ValueError('final_readback_proof_required')
    completed=request_status(identifier,ownership.store)
    if not final_readback_only and completed.get('state')=='complete' and completed.get('stage')=='complete':
        if action is not None and completed.get('action')!=action:raise ValueError('operation_action_conflict')
        return completed
    submission=_optional_record(ownership.store,'submission-'+identifier)
    if submission is None:raise ValueError('verified_worker_snapshot_required')
    if action is not None and submission.get('action')!=action:raise ValueError('operation_action_conflict')
    root=Path(ownership.store.root)/('request-'+identifier)
    LocalDevice().verify_resume(root,submission)
    # Product recovery executes the current trusted coordinator; the retained
    # snapshot remains data and the original candidate, lease and ID are reused.
    worker=Path(__file__).resolve() if final_readback_only else root/'root-updater/install_driver.py'
    args=[sys.executable,'-B',str(worker),submission['action'],'--operation',identifier,'--payload',str(root),'--worker','--resume']
    if final_readback_only:args.append('--final-readback-only')
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
    result=dict(can_resume=False,resume_reason='original-request-unverified')
    directory=fd=None
    try:
        identifier=operation_id(identifier)
        owner=Ownership.__new__(Ownership);owner.store=store
        # Opening an existing checked mutex read-only never provisions absent state.
        directory=store._directory()
        fd=os.open('ownership.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        store._check(os.fstat(fd))
        result['resume_reason']='worker-not-quiescent'
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['resume_reason']='original-request-unverified'
        record=Coordinator(device,owner).status(identifier)
        lease=owner.status()
        if (lease is None or lease['terminal'] or lease['owner']!='product'
                or lease['journal']!='product-'+identifier+'.json' or record.get('lease')!=lease['id']):return result
        submission=_optional_record(store,'submission-'+identifier)
        if (not isinstance(submission,dict) or submission.get('operation')!=identifier
                or submission.get('action')!=record.get('action')):return result
        device=device if device is not None else LocalDevice()
        result['resume_reason']='original-snapshot-unverified'
        snapshot=Path(store.root)/('request-'+identifier)
        options=device.verify_resume(snapshot,submission)
        if (record.get('candidate_sha256')!=submission.get('candidate_sha256')
                or candidate_digest(snapshot,_verified_payload(snapshot,options['prepare_supervisor']))!=submission.get('candidate_sha256')):return result
        device.operation=lease;device.ownership=owner
        result['resume_reason']='worker-not-quiescent'
        device.continuation_quiescent(snapshot)
        result['resume_reason']='package-terminal-unverified'
        if record.get('action')=='install' and record.get('stage') not in ('readback','complete'):return result
        result['resume_reason']='current-package-files-unverified'
        if device.continuation_ready(record,submission,store) and owner.status()==lease:
            return dict(can_resume=True,resume_reason='original_final_readback_verified')
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):pass
    finally:
        if fd is not None:os.close(fd)
        if directory is not None:os.close(directory)
    return result


def wait_submission_parent(parent):
    """Let the exact spawning CLI exit before live-original-worker readback.

    Timing never establishes cleanliness: verify_clean still checks every process
    after this bounded drain, including a parent that has not exited.
    """
    import os,time
    deadline=time.monotonic()+2
    while os.getppid()==parent and time.monotonic()<deadline:time.sleep(0.02)


def main():
    import argparse
    import json
    from pathlib import Path
    from install_device import LocalDevice, checked_store
    from installation import STATE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','install','native-install','status','restore','remove','activate','clean-remove','clean-status','clean-target'))
    parser.add_argument('--operation')
    parser.add_argument('--payload',type=Path)
    parser.add_argument('--retire-stage',action='append',default=[])
    parser.add_argument('--helper-fence',help=argparse.SUPPRESS)
    parser.add_argument('--removal-intent',help=argparse.SUPPRESS)
    parser.add_argument('--removal-lease',help=argparse.SUPPRESS)
    parser.add_argument('--candidate',help='SHA-256 of the reviewed component bundle manifests')
    parser.add_argument('--migrate-packaged-home',action='store_true')
    parser.add_argument('--prepare-supervisor',action='store_true')
    parser.add_argument('--verify-current',action='store_true',help='Read current completion proof without replay')
    parser.add_argument('--resume',action='store_true',help='Explicitly continue the original verified request; never replay unknown submissions')
    parser.add_argument('--final-readback-only',action='store_true',help='Revalidate the final readback under the original lease; no package replay')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--submission-parent',type=int,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.final_readback_only and (not args.resume or args.action!='install'):
        parser.error('--final-readback-only requires install --resume')
    if args.action in ('install','native-install','remove','status','clean-remove','clean-status','clean-target'): operation_id(args.operation)
    if args.action not in ('install','inspect') and (args.migrate_packaged_home or args.prepare_supervisor): parser.error('install options require install')
    if args.submission_parent is not None:
        if not args.worker or args.action not in ('install','remove') or args.submission_parent<=1:parser.error('invalid submission parent')
        wait_submission_parent(args.submission_parent)
    device=LocalDevice()
    if args.action in ('inspect','status','restore','activate','clean-status','clean-target'):
        ownership=Ownership.__new__(Ownership);ownership.store=checked_store(STATE)
    else: ownership=Ownership()
    coordinator=Coordinator(device,ownership)
    try:
        if args.action=='clean-target':
            result=coordinator.removal_target(args.operation)
        elif args.action=='clean-remove':
            if args.payload is None:parser.error('clean-remove requires current verified support')
            if any(not re.fullmatch(r'/tmp/cytv-product-[a-f0-9]{32}',path) for path in args.retire_stage):
                raise ValueError('invalid_cleanup_support_stage')
            device.previous_stages=args.retire_stage
            device.helper_fence=json.loads(args.helper_fence) if args.helper_fence is not None else None
            device.preflight(args.payload,dict(migrate=False,prepare_supervisor=False),product=False)
            result=coordinator.clean_remove(args.operation,args.removal_intent,args.removal_lease)
        elif args.action=='clean-status':
            result=_optional_record(ownership.store,'clean-removal-'+args.operation)
            if result is None:result=dict(operation=args.operation,state='unknown',stage='requested')
            else:
                result=dict(result,current=False)
                if args.verify_current and result.get('stage')=='verified-clean':
                    device.ownership=ownership
                    result['current']=device.verify_clean(result)
        elif args.resume:
            if args.action not in ('install','remove'):parser.error('--resume requires install or remove')
            if args.worker:result=coordinator.resume(args.operation,args.payload,final_readback_only=args.final_readback_only)
            else:result=resume_submit(args.operation,ownership,action=args.action,final_readback_only=args.final_readback_only)
        elif args.action=='native-install':
            if args.payload is None:parser.error('native-install requires current verified support')
            result=coordinator.native_install(args.operation,args.payload)
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
            inspected=coordinator.inspect()
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
        if args.action=='inspect' and isinstance(error,ValueError) and error.args in (('support_stage_remains',),('live_original_worker',)):
            result['reason']='restart-required'
        if args.action=='inspect' and isinstance(error,ValueError) and error.args==('project_apps_remain',):
            result['reason']='project-apps-remain'
        if args.action=='clean-remove':result['cleanup_error']=cleanup_failure(error)
        if args.action in ('install','remove') and not isinstance(error,Busy):
            result['action']=args.action
            if _optional_record(ownership.store,'request-'+args.operation) is None:
                ownership.store.write('request-'+args.operation,result)
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__': main()
