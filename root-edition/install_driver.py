#!/usr/bin/env python3
"""Shared Root product lifecycle. Package journals retain terminal evidence.

Request IDs are data, never commands. A repeated request only reads its durable
record; even a dead worker cannot authorize replay of an uncertain submission.
"""
import re

from installation import (Busy, Ownership, _optional_record, pending_journals, read_journal,
                          TV_INSTALLER, TV_APPROVAL, TV_APPROVAL_TOKEN, setup_activation_lock,
                          setup_activation_token, cancel_setup_activation)


def operation_id(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):
        raise ValueError('invalid_operation_uuid')
    return value


def homebrew_removal_result(state, stage, code, *, current=False, restart_required=False, can_resume=False):
    return dict(action='remove', state=state, stage=stage, code=code, current=current,
                restart_required=restart_required, can_resume=can_resume)


def cleanup_probe_details(value):
    """Revalidate the fixed child diagnostic; never treat it as recovery proof."""
    if not isinstance(value,dict):return {}
    names=('ValueError','RuntimeError','OSError','PermissionError','FileNotFoundError',
           'FileExistsError','CalledProcessError','TimeoutExpired','TimeoutError','TypeError','KeyError','unknown')
    if value.get('exception_type') not in names:return {}
    frames=value.get('frames',[])
    if not isinstance(frames,list) or len(frames)>8:return {}
    files=('deploy.py','installation.py','c1_gate.py','c1_keyfilter.py','package_data.py',
           'python_binding.py','observed_install.py','provision.py','store.py')
    result={'exception_type':value['exception_type'],'frames':[{'file':frame['file'],'line':frame['line']}
        for frame in frames if isinstance(frame,dict) and frame.get('file') in files
        and type(frame.get('line')) is int and 1<=frame['line']<=10000]}
    for key,low,high in (('errno',0,4095),('exit_status',-255,255)):
        number=value.get(key)
        if type(number) is int and low<=number<=high:result[key]=number
    reason=value.get('native_reason')
    if reason in ('effect_busy','ui_release_failed'):
        result['native_reason']=reason
        check=value.get('restore_check')
        if reason=='ui_release_failed' and check in ('native-stop-unverified','stock-foreground-unverified',
                'stock-surface-unverified','stock-routing-unverified'):
            result['restore_check']=check
    return result


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
            'legacy-lockdown','registration-restore','legacy-permissions','home-readback','boot-identity','private-inventory'):result['cleanup_step']=step
    from updater.luna import summary
    if getattr(error,'package_rejected',False) is True:
        result['package_rejected']=True
    detail=summary(getattr(error,'luna',None))
    if detail:result['luna']=detail
    probe=cleanup_probe_details(getattr(error,'cleanup_probe',None))
    if probe:result['cleanup_probe']=probe
    from deploy import install_failure_details
    detail=install_failure_details(getattr(error,'root_driver',None))
    if detail:result['root_driver']=detail
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
    import os
    from installation import retire_product_staging
    from updater.store import Store, prune_update_caches
    from install_device import UPDATER, SUPERVISOR

    def prune(stable):
        # Exact product readback can seed baselines without an OTA journal.
        peers = [Store(path, uid=store.uid) for path in (UPDATER, SUPERVISOR) if os.path.lexists(path)]
        if peers and stable():
            prune_update_caches(peers, product_complete=True)

    return retire_product_staging(store, identifier, ownership, after=prune)

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

    def activation_status(self, record, verify_current):
        """Report the original attempt without issuing another enable or launch."""
        if record.get('tv_activation') not in (True, TV_INSTALLER):
            return record
        identifier = operation_id(record['operation'])
        outcome = dict(state='unverified', launch_requested=False, completed=False)
        try:
            attempt = self.store.read('activation-' + identifier) or {}
            bound = (record.get('lease') is not None and attempt.get('operation') == identifier
                     and attempt.get('lease') == record['lease'])
            if bound:
                outcome['launch_requested'] = attempt.get('launch_requested') is True
                outcome['completed'] = attempt.get('state') == 'active' and outcome['launch_requested']
            if outcome['completed']:
                # A new boot may legitimately assign a new intent token. Keep the
                # original completion while making no claim about today's routing.
                outcome['state'] = 'finished'
            complete = record.get('state') == 'complete' and record.get('stage') == 'complete'
            owner = self.ownership.status() if complete else None
            if complete and record.get('lease') and owner and owner['id'] != record['lease']:
                outcome['state'] = 'superseded'
                return dict(record, activation=outcome)
            approval = self.store.read(TV_APPROVAL) or {}
            if (approval.get('operation') != identifier or approval.get('issuer') != TV_INSTALLER
                    or approval.get('candidate_sha256') != record.get('candidate_sha256')
                    or not approval.get('token') or self.store.read(TV_APPROVAL_TOKEN) != approval['token']):
                outcome['state'] = 'cancelled'
            elif record.get('state') == 'pending':
                outcome['state'] = 'pending'
            elif complete and bound and owner:
                if (attempt.get('state') in ('ready', 'claimed')
                        and self.device.setup_worker_live(self.store, identifier, attempt.get('worker'))):
                    # The worker can still compensate a failed launch. Its own
                    # live intermediate route is never a terminal startup result.
                    outcome['state'] = 'pending'
                    if owner['terminal'] is False:
                        return dict(record, state='pending', stage='readback', activation=outcome)
                elif (attempt.get('state') in ('claimed', 'active') and verify_current
                        and record.get('current') is True and self.device.setup_activation_active(identifier)
                        and self.ownership.status() == owner and self.store.read(TV_APPROVAL) == approval
                        and self.store.read(TV_APPROVAL_TOKEN) == approval['token']):
                    outcome['state'] = 'active'
        except (OSError, ValueError, RuntimeError, AttributeError, TypeError, KeyError):
            pass
        return dict(record, activation=outcome)

    def _clean_record(self, lease, *, for_install_inspection=False):
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
        if for_install_inspection and isinstance(record.get('routes'),dict) and record['routes'].get('mode')=='stock-compositor':
            if self.device.verify_clean(record, check_routes=False) is not True:raise Busy()
        elif self.device.verify_clean(record) is not True:raise Busy()
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

    def inspect(self, *, for_install=False):
        lease=self.ownership.status()
        if lease and lease['owner']=='clean-removal' and lease['stage']=='verified-clean':
            # Resume the same reservation only to acquire its original mutex.
            # Inspection never releases the durable old-worker fence.
            with self.ownership.operation('clean-removal',lease['journal'],resume=lease['id']) as current:
                if current!=lease:raise Busy()
                # Native install verifies live routing with its selected bundle
                # before taking over this fence. This read has no such bundle.
                self._clean_record(current, for_install_inspection=for_install)
                return dict(state='fresh',reason='verified_clean_removal',can_install=True,
                            can_maintain=False,clean_removal_verified=True)
        return self.device.inspect()

    def _cancel_setup_activation(self):
        try:
            cancel_setup_activation(self.store)
        except (OSError, ValueError) as error:
            log_failure(self.device, error)

    def restore(self):
        # Always attempt emergency restoration, including with damaged approval data.
        self._cancel_setup_activation()
        # Emergency restoration must work even while another operation is retained.
        lease=self.ownership.status()
        if lease and lease['owner']=='clean-removal' and lease['stage']=='verified-clean':
            if self.inspect().get('clean_removal_verified') is True:
                return dict(restored=True,already_removed=True)
        return self.device.restore()

    def _run(self, identifier, action, perform, *, native=False):
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
                try:
                    record=self._clean_record(previous)
                except Exception as error:
                    if not native:raise
                    # The check callback runs before the device lease changes.
                    log_failure(self.device,error)
                    raise _Recorded(dict(operation=identifier,action=action,stage='blocked',
                        state='recovery_required',code='clean-handoff-refused',home_changed=False,
                        failure=failure_summary(error))) from error
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
                if submission is not None:
                    record['candidate_sha256']=submission['candidate_sha256']
                    if 'homebrew_settings' in submission:
                        self.device.homebrew_settings = submission['homebrew_settings']
                    if submission.get('tv_activation') == TV_INSTALLER:
                        record['tv_activation'] = True
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
        return self._run(identifier,'install',perform,native=True)

    def install(self, identifier, payload, migrate=False, prepare_supervisor=False, activate_after_install=False):
        operation_id(identifier)
        if type(migrate) is not bool or type(prepare_supervisor) is not bool or type(activate_after_install) is not bool:
            raise ValueError('invalid_install_options')
        # Validate payload/runtime readiness before taking the product lease. A
        # replay never re-enters preflight, provisioning, or package submission.
        previous=self.status(identifier)
        if previous['state']!='unknown':
            if previous['action']!='install': raise ValueError('operation_action_conflict')
            return previous
        options=dict(migrate=migrate,prepare_supervisor=prepare_supervisor)
        self.device.preflight(payload,options)
        dispatch = None
        def perform(checkpoint):
            nonlocal dispatch
            state=self.device.inspect()['state']
            if state != 'fresh' and isinstance(getattr(self.device, 'homebrew_settings', None), str):
                raise ValueError('homebrew_setup_requires_fresh_installation')
            if state=='fresh':
                checkpoint('root-deploy')
                self.device.deploy(payload,options)
                if not getattr(self.device, 'single_tile', False):
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
            verified = self.device.readback()
            if (activate_after_install and state == 'fresh' and verified.get('verified') is True
                    and self.status(identifier).get('tv_activation') is True):
                try:
                    run = self.device.prepare_setup_activation(identifier, payload)
                    import os
                    self.store.write('activation-' + identifier, dict(state='ready', worker=os.getpid(),
                                     operation=identifier, lease=self.device.operation['id'], launch_requested=False))
                    dispatch = run
                except Exception as error:
                    log_failure(self.device, error)
            return verified
        record = self._run(identifier,'install',perform)
        # The public enable command must take the shared mutex itself. Its fixed
        # interpreter and retained runtime entry were verified before retiring staging.
        if dispatch and record.get('state') == 'complete' and record.get('tv_activation') is True:
            try:
                dispatch()
            except Exception as error:
                log_failure(self.device, error)
        return record

    def remove(self, identifier):
        def perform(checkpoint):
            self._cancel_setup_activation()
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

    def _homebrew_binding(self, identifier):
        binding = _optional_record(self.store, 'homebrew-removal-'+identifier)
        if binding is not None:
            if (not isinstance(binding, dict) or set(binding) != {'schema','operation','target','lease'}
                    or type(binding['schema']) is not int or binding['schema'] != 1
                    or binding['operation'] != identifier): raise Busy()
            operation_id(binding['target'])
            if binding['lease'] == '-':
                if binding['target'] != identifier: raise Busy()
            else:
                operation_id(binding['lease'])
        return binding

    def _homebrew_record(self, binding):
        record = _optional_record(self.store, 'clean-removal-'+binding['target'])
        if record is not None:
            if (not isinstance(record, dict) or type(record.get('schema')) is not int or record['schema'] != 1
                    or record.get('protocol') != 'clean-removal-v1' or record.get('operation') != binding['target']
                    or record.get('removal') != binding['operation']
                    or binding['lease'] not in ('-', record.get('lease'))): raise Busy()
            operation_id(record.get('lease'))
            final = record.get('final_fence')
            if final is not None and (operation_id(final) == record['lease']
                    or record.get('final_original_lease') != record['lease']): raise Busy()
        return record

    def _homebrew_lease(self, binding, record, lease):
        target = binding['target']
        journal = 'product-'+target+'.json'
        expected = binding['lease']
        if lease is None:
            if expected == '-' and record is None: return '-'
            raise Busy()
        if lease['owner'] == 'clean-removal' and lease['journal'] == journal and not lease['terminal']:
            if record and lease['id'] in (record['lease'], record.get('final_fence')):
                return lease['id']
            if record is None and expected == '-' and lease['stage'] == 'reserved':
                return lease['id']  # The initial reservation was written before the engine receipt.
        if lease['owner'] == 'clean-removal' and lease['stage'] != 'verified-clean': raise Busy()
        if lease['id'] != expected or record and record.get('stage') != 'requested': raise Busy()
        if lease['owner'] == 'product' and not lease['terminal']:
            if any((_optional_record(self.store, prefix+target) or {}).get('action') == 'remove'
                   for prefix in ('request-', 'submission-')): raise Busy()
        return expected

    def _homebrew_worker_active(self):
        import fcntl
        import os
        directory = self.store._directory()
        try:
            try:
                fd = os.open('worker.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError:
                return False
            try:
                self.store._check(os.fstat(fd))
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                return False
            except BlockingIOError:
                return True
            finally:
                os.close(fd)
        finally:
            os.close(directory)

    def homebrew_remove_status(self, identifier):
        return self._homebrew_remove_status(operation_id(identifier))

    def _homebrew_remove_status(self, identifier, proof=None):
        reply = homebrew_removal_result
        try:
            binding = self._homebrew_binding(identifier)
            if binding is None: return reply('unknown', 'unknown', 'unknown-operation')
            record = self._homebrew_record(binding)
            lease = self.ownership.status()
            if record and record.get('stage') == 'verified-clean':
                stale = reply('recovery_required', 'verified-clean', 'removal-not-current')
                if (not lease or record.get('final_fence') != lease['id']
                        or lease['owner'] != 'clean-removal' or lease['journal'] != 'product-'+binding['target']+'.json'
                        or lease['terminal'] or record.get('state') != 'complete' or record.get('current') is not True
                        or (record.get('result') or {}).get('private_cleanup_verified') is not True):
                    return stale
                if lease['stage'] == 'final-fence-pending':
                    return reply('recovery_required', 'private-cleanup', 'removal-pending', can_resume=True)
                if lease['stage'] != 'verified-clean': return stale
                try:
                    # A just-returned tail proved live absence while owning this fence and
                    # can have retired Python and its support files before replying.
                    if not (proof and proof.get('state') == 'complete' and proof.get('current') is True
                            and proof.get('stage') == 'verified-clean' and proof.get('operation') == binding['target']
                            and proof.get('removal') == identifier):
                        with self.ownership._lock(create=False):
                            if self.ownership.status() != lease: return stale
                            try:
                                self._clean_record(lease)
                            except Busy:
                                return stale
                except Busy:
                    return reply('pending', 'verified-clean', 'root-worker-busy')
                except (OSError, RuntimeError, ValueError, KeyError, TypeError):
                    return stale
                if self.ownership.status() != lease or self._homebrew_record(binding) != record: return stale
                return reply('complete', 'verified-clean', 'removal-verified', current=True)
            self._homebrew_lease(binding, record, lease)
            stage = record.get('stage') if record else 'requested'
            if stage not in ('requested', 'original-writers-fenced', 'controls-restored', 'package-removal',
                             'private-cleanup', 'restart-required'): raise Busy()
            if self._homebrew_worker_active():
                return reply('pending', stage, 'removal-pending')
            if stage == 'restart-required' or proof and proof.get('restart_required') is True:
                return reply('recovery_required', 'restart-required', 'restart-required',
                             restart_required=True, can_resume=True)
            failure = (proof or {}).get('cleanup_error') or (record or {}).get('cleanup_error')
            if failure not in ('root-access-required', 'root-worker-busy', 'removal-failed', 'cleanup-check-failed'):
                failure = 'removal-pending' if stage == 'requested' else 'cleanup-check-failed'
            return reply('recovery_required', stage, failure, can_resume=True)
        except Busy:
            return reply('recovery_required', 'blocked', 'ownership-conflict')
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            log_failure(self.device, error)
            return reply('recovery_required', 'blocked', 'cleanup-check-failed')

    def homebrew_remove(self, identifier, payload):
        """Submit or explicitly continue the browser's original, bound removal."""
        from pathlib import Path
        import os
        from clean_removal import boot_format, verified_restart
        from install_device import PRIVATE_TEMP, support_stage_path

        identifier = operation_id(identifier)
        reply = homebrew_removal_result
        try:
            # Completed IDs take the read-only route even if their previous support
            # and interpreter have already been retired by the cleanup tail.
            proof = None
            binding = self._homebrew_binding(identifier)
            if binding:
                status = self.homebrew_remove_status(identifier)
                if not status['can_resume']: return status
            with self.store.lock(blocking=False):
                binding = self._homebrew_binding(identifier)
                if binding is None:
                    lease = self.ownership.status()
                    target = self.removal_target(identifier)
                    if (self.ownership.status() != lease or target['target_removal'] is not None
                            or lease and lease['owner'] == 'clean-removal' and lease['stage'] != 'verified-clean'):
                        raise Busy()
                    binding = dict(schema=1, operation=identifier, target=target['target_operation'],
                                   lease=target['target_lease'] or '-')
                    if _optional_record(self.store, 'clean-removal-'+binding['target']) is not None: raise Busy()
                    fresh = True
                    record = None
                else:
                    fresh = False
                    record = self._homebrew_record(binding)
                lease = self.ownership.status()
                expected = self._homebrew_lease(binding, record, lease)
                if not (record and record.get('stage') == 'verified-clean' and lease['stage'] != 'final-fence-pending'):
                    payload = Path(payload)
                    if payload.parent != PRIVATE_TEMP or not support_stage_path(payload, 'product'):
                        raise ValueError('invalid_cleanup_support_stage')
                    directory = self.store._walk(str(payload))
                    try:
                        info = os.fstat(directory)
                        if info.st_uid != self.store.uid or info.st_mode & 0o777 != 0o700:
                            raise ValueError('unsafe_cleanup_support_stage')
                        if set(os.listdir(directory)) != {'root', 'root-updater'}:
                            raise ValueError('invalid_cleanup_support_stage')
                    finally:
                        os.close(directory)
                    self.device.preflight(payload, dict(migrate=False, prepare_supervisor=False), product=False)
                    if fresh: self.store.write('homebrew-removal-'+identifier, binding)
                    baseline = (record or {}).get('cleanup_boot_id')
                    if not (record and record.get('stage') == 'restart-required' and not verified_restart(record)
                            and boot_format(baseline) == 'session' and self.device.boot_id() == baseline):
                        proof = self._clean_remove_locked(binding['target'], identifier, expected)
            return self._homebrew_remove_status(identifier, proof)
        except Busy:
            return reply('recovery_required', 'blocked', 'ownership-conflict')
        except BlockingIOError:
            return reply('pending', 'requested', 'root-worker-busy')
        except Exception as error:
            log_failure(self.device, error)
            return reply('recovery_required', 'blocked', cleanup_failure(error))

    def clean_remove(self, identifier, intent=None, expected_lease=None):
        """Explicit desired absence, distinct from an old unknown installation."""
        identifier = operation_id(identifier)
        intent=operation_id(intent if intent is not None else identifier)
        with self.store.lock(blocking=False):
            return self._clean_remove_locked(identifier, intent, expected_lease)

    def _clean_remove_locked(self, identifier, intent, expected_lease):
        name = 'clean-removal-'+identifier
        with self.ownership.removal(identifier,expected=expected_lease) as (lease, original_lease):
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
                elif lease['owner']=='system-replace':
                    if not lease['terminal'] or lease['stage']!='complete' or lease['journal']!='system-replacement.json':
                        raise Busy()
                    replacement=_optional_record(self.store,'system-replacement')
                    if (not isinstance(replacement,dict) or replacement.get('schema')!=1
                            or replacement.get('id')!=lease['id'] or replacement.get('stage')!='complete'
                            or any(not isinstance(replacement.get(field),str) or not re.fullmatch('[a-f0-9]{64}',replacement[field])
                                   for field in ('bundle_sha256','source_sha256','baseline_sha256'))):
                        raise Busy()
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
            self._cancel_setup_activation()
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
            def observed(**fields):
                evidence = getattr(self.device, 'removal_evidence', None)
                if type(evidence) is dict:
                    fields['removal_evidence'] = evidence
                return dict(record, **fields)
            try:
                record.pop('cleanup_error',None)
                if record['stage']=='verified-clean':record.pop('runtime_cleanup',None)
                record['result'] = self.device.clean_remove(record, save)
                if record['result'].get('restart_required'):
                    record.update(stage='restart-required',reason='restart-required',current=False)
                    self.store.write(name,record)
                    return observed()
                from clean_removal import compact_audit
                compact_audit(record,self.store)
                self.store.write(name,record)
                if hasattr(self.device,'finish_clean_tail'):
                    tail=self.device.finish_clean_tail(record)
                    if tail is not None:return observed(**tail)
                if self.device.verify_clean(record) is not True: raise ValueError('clean_readback_unverified')
                if hasattr(self.device,'retire_current_support'):self.device.retire_current_support()
                self._finish_clean(record,lease)
            except Exception as error:
                log_failure(self.device,error)
                if getattr(self.device,'cleanup_tail_started',False):
                    # The independent child owns this receipt after interpreter
                    # retirement starts. Parent errors cannot overwrite its proof.
                    return observed(state='recovery_required',current=False,reason='private-cleanup-incomplete')
                if record.get('cleanup_error') != 'removal-failed':
                    record['last_failure']=dict(failure_summary(error),stage=record['stage'])
                    record.setdefault('failure',record['last_failure'])
                    record.setdefault('cleanup_error',cleanup_failure(error))
                reasons={'requested':'original-writer-active','original-writers-fenced':'controls-unverified',
                         'controls-restored':'controls-unverified','package-removal':'removal-terminal-unknown',
                         'private-cleanup':'private-cleanup-incomplete','verified-clean':'ownership-conflict','restart-required':'restart-required'}
                record.update(state='recovery_required',current=False,reason=reasons[record['stage']])
                self.store.write(name,record)
            return observed()


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
                    or reviewed_candidate(payload,_verified_payload(payload,options['prepare_supervisor']),submission.get('homebrew_settings'))!=submission.get('candidate_sha256')):
                raise ValueError('original_candidate_changed')
        original_binding = dict(candidate_sha256=submission.get('candidate_sha256'))
        if submission.get('tv_activation') == TV_INSTALLER:
            # A continued package request still owes an activation outcome. Recovery
            # never grants its worker permission to reissue the original enable.
            original_binding['tv_activation'] = True
        if previous['state']=='unknown' or (not previous.get('lease') and previous.get('stage')=='blocked'):
            current=self.ownership.status()
            journal='product-'+identifier+'.json'
            if current is not None and current['owner']=='product' and current['journal']==journal:
                if current['terminal']:raise ValueError('completed_request_record_required')
                # The lease itself durably names the request before its first
                # checkpoint. Effects are forbidden until that checkpoint exists.
                with self.ownership.operation('product',journal,resume=current['id']) as lease:
                    if self.status(identifier)['state']=='unknown' or not self.status(identifier).get('lease'):
                        self.store.write('request-'+identifier,dict(operation=identifier,lease=lease['id'],action=submission['action'],stage='reserved',state='pending',code='operation_pending',home_changed=False,**original_binding))
                previous=self.status(identifier)
            elif previous['state']!='unknown':
                # A blocked record without a reservation is a proved failure
                # before the kernel's first checkpoint, not a package attempt.
                with self.ownership.operation('product',journal,check=lambda:pending_journals('product',self.read)) as lease:
                    self.store.write('request-'+identifier,dict(operation=identifier,lease=lease['id'],action=submission['action'],stage='reserved',state='pending',code='operation_pending',home_changed=False,**original_binding))
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
                if reviewed_candidate(payload,_verified_payload(payload,options['prepare_supervisor']),submission.get('homebrew_settings'))!=submission.get('candidate_sha256'):
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


