"""Bounded device effects for replacement of the System Updater's own package."""
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
from .activation import atomic, digest
from .support.store import Store
from .support.package import safe_bytes, members, verify_payload
from .bootstrap_migration import Migration, _descriptor

APP='com.cleanyourtv.system.updater'
SERVICE=APP+'.service'
INSTALLED=Path('/media/developer/apps')
BASE=Path('/var/luna-service2-dev')


def package_files(raw, descriptor):
    from .device import package_archive
    _descriptor(descriptor)
    if len(raw)!=descriptor['size'] or digest(raw)!=descriptor['sha256']:raise ValueError('Supervisor package changed')
    parts=members(raw)
    control=package_archive(parts['control.tar.gz'])
    if set(control)!={'control'}:raise ValueError('Supervisor package scripts forbidden')
    lines=control['control'].decode().splitlines()
    if lines.count('Package: '+APP)!=1 or lines.count('Version: '+descriptor['version'])!=1:raise ValueError('Supervisor control identity mismatch')
    files=package_archive(parts['data.tar.gz'])
    prefixes=('usr/palm/applications/'+APP+'/', 'usr/palm/services/'+SERVICE+'/')
    info='usr/palm/packages/'+APP+'/packageinfo.json'
    if any(not(name.startswith(prefixes) or name==info) for name in files):raise ValueError('Foreign supervisor payload')
    app=json.loads(files.get(prefixes[0]+'appinfo.json',b'{}'));pkg=json.loads(files.get(info,b'{}'))
    if app.get('id')!=APP or pkg.get('id')!=APP or pkg.get('app')!=APP or app.get('version')!=descriptor['version'] or pkg.get('version')!=descriptor['version']:
        raise ValueError('Supervisor package identity mismatch')
    return files


def permissions(value):
    clients=('com.gathin.tvhome','com.cleanyourtv.root.preview','com.cleanyourtv.updater','com.cleanyourtv.root.updater')
    allowed=set(clients)|{name+'-*' for name in clients}
    if not isinstance(value,dict) or set(value)!={'role.json','client.json','api.json'}:raise ValueError('Invalid supervisor permissions')
    role=value['role.json'];client=value['client.json'];api=value['api.json']
    if (not isinstance(role,dict) or set(role)!={'appId','type','allowedNames','permissions'} or role['appId']!=SERVICE
            or role['type']!='regular' or role['allowedNames']!=[SERVICE]
            or not isinstance(role['permissions'],list) or len(role['permissions'])!=1):raise ValueError('Foreign supervisor role')
    entry=role['permissions'][0]
    if (set(entry)!={'service','inbound','outbound'} or entry['service']!=SERVICE or entry['outbound']!=[]
            or not isinstance(entry['inbound'],list) or not set(entry['inbound'])<=allowed):raise ValueError('Foreign supervisor role permissions')
    group=lambda key:isinstance(key,str) and re.fullmatch(re.escape(SERVICE)+r'\.[a-z][a-z0-9-]{0,40}',key)
    if (not isinstance(api,dict) or not api or len(api)>16 or any(not group(key) or not isinstance(methods,list) or not methods or len(methods)>32
            or any(not isinstance(m,str) or not re.fullmatch(re.escape(SERVICE)+r'/[A-Za-z][A-Za-z0-9]{0,48}',m) for m in methods) for key,methods in api.items())):raise ValueError('Foreign supervisor API')
    if not isinstance(client,dict) or not set(client)<=allowed or any(not isinstance(groups,list) or not set(groups)<=set(api) for groups in client.values()):raise ValueError('Foreign supervisor clients')
    return value


def package_path(state, descriptor):
    selected=Path(state)/'engine-state/cache'/(descriptor['sha256']+'.ipk')
    if os.path.lexists(selected):return selected
    # Only the immutable original is stored in the ordinary product cache.
    return Path(state)/'cache'/(descriptor['sha256']+'.ipk')


