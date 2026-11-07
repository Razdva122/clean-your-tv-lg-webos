"""Fixed, fail-closed removal of the independently provisioned supervisor."""
SCRIPT = r'''
import fcntl, hashlib, json, os, re, signal, stat, subprocess, sys, tempfile, time, uuid
from pathlib import Path

APP='com.cleanyourtv.system.updater'
SERVICE=APP+'.service'
STATE=Path('/var/lib/clean-your-tv-system-updater')
ROOT_UPDATER=Path('/var/lib/clean-your-tv-root-updater')

def directory(path):
    for parent in (path,*path.parents):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,os.geteuid()) or (info.st_mode&0o022 and not info.st_mode&stat.S_ISVTX):raise ValueError('Unsafe supervisor cleanup directory')

def read(path,limit=4*1024*1024):
    directory(path.parent)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or info.st_mode&0o022 or info.st_size>limit:raise ValueError('Unsafe supervisor cleanup file')
        raw=stream.read(limit+1)
        if len(raw)>limit:raise ValueError('Oversized supervisor cleanup file')
        return raw

def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

def write(path,value,mode=0o600):
    directory(path.parent)
    fd,name=tempfile.mkstemp(prefix='.system-removal-',dir=str(path.parent));temp=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:os.fchmod(stream.fileno(),mode);stream.write(value if isinstance(value,bytes) else json.dumps(value).encode());stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path);sync(path.parent)
    finally:
        if temp.exists():temp.unlink()

def processes(code,proc=Path('/proc')):
    result=[]
    for path in proc.iterdir():
        if not path.name.isdigit() or int(path.name)==os.getpid():continue
        try:
            if path.stat().st_uid!=os.geteuid():continue
            args=[a.decode('utf8') for a in (path/'cmdline').read_bytes().split(b'\0') if a]
            start=(path/'stat').read_text().rsplit(')',1)[1].split()[19]
        except (FileNotFoundError,ProcessLookupError,UnicodeError):continue
        if not args:continue
        executable=Path(args[0]).name
        worker=False;match=False
        if executable in ('python3','python3.9','python3.10','python3.11','python3.12','python3.13','python3.14') and len(args)>=3:
            if args[1]==str(code/'run-system-updater.py'):
                match=True;worker=args[2]=='worker'
            elif re.fullmatch(r'/tmp/cytv-system-updater-[0-9a-f]{32}/(?:(?:system-updater|bundle)/)?setup-system-updater\.py',args[1]) and '--device' in args[2:] and '--apply' in args[2:]:
                match=True;worker=True
        if executable in ('sh','bash','dash') and len(args)>=2 and args[1]==str(code.parent/'run-service'):match=True
        if executable in ('node','nodejs'):
            match=(len(args)>=2 and args[1]==str(code/'system_updater/policy.js')) or (str(code) in args and '/usr/palm/services/jsservicelauncher/bootstrap-node.js' in args)
        if match:result.append((int(path.name),start,worker))
    return result

def stop(code):
    current=processes(code)
    if any(p[2] for p in current):raise ValueError('Supervisor worker still running')
    for pid,start,_ in current:
        if (pid,start,False) in processes(code):
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
    for _ in range(50):
        if not processes(code):return
        time.sleep(.1)
    raise ValueError('Supervisor processes have not stopped')

def bootstrap(state):
    value=json.loads(read(state/'bootstrap.json'))
    if value.get('phase')!='complete' or value.get('edition') not in ('root','no-root'):raise ValueError('Incomplete supervisor bootstrap requires computer recovery')
    code=json.loads(read(state/'infrastructure.json'))
    if code.get('schema')!=1 or not isinstance(code.get('code'),dict) or not code['code'] or 'run-system-updater.py' not in code['code']:raise ValueError('Invalid supervisor integrity receipt')
    for name,sha in code['code'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or str(path)!=name or not re.fullmatch('[a-f0-9]{64}',sha) or hashlib.sha256(read(state/'code'/name)).hexdigest()!=sha:raise ValueError('Supervisor code integrity mismatch')
    baseline=json.loads(read(state/'baseline.json'));expected={'root','root-updater','root-infrastructure'} if value['edition']=='root' else {'home','helper','updater'}
    if baseline.get('schema')!=1 or baseline.get('supervisor')!=1 or baseline.get('edition')!=value['edition'] or not isinstance(baseline.get('components'),list) or len(baseline['components'])!=len(expected) or {c.get('name') for c in baseline['components']}!=expected:raise ValueError('Invalid supervisor baseline receipt')
    for item in baseline['components']:
        sha=item.get('sha256','');size=item.get('size')
        if not re.fullmatch('[a-f0-9]{64}',sha) or item.get('local') is not True or type(size) is not int or not 0<size<=64*1024*1024:raise ValueError('Invalid supervisor baseline descriptor')
        raw=read(state/'cache'/sha,64*1024*1024)
        if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Supervisor baseline cache integrity mismatch')
    return value

def lockdown(state,base,allow_missing=False,check=None):
    value=json.loads(read(state/'legacy-lockdown.json'))
    bases=(base,Path('/var/luna-service2'))
    allowed={str(root/folder/name) for root in bases for folder,name in (('api-permissions.d','com.cleanyourtv.updater.permissions.json'),('','com.cleanyourtv.updater.permissions.receipt.json'))}|{str(base/'api-permissions.d/com.cleanyourtv.root.updater.service.api.json'),str(ROOT_UPDATER/'registration.json')}
    if value.get('schema')!=1 or not isinstance(value.get('files'),dict) or set(value['files'])-allowed:raise ValueError('Unknown legacy lockdown ownership')
    result=dict(value['files'])
    for name,record in value['files'].items():
        if set(record)!={'original','disabled','mode'} or not isinstance(record['original'],str) or not isinstance(record['disabled'],str) or type(record['mode']) is not int or record['mode']<0 or record['mode']>0o777 or record['mode']&0o022:raise ValueError('Legacy lockdown file changed')
        if allow_missing and not os.path.lexists(name):continue
        if read(Path(name)) not in (record['original'].encode(),record['disabled'].encode()):
            if check is None or name!=str(base/'api-permissions.d/com.cleanyourtv.root.updater.service.api.json'):raise ValueError('Legacy lockdown file changed')
            check(value['files'])
            del result[name]  # Already at SDK originals; never republish private API bytes.
    return result




def root_removal_repair(legacy,base):
    state=ROOT_UPDATER;registration=state/'registration.json';journal=state/'cytv-removal.json'
    if not os.path.lexists(journal):return None
    record=json.loads(read(journal))
    if (not isinstance(record,dict) or set(record)!={'phase','archive'} or record['phase']!='disabled'
            or not isinstance(record['archive'],str) or not re.fullmatch(re.escape(str(state))+r'\.archive-[0-9a-f]{32}',record['archive']) or os.path.lexists(record['archive'])):raise ValueError('Root updater removal ownership conflict')
    app='com.cleanyourtv.root.updater';service=app+'.service'
    paths={key:base/folder/(service+suffix) for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json'))}
    api=paths['api']
    if str(api) not in legacy or str(registration) not in legacy:raise ValueError('Root updater removal ownership conflict')
    proof=legacy[str(registration)];api_proof=legacy[str(api)]
    original=json.loads(proof['original']);disabled=json.loads(proof['disabled'])
    if (not isinstance(original,dict) or set(original)!={'files'} or not isinstance(original['files'],dict)
            or set(original['files'])!=set(map(str,paths.values()))):raise ValueError('Root updater removal ownership conflict')
    expected=json.loads(proof['original'])
    for key,path in paths.items():
        entry=expected['files'][str(path)]
        if not isinstance(entry,dict) or set(entry)!={'original','installed'} or not isinstance(entry['installed'],str) or entry['original'] is not None and not isinstance(entry['original'],str):raise ValueError('Root updater removal ownership conflict')
    if expected['files'][str(api)]['installed']!=api_proof['original']:raise ValueError('Root updater removal ownership conflict')
    expected['files'][str(api)]['installed']=api_proof['disabled']
    if expected!=disabled:raise ValueError('Root updater removal ownership conflict')
    before=json.loads(api_proof['original']);after=json.loads(api_proof['disabled'])
    if not isinstance(before,dict) or not isinstance(after,dict) or set(before)!=set(after):raise ValueError('Root updater removal ownership conflict')
    for name,methods in before.items():
        if not isinstance(methods,list) or not all(isinstance(v,str) for v in methods) or not isinstance(after[name],list) or any(v not in methods for v in after[name]):raise ValueError('Root updater removal ownership conflict')
    saved=state/'removed-registration'
    directory(saved)
    if {p.name for p in saved.iterdir()}!={'service','role','client','api','hook','manifest'}:raise ValueError('Root updater removal ownership conflict')
    if os.path.lexists(state/'transaction.json'):
        tx=json.loads(read(state/'transaction.json'))
        if not isinstance(tx,dict) or tx.get('schema')!=1 or tx.get('phase') not in ('complete','rolled-back','aborted'):raise ValueError('Root updater removal ownership conflict')
    target=disabled;target_raw=proof['disabled'].encode()
    if read(saved/'api')==api_proof['original'].encode():target=original;target_raw=proof['original'].encode()
    for key,path in paths.items():
        if os.path.lexists(path) or read(saved/key)!=target['files'][str(path)]['installed'].encode():raise ValueError('Root updater removed registration changed: '+key)
    hook=Path('/var/lib/webosbrew/init.d/51-clean-your-tv-root-updater');manifest=base/'manifests.d'/(app+'.json')
    if os.path.lexists(hook) or os.path.lexists(manifest):raise ValueError('Root updater removal ownership conflict')
    python=python_command(state)
    expected_hook=('#!/bin/sh\nunset NODE_OPTIONS NODE_PATH\n/usr/bin/node '+str(state/'code/python_boot.js')+' '+str(state)+' '+str(state/'code/run-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n').encode()
    legacy_hook=('#!/bin/sh\n/usr/bin/python3 '+str(state/'code/run-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n').encode()
    if hook_read(saved/'hook',state,hook,app,Path('/media/developer/apps/usr/palm'),expected_hook) not in ((expected_hook,legacy_hook) if python=='/usr/bin/python3' else (expected_hook,)):raise ValueError('Root updater removal ownership conflict')
    value=json.loads(read(saved/'manifest'))
    shape={'id':app,'version':value.get('version'),'serviceFiles':[str(paths['service'])],'apiPermissionFiles':[str(api)],'roleFiles':[str(paths['role']),str(base/'roles.d'/(app+'.app.json'))],'clientPermissionFiles':[str(paths['client']),str(base/'client-permissions.d'/(app+'.app.json'))]}
    if value!=shape or not isinstance(value.get('version'),str) or not re.fullmatch(r'\d+\.\d+\.\d+',value['version']):raise ValueError('Root updater removal ownership conflict')
    current=read(registration)
    if current not in (proof['original'].encode(),proof['disabled'].encode()):raise ValueError('Root updater removal ownership conflict')
    if current==target_raw:return None
    if target is original:raise ValueError('Root updater removal ownership conflict')
    return (registration,target_raw,proof['mode'])


def python_command(state):
    launcher=state/'python-launcher';receipt=state/'python-runtime.json'
    if not os.path.lexists(launcher) and not os.path.lexists(receipt):return '/usr/bin/python3'
    pinned='4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea'
    executable='/var/lib/clean-your-tv-python/'+pinned+'/bin/python3.13'
    value=json.loads(read(receipt))
    if (not isinstance(value,dict) or set(value)!={'schema','executable','archive_sha256','inventory_sha256'} or value.get('schema')!=1
            or value.get('executable')!=executable or value.get('archive_sha256')!=pinned
            or not isinstance(value.get('inventory_sha256'),str) or not re.fullmatch('[a-f0-9]{64}',value['inventory_sha256'])
            or read(launcher)!=('#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+executable+' "$@"\n').encode()
            or stat.S_IMODE(launcher.stat().st_mode)!=0o700):raise ValueError('Unknown updater Python binding')
    return str(launcher)


def operate(action,state=STATE,base=Path('/var/luna-service2-dev'),hook=Path('/var/lib/webosbrew/init.d/52-clean-your-tv-system-updater'),installed=Path('/media/developer/apps/usr/palm'),destination=None,refresh=lambda:None,stop_processes=stop,proc=Path('/proc')):
    if action not in ('status','disable','archive'):raise ValueError('Unsupported supervisor cleanup action')
    state,base,hook,installed=map(Path,(state,base,hook,installed))
    paths={key:base/folder/(SERVICE+suffix) for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json'))}
    paths.update(hook=hook,manifest=base/'manifests.d'/(APP+'.json'),app_role=base/'roles.d'/(APP+'.app.json'),app_client=base/'client-permissions.d'/(APP+'.app.json'))
    package_paths=[installed/kind/name for kind,name in (('applications',APP),('services',SERVICE),('packages',APP))]
    if not os.path.lexists(state):
        active=processes(state/'code',proc)
        if any(p[2] for p in active):raise ValueError('Supervisor bootstrap or worker is active; retry status after it exits')
        if any(os.path.lexists(p) for p in [*paths.values(),*package_paths]) or active:raise ValueError('Supervisor artifacts exist without ownership state')
        return {'present':False}
    directory(state);locks=[]
    def locked(create=False):
        for name in ('daemon.lock','worker.lock'):
            path=state/name
            if not create and not os.path.lexists(path):continue
            if any(saved==name for saved,_ in locks):continue
            fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_CREAT if create else 0),0o600)
            locks.append((name,fd));info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_nlink!=1 or info.st_mode&0o022:raise ValueError('Unsafe supervisor worker lock')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('Supervisor worker is active; retry after recovery')
    def idle():
        if any(p[2] for p in processes(state/'code',proc)):raise ValueError('Supervisor worker is active; retry after recovery')
        path=state/'transaction.json'
        if os.path.lexists(path):
            tx=json.loads(read(path))
            if tx.get('schema')!=1 or tx.get('phase') not in ('complete','rolled-back','aborted'):raise ValueError('Supervisor transaction requires recovery before removal')
    try:
        locked();idle();setup=bootstrap(state)
        journal=state/'cytv-removal.json';record=json.loads(read(journal)) if os.path.lexists(journal) else None
        if os.path.lexists(journal) and (not isinstance(record,dict) or set(record)!={'phase','archive'} or record.get('phase') not in ('disabling','disabled')):raise ValueError('Unknown supervisor removal journal')
        legacy=lockdown(state,base,allow_missing=record is not None and record.get('phase')=='disabled')
        receipt=json.loads(read(state/'registration.json')).get('files')
        if not isinstance(receipt,dict) or set(receipt)!={str(paths[k]) for k in ('service','role','client','api')}:raise ValueError('Unknown supervisor registration ownership inventory')
        expected={key:receipt[str(paths[key])]['installed'].encode() for key in ('service','role','client','api')}
        python=python_command(state)
        expected['hook']=('#!/bin/sh\nunset NODE_OPTIONS NODE_PATH\n/usr/bin/node '+str(state/'code/python_boot.js')+' '+str(state)+' '+str(state/'code/run-system-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n').encode()
        legacy_hook=('#!/bin/sh\n/usr/bin/python3 '+str(state/'code/run-system-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n').encode()
        retained_hook=hook if os.path.lexists(hook) else state/'removed-registration/hook'
        if python=='/usr/bin/python3' and hook_read(retained_hook,state,hook,APP,installed,expected['hook'])==legacy_hook:expected['hook']=legacy_hook
        if record is not None:
            if destination is not None and destination!=record.get('archive'):raise ValueError('Different supervisor archive already reserved')
            destination=record.get('archive')
        if destination is not None and (not isinstance(destination,str) or not re.fullmatch(re.escape(str(state))+r'\.archive-[0-9a-f]{32}',destination)):raise ValueError('Invalid supervisor archive destination')
        saved=state/'removed-registration'
        def owned(key):
            return read(paths[key] if os.path.lexists(paths[key]) else saved/key)
        manifest_raw=owned('manifest');manifest=json.loads(manifest_raw)
        shape={'id':APP,'version':manifest.get('version'),'serviceFiles':[str(paths['service'])],'apiPermissionFiles':[str(paths['api'])],'roleFiles':[str(paths['role']),str(paths['app_role'])],'clientPermissionFiles':[str(paths['client']),str(paths['app_client'])]}
        if manifest!=shape or not isinstance(manifest.get('version'),str) or not re.fullmatch(r'\d+\.\d+\.\d+',manifest['version']):raise ValueError('Unknown supervisor package manifest')
        expected['manifest']=manifest_raw
        role=owned('app_role');client=owned('app_client')
        if json.loads(role)!={'appId':APP,'type':'regular','allowedNames':[APP+'-*'],'trustLevel':'public','permissions':[{'service':APP+'-*','outbound':['*']}]}:raise ValueError('Unknown supervisor app role')
        client_value=json.loads(client)
        if not isinstance(client_value,dict) or set(client_value)!={APP+'-*'} or not isinstance(client_value[APP+'-*'],list) or not all(isinstance(v,str) for v in client_value[APP+'-*']):raise ValueError('Unknown supervisor app permissions')
        expected.update(app_role=role,app_client=client)
        for key,path in paths.items():
            if os.path.lexists(path):
                if (hook_read(path,state,hook,APP,installed,expected['hook']) if key=='hook' else read(path))!=expected[key] or (record is not None and os.path.lexists(saved/key)):raise ValueError('Supervisor registration changed: '+key)
            elif record is None or (hook_read(saved/key,state,hook,APP,installed,expected['hook']) if key=='hook' else read(saved/key))!=expected[key]:raise ValueError('Supervisor registration missing without ownership proof: '+key)
        repair=root_removal_repair(legacy,base) if record is not None and record.get('phase')=='disabled' else None
        if action=='status' and record is None and any(read(Path(name))!=entry['disabled'].encode() for name,entry in legacy.items()):raise ValueError('Legacy lockdown is not active')
        if action=='status':return {'present':True,'bootstrap_complete':record is None,'edition':setup['edition'],'ownership_verified':True,'disabled':record is not None and record['phase']=='disabled','archive':destination}
        if action=='disable' and record is not None and record['phase']=='disabled':
            stop_processes(state/'code');idle()
            if repair is not None:write(*repair)
            return {'present':True,'disabled':True,'removed':False,'archive':destination}
        locked(True);idle()
        if record is None:
            if action=='archive':raise ValueError('Supervisor must be disabled before archive')
            destination=destination or str(state)+'.archive-'+uuid.uuid4().hex
            if os.path.lexists(saved):
                directory(saved)
                if any(saved.iterdir()):raise ValueError('Supervisor backup collision')
            else:saved.mkdir(mode=0o700)
            write(journal,{'phase':'disabling','archive':destination});record={'phase':'disabling','archive':destination}
        if action=='disable':
            for key,path in sorted(paths.items(),key=lambda item:0 if item[0]=='hook' else 1 if item[0]=='manifest' else 2):
                if os.path.lexists(path):os.replace(path,saved/key);sync(path.parent);sync(saved)
            refresh();stop_processes(state/'code')
            for name,entry in legacy.items():
                if record['phase']=='disabled' and not os.path.lexists(name):continue
                if read(Path(name))!=entry['original'].encode():write(Path(name),entry['original'].encode(),entry['mode'])
            refresh()
            write(journal,{'phase':'disabled','archive':destination})
            return {'present':True,'disabled':True,'removed':False,'archive':destination}
        if record['phase']!='disabled':raise ValueError('Supervisor disable operation is unfinished')
        if any(os.path.lexists(p) for p in [*paths.values(),*package_paths]):raise ValueError('Supervisor package or registration remains')
        stop_processes(state/'code');idle();archive=Path(destination)
        if os.path.lexists(archive):raise ValueError('Supervisor archive collision')
        state.rename(archive);sync(state.parent)
        return {'present':False,'disabled':True,'removed':True,'archive':destination}
    finally:
        for _,fd in reversed(locks):os.close(fd)

def main():
    if os.geteuid()!=0:raise PermissionError('Explicit root cleanup required')
    if len(sys.argv) not in (2,3):raise ValueError('Expected status, disable or archive and optional archive destination')
    def refresh():
        ctl=next((p for p in ('/usr/bin/ls-control','/usr/sbin/ls-control') if Path(p).is_file()),None)
        if ctl is None:raise ValueError('LS2 scanner unavailable')
        subprocess.run([ctl,'scan-services'],check=True,timeout=15,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    print(json.dumps(operate(sys.argv[1],destination=sys.argv[2] if len(sys.argv)==3 else None,refresh=refresh)))

if __name__=='__main__':main()
'''
from .startup_remove import HELPER
SCRIPT=SCRIPT.replace('\ndef operate(',HELPER+'\ndef operate(',1)

import base64
import zlib
import io
import tokenize
# Whitespace/comments are transport-only; the readable SCRIPT remains inspectable.
transport=tokenize.untokenize(t for t in tokenize.generate_tokens(io.StringIO(SCRIPT).readline) if t.type!=tokenize.COMMENT)
# Normalize this fixed script's four-space indents for the bounded SSH transport.
transport='\n'.join(' ' *((len(line)-len(line.lstrip()))//4)+line.strip() for line in transport.splitlines() if line.strip())+'\n'
COMMAND='import base64,zlib;exec(zlib.decompress(base64.b85decode('+repr(base64.b85encode(zlib.compress(transport.encode(),9)).decode())+')))'
