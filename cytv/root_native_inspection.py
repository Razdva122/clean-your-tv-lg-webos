"""Reviewed-source, original-operation native observation. No TV writes or replay.

Internal source tool only: execute host-pinned modules from stdin, never import
retained TV code. A current admission observation is not the old failure cause
or permission to retry, activate, remove or clear a request.
"""
import hashlib
import json
from pathlib import Path
import re
import shlex
import tempfile

MODULES=('updater.store','installation','runtime.profile_plan','runtime.transport',
         'runtime.emergency_gesture','runtime.emergency_reader','runtime.c1_gate','runtime.c1_keyfilter')
PROGRAM=r'''
import fcntl,json,os,stat,sys,traceback,types
from pathlib import Path
sources=SOURCES
operation=OPERATION
for package in ('updater','runtime'):
    module=types.ModuleType(package);module.__path__=[];sys.modules[package]=module
for name,source in sources:
    module=types.ModuleType(name);module.__package__=name.rpartition('.')[0]
    module.__file__=name.replace('.','/')+'.py';sys.modules[name]=module
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    if module.__package__:setattr(sys.modules[module.__package__],name.rpartition('.')[2],module)
from updater.store import Store
from installation import Ownership
from runtime import c1_keyfilter
STATE=Path('/var/lib/clean-your-tv-installation')
ROOT=Path('/var/lib/clean-your-tv-root')

def observe():
    store=Store.__new__(Store);store.root=str(STATE);store.uid=0
    directory=store._directory();lock=None
    try:
        lock=os.open('ownership.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        store._check(os.fstat(lock));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_nlink)
        lock_identity=identity(os.fstat(lock));directory_identity=identity(os.fstat(directory))
        owner=Ownership.__new__(Ownership);owner.store=store
        lease=owner.status();request=store.read('request-'+operation)
        if (not isinstance(request,dict) or not isinstance(lease,dict)
                or request.get('operation')!=operation or request.get('action')!='install'
                or request.get('state')!='recovery_required' or request.get('stage')!='root-deploy'
                or request.get('home_changed') is not False or request.get('lease')!=lease['id']
                or lease['owner']!='product' or lease['terminal'] or lease['stage']!='root-deploy'
                or lease['journal']!='product-'+operation+'.json'):
            raise ValueError('original_operation_required')
        root=Store.__new__(Store);root.root=str(ROOT);root.uid=0
        from installation import _optional_record
        journal=_optional_record(root,'deploy')
        stages=('prepared','install-submitting','install-accepted','install-observed','payload-verified',
            'provision-apply-starting','provision-apply-complete','provision-refresh-starting',
            'provision-refresh-complete','provision-finalize-starting','provision-finalize-complete',
            'installed-recovery-only')
        stage='absent' if journal is None else journal.get('stage') if isinstance(journal,dict) else 'unknown'
        if stage not in stages+('absent',):stage='unknown'
        result={'schema':1,'status':'observed','deployment_stage':stage}
        try:
            c1_keyfilter.probe()
            result['admission']='passed'
        except Exception as error:
            names=('ValueError','RuntimeError','PermissionError','FileNotFoundError','OSError',
                'TimeoutError','CalledProcessError','TimeoutExpired','TypeError','KeyError')
            files=('c1_gate.py','c1_keyfilter.py','transport.py','emergency_reader.py')
            detail={'exception_type':type(error).__name__ if type(error).__name__ in names else 'unknown',
                'frames':[{'file':Path(f.filename).name,'line':f.lineno} for f in traceback.extract_tb(error.__traceback__)
                    if Path(f.filename).name in files and 1<=f.lineno<=10000][-8:]}
            if isinstance(error,OSError) and type(error.errno) is int and 0<=error.errno<=4095:detail['errno']=error.errno
            result.update(admission='failed',failure=detail)
        current=store._directory()
        try:
            if (identity(os.fstat(current))!=directory_identity
                    or identity(os.stat('ownership.lock',dir_fd=current,follow_symlinks=False))!=lock_identity
                    or store.read('request-'+operation)!=request or owner.status()!=lease
                    or _optional_record(root,'deploy')!=journal):
                raise ValueError('original_operation_changed')
        finally:os.close(current)
        return result
    finally:
        if lock is not None:os.close(lock)
        os.close(directory)
try:result=observe()
except Exception:result={'schema':1,'status':'refused'}
print(json.dumps(result,sort_keys=True))
'''


