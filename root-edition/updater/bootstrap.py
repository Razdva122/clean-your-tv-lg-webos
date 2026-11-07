"""Explicit one-time device setup, never an in-app updater self-upgrade."""
import hashlib
import json
import os
from pathlib import Path
import stat

from updater.package import APP, inspect_package, safe_bytes

SERVICE='com.cleanyourtv.root.updater.service'
STATE=Path('/var/lib/clean-your-tv-root-updater')
ROOT_STATE=Path('/var/lib/clean-your-tv-root')
INSTALLED=Path('/media/developer/apps')
BASE=Path('/var/luna-service2-dev')
HOOK=Path('/var/lib/webosbrew/init.d/51-clean-your-tv-root-updater')


def permission_plan():
    ui=SERVICE+'.ui';health=SERVICE+'.health'
    methods=('check','status','reconcile','rollback')
    clients={}
    for app in (APP,'com.cleanyourtv.root.updater'):
        for pattern in (app,app+'-*'):clients[pattern]=[ui]+([health] if app==APP else [])
    return {'role.json':{'appId':SERVICE,'type':'regular','allowedNames':[SERVICE],
                        'permissions':[{'service':SERVICE,'inbound':[APP,APP+'-*','com.cleanyourtv.root.updater','com.cleanyourtv.root.updater-*'],'outbound':[]}]},
            'client.json':clients,
            'api.json':{ui:[SERVICE+'/'+m for m in methods],health:[SERVICE+'/'+m for m in ('install','restoreProfile','ready','confirm')]}}


def digest(raw):return hashlib.sha256(raw).hexdigest()


def persistent_code(manifest):
    """Keep one-time installer helpers outside supervisor-pinned TV code."""
    from coordinator_inventory import INSTALLER_ONLY_FILES
    return {name:sha for name,sha in manifest['files'].items()
            if name not in ('root-updater.ipk','setup-updater.py',*INSTALLER_ONLY_FILES)}


def verify_bundle(bundle,reader=None,allow_legacy_recovery=False):
    bundle=Path(bundle);reader=safe_bytes if reader is None else reader
    manifest=json.loads(reader(bundle/'bundle.json',limit=65536))
    if manifest.get('schema')!=1 or not isinstance(manifest.get('files'),dict):raise ValueError('Invalid updater bundle')
    required={'root-updater.ipk','run-updater.py','service.js','services.json','package.json','setup-updater.py',
              'updater/core.py','updater/store.py','updater/profile.py','updater/device.py','updater/package.py','updater/cli.py',
              'updater/fetch.js','updater/bridge.js','updater/luna.py','updater/bootstrap.py','updater/release-public.pem',
              'updater/ca-bundle.crt','updater/ca-LICENSE.txt',
              'installation.py','observed_install.py','installer_status.py','provision.py','deploy.py','setup.py','system_permissions.py','activity.py','startup_hook.py','package_data.py','package_identity.py','startup_guard.py','python_binding.py','python_boot.js'}
    from coordinator_inventory import BUNDLED_FILES
    required.update(BUNDLED_FILES)
    cleanup={'clean_removal.py','cleanup_tail.js','cleanup_no_root_private.js'}
    inventories=(required,required-{'cleanup_no_root_private.js'},required-cleanup,required-cleanup-{'cancel_install.py','cancel_provision.py'}) if allow_legacy_recovery else (required,)
    if set(manifest['files']) not in inventories:raise ValueError('Unexpected updater bundle inventory')
    for name,sha in manifest['files'].items():
        if digest(reader(bundle/name))!=sha:raise ValueError('Updater bundle hash mismatch: '+name)
    return manifest