def generation_inventory(state, uid=0):
    """Read only signed package data; suitable for the fixed private helper."""
    from .bootstrap import Bootstrap
    runtime=Bootstrap(state,uid=uid)
    generation=runtime.store.read('supervisor-generation')
    if generation is None:return None
    if (not isinstance(generation,dict) or set(generation)!={'schema','operation','package','files','terminal','slot'}
            or generation['schema']!=1 or not re.fullmatch('[a-f0-9]{32}',generation['operation'])):raise ValueError('Invalid supervisor generation')
    descriptor=generation['package'];_descriptor(descriptor)
    raw=safe_bytes(package_path(state,descriptor),limit=32*1024*1024,uid=uid)
    files=package_files(raw,descriptor)
    if generation['files']!={name:digest(data) for name,data in files.items()}:raise ValueError('Supervisor generation inventory changed')
    if generation['slot']:
        slot=runtime.slots.verify_slot(generation['slot'])
        if safe_bytes(slot/'system-updater.ipk',limit=32*1024*1024,uid=uid)!=raw:raise ValueError('Supervisor generation differs from signed engine')
    else:
        original=runtime.product.read('installed-package')
        if not original or {k:original['package'][k] for k in descriptor}!=descriptor:raise ValueError('Original supervisor generation changed')
    from installation import terminal_install
    terminal=generation['terminal']
    if not terminal_install(terminal,APP):raise ValueError('Supervisor generation terminal missing')
    if terminal.get('package')!=descriptor:
        original=runtime.product.read('installed-package')
        if (not original or {k:original['package'][k] for k in descriptor}!=descriptor
                or terminal!=runtime.product.read('installed-terminal')):
            raise ValueError('Supervisor generation terminal belongs to another package')
    return generation['files']


