"""Shared, conservative installation inspection and durable operation ownership.

The ownership receipt provides exclusion only. Component journals remain the
source of truth; a closed file descriptor or package readback is never success.
"""
from contextlib import ExitStack, contextmanager
import fcntl
import os
from pathlib import Path
import re
import uuid

try:
    from updater.store import Store
except ImportError:
    from system_updater.support.store import Store

STATE = Path('/var/lib/clean-your-tv-installation')
FIELDS = {'supported', 'packages_match', 'receipts_match', 'pending', 'retained',
          'complete', 'migration_supported'}
COMPONENTS = ('root', 'root-updater', 'system-updater')


def classify(snapshot):
    if (not isinstance(snapshot, dict) or set(snapshot) != FIELDS
            or any(type(value) is not bool for value in snapshot.values())):
        state, reason = 'conflict', 'invalid_snapshot'
    elif not snapshot['supported']:
        state, reason = 'unsupported', 'unsupported_device'
    elif snapshot['pending'] or snapshot['retained']:
        state, reason = 'recovery_required', 'retained_operation'
    elif all(snapshot[key] for key in ('packages_match', 'receipts_match', 'complete')):
        state, reason = 'installed', 'verified_components'
    elif snapshot['migration_supported']:
        state, reason = 'migration_required', 'supported_migration'
    elif any(snapshot[key] for key in ('packages_match', 'receipts_match', 'complete')):
        state, reason = 'conflict', 'component_mismatch'
    else:
        state, reason = 'fresh', 'no_installation'
    return dict(state=state, reason=reason, can_install=state == 'fresh', can_maintain=state == 'installed')


def snapshot(supported, observe):
    """Combine fixed component observers; unknown protocols fail closed.

    Each observer verifies package files, runtime bindings and its own receipts.
    No version-only observation can establish a complete installation.
    """
    observations = []
    for name in COMPONENTS:
        try:
            value = observe(name)
            keys = (FIELDS - {'supported'}) | {'present'}
            if set(value) != keys or any(type(v) is not bool for v in value.values()):
                raise ValueError('unknown observation')
            if not value['present'] and any(value[key] for key in keys - {'present'}):
                raise ValueError('inconsistent observation')
        except (OSError, ValueError, TypeError, KeyError, ImportError):
            value = dict(present=True, packages_match=False, receipts_match=False,
                         pending=False, retained=True, complete=False, migration_supported=False)
        if name != 'system-updater' or value['present']:
            observations.append(value)
    present = any(v['present'] for v in observations)
    result = dict(supported=supported,
                  packages_match=all(v['packages_match'] for v in observations),
                  receipts_match=all(v['receipts_match'] for v in observations),
                  complete=all(v['complete'] for v in observations),
                  pending=any(v['pending'] for v in observations),
                  retained=any(v['retained'] for v in observations),
                  migration_supported=present and all(v['migration_supported'] for v in observations))
    # Partial installations must not collapse to the clean-device booleans.
    if present and not any(result[k] for k in ('packages_match','receipts_match','complete','migration_supported')):
        result['retained'] = True
    return result


class Busy(RuntimeError):
    def __init__(self):
        super().__init__('installation_operation_retained')


def _optional_record(store, name):
    """Recognize only checked-traversal ENOENT, preserving every unsafe error."""
    try:
        return store.read(name)
    except FileNotFoundError:
        return None
    except ValueError as error:
        # Store._walk validates each ancestor before opening the next one and
        # preserves the original OSError as its direct cause. A symlink,
        # ownership/permission failure or corrupt receipt is not this case.
        if error.args == ('unsafe store path',) and isinstance(error.__cause__, FileNotFoundError):
            return None
        raise


def _fence_store(path, uid):
    store=Store.__new__(Store)
    store.root,store.uid=str(path),uid
    return store


