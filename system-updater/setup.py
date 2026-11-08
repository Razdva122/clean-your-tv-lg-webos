#!/usr/bin/env python3
"""Explicit computer bootstrap; never repairs or replaces an existing supervisor."""
import argparse
LEGACY_NODE_BETA = False
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid

SERVICE='com.cleanyourtv.system.updater.service'
APP='com.cleanyourtv.system.updater'
STATE=Path('/var/lib/clean-your-tv-system-updater')
INSTALLED=Path('/media/developer/apps')
BASE=Path('/var/luna-service2-dev')
HOOK=Path('/var/lib/webosbrew/init.d/52-clean-your-tv-system-updater')
ROOT_UPDATER_TRANSACTION=Path('/var/lib/clean-your-tv-root-updater/transaction.json')
APPS={'home':'com.gathin.tvhome','helper':'com.local.nativehome','updater':'com.cleanyourtv.updater','root':'com.cleanyourtv.root.preview','root-updater':'com.cleanyourtv.root.updater'}
CODE={'startup_hook.py','package_data.py','package_identity.py','startup_guard.py','installation.py','python_boot.js','python_binding.py','infrastructure-paths.json','system_updater/__init__.py','system_updater/support/__init__.py','system_updater/core.py','system_updater/device.py','system_updater/cli.py','system_updater/policy.js','system_updater/release-public.pem','system_updater/ca-bundle.crt','system_updater/ca-LICENSE.txt','system_updater/support/store.py','system_updater/support/package.py','system_updater/support/profile.py','system_updater/support/luna.py','observed_install.py','installer_status.py','service.js','run-system-updater.py','services.json','package.json'}

def require_normal_root(root=Path('/var/lib/clean-your-tv-root')):
    if any(os.path.lexists(Path(root)/name) for name in ('home-backend.json','c1-gate','c1-keyfilter','runtime/c1_gate.py','runtime/c1_keyfilter.py','runtime/c1-home-gate','runtime/c1-keyfilter-guard')):
        raise ValueError('Experimental C1 routing is excluded from normal System Updater setup')


def digest(raw):return hashlib.sha256(raw).hexdigest()

def safe(path,uid=None):
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Indirect file')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>96*1024*1024 or (uid is not None and (info.st_uid!=uid or info.st_mode&0o022)):raise ValueError('Unsafe file')
        return stream.read(96*1024*1024+1)