class SupervisorIO:
    def __init__(self, runtime, slot, installed=INSTALLED, base=BASE):
        self.runtime=runtime;self.state=runtime.state;self.store=runtime.store;self.slot=Path(slot)
        self.uid=runtime.store.uid;self.installed=Path(installed);self.base=Path(base)
        self.outer=runtime.transaction()

    def path(self, descriptor):return package_path(self.state,descriptor)

    def descriptors(self):
        raw=safe_bytes(self.slot/'system-updater.ipk',limit=32*1024*1024,uid=self.uid)
        from .device import package_archive
        info=json.loads(package_archive(members(raw)['data.tar.gz'])['usr/palm/applications/'+APP+'/appinfo.json'])
        candidate=dict(version=info['version'],sha256=digest(raw),size=len(raw));package_files(raw,candidate)
        previous=self.outer.get('previousGeneration') or self.runtime.product.read('installed-package')
        prior={key:previous['package'][key] for key in ('version','sha256','size')}
        return candidate,prior

    def prepare(self,candidate,prior):
        raw=safe_bytes(self.slot/'system-updater.ipk',limit=32*1024*1024,uid=self.uid)
        package_files(raw,candidate)
        package_files(safe_bytes(self.path(prior),limit=32*1024*1024,uid=self.uid),prior)
        cache=self.state/'engine-state/cache';Store(cache,uid=self.uid)
        target=cache/(candidate['sha256']+'.ipk')
        if target.exists():
            if safe_bytes(target,limit=32*1024*1024,uid=self.uid)!=raw:raise ValueError('Supervisor cache conflict')
        else:atomic(target,raw)
        permissions(json.loads(safe_bytes(self.slot/'permissions.json',limit=65536,uid=self.uid)))

    def install(self,target,on_intent,on_accepted,on_terminal):
        from observed_install import install
        result=install(APP,str(self.path(target)),timeout=180,on_ready=on_intent,on_accepted=on_accepted)
        on_terminal(dict(result,package=target))

    def terminal(self,value,target):
        from installation import terminal_install
        if not terminal_install(value,APP) or value.get('package')!=target:return False
        tx=self.store.read('supervisor-migration')
        evidence=tx['rollbackEvidence' if tx['rollback'] else 'forwardEvidence']
        accepted=evidence.get('accepted')
        if accepted:
            original=accepted.get('details',{});observed=value['event']['details']
            if any(observed.get(key)!=original.get(key) for key in ('ipkFile','client','packageId')):return False
        return True

    def publish(self,tx):
        target=tx['prior'] if tx['rollback'] else tx['candidate']
        files=package_files(safe_bytes(self.path(target),limit=32*1024*1024,uid=self.uid),target)
        if tx['rollback']:
            previous=self.outer.get('previousGeneration')
            slot=previous['slot'] if previous else None
        else:slot=self.store.read('trial')['candidate']
        leg=tx['rollbackEvidence' if tx['rollback'] else 'forwardEvidence']
        terminal=leg['terminal']
        if terminal is None:
            previous=self.outer.get('previousGeneration')
            terminal=previous['terminal'] if previous else self.runtime.product.read('installed-terminal')
        self.store.write('supervisor-generation',dict(schema=1,operation=tx['operation'],package=target,
            files={name:digest(raw) for name,raw in files.items()},terminal=terminal,slot=slot))
        generation_inventory(self.state,self.uid)

    def verify_installed(self,target):
        try:
            files=package_files(safe_bytes(self.path(target),limit=32*1024*1024,uid=self.uid),target)
            verify_payload(self.installed,{name:digest(raw) for name,raw in files.items()},uid=self.uid)
            return True
        except (OSError,ValueError):return False

    def activate(self,tx):
        generation_inventory(self.state,self.uid)
        generation=self.store.read('supervisor-generation')
        code=self.runtime.slots.verify_slot(generation['slot']) if generation['slot'] else self.runtime.code
        plan=permissions(json.loads(safe_bytes(code/'permissions.json',limit=65536,uid=self.uid)))
        original=self.runtime.product.read('registration')
        keys={'service':('services.d',SERVICE+'.service'),'role':('roles.d',SERVICE+'.service.json'),
              'client':('client-permissions.d',SERVICE+'.service.json'),'api':('api-permissions.d',SERVICE+'.api.json')}
        paths={key:self.base/folder/name for key,(folder,name) in keys.items()}
        if set(original.get('files',{}))!={str(path) for path in paths.values()}:raise ValueError('Supervisor registration inventory changed')
        before={key:original['files'][str(path)] for key,path in paths.items()}
        role=json.loads(before['role']['original']);role.update(plan['role.json'])
        registered='Exec=/usr/bin/run-js-service -n '+str(self.installed/'usr/palm/services'/SERVICE)
        service=before['service']['original']
        if service.splitlines().count(registered)!=1:raise ValueError('Supervisor service registration changed')
        desired={'service':service.replace(registered,'Exec='+str(self.state/'run-service')),
                 'role':json.dumps(role),'client':json.dumps(plan['client.json']),'api':json.dumps(plan['api.json'])}
        receipt={'files':{str(paths[key]):{'original':before[key]['original'],'installed':value} for key,value in desired.items()}}
        # Persist the exact before/after registration plan before replacing any
        # LS2 file; retries accept only the old receipt, package original or plan.
        journal=self.store.read('supervisor-registration')
        if journal and journal.get('operation')==tx['operation'] and journal.get('rollback')==tx['rollback']:
            if journal['after']!=receipt:raise ValueError('Supervisor registration plan changed')
        else:
            journal=dict(operation=tx['operation'],rollback=tx['rollback'],before=original,after=receipt)
            self.store.write('supervisor-registration',journal)
        for key,path in paths.items():
            raw=safe_bytes(path,limit=65536,uid=self.uid).decode()
            permitted={journal['before']['files'][str(path)]['installed'],before[key]['original'],desired[key]}
            if raw not in permitted:raise ValueError('Supervisor LS2 registration conflict')
        from .device import Device
        device=Device(self.runtime.product,code=self.runtime.code,uid=self.uid)
        for key,path in paths.items():device.atomic(path,desired[key].encode(),stat.S_IMODE(path.stat().st_mode))
        self.runtime.product.write('registration',receipt)
        # Stop only our root-owned Node service, including webos-service's
        # rewritten argv. The independent Python migration worker survives.
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():continue
            try:
                args=[part.decode() for part in (process/'cmdline').read_bytes().split(b'\0') if part]
                cwd=Path(os.readlink(process/'cwd'))
                allowed=cwd==self.runtime.code or cwd in (self.state/'engine-state/slots/a',self.state/'engine-state/slots/b')
                if process.stat().st_uid==self.uid and os.readlink(process/'exe')=='/usr/bin/node' and allowed and (args==[SERVICE] or str(cwd) in args or str(cwd/'service.js') in args):
                    pid=int(process.name);start=device._process_start(pid);device._signal_checked(pid,start,signal.SIGKILL)
            except FileNotFoundError:continue
        device.scan_services()
        launcher='com.gathin.tvhome' if self.outer['edition']=='no-root' else 'com.cleanyourtv.root.preview'
        result=subprocess.run(['/usr/bin/luna-send','-a',launcher,'-m',launcher+'-cytv','-n','1',
            'luna://'+SERVICE+'/status','{}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25,check=True)
        reply=json.loads(result.stdout)
        if reply.get('returnValue') is not True or reply.get('result',{}).get('id')!=tx['operation']:
            raise ValueError('New System Updater service did not pass its bus readiness check')