def atomic(path,raw,mode=0o600):
    from updater.store import Store
    if isinstance(raw,str):raw=raw.encode()
    for parent in (path.parent,*path.parent.parents):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o022:raise ValueError('Unsafe bootstrap path')
    temporary=path.with_name(path.name+'.updater-new')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),mode);f.write(raw);f.flush();os.fsync(f.fileno())
        if os.path.lexists(path):safe_bytes(path,uid=0)
        os.replace(temporary,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if temporary.exists():temporary.unlink()


def preflight(bundle,baseline):
    import sys
    if any(os.path.lexists(ROOT_STATE/name) for name in ('home-backend.json','c1-gate','runtime/c1_gate.py','runtime/c1-home-gate')):
        raise ValueError('Experimental C1 routing is excluded from normal Root Updater setup')
    if sys.version_info < (3, 9):raise RuntimeError('Root Updater requires TV Python 3.9+')
    if os.geteuid()!=0 or not Path('/usr/bin/luna-send').is_file():raise PermissionError('Explicit rooted webOS device required')
    from deploy import require_node
    require_node()
    manifest=verify_bundle(bundle);bundle=Path(bundle);baseline=Path(baseline)
    from deploy import verify_bundle as root_bundle
    baseline_manifest=root_bundle(baseline)
    release=json.loads(safe_bytes(baseline/'release.json'))
    raw=safe_bytes(baseline/baseline_manifest['package'])
    descriptor={'version':release['version'],'sha256':digest(raw),'size':len(raw),'local':True}
    hashes=inspect_package(raw,descriptor)
    # Compatibility bootstrap is refused on legacy infrastructure. Host migration
    # must restore and provision the new runtime; never overwrite a live runtime.
    proof=safe_bytes(ROOT_STATE/'recovery-provision.json',limit=65536,uid=0)
    recovery=json.loads(proof);runtime=ROOT_STATE/'runtime'
    if recovery.get('mode')!='recovery-only':raise ValueError('Recovery not provisioned')
    for name,expected in recovery.get('files',{}).items():
        target=Path(name)
        if not target.is_relative_to(ROOT_STATE):raise ValueError('Foreign recovery infrastructure')
        if digest(safe_bytes(target,limit=1048576,uid=0))!=expected:raise ValueError('Recovery integrity failed')
    for name in ('cli.py','update_guard.py'):
        target=runtime/name
        if recovery.get('files',{}).get(str(target))!=digest(safe_bytes(target,uid=0)):
            raise ValueError('Updater-compatible Root infrastructure required; migrate from computer first')
    from updater.device import Device
    Device.require_home_resume_runtime(ROOT_STATE)
    from package_data import read_verified
    from updater.package import verify_payload
    verify_payload(INSTALLED,hashes)
    info='usr/palm/applications/'+APP+'/appinfo.json'
    current=json.loads(read_verified(INSTALLED/info,sha256=hashes[info],installed=INSTALLED))
    if current.get('version')!=descriptor['version']:raise ValueError('Baseline must match installed Root version')
    if STATE.exists() or STATE.is_symlink():raise FileExistsError('Updater setup exists; inspect retained state')
    if os.path.lexists(HOOK):raise FileExistsError('Updater boot hook collision')
    from python_binding import verify_binding
    verify_binding(ROOT_STATE)
    from updater.store import Store
    store=Store.__new__(Store);store.root=str(STATE)
    status=Device(store,code=STATE/'code').routing_status()
    if status['active'] or not status['safe']:raise ValueError('Verify LG Home routing before one-time updater setup')
    return manifest, baseline_manifest, descriptor, proof, raw


def apply(bundle,baseline):
    manifest, baseline_manifest, descriptor, proof, raw=preflight(bundle,baseline)
    bundle=Path(bundle)
    STATE.mkdir(mode=0o700);(STATE/'cache').mkdir(mode=0o700);code=STATE/'code';code.mkdir(mode=0o700)
    from updater.store import Store
    from python_binding import install_launcher, verify_binding
    verify_binding(ROOT_STATE)
    store=Store(STATE)
    store.write('bootstrap-bundle',{'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['root-updater.ipk'],'size':len(safe_bytes(bundle/'root-updater.ipk'))}})
    install_launcher(STATE, atomic)
    store.write('bootstrap',{'phase':'prepared','bundle':manifest})
    code_files=persistent_code(manifest)
    for name in code_files:
        target=code/name;target.parent.mkdir(mode=0o700,exist_ok=True)
        atomic(target,safe_bytes(bundle/name))
    atomic(STATE/'cache'/(descriptor['sha256']+'.ipk'),raw)
    store.write('current',descriptor)
    store.write('infrastructure',{'schema':1,'runtime':1,'updater':1,'code':code_files,'recovery_sha256':digest(proof)})
    from updater.device import Device
    device=Device(store,code=code);device.integrity()
    status=device.routing_status()
    if status['active'] or not status['safe']:raise ValueError('Verify LG Home routing before one-time updater setup')
    from observed_install import install
    store.write('bootstrap',{'phase':'installing-updater'})
    terminal=install('com.cleanyourtv.root.updater',str(bundle/'root-updater.ipk'),timeout=180,
            on_ready=lambda:store.write('bootstrap',{'phase':'submitting-updater'}),
            on_accepted=lambda event:store.write('bootstrap',{'phase':'accepted-updater','evidence':event}))
    if terminal is not None: store.write('installed-terminal',terminal)
    return finish_registration(bundle)


def finish_registration(bundle):
    from updater.store import Store
    bundle=Path(bundle);verify_bundle(bundle);store=Store(STATE);code=STATE/'code'
    from updater.package import members,archive,verify_payload
    from installation import terminal_install
    if not terminal_install(store.read('installed-terminal'),'com.cleanyourtv.root.updater'):raise ValueError('Exact updater terminal required')
    payload=archive(members(safe_bytes(bundle/'root-updater.ipk'))['data.tar.gz'])
    verify_payload(INSTALLED,{name:digest(raw) for name,raw in payload.items()})
    import io, tarfile
    with tarfile.open(fileobj=io.BytesIO(members(safe_bytes(bundle/'root-updater.ipk'))['data.tar.gz']),mode='r:gz') as stream:
        executable=sorted(member.name for member in stream if member.isfile() and member.mode & 0o111)
    store.write('installed-package',{'schema':1,'files':{name:digest(raw) for name,raw in payload.items()},'executable':executable})
    store.write('bootstrap',{'phase':'provisioning'})
    paths={'service':BASE/'services.d'/(SERVICE+'.service'),'role':BASE/'roles.d'/(SERVICE+'.service.json'),
           'client':BASE/'client-permissions.d'/(SERVICE+'.service.json'),'api':BASE/'api-permissions.d'/(SERVICE+'.api.json')}
    saved=store.read('registration')
    if saved is not None:
        if not isinstance(saved,dict) or set(saved.get('files',{}))!=set(map(str,paths.values())):raise ValueError('Unknown updater registration inventory')
        original={key:saved['files'][str(path)]['original'].encode() for key,path in paths.items()}
    else:original={key:safe_bytes(path,uid=0) for key,path in paths.items()}
    expected='Exec=/usr/bin/run-js-service -n /media/developer/apps/usr/palm/services/'+SERVICE
    if original['service'].decode().splitlines().count(expected)!=1:raise ValueError('Unexpected updater service registration')
    plan=permission_plan();role=json.loads(original['role'])
    if role.get('appId')!=SERVICE:raise ValueError('Unexpected updater role identity')
    role.update(plan['role.json'])
    runner=STATE/'run-service'
    runner_bytes=('#!/bin/sh\nset -eu\n[ "$#" -eq 0 ] || exit 2\ncd '+str(code)+'\nexport NODE_PATH=/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules\nexec /usr/bin/node /usr/palm/services/jsservicelauncher/bootstrap-node.js -- '+str(STATE/'bootstrap.pid')+' /var/palm/ls2-dev '+str(code)+'\n').encode()
    atomic(runner,runner_bytes,0o700)
    updated={'service':original['service'].decode().replace(expected,'Exec='+str(runner)).encode(),
             'role':json.dumps(role).encode(),'client':json.dumps(plan['client.json']).encode(),'api':json.dumps(plan['api.json']).encode()}
    expected={'files':{str(paths[k]):{'original':v.decode(),'installed':updated[k].decode()} for k,v in original.items()}}
    for key,path in paths.items():
        # Older receipts have byte evidence only; do not manufacture historical
        # metadata on resume. New receipts capture it before any replacement.
        entry=saved['files'][str(path)] if saved is not None else None
        if entry is None:
            info=path.lstat()
            expected['files'][str(path)].update(mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid)
        elif set(entry)=={'original','installed','mode','uid','gid'}:
            expected['files'][str(path)].update({name:entry[name] for name in ('mode','uid','gid')})
    if saved is not None and saved!=expected:raise ValueError('Updater registration receipt mismatch')
    for key,path in paths.items():
        if safe_bytes(path,uid=0) not in (original[key],updated[key]):raise ValueError('Updater registration changed')
        entry=expected['files'][str(path)]
        if 'mode' in entry:
            info=path.lstat()
            if (any(type(entry[k]) is not int or entry[k]<0 for k in ('mode','uid','gid'))
                    or entry['uid']!=store.uid or entry['mode']>0o777 or entry['mode']&0o022
                    or (entry['mode'],entry['uid'],entry['gid'])!=(stat.S_IMODE(info.st_mode),info.st_uid,info.st_gid)):
                raise ValueError('Updater registration metadata changed')
    store.write('registration',expected)
    for key,path in paths.items():
        entry=expected['files'][str(path)]
        if 'mode' in entry:
            from cancel_provision import write_registration
            write_registration(path,dict(entry,original=updated[key].decode()))
        else:
            mode=stat.S_IMODE(path.stat().st_mode);atomic(path,updated[key],mode)
    import startup_hook
    startup_hook.install_link(safe_bytes,atomic,STATE,HOOK,'com.cleanyourtv.root.updater',sha256=digest(payload['usr/palm/applications/com.cleanyourtv.root.updater/appinfo.json']))
    import provision
    provision.refresh()
    store.write('bootstrap',{'phase':'complete','hardware_validated':False})
    return {'installed':True,'hardware_validated':False,'instruction':'Open Root Updater and verify the service on the TV before enabling Root.'}


def resume(bundle):
    """Continue the owned bootstrap only with pre-submission or exact terminal proof."""
    from updater.store import Store
    from updater.device import Device
    from installation import terminal_install
    store=Store(STATE);bundle=Path(bundle);manifest=verify_bundle(bundle)
    expected={'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['root-updater.ipk'],'size':len(safe_bytes(bundle/'root-updater.ipk'))}}
    if store.read('bootstrap-bundle')!=expected:
        raise ValueError('Matching original bootstrap bundle proof required; retain state for recovery')
    code=persistent_code(manifest)
    infrastructure=store.read('infrastructure')
    if not isinstance(infrastructure,dict) or infrastructure.get('code')!=code:
        raise ValueError('Retained code differs from original bootstrap bundle')
    Device(store,code=STATE/'code').integrity()
    phase=store.read('bootstrap').get('phase')
    terminal=store.read('installed-terminal')
    if not terminal_install(terminal,'com.cleanyourtv.root.updater'):
        if phase not in ('prepared','installing-updater'):raise ValueError('Updater submission outcome unknown')
        if os.path.lexists(HOOK):raise ValueError('Updater startup already retained')
        base=INSTALLED/'usr/palm'
        if any(os.path.lexists(base/folder/name) for folder,name in (('applications','com.cleanyourtv.root.updater'),('packages','com.cleanyourtv.root.updater'),('services','com.cleanyourtv.root.updater.service'))):raise ValueError('Updater artifacts without terminal proof')
        routing=Device(store,code=STATE/'code').routing_status()
        if routing['active'] or not routing['safe']:raise ValueError('Verify LG Home before bootstrap continuation')
        from observed_install import install
        terminal=install('com.cleanyourtv.root.updater',str(bundle/'root-updater.ipk'),timeout=180,
          on_ready=lambda:store.write('bootstrap',{'phase':'submitting-updater'}),on_accepted=lambda event:store.write('bootstrap',{'phase':'accepted-updater','evidence':event}))
        store.write('installed-terminal',terminal)
        if not terminal_install(terminal,'com.cleanyourtv.root.updater'):raise ValueError('Exact updater terminal required')
    return finish_registration(bundle)