def entries(raw):
    result={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        total=0
        for member in archive:
            name=member.name;p=PurePosixPath(name)
            if member.isdir():continue
            if not member.isfile() or p.is_absolute() or str(p)!=name or '..' in p.parts or '\\' in name or '\x00' in name or name in result or member.size>32*1024*1024:raise ValueError('Unsafe archive')
            total+=member.size
            if total>96*1024*1024 or len(result)>4096:raise ValueError('Oversized archive')
            result[name]=archive.extractfile(member).read()
    return result

def package_files(raw):
    if raw[:8]!=b'!<arch>\n':raise ValueError('Invalid IPK')
    offset=8;parts={}
    while offset<len(raw):
        header=raw[offset:offset+60]
        if len(header)!=60 or header[58:]!=b'`\n':raise ValueError('Invalid IPK')
        size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
        if size<0 or name in parts or offset+60+size>len(raw):raise ValueError('Invalid IPK')
        parts[name]=raw[offset+60:offset+60+size];offset+=60+size+size%2
    if set(parts)!={'debian-binary','control.tar.gz','data.tar.gz'} or parts['debian-binary']!=b'2.0\n':raise ValueError('Invalid IPK inventory')
    return entries(parts['data.tar.gz'])

def verify_bundle(bundle):
    bundle=Path(bundle);manifest=json.loads(safe(bundle/'bundle.json'))
    if manifest.get('schema')!=1 or manifest.get('supervisor')!=1 or set(manifest.get('files',{}))!=CODE|{'setup-system-updater.py','system-updater.ipk'}:raise ValueError('Unexpected supervisor bundle inventory')
    for name,sha in manifest['files'].items():
        if digest(safe(bundle/name))!=sha:raise ValueError('Supervisor bundle hash mismatch')
    return manifest

def infrastructure_name(name):
    if not isinstance(name,str):raise ValueError('Invalid infrastructure inventory')
    path=PurePosixPath(name)
    if path.is_absolute() or str(path)!=name or '..' in path.parts or '\\' in name or '\x00' in name or len(path.parts)<2 or path.parts[0] not in ('runtime','updater','service','support'):raise ValueError('Invalid infrastructure inventory')
    if path.parts[0]=='support' and name not in ('support/python_binding.py','support/python_boot.js','support/package_data.py','support/package_identity.py','support/updater/store.py','support/updater/package.py','support/startup_guard.py'):raise ValueError('Invalid infrastructure support path')
    return name

def infrastructure_paths(bundle):
    names=json.loads(safe(Path(bundle)/'infrastructure-paths.json'))
    if not isinstance(names,list) or not names or len(set(map(infrastructure_name,names)))!=len(names):raise ValueError('Invalid pinned infrastructure inventory')
    return names

def infrastructure_destination(name,runtime=Path('/var/lib/clean-your-tv-root/runtime'),updater=Path('/var/lib/clean-your-tv-root-updater/code'),service=Path('/var/lib/clean-your-tv-root/service')):
    kind,relative=infrastructure_name(name).split('/',1)
    path=Path({'runtime':runtime,'updater':updater,'service':service,'support':Path(runtime).parent}[kind])/relative
    if any(parent.is_symlink() for parent in path.parents):raise ValueError('Indirect infrastructure path')
    return path

def capture_infrastructure(names,runtime=Path('/var/lib/clean-your-tv-root/runtime'),updater=Path('/var/lib/clean-your-tv-root-updater/code'),service=Path('/var/lib/clean-your-tv-root/service')):
    files={};absent=[]
    for name in names:
        path=infrastructure_destination(name,runtime,updater,service)
        try:path.lstat()
        except FileNotFoundError:absent.append(name);continue
        files[name]=safe(path,os.geteuid())
    return files,sorted(absent)

def verify_infrastructure_inventory(item,files,pinned=None):
    absent=item.get('absent',[])
    if item.get('kind')!='infrastructure' or item.get('files')!={n:digest(b) for n,b in files.items()} or not files or not isinstance(absent,list) or any(not isinstance(n,str) for n in absent) or len(set(absent))!=len(absent) or set(absent)&set(files):raise ValueError('Invalid infrastructure inventory')
    names=set(files)|set(absent)
    for name in names:infrastructure_name(name)
    if pinned is not None and names!=set(pinned):raise ValueError('Baseline infrastructure inventory differs from pinned bootstrap inventory')
    return names

def infrastructure_readback(item,raw):
    for name,data in entries(raw).items():
        if safe(infrastructure_destination(name),os.geteuid())!=data:raise ValueError('Installed infrastructure baseline mismatch')
    for name in item.get('absent',[]):
        try:infrastructure_destination(name).lstat()
        except FileNotFoundError:continue
        raise ValueError('Absent infrastructure baseline changed')


def verify_baseline(baseline,bundle=None):
    baseline=Path(baseline);manifest=json.loads(safe(baseline/'baseline.json'))
    edition=manifest.get('edition');expected={'root','root-updater'} if edition=='root' else {'home','helper','updater'}
    if edition=='root':expected.add('root-infrastructure')
    if manifest.get('schema')!=1 or manifest.get('supervisor')!=1 or edition not in ('root','no-root') or not re.fullmatch(r'v\d{1,4}\.\d{1,4}\.\d{1,4}',manifest.get('release','')) or {c['name'] for c in manifest['components']}!=expected or len(manifest['components'])!=len(expected):raise ValueError('Invalid baseline')
    for item in manifest['components']:
        sha=item.get('sha256','')
        if not re.fullmatch('[a-f0-9]{64}',sha) or item.get('local') is not True:raise ValueError('Invalid baseline descriptor')
        raw=safe(baseline/'cache'/sha)
        if len(raw)!=item['size'] or digest(raw)!=sha:raise ValueError('Baseline hash mismatch')
        if item['name']=='root-infrastructure':
            files=entries(raw)
            verify_infrastructure_inventory(item,files,infrastructure_paths(bundle) if bundle is not None else None)
        else:
            app=APPS[item['name']];files=package_files(raw)
            info=json.loads(files['usr/palm/applications/'+app+'/appinfo.json'])
            if item.get('kind')!='ipk' or item.get('application')!=app or info.get('id')!=app or info.get('version')!=item['version']:raise ValueError('Baseline package identity mismatch')
    return manifest

def tgz(files,executable=None):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        channel='usr/palm/services/com.gathin.tvhome.renewal/state/home-control/.keep'
        if channel in files:
            for name in ('usr/palm/services/com.gathin.tvhome.renewal/state',
                         'usr/palm/services/com.gathin.tvhome.renewal/state/home-control'):
                item=tarfile.TarInfo(name);item.type=tarfile.DIRTYPE;item.mtime=1704067200
                item.uid,item.gid,item.mode=5999,5000,0o2770
                item.uname,item.gname='prisoner','jailer';archive.addfile(item)
        for name,raw in sorted(files.items()):
            item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o644;item.mtime=1704067200
            # Helper native binaries must remain runnable after rollback.
            if (name in executable if executable is not None else name.rsplit('/',1)[-1] in ('detach','relay','resume','boot-recover.sh')):item.mode=0o755
            archive.addfile(item,io.BytesIO(raw))
    return gzip.compress(buffer.getvalue(),mtime=0)

def require_transition_home(installed,edition):
    app=APPS['root' if edition=='root' else 'home']
    if edition=='root':
        from package_identity import identity
        info=identity(app,installed=installed,uid=os.geteuid())
    else:info=json.loads(safe(Path(installed)/'usr/palm/applications'/app/'appinfo.json'))
    if info.get('id')!=app or type(info.get('systemUpdateProtocol')) is not int or info['systemUpdateProtocol']!=1:raise ValueError('Install the transition Home from computer before enabling System Updates')

def snapshot(bundle,edition,output,installed=INSTALLED,runtime=Path('/var/lib/clean-your-tv-root/runtime'),updater=Path('/var/lib/clean-your-tv-root-updater/code'),service=Path('/var/lib/clean-your-tv-root/service')):
    require_normal_root()
    if Path(runtime).parent != Path('/var/lib/clean-your-tv-root'):require_normal_root(Path(runtime).parent)
    verify_bundle(bundle)
    names=('root','root-updater') if edition=='root' else ('home','helper','updater')
    if edition not in ('root','no-root'):raise ValueError('Invalid edition')
    rooted={};desired={}
    if edition=='root':
        import package_identity
        from package_data import read_verified
        states={**package_identity.STATES,package_identity.ROOT:Path(runtime).parent,package_identity.UPDATER:Path(updater).parent}
        for name in names:
            app=APPS[name]
            rooted[name]=package_identity.inventory(app,states=states,uid=os.geteuid())
        # Root archive modes are original pinned metadata; Updater keeps its
        # original archive executable inventory through System publication.
        root_store=package_identity.store(Path(updater).parent,os.geteuid())
        descriptor=root_store.read('current')
        original=safe(Path(updater).parent/'cache'/(descriptor['sha256']+'.ipk'),os.geteuid())
        if len(original)!=descriptor['size'] or digest(original)!=descriptor['sha256'] or {n:digest(b) for n,b in package_files(original).items()}!=rooted['root']:raise ValueError('Root original cache/identity conflict')
        # Read modes only after the original private package has been checked.
        try:from updater.package import members
        except ModuleNotFoundError:from system_updater.support.package import members
        parts=members(original)
        with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']),mode='r:gz') as archive:
            desired['root']={m.name for m in archive if m.isfile() and m.mode&0o111}
        receipt=root_store.read('installed-package')
        if not isinstance(receipt,dict) or receipt.get('files')!=rooted['root-updater'] or not isinstance(receipt.get('executable'),list):raise ValueError('Root Updater original mode inventory unavailable')
        desired['root-updater']=set(receipt['executable'])
    else:require_transition_home(installed,edition)
    output=Path(output);output.mkdir(mode=0o700);(output/'cache').mkdir(mode=0o700)
    components=[]
    for name in names:
        app=APPS[name];appinfo='usr/palm/applications/'+app+'/appinfo.json';packageinfo='usr/palm/packages/'+app+'/packageinfo.json'
        if edition=='root':
            files={n:read_verified(Path(installed)/n,sha256=h,limit=32*1024*1024,installed=installed,uid=os.geteuid()) for n,h in rooted[name].items()}
            info=json.loads(files[appinfo]);metadata=json.loads(files[packageinfo]);executable=desired[name]
            if name=='root' and info.get('systemUpdateProtocol')!=1:raise ValueError('Transition Root required')
        else:
            info=json.loads(safe(Path(installed)/appinfo));metadata=json.loads(safe(Path(installed)/packageinfo));files={};executable=set()
        if info.get('id')!=app or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',info.get('version','')):raise ValueError('Installed package identity invalid')
        services=metadata.get('services',[])
        allowed={'home':['com.gathin.tvhome.renewal'],'helper':['com.local.nativehome.service'],'updater':['com.cleanyourtv.updater.service'],'root':['com.cleanyourtv.root.preview.service'],'root-updater':['com.cleanyourtv.root.updater.service']}
        if metadata.get('id')!=app or metadata.get('version')!=info['version'] or services!=allowed[name]:raise ValueError('Installed package services invalid')
        if edition!='root':
            prefixes=['usr/palm/applications/'+app,'usr/palm/packages/'+app]+['usr/palm/services/'+s for s in services]
            for prefix in prefixes:
                folder=Path(installed)/prefix
                for path in sorted(folder.rglob('*')):
                    rel=path.relative_to(folder)
                    channel=(name=='home' and prefix=='usr/palm/services/com.gathin.tvhome.renewal'
                             and rel.as_posix()=='state/home-control/.keep')
                    if 'state' in rel.parts and not channel:continue
                    if path.is_symlink():raise ValueError('Indirect installed package')
                    if path.is_file():
                        relative_name=prefix+'/'+rel.as_posix();files[relative_name]=safe(path)
                        if channel and files[relative_name]!=b'':raise ValueError('Nonempty Home channel sentinel')
                        if path.stat().st_mode&0o111:executable.add(relative_name)
        control=('Package: '+app+'\nVersion: '+info['version']+'\nArchitecture: '+('arm' if name=='helper' else 'all')+'\nMaintainer: Clean Your TV\nDescription: Captured installed baseline\n').encode()
        raw=bytearray(b'!<arch>\n')
        for part,data in {'debian-binary':b'2.0\n','control.tar.gz':tgz({'control':control}),'data.tar.gz':tgz(files,executable)}.items():
            raw.extend(f'{part + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode());raw.extend(data)
            if len(data)%2:raw.extend(b'\n')
        raw=bytes(raw);sha=digest(raw);(output/'cache'/sha).write_bytes(raw)
        components.append({'name':name,'kind':'ipk','application':app,'version':info['version'],'sha256':sha,'size':len(raw),'local':True})
    if edition=='root':
        files,absent=capture_infrastructure(infrastructure_paths(bundle),runtime,updater,service)
        raw=tgz(files);sha=digest(raw);(output/'cache'/sha).write_bytes(raw)
        components.append({'name':'root-infrastructure','kind':'infrastructure','version':components[0]['version'],'sha256':sha,'size':len(raw),'local':True,'files':{n:digest(b) for n,b in files.items()},'absent':absent})
    manifest={'schema':1,'supervisor':1,'edition':edition,'release':'v0.0.0','notes':'Exact installed baseline captured during explicit computer setup.','components':components}
    (output/'baseline.json').write_text(json.dumps(manifest)+'\n')
    verify_baseline(output,bundle)
    return output


def permission_plan():
    group=SERVICE+'.ui';launcher=SERVICE+'.launcher'
    clients={}
    for app in ('com.gathin.tvhome','com.cleanyourtv.root.preview','com.cleanyourtv.updater','com.cleanyourtv.root.updater'):
        for pattern in (app,app+'-*'):clients[pattern]=[group]+([launcher] if app in ('com.gathin.tvhome','com.cleanyourtv.root.preview') else [])
    return {'role.json':{'appId':SERVICE,'type':'regular','allowedNames':[SERVICE],'permissions':[{'service':SERVICE,'inbound':list(clients),'outbound':[]}]},
            'client.json':clients,'api.json':{group:[SERVICE+'/'+m for m in ('check','status','rollback','reconcile')],launcher:[SERVICE+'/'+m for m in ('install','restoreProfile','healthy')]}}

def atomic(path,raw,mode=0o600):
    path=Path(path);raw=raw.encode() if isinstance(raw,str) else raw
    for parent in path.parents:
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,os.geteuid()) or (info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX):raise ValueError('Unsafe destination parent')
    if os.path.lexists(path):safe(path,os.geteuid())
    tmp=path.with_name(path.name+'.system-new')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(fd,'wb') as stream:os.fchmod(stream.fileno(),mode);stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path);fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if tmp.exists():tmp.unlink()