def reviewed_candidate(payload, inventories, settings=None):
    digest = candidate_digest(payload, inventories)
    if settings is None:
        return digest
    if settings != 'absent' and (not isinstance(settings, str) or not re.fullmatch('[a-f0-9]{64}', settings)):
        raise ValueError('invalid_homebrew_settings_binding')
    import hashlib
    return hashlib.sha256(('homebrew-setup-v1:' + digest + ':' + settings).encode()).hexdigest()


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


def submit(identifier, payload, migrate=False, prepare_supervisor=False, action='install', candidate=None, ownership=None, activate_after_install=False, homebrew_setup=False):
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
    if type(activate_after_install) is not bool or activate_after_install and (action != 'install' or not candidate):
        raise ValueError('invalid_setup_activation_request')
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
        token = setup_activation_token(store) if activate_after_install else None
        settings = None
        if homebrew_setup:
            if action != 'install' or not activate_after_install or not candidate:
                raise ValueError('invalid_homebrew_setup')
            from deploy import homebrew_migration
            prepared, settings = homebrew_migration()
            migrate = prepared is not None
            del prepared
            prepare_supervisor = True
        inventories=_verified_payload(payload,prepare_supervisor)
        actual_candidate=reviewed_candidate(payload,inventories,settings)
        if candidate is not None and candidate!=actual_candidate: raise ValueError('reviewed_candidate_changed')
        device=LocalDevice();device.preflight(payload,dict(migrate=migrate,prepare_supervisor=prepare_supervisor),product=action=='install')
        receipt=dict(operation=identifier,stage='preparing',state='pending',code='operation_pending',action=action,home_changed=False,candidate_sha256=actual_candidate,options=dict(migrate=migrate,prepare_supervisor=prepare_supervisor),worker_sha256=hashlib.sha256((__import__('pathlib').Path(payload)/'root-updater/bundle.json').read_bytes()).hexdigest(),root_binding=root_review_binding(payload,inventories),root_static={n:d for n,d in inventories['root']['files'].items() if n not in (inventories['root'].get('package'),'release.json','SHA256SUMS')})
        if settings is not None:
            receipt['homebrew_settings'] = settings
        if activate_after_install:
            receipt['tv_activation'] = TV_INSTALLER
            receipt['tv_activation_token'] = token
            with setup_activation_lock(store):
                if store.read(TV_APPROVAL_TOKEN) == token:
                    store.write(TV_APPROVAL, dict(issuer=TV_INSTALLER, operation=identifier,
                                                 candidate_sha256=actual_candidate, token=token))
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
            if reviewed_candidate(root,inventories,settings)!=actual_candidate: raise ValueError('worker_source_changed')
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
        if activate_after_install: args.append('--activate-after-install')
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