@contextmanager
def component_locks(roots, uid):
    """Keep original component lock inodes throughout restoration and cleanup."""
    with ExitStack() as stack:
        for index, root in enumerate(roots):
            if not os.path.lexists(root): continue
            store=Store(root,uid=uid)
            directory=store._directory();stack.callback(os.close,directory)
            for name in (('provision.lock',) if index==0 else ('daemon.lock','worker.lock')):
                fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=directory)
                stack.callback(os.close,fd);store._check(os.fstat(fd))
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def archive_component_fences(store, record, successor, roots, require_cancelled=False):
    """Archive only pinned fence directories while the caller holds all locks."""
    uid=store.uid
    archive=Path(store.root)/('component-fences-'+record['operation'])
    archive.mkdir(mode=0o700,exist_ok=True)
    os.close(_fence_store(archive,uid)._directory())
    key='component-fences-plan-'+record['operation']
    plan=_optional_record(store,key)
    binding=dict(operation=record['operation'],lease=record['lease'],successor=successor)
    if plan is None:
        if any(archive.iterdir()):raise ValueError('component_fence_conflict')
        entries={}
        for root in roots:
            info=root.lstat() if os.path.lexists(root) else None
            entries[root.name]=[info.st_dev,info.st_ino] if info else None
        plan=dict(binding,entries=entries)
        store.write(key,plan)
    if any(plan.get(k)!=v for k,v in binding.items()) or set(plan.get('entries',{}))!={root.name for root in roots}:
        raise ValueError('component_fence_conflict')
    if {entry.name for entry in archive.iterdir()}-set(plan['entries']):raise ValueError('component_fence_conflict')
    # Validate every remaining source and every previous move before the
    # first rename, allowing the same reservation to finish after a crash.
    for index,root in enumerate(roots):
        target=archive/root.name
        paths=[path for path in (root,target) if os.path.lexists(path)]
        expected=plan['entries'][root.name]
        if len(paths)!=(0 if expected is None else 1):raise ValueError('component_fence_conflict')
        for path in paths:
            info=path.lstat()
            if [info.st_dev,info.st_ino]!=expected:raise ValueError('component_fence_changed')
            os.close(_fence_store(path,uid)._directory())
            allowed={'deploy.json','provision.lock'} if index==0 else {'bootstrap.json','daemon.lock','worker.lock'}
            if {p.name for p in path.iterdir()}-allowed:raise ValueError('component_fence_changed')
            if require_cancelled:
                expected_marker=({'version':1,'app':'com.cleanyourtv.root.preview','stage':'cancellation-admitted'}
                                 if index==0 else {'phase':'cancellation-admitted'})
                marker='deploy' if index==0 else 'bootstrap'
                if _fence_store(path,uid).read(marker)!=expected_marker:raise Busy()
    for root in roots:
        if not os.path.lexists(root):continue
        sourcefd=_fence_store(root.parent,uid)._directory()
        destination=_fence_store(archive,uid)._directory()
        try:
            os.rename(root.name,root.name,src_dir_fd=sourcefd,dst_dir_fd=destination)
            os.fsync(sourcefd);os.fsync(destination)
        finally:os.close(sourcefd);os.close(destination)


def completed_no_root_fence(store, lease):
    """Authenticate the durable No-root successor and its clean predecessor."""
    match=re.fullmatch(r'no-root-([a-f0-9]{32})\.json',lease['journal'])
    if not match or lease['owner']!='no-root' or lease['stage']!='reserved' or lease['terminal']:
        raise Busy()
    binding=_optional_record(store,lease['journal'])
    if (not isinstance(binding,dict) or binding.get('schema')!=1
            or binding.get('protocol')!='no-root-root-handoff-v1'
            or binding.get('operation')!=match[1] or binding.get('lease')!=lease['id']
            or binding.get('effects_started') is not True or binding.get('completed') is not True
            or binding.get('revoked',False) is not False
            or any(not isinstance(binding.get(k),str) or not re.fullmatch(r'[a-f0-9]{64}',binding[k])
                   for k in ('plan_sha256','source_sha256'))):
        raise Busy()
    previous=binding.get('predecessor')
    if (not isinstance(previous,dict) or set(previous)!={'operation','removal','lease'}
            or any(not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{32}',value)
                   for value in previous.values()) or previous['lease']==lease['id']):
        raise Busy()
    record=_optional_record(store,'clean-removal-'+previous['operation'])
    result=record.get('result') if isinstance(record,dict) else None
    if (not isinstance(result,dict) or record.get('schema')!=1
            or record.get('protocol')!='clean-removal-v1'
            or any(record.get(k)!=previous[k] for k in ('operation','removal'))
            or record.get('final_fence')!=previous['lease']
            or not isinstance(record.get('lease'),str) or not re.fullmatch(r'[a-f0-9]{32}',record['lease'])
            or record.get('final_original_lease')!=record['lease']
            or record.get('stage')!='verified-clean' or record.get('state')!='complete'
            or record.get('current') is not True or result.get('verified_clean') is not True
            or result.get('private_cleanup_verified') is not True):
        raise Busy()
    return record