def sources(project):
    root=Path(project)/'root-edition';result=[]
    for name in MODULES:
        path=root/(name.replace('.','/')+'.py')
        if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():
            raise ValueError('reviewed_native_sources_required')
        result.append((name,path.read_text()))
    return result


def source_material(project):
    project=Path(project)
    return {'modules':sources(project),'program':PROGRAM,'host':Path(__file__).read_text(),
            'script':(project/'scripts/root-native-inspection.py').read_text()}


def material_pin(material):
    return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def source_pin(project):
    return material_pin(source_material(project))


def render(material, operation):
    if not isinstance(operation,str) or not re.fullmatch('[a-f0-9]{32}',operation):
        raise ValueError('original_operation_required')
    return material['program'].replace('SOURCES',repr(material['modules']),1).replace('OPERATION',repr(operation),1)


def program(project, operation):
    return render(source_material(project),operation)


def collect(remote, store, code):
    # Verify the existing pinned interpreter against the host's pinned archive.
    # No promotion, provisioning, smoke test, TV staging or executable fallback.
    from . import python_runtime as runtime
    raw=runtime._verified_bytes(runtime.prime_cache(store.root/'python-cache',lambda *_:None))
    with tempfile.TemporaryDirectory(prefix='cytv-native-inspect-') as folder:
        inventory=runtime.normalize_to_file(raw,Path(folder)/'runtime.tar.gz')
    slot=runtime.RUNTIME_ROOT+'/'+runtime.SHA256
    runtime._verify(remote,slot,inventory)
    raw=remote.run(shlex.join(['env','-u','PYTHONHOME','-u','PYTHONPATH',slot+'/bin/python3.13','-I','-B','-']),
        data=code.encode(),timeout=90)
    if not isinstance(raw,(str,bytes)) or len(raw)>4096:raise ValueError('invalid_native_observation')
    value=json.loads(raw)
    if value=={'schema':1,'status':'refused'}:return value
    from .errors import root_driver_details
    if (not isinstance(value,dict) or value.get('schema')!=1 or value.get('status')!='observed'
            or value.get('admission') not in ('passed','failed')):raise ValueError('invalid_native_observation')
    # Output is diagnostic only, and is revalidated before returning it to the host.
    allowed=('absent','unknown','prepared','install-submitting','install-accepted','install-observed',
        'payload-verified','installed-recovery-only')+tuple('provision-'+s+'-'+p
        for s in ('apply','refresh','finalize') for p in ('starting','complete'))
    if value.get('deployment_stage') not in allowed:raise ValueError('invalid_native_observation')
    result={key:value[key] for key in ('schema','status','admission','deployment_stage')}
    if value['admission']=='failed':
        detail=root_driver_details(value.get('failure'))
        if not detail:raise ValueError('invalid_native_observation')
        result['failure']=detail
    return result


def inspect_saved(store, profile, operation, secret, project, pin):
    from .transport import SSH
    material=source_material(project)
    if pin!=material_pin(material):raise ValueError('reviewed_native_sources_changed')
    code=render(material,operation)
    with store.lock(profile):
        pending=store.pending(profile)
        if (profile.get('edition')!='root' or not isinstance(pending,dict) or 'previous' in pending
                or pending.get('action')!='install' or pending.get('stage')!='setup'
                or pending.get('home_backend')!='c1-native-gate' or pending.get('product_operation')!=operation):
            raise ValueError('original_native_pending_required')
        paths=[store.device_dir(profile)/n for n in ('profile.json','known_hosts','operation.json')]
        before=[path.read_bytes() for path in paths]
        remote=SSH.connect(profile,store.device_dir(profile),secret,lambda *_:False,persist=False)
        try:
            result=collect(remote,store,code)
            if store.pending(profile)!=pending or [path.read_bytes() for path in paths]!=before:
                raise ValueError('original_host_records_changed')
            return dict(result,source_sha256=pin)
        finally:remote.close()