def require_legacy_idle(paths=None):
    paths=paths or [ROOT_UPDATER_TRANSACTION,INSTALLED/'usr/palm/services/com.cleanyourtv.updater.service/state/transaction.json']
    for path in paths:
        if os.path.lexists(path):
            value=json.loads(safe(path))
            if not isinstance(value,dict) or value.get('phase',value.get('status')) not in ('complete','healthy','rolled-back','aborted'):raise ValueError('Unfinished legacy update requires recovery before supervisor setup')
            if path==ROOT_UPDATER_TRANSACTION and value.get('homeResumePhase')!=value.get('phase'):raise ValueError('Pending legacy Root Home recovery must finish before supervisor setup')


def legacy_lockdown_targets(bases,root_updater):
    return {str(Path(base)/folder/name) for base in bases for folder,name in (('api-permissions.d','com.cleanyourtv.updater.permissions.json'),('','com.cleanyourtv.updater.permissions.receipt.json'))}|{str(Path(bases[0])/'api-permissions.d/com.cleanyourtv.root.updater.service.api.json'),str(Path(root_updater)/'registration.json')}

def apply_legacy_lockdown(state,bases=None,root_updater=Path('/var/lib/clean-your-tv-root-updater')):
    bases=[Path(p) for p in (bases or [BASE,Path('/var/luna-service2')])];root_updater=Path(root_updater);state=Path(state)
    receipt=state/'legacy-lockdown.json';allowed=legacy_lockdown_targets(bases,root_updater)
    forbidden={'com.cleanyourtv.updater.service/'+m for m in ('install','rollback','reconcile')}|{'com.cleanyourtv.root.updater.service/'+m for m in ('install','rollback','reconcile','ready','confirm')}|{'org.webosbrew.hbchannel.service/install'}
    def disabled(raw):
        value=json.loads(raw)
        if not isinstance(value,dict) or any(not isinstance(k,str) or not isinstance(v,list) or any(not isinstance(uri,str) for uri in v) for k,v in value.items()):raise ValueError('Invalid legacy API permissions')
        for methods in value.values():
            if any(uri.endswith('/*') and any(target.startswith(uri[:-1]) for target in forbidden) for uri in methods):raise ValueError('Unknown wildcard legacy mutating grant')
        return (json.dumps({k:[uri for uri in v if uri not in forbidden] for k,v in value.items()},sort_keys=True,separators=(',',':'))+'\n').encode()
    if os.path.lexists(receipt):value=json.loads(safe(receipt,os.geteuid()))
    else:
        files={}
        def add(path,raw,new):files[str(path)]={'original':raw.decode(),'disabled':new.decode(),'mode':stat.S_IMODE(path.stat().st_mode)}
        for base in bases:
            api=base/'api-permissions.d/com.cleanyourtv.updater.permissions.json';ownership=base/'com.cleanyourtv.updater.permissions.receipt.json'
            if not os.path.lexists(api) and not os.path.lexists(ownership):continue
            original=safe(api,os.geteuid());proof_raw=safe(ownership,os.geteuid());proof=json.loads(proof_raw)
            expected={str(base/folder/'com.cleanyourtv.updater.permissions.json') for folder in ('api-permissions.d','client-permissions.d','manifests.d')}
            if proof.get('schema')!=1 or not isinstance(proof.get('files'),list) or len(proof['files'])!=3 or {e.get('path') for e in proof['files']}!=expected:raise ValueError('Unknown legacy permission ownership')
            for entry in proof['files']:
                raw=safe(Path(entry['path']),os.geteuid())
                if raw.decode()!=entry.get('content') or digest(raw)!=entry.get('sha256'):raise ValueError('Legacy permission changed')
            new=disabled(original);add(api,original,new)
            for entry in proof['files']:
                if entry['path']==str(api):entry.update(content=new.decode(),sha256=digest(new))
            add(ownership,proof_raw,(json.dumps(proof,sort_keys=True,separators=(',',':'))+'\n').encode())
        api=bases[0]/'api-permissions.d/com.cleanyourtv.root.updater.service.api.json';registration=root_updater/'registration.json'
        if os.path.lexists(api) or os.path.lexists(registration):
            original=safe(api,os.geteuid());proof_raw=safe(registration,os.geteuid());proof=json.loads(proof_raw)
            if not isinstance(proof.get('files'),dict) or str(api) not in proof['files'] or proof['files'][str(api)].get('installed')!=original.decode():raise ValueError('Root updater permission ownership changed')
            new=disabled(original);add(api,original,new);proof['files'][str(api)]['installed']=new.decode()
            add(registration,proof_raw,(json.dumps(proof,sort_keys=True,separators=(',',':'))+'\n').encode())
        value={'schema':1,'files':files};atomic(receipt,json.dumps(value,sort_keys=True))
    if value.get('schema')!=1 or not isinstance(value.get('files'),dict) or set(value['files'])-allowed:raise ValueError('Unknown legacy lockdown receipt')
    for name,record in value['files'].items():
        if set(record)!={'original','disabled','mode'} or not isinstance(record['original'],str) or not isinstance(record['disabled'],str) or type(record['mode']) is not int or not 0<=record['mode']<=0o777 or record['mode']&0o022 or safe(Path(name),os.geteuid()) not in (record['original'].encode(),record['disabled'].encode()):raise ValueError('Legacy lockdown permission changed')
    for name,record in value['files'].items():
        if safe(Path(name),os.geteuid())!=record['disabled'].encode():atomic(Path(name),record['disabled'],record['mode'])
    return value