def setup_public_result(record):
    if not isinstance(record, dict) or record.get('tv_activation') not in (True, TV_INSTALLER):
        return record
    # The detached submission can include a full staging inventory. Expose only
    # progress and evidence to HBC, whose stdout is bounded at 64 KiB.
    fields = ('operation', 'action', 'stage', 'state', 'code', 'candidate_sha256', 'home_changed',
              'current', 'can_resume', 'resume_reason', 'result', 'activation', 'failure')
    return {field: record[field] for field in fields if field in record}


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
                or reviewed_candidate(snapshot,_verified_payload(snapshot,options['prepare_supervisor']),submission.get('homebrew_settings'))!=submission.get('candidate_sha256')):return result
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
    import subprocess
    from pathlib import Path
    from install_device import LocalDevice, checked_store, support_stage_path
    from installation import STATE
    parser=argparse.ArgumentParser(description=__doc__)
    homebrew_removal = ('homebrew-remove', 'homebrew-remove-status')
    parser.add_argument('action',choices=('inspect','install','native-install','status','restore','remove','activate',
                                          'clean-remove','clean-status','clean-target',*homebrew_removal))
    parser.add_argument('--operation')
    parser.add_argument('--payload',type=Path)
    parser.add_argument('--retire-stage',action='append',default=[])
    parser.add_argument('--helper-fence',help=argparse.SUPPRESS)
    parser.add_argument('--removal-intent',help=argparse.SUPPRESS)
    parser.add_argument('--removal-lease',help=argparse.SUPPRESS)
    parser.add_argument('--candidate',help='SHA-256 of the reviewed component bundle manifests')
    parser.add_argument('--migrate-packaged-home',action='store_true')
    parser.add_argument('--prepare-supervisor',action='store_true')
    parser.add_argument('--activate-after-install',action='store_true')
    parser.add_argument('--verify-current',action='store_true',help='Read current completion proof without replay')
    parser.add_argument('--homebrew-setup',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--for-install',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--resume',action='store_true',help='Explicitly continue the original verified request; never replay unknown submissions')
    parser.add_argument('--final-readback-only',action='store_true',help='Revalidate the final readback under the original lease; no package replay')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--submission-parent',type=int,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.action in homebrew_removal:
        if (args.operation is None or (args.payload is not None) != (args.action == 'homebrew-remove')
                or any(value is not None and value is not False and value != [] for key,value in vars(args).items()
                       if key not in ('action','operation','payload'))):
            parser.error('Homebrew removal requires --operation and only submission accepts --payload')
    if args.activate_after_install and (args.action != 'install' or args.resume):parser.error('--activate-after-install requires a fresh install')
    if args.homebrew_setup and (args.action not in ('install','inspect') or args.worker or args.resume
                                or not args.payload or args.action == 'install' and not args.activate_after_install):
        parser.error('--homebrew-setup requires a first Homebrew setup inspection or submission')
    if args.for_install and args.action!='inspect':parser.error('--for-install requires inspect')
    if args.final_readback_only and (not args.resume or args.action!='install'):
        parser.error('--final-readback-only requires install --resume')
    if args.action in ('install','native-install','remove','status','clean-remove','clean-status','clean-target'): operation_id(args.operation)
    if args.action not in ('install','inspect') and (args.migrate_packaged_home or args.prepare_supervisor): parser.error('install options require install')
    if args.submission_parent is not None:
        if not args.worker or args.action not in ('install','remove') or args.submission_parent<=1:parser.error('invalid submission parent')
        wait_submission_parent(args.submission_parent)
    device=LocalDevice()
    if args.action in homebrew_removal:
        try:
            if args.action == 'homebrew-remove':
                result = Coordinator(device).homebrew_remove(operation_id(args.operation), args.payload)
            else:
                result = Coordinator(device, Ownership(checked_store(STATE))).homebrew_remove_status(args.operation)
        except Exception as error:
            log_failure(device,error)
            result = homebrew_removal_result('recovery_required','blocked',cleanup_failure(error))
        print(json.dumps(result,sort_keys=True),flush=True)
        return
    if args.action in ('inspect','status','restore','activate','clean-status','clean-target'):
        ownership=Ownership.__new__(Ownership);ownership.store=checked_store(STATE)
    else: ownership=Ownership()
    coordinator=Coordinator(device,ownership)
    try:
        if args.action=='clean-target':
            result=coordinator.removal_target(args.operation)
        elif args.action=='clean-remove':
            if args.payload is None:parser.error('clean-remove requires current verified support')
            if any(not support_stage_path(path,'product') for path in args.retire_stage):
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
                result=coordinator.install(args.operation,args.payload,migrate=args.migrate_packaged_home,prepare_supervisor=args.prepare_supervisor,activate_after_install=args.activate_after_install)
            else:
                result=submit(args.operation,args.payload,migrate=args.migrate_packaged_home,prepare_supervisor=args.prepare_supervisor,candidate=args.candidate,activate_after_install=args.activate_after_install,homebrew_setup=args.homebrew_setup)
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
            result=coordinator.activation_status(result,args.verify_current)
        elif args.action=='inspect':
            inspected=coordinator.inspect(for_install=True) if args.for_install else coordinator.inspect()
            result=dict(operation=None,stage='inspect',state=inspected['state'],code='inspected',installation=inspected)
            try:
                active=ownership.status()
                match=re.fullmatch(r'product-([0-9a-f]{32})\.json',active['journal']) if active and active['owner']=='product' and not active['terminal'] else None
                result['active_operation']=dict(request_status(match.group(1),ownership.store),**continuation_status(match.group(1),ownership.store)) if match else None
            except (OSError,ValueError):result['active_operation']=None
            if args.payload:
                # Maintenance reviews the removal closure. The optional supervisor
                # bundle is an install input only; submit still verifies the digest.
                fresh = inspected['state'] == 'fresh'
                prepare_supervisor = fresh and (args.prepare_supervisor or args.homebrew_setup)
                settings = None
                if args.homebrew_setup and fresh and result['active_operation'] is None:
                    from deploy import homebrew_migration
                    prepared, settings = homebrew_migration()
                    inspected['migrate_available'] = prepared is not None
                result['candidate_sha256']=reviewed_candidate(args.payload,_verified_payload(args.payload,prepare_supervisor),settings)
        elif args.action=='activate':result=dict(operation=None,stage='activate',state='complete',code='activated',result=device.activate())
        else: result=dict(operation=None,stage='restore',state='complete',code='restored',result=coordinator.restore())
    except Exception as error:
        device.log(error)
        result=dict(operation=args.operation,stage='blocked',state='recovery_required',code='operation_requires_recovery',home_changed=False)
        if args.action=='inspect':
            detail=failure_summary(error)
            checks=('restart_required', 'support_stage_remains', 'live_original_worker',
                  'project_apps_remain', 'restored_routes_changed', 'startup_remains',
                  'owned_registration_remains', 'no_root_private_cleanup_required',
                  'private_members_remain', 'owned_activity_remains', 'owned_input_registration_remains')
            if type(error) is ValueError and len(error.args)==1 and error.args[0] in checks:
                detail['inspect_check']=error.args[0]
            if (isinstance(error, subprocess.CalledProcessError)
                    and isinstance(error.cmd, list) and len(error.cmd)>=3
                    and error.cmd[0]=='/usr/bin/node'
                    and isinstance(error.cmd[1], str) and error.cmd[1].endswith('/cleanup_tail.js')
                    and error.cmd[2]=='stock-proof'):
                for check in ('route-changed', 'original-removal-required', 'different-removal-intent',
                              'unsafe-cleanup-directory', 'unsafe-cleanup-member', 'cleanup-guard-failed'):
                    if error.stderr==('CYTV_CLEAN_TAIL: '+check+'\n').encode():
                        detail['inspect_check']=check
                        break
            result['failure']=detail
        if args.action=='inspect' and isinstance(error,ValueError) and error.args in (('support_stage_remains',),('live_original_worker',)):
            result['reason']='restart-required'
        if args.action=='inspect' and isinstance(error,ValueError) and error.args==('project_apps_remain',):
            result['reason']='project-apps-remain'
        if args.action=='clean-remove':result['cleanup_error']=cleanup_failure(error)
        if args.action in ('install','remove') and not isinstance(error,Busy):
            result['action']=args.action
            if _optional_record(ownership.store,'request-'+args.operation) is None:
                ownership.store.write('request-'+args.operation,result)
    if result.get('active_operation'):
        result['active_operation'] = setup_public_result(result['active_operation'])
    print(json.dumps(setup_public_result(result),sort_keys=True),flush=True)


if __name__=='__main__': main()