class Ownership:
    def __init__(self, store=None):
        self.store = store if store is not None else Store(STATE)

    def status(self):
        value = _optional_record(self.store,'operation')
        if value is not None:
            if (not isinstance(value, dict) or set(value) != {'schema','id','owner','journal','stage','terminal'}
                    or type(value['schema']) is not int or value['schema'] != 1 or type(value['terminal']) is not bool
                    or not isinstance(value['id'],str) or not re.fullmatch('[0-9a-f]{32}',value['id'])
                    or any(not isinstance(value[k], str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',value[k])
                           for k in ('owner','journal','stage'))):
                raise ValueError('unknown_installation_receipt')
        return value

    @contextmanager
    def operation(self, owner, journal, resume=None, check=None, handoff=None):
        directory = self.store._directory()
        fd = None
        try:
            fd = os.open('ownership.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,
                         0o600, dir_fd=directory)
            self.store._check(os.fstat(fd))
            try: fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise Busy() from None
            if check is not None: check()
            previous = self.status()
            replace = previous is not None and handoff is not None and handoff(previous) is True
            if previous and not replace and (not previous['terminal'] or resume is not None):
                if (previous['id'], previous['owner'], previous['journal']) != (resume, owner, journal):
                    raise Busy()
                record = previous
            else:
                record = dict(schema=1, id=uuid.uuid4().hex, owner=owner, journal=journal,
                              stage='reserved', terminal=False)
                # Validate identifiers before committing durable state.
                if any(not isinstance(v,str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',v)
                       for v in (owner,journal)):
                    raise ValueError('invalid_installation_owner')
                self.store.write('operation', record)
            self.fd=fd
            yield record
        finally:
            self.fd=None
            if fd is not None: os.close(fd)
            os.close(directory)

    def stage(self, record, stage, terminal=False):
        """Call only after the owning component has durably written its journal."""
        current = self.status()
        if current != record: raise Busy()
        if not isinstance(stage,str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}', stage):
            raise ValueError('invalid_installation_stage')
        record.update(stage=stage, terminal=terminal)
        self.store.write('operation', record)

    @contextmanager
    def removal(self, identifier, expected=None):
        """Transfer the existing lease under its original mutex, never bypass it.

        The permanent nonterminal exclusion is deliberate: historical workers
        treat a different owner as busy even after the requested absence is
        verified. Clean completion is recorded separately, not install success.
        """
        current = self.status()
        if expected is not None and expected!='-' and not re.fullmatch('[a-f0-9]{32}',expected):
            raise ValueError('invalid_expected_lease')
        def check():
            if expected is None:return
            actual=self.status()
            if (actual['id'] if actual else '-')!=expected:raise Busy()
        owner = current['owner'] if current else 'clean-removal'
        journal = current['journal'] if current else 'product-'+identifier+'.json'
        with self.operation(owner, journal, resume=current['id'] if current else None,check=check) as lease:
            saved = dict(lease)
            yield lease, saved


JOURNALS = {
    'deploy': (Path('/var/lib/clean-your-tv-root/deploy.json'), 'stage', {'installed-recovery-only','uninstalled-state-retained'}),
    'root-bootstrap': (Path('/var/lib/clean-your-tv-root-updater/bootstrap.json'), 'phase', {'complete'}),
    'root-update': (Path('/var/lib/clean-your-tv-root-updater/transaction.json'), 'phase', {'complete','rolled-back','aborted'}),
    'system-bootstrap': (Path('/var/lib/clean-your-tv-system-updater/bootstrap.json'), 'phase', {'complete'}),
    'system-update': (Path('/var/lib/clean-your-tv-system-updater/transaction.json'), 'phase', {'complete','rolled-back','aborted'}),
}


def read_journal(path):
    """Read through the existing checked store without creating absent state."""
    store = Store.__new__(Store)
    store.root, store.uid = str(path.parent), 0
    return _optional_record(store,path.name)


def pending_journals(owner, read=read_journal):
    for other, (path, field, finished) in JOURNALS.items():
        value = read(path)
        if value is not None:
            pending = not isinstance(value,dict) or value.get(field) not in finished
            if other.endswith('-update') and isinstance(value,dict):
                pending = pending or value.get('homeResumePhase') != value.get(field)
            if pending and other != owner: raise Busy()


@contextmanager
def device_operation(owner, recovery=False, ownership=None, read=read_journal, check=None, handoff=None):
    """Short mutation lock plus durable reservation across asynchronous workers.

    Same-component continuation is authorized by the fixed CLI operation, while
    foreign journals always prevent a new installation or update. Recovery may
    continue the recorded owner; it never bypasses another component's journal.
    """
    ownership = ownership if ownership is not None else Ownership()
    path, field, finished = JOURNALS[owner]
    current = ownership.status()
    resume = None
    # Finished component work is a new mutation, not recovery of its old lease.
    # Reserve it nonterminal before the caller can write a new transaction.
    if recovery and current and not current['terminal'] and (current['owner'],current['journal']) == (owner,path.name):
        resume = current['id']
    admitted=None
    def eligible():
        nonlocal admitted
        if handoff is not None:
            previous=ownership.status()
            if previous is not None and handoff(previous):
                admitted=previous
        pending_journals(owner,read)
        if check is not None: check()
    with ownership.operation(owner,path.name,resume=resume,check=eligible,
                             handoff=lambda previous:previous==admitted) as record:
        yield record
        journal = read(path)
        if journal is not None:
            if not isinstance(journal,dict) or not isinstance(journal.get(field),str):
                raise ValueError('unknown_component_journal')
            stage = journal[field]
            # Updater finish restores routing and writes a separate exact receipt.
            terminal = stage in finished
            if owner.endswith('-update'):
                terminal = terminal and journal.get('homeResumePhase') == stage
            ownership.stage(record,stage,terminal=terminal)


def device_snapshot(supported=True, read=read_journal, owned_operation=None):
    """Read existing device evidence without modifying state or executing workers.

    Legacy bootstrap receipts do not inventory all installed app bytes. They
    cannot alone advertise complete-product maintenance. The shared coordinator
    must supply current descriptor/profile observers to snapshot() for that gate.
    """
    import hashlib
    import json
    from pathlib import PurePosixPath
    from python_binding import verify_binding, _read
    from package_identity import identity
    installed = Path('/media/developer/apps')
    def observe(name):
        root = Path('/var/lib/clean-your-tv-' + name)
        app = {'root':'com.cleanyourtv.root.preview', 'root-updater':'com.cleanyourtv.root.updater',
               'system-updater':'com.cleanyourtv.system.updater'}[name]
        paths = [installed/'usr/palm'/kind/identity for kind,identity in
                 (('applications',app),('services',app+'.service'),('packages',app))]
        result = dict(present=False,packages_match=False,receipts_match=False,
                      pending=False,retained=False,complete=False,migration_supported=False)
        if not os.path.lexists(root):
            if any(os.path.lexists(p) for p in paths): result.update(present=True,retained=True)
            return result
        result['present'] = True
        if name == 'root' and any(os.path.lexists(root/entry) for entry in ('home-backend.json','c1-gate','runtime/c1_gate.py','runtime/c1-home-gate')):
            # Developer-only routing is not a complete normal product contract.
            # Its own retained deploy driver supplies explicit status/removal.
            result['retained'] = True
            return result
        verify_binding(root)
        owner = {'root':'deploy','root-updater':'root-bootstrap','system-updater':'system-bootstrap'}[name]
        path, field, finished = JOURNALS[owner]
        journal = read(path)
        if not isinstance(journal,dict) or journal.get(field) not in finished:
            result['retained'] = True
            return result
        if any(not p.is_dir() or p.is_symlink() for p in paths):
            raise ValueError('incomplete_component')
        info = identity(app,installed=installed)
        if info.get('id') != app:
            raise ValueError('component_identity_mismatch')
        if name == 'root':
            receipt = read(root/'recovery-provision.json')
            if not isinstance(receipt,dict) or receipt.get('mode') != 'recovery-only':
                raise ValueError('unknown_recovery_receipt')
            files = receipt.get('files')
            if not isinstance(files,dict) or not files: raise ValueError('empty_recovery_inventory')
            for target, digest in files.items():
                target = Path(target)
                if not target.is_relative_to(root): raise ValueError('foreign_recovery_file')
                if hashlib.sha256(_read(target,4*1024*1024)).hexdigest() != digest:
                    raise ValueError('recovery_integrity_mismatch')
        else:
            receipt = read(root/'infrastructure.json')
            if not isinstance(receipt,dict) or receipt.get('schema') != 1:
                raise ValueError('unknown_infrastructure_receipt')
            if name == 'root-updater' and (receipt.get('runtime'),receipt.get('updater')) != (1,1):
                raise ValueError('unknown_updater_protocol')
            files = receipt.get('code')
            if not isinstance(files,dict) or not files: raise ValueError('empty_infrastructure_inventory')
            for relative,digest in files.items():
                path = PurePosixPath(relative)
                if path.is_absolute() or '..' in path.parts or str(path) != relative:
                    raise ValueError('foreign_infrastructure_file')
                if hashlib.sha256(_read(root/'code'/relative,4*1024*1024)).hexdigest() != digest:
                    raise ValueError('infrastructure_integrity_mismatch')
            tx = read(root/'transaction.json')
            if tx and (not isinstance(tx,dict) or tx.get('phase') not in {'complete','rolled-back','aborted'}
                       or tx.get('homeResumePhase') != tx.get('phase')):
                result['pending'] = True
        # Recognized final lifecycle receipts are evidence, but they do not
        # replace a complete current package/profile inventory after updates.
        result['receipts_match'] = True
        return result
    values = snapshot(supported,observe)
    ownership = Ownership.__new__(Ownership)
    ownership.store = Store.__new__(Store)
    ownership.store.root, ownership.store.uid = str(STATE),0
    try: operation = ownership.status()
    except FileNotFoundError: operation = None
    except ValueError:
        values['retained'] = True
        operation = None
    if operation and not operation['terminal'] and operation['id'] != owned_operation: values['pending'] = True
    return values


def terminal_install(value, application):
    """Validate an exact saved independent completion; never use package absence."""
    if not isinstance(value,dict) or value.get('completed') is not True:return False
    event=value.get('event');details=event.get('details') if isinstance(event,dict) else None
    return (isinstance(details,dict) and event.get('id')==application and type(event.get('statusValue')) is int
            and event['statusValue']==30 and event.get('returnValue') is not False and 'errorCode' not in event
            and details.get('packageId')==application and 'errorCode' not in details
            and isinstance(details.get('client'),str) and re.fullmatch(r'com.webos.lunasend-[0-9]+',details['client']) is not None
            and isinstance(details.get('ipkFile'),str) and re.fullmatch(r'/var/lib/clean-your-tv-installer/cytv-root-install-[A-Za-z0-9_-]+/package.ipk',details['ipkFile']) is not None)


def terminal_removal(value, application):
    """Saved bound-request completion, including firmware replies omitting IDs."""
    if not isinstance(value,dict) or value.get('completed') is not True:return False
    event=value.get('event');details=event.get('details') if isinstance(event,dict) else None
    return (isinstance(details,dict) and event.get('returnValue') is not False and 'errorCode' not in event
            and 'errorCode' not in details and event.get('id',application)==application
            and details.get('packageId',application)==application
            and isinstance(details.get('state'),str) and details['state'].lower() in ('removed','success'))