def installed_data(path,expected,installed,edition):
    if edition!='root':return safe(path)
    from package_data import read_verified
    return read_verified(path,sha256=digest(expected),limit=32*1024*1024,installed=installed,uid=os.geteuid())


def preflight(bundle,baseline,state=STATE,installed=INSTALLED,base=BASE,hook=HOOK):
    require_normal_root()
    state=Path(state)
    if os.path.lexists(state):raise FileExistsError('Supervisor setup exists; inspect retained state from computer before changing it')
    require_legacy_idle()
    bundle=Path(bundle);baseline=Path(baseline);manifest=verify_bundle(bundle);current=verify_baseline(baseline,bundle)
    require_transition_home(installed,current['edition'])
    if os.path.lexists(hook):raise FileExistsError('Supervisor boot hook exists')
    # Prove baseline payloads match installed files before creating any durable state.
    for item in current['components']:
        raw=safe(baseline/'cache'/item['sha256'])
        if item['kind']=='ipk':
            for name,data in package_files(raw).items():
                if installed_data(Path(installed)/name,data,installed,current['edition'])!=data:raise ValueError('Installed baseline payload mismatch: '+name)
        else:infrastructure_readback(item,raw)
    return manifest,current


def provision(bundle,baseline,state=STATE,installed=INSTALLED,base=BASE,hook=HOOK,install=None,refresh=None):
    require_normal_root()
    manifest,current=preflight(bundle,baseline,state,installed,base,hook)
    state=Path(state);bundle=Path(bundle);baseline=Path(baseline)
    state.mkdir(mode=0o700);code=state/'code';code.mkdir(mode=0o700);(state/'cache').mkdir(mode=0o700)
    def record(name,value):atomic(state/(name+'.json'),json.dumps(value,sort_keys=True))
    own=safe(bundle/'system-updater.ipk')
    record('bootstrap-bundle',{'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['system-updater.ipk'],'size':len(own)}})
    # Retain the independently verified original before submission/source loss.
    # It gains installed authority only after exact terminal and full readback.
    atomic(state/'cache'/(digest(own)+'.ipk'),own)
    sys.path.insert(0,str(bundle))
    from python_binding import install_launcher
    install_launcher(state, atomic)
    record('bootstrap',{'phase':'prepared','edition':current['edition']})
    for name in CODE:
        path=code/name;path.parent.mkdir(parents=True,mode=0o700,exist_ok=True);atomic(path,safe(bundle/name))
    record('infrastructure',{'schema':1,'code':{name:manifest['files'][name] for name in sorted(CODE)}})
    for item in current['components']:atomic(state/'cache'/item['sha256'],safe(baseline/'cache'/item['sha256']))
    record('baseline',current);record('current-'+current['edition'],current)
    if install is None:
        sys.path.insert(0,str(code));from observed_install import install
    require_legacy_idle()
    record('bootstrap',{'phase':'installing-supervisor'})
    terminal=install(APP,str(bundle/'system-updater.ipk'),timeout=180,on_ready=lambda:record('bootstrap',{'phase':'submitting-supervisor'}),on_accepted=lambda evidence:record('bootstrap',{'phase':'accepted-supervisor','evidence':evidence}))
    if terminal is not None:record('installed-terminal',terminal)
    return finish_registration(bundle,baseline,state,installed,base,hook,refresh)


def restart_registered_launcher(edition,rpc=None):
    """New LS2 client grants require a new launcher process, not a page reload."""
    if edition not in ('root','no-root'):raise ValueError('Unknown launcher edition')
    if rpc is None:
        from system_updater.support.luna import call
        rpc=call
    app=APPS['root' if edition=='root' else 'home']
    for method in ('closeByAppId','launch'):
        try:reply=rpc('luna://com.webos.applicationManager/'+method,{'id':app})
        except RuntimeError as error:
            if method=='closeByAppId' and getattr(error,'stopped_launcher',None)==app:continue
            raise
        if not isinstance(reply,dict) or reply.get('returnValue') is not True:
            raise ValueError('Launcher '+method+' rejected after supervisor registration')


def finish_registration(bundle,baseline,state=STATE,installed=INSTALLED,base=BASE,hook=HOOK,refresh=None):
    require_normal_root()
    bundle=Path(bundle);baseline=Path(baseline);state=Path(state);code=state/'code'
    verify_bundle(bundle);current=verify_baseline(baseline,bundle)
    def record(name,value):atomic(state/(name+'.json'),json.dumps(value,sort_keys=True))
    from installation import terminal_install
    terminal=json.loads(safe(state/'installed-terminal.json',os.geteuid()))
    if not terminal_install(terminal,APP):raise ValueError('Exact supervisor terminal required')
    own=safe(bundle/'system-updater.ipk');files=package_files(own)
    binding=json.loads(safe(state/'bootstrap-bundle.json',os.geteuid()))
    pin={'sha256':digest(own),'size':len(own)}
    if binding.get('package')!=pin or binding.get('bundle')!=verify_bundle(bundle):raise ValueError('Original supervisor pin changed')
    if safe(state/'cache'/(pin['sha256']+'.ipk'),os.geteuid())!=own:raise ValueError('Original supervisor cache changed')
    from package_data import read_verified
    for name,data in files.items():
        read_verified(Path(installed)/name,sha256=digest(data),limit=32*1024*1024,installed=installed,uid=os.geteuid())
    version=json.loads(files['usr/palm/applications/'+APP+'/appinfo.json'])['version']
    record('installed-package',{'schema':1,'package':dict(pin,version=version,local=True),'files':{n:digest(b) for n,b in files.items()}})
    record('bootstrap',{'phase':'provisioning'})
    paths={'service':Path(base)/'services.d'/(SERVICE+'.service'),'role':Path(base)/'roles.d'/(SERVICE+'.service.json'),'client':Path(base)/'client-permissions.d'/(SERVICE+'.service.json'),'api':Path(base)/'api-permissions.d'/(SERVICE+'.api.json')}
    saved=json.loads(safe(state/'registration.json',os.geteuid())) if os.path.lexists(state/'registration.json') else None
    if saved is not None:
        if not isinstance(saved,dict) or set(saved.get('files',{}))!=set(map(str,paths.values())):raise ValueError('Unknown supervisor registration inventory')
        original={key:saved['files'][str(path)]['original'].encode() for key,path in paths.items()}
    else:original={key:safe(path,os.geteuid()) for key,path in paths.items()}
    expected='Exec=/usr/bin/run-js-service -n '+str(Path(installed)/'usr/palm/services'/SERVICE)
    if original['service'].decode().splitlines().count(expected)!=1 or json.loads(original['role']).get('appId')!=SERVICE:raise ValueError('Unexpected supervisor registration')
    runner=state/'run-service'
    atomic(runner,'#!/bin/sh\nset -eu\n[ "$#" -eq 0 ] || exit 2\ncd '+str(code)+'\nexport NODE_PATH=/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules\nexec /usr/bin/node /usr/palm/services/jsservicelauncher/bootstrap-node.js -- '+str(state/'bootstrap.pid')+' /var/palm/ls2-dev '+str(code)+'\n',0o700)
    plan=permission_plan();role=json.loads(original['role']);role.update(plan['role.json'])
    updated={'service':original['service'].decode().replace(expected,'Exec='+str(runner)).encode(),'role':json.dumps(role).encode(),'client':json.dumps(plan['client.json']).encode(),'api':json.dumps(plan['api.json']).encode()}
    expected={'files':{str(paths[k]):{'original':original[k].decode(),'installed':v.decode()} for k,v in updated.items()}}
    if saved is not None and saved!=expected:raise ValueError('Supervisor registration receipt mismatch')
    for key,path in paths.items():
        if safe(path,os.geteuid()) not in (original[key],updated[key]):raise ValueError('Supervisor registration changed')
    record('registration',expected)
    for key,path in paths.items():atomic(path,updated[key],stat.S_IMODE(path.stat().st_mode))
    apply_legacy_lockdown(state)
    import startup_hook
    startup_hook.install_link(safe,atomic,state,Path(hook),APP,sha256=digest(files['usr/palm/applications/'+APP+'/appinfo.json']))
    if refresh is None:
        executable=next((p for p in (Path('/usr/bin/ls-control'),Path('/usr/sbin/ls-control')) if p.is_file()),None)
        if executable is None:raise ValueError('ls-control unavailable')
        subprocess.run([str(executable),'scan-services'],check=True,timeout=15,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        restart_registered_launcher(current['edition'])
    else:refresh()
    require_legacy_idle()
    for item in current['components']:
        if item['kind']=='ipk':
            for name,data in package_files(safe(baseline/'cache'/item['sha256'])).items():
                if installed_data(Path(installed)/name,data,installed,current['edition'])!=data:raise ValueError('Installed baseline changed during bootstrap')
        else:infrastructure_readback(item,safe(baseline/'cache'/item['sha256']))
    record('bootstrap',{'phase':'complete','edition':current['edition'],'hardware_validated':False})
    return {'installed':True,'edition':current['edition'],'hardware_validated':False}

def resume(bundle,state=STATE,installed=INSTALLED,base=BASE,hook=HOOK,refresh=None):
    """Bounded explicit bootstrap continuation, using original cached baseline."""
    require_normal_root()
    from installation import terminal_install
    from python_binding import verify_binding
    state=Path(state);bundle=Path(bundle);manifest=verify_bundle(bundle)
    expected={'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['system-updater.ipk'],'size':len(safe(bundle/'system-updater.ipk'))}}
    try:binding=json.loads(safe(state/'bootstrap-bundle.json',os.geteuid()))
    except FileNotFoundError:binding=None
    if binding!=expected:
        raise ValueError('Matching original bootstrap bundle proof required; retain state for recovery')
    verify_binding(state)
    receipt=json.loads(safe(state/'infrastructure.json',os.geteuid()))
    expected={name:manifest['files'][name] for name in sorted(CODE)}
    if receipt!={'schema':1,'code':expected}:raise ValueError('Unknown supervisor bootstrap infrastructure')
    for name,digest_value in expected.items():
        if digest(safe(state/'code'/name,os.geteuid()))!=digest_value:raise ValueError('Supervisor bootstrap code changed')
    current=verify_baseline(state,bundle)
    require_legacy_idle()
    phase=json.loads(safe(state/'bootstrap.json',os.geteuid())).get('phase')
    terminal=json.loads(safe(state/'installed-terminal.json',os.geteuid())) if os.path.lexists(state/'installed-terminal.json') else None
    def record(name,value):atomic(state/(name+'.json'),json.dumps(value,sort_keys=True))
    if not terminal_install(terminal,APP):
        if phase not in ('prepared','installing-supervisor'):raise ValueError('Supervisor submission outcome unknown')
        if any(os.path.lexists(Path(installed)/'usr/palm'/folder/name) for folder,name in (('applications',APP),('packages',APP),('services',SERVICE))) or os.path.lexists(hook):raise ValueError('Supervisor artifacts without terminal proof')
        from observed_install import install
        terminal=install(APP,str(bundle/'system-updater.ipk'),timeout=180,on_ready=lambda:record('bootstrap',{'phase':'submitting-supervisor'}),on_accepted=lambda evidence:record('bootstrap',{'phase':'accepted-supervisor','evidence':evidence}))
        record('installed-terminal',terminal)
        if not terminal_install(terminal,APP):raise ValueError('Exact supervisor terminal required')
    own=safe(bundle/'system-updater.ipk');cache=state/'cache'/(digest(own)+'.ipk')
    if not os.path.lexists(cache):atomic(cache,own)  # Explicit original-pin continuation, never SDK adoption.
    return finish_registration(bundle,state,state,installed,base,hook,refresh)


def execute(bundle,baseline,alias,identity=None,run=subprocess.run,edition=None,python='/usr/bin/python3',resume=False):
    if python not in ('/usr/bin/python3','/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'):raise ValueError('Unapproved Python executable')
    manifest=verify_bundle(bundle)
    baseline_manifest=verify_baseline(baseline,bundle) if baseline is not None else None
    if baseline is None and edition not in ('root','no-root'):raise ValueError('Edition required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',alias):raise ValueError('Use an explicit OpenSSH host alias')
    options=['-o','StrictHostKeyChecking=yes','-o','BatchMode=yes','-o','ConnectTimeout=10']
    if identity is not None:options+=['-i',str(Path(identity).expanduser().resolve())]
    remote='/tmp/cytv-system-updater-'+uuid.uuid4().hex
    run(['ssh',*options,alias,'umask 077; test "$(id -u)" = 0 && mkdir '+shlex.quote(remote)],check=True,stdin=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='system-transfer-') as temporary:
        staging=Path(temporary).resolve();source=staging/'bundle';source.mkdir()
        for name in (*manifest['files'],'bundle.json'):
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(safe(Path(bundle)/name))
        sources=[str(source)]
        if baseline_manifest is not None:
            target=staging/'baseline';target.mkdir();(target/'cache').mkdir()
            (target/'baseline.json').write_bytes(safe(Path(baseline)/'baseline.json'))
            for item in baseline_manifest['components']:(target/'cache'/item['sha256']).write_bytes(safe(Path(baseline)/'cache'/item['sha256']))
            sources.append(str(target))
        run(['scp','-O',*options,'-r',*sources,alias+':'+remote+'/'],check=True,stdin=subprocess.DEVNULL)
    remote_bundle=remote+'/bundle'
    argv=['env','-u','PYTHONHOME','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1',python,remote_bundle+'/setup-system-updater.py','--device','--apply','--bundle',remote_bundle]
    if resume:argv.append('--resume')
    if baseline is not None:argv+=['--baseline',remote+'/baseline']
    else:argv+=['--edition',edition]
    return run(['ssh',*options,alias,shlex.join(argv)],check=True,stdin=subprocess.DEVNULL)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--baseline',type=Path);parser.add_argument('--edition',choices=('root','no-root'));parser.add_argument('--ssh');parser.add_argument('--identity',type=Path);parser.add_argument('--apply',action='store_true');parser.add_argument('--device',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--python',default='/usr/bin/python3',choices=('/usr/bin/python3','/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'))
    parser.add_argument('--resume',action='store_true',help='Explicit bounded continuation of retained bootstrap; never replay unknown submissions')
    args=parser.parse_args()
    if args.device:
        if not args.apply or os.geteuid()!=0 or not Path('/usr/bin/luna-send').is_file() or sys.version_info<(3,9):raise PermissionError('Explicit root webOS Python 3.9+ setup required')
        policy = 'process.versions.node === "0.12.2"' if LEGACY_NODE_BETA else 'Number(process.versions.node.split(".")[0])>=8'
        subprocess.run(['/usr/bin/node','-e','process.exit(('+policy+')?0:1)'],check=True)
        sys.path.insert(0,str(args.bundle))
        from installation import device_operation, Ownership, read_journal, JOURNALS
        with tempfile.TemporaryDirectory(prefix='system-baseline-') as tmp:
            selected=[args.baseline]
            def eligible():
                require_normal_root()
                if args.resume:
                    current=Ownership().status()
                    if not current or current['terminal'] or (current['owner'],current['journal'])!=('system-bootstrap','bootstrap.json') or read_journal(JOURNALS['system-bootstrap'][0]) is None:
                        raise ValueError('No matching pending supervisor bootstrap; inspect retained state')
                    return
                if selected[0] is None:
                    if not args.edition:parser.error('--edition is required without --baseline')
                    # Snapshot is private staging only, under the global mutex.
                    if os.path.lexists(STATE):raise FileExistsError('Supervisor setup exists; inspect or explicitly --resume')
                    selected[0]=snapshot(args.bundle,args.edition,Path(tmp)/'baseline')
                preflight(args.bundle,selected[0])
            with device_operation('system-bootstrap', recovery=args.resume, check=eligible):
                print(json.dumps(resume(args.bundle) if args.resume else provision(args.bundle,selected[0])))
        return
    verify_bundle(args.bundle);baseline=verify_baseline(args.baseline,args.bundle) if args.baseline else {'edition':args.edition}
    if not baseline['edition']:parser.error('--edition is required without --baseline')
    print(json.dumps({'operation':'one-time-system-updater-setup','edition':baseline['edition'],'permissions':permission_plan(),'hardware_validated':False},indent=2))
    if args.apply:
        if not args.ssh:parser.error('--apply requires --ssh')
        execute(args.bundle,args.baseline,args.ssh,args.identity,edition=baseline['edition'],python=args.python,resume=args.resume)

if __name__=='__main__':main()
