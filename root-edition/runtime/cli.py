#!/usr/bin/python3
"""Root activation, status, restore, boot recovery and diagnostic trials."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import device_adapter as d
from transport import call as luna



def repair_sdk_permissions(installed='/media/developer/apps',states=None,uid=0,version=None):
    """Explicit, lock-held hardening; private writer bytes select every own leaf."""
    import hashlib,os,stat
    from pathlib import Path
    from package_identity import ROOT,inventory,identity
    from package_data import read_verified
    installed=Path(installed)
    expected=inventory(ROOT,states=states,uid=uid)
    info=identity(ROOT,states=states,installed=installed,uid=uid,full=True)
    if info['version']!=version:raise ValueError('Repair version differs from protected manifest')
    files={installed/name:digest for name,digest in expected.items()}
    roots={installed/'usr/palm'/kind/(ROOT+suffix) for kind,suffix in (('applications',''),('services','.service'),('packages',''))}
    directories=set()
    for path in files:
        for parent in path.parents:
            if any(parent==root or root in parent.parents for root in roots):directories.add(parent)
    # Only directories required by the authenticated package may be hardened.
    children={path:{other.name for other in set(files)|directories if other.parent==path} for path in directories}
    fds={};owned={};repaired=0
    def binding(s):return s.st_dev,s.st_ino
    def valid(s,isdir):
        if (not (stat.S_ISDIR(s.st_mode) if isdir else stat.S_ISREG(s.st_mode)) or s.st_uid!=uid
                or s.st_mode&0o7000 or not isdir and s.st_nlink!=1):raise ValueError('Unsafe own package repair path')
    def directory(path):
        if path in fds:return fds[path]
        if path.parent==path:fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        else:fd=os.open(path.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory(path.parent))
        fds[path]=fd
        if path in directories:valid(os.fstat(fd),True);owned[path]=(fd,True)
        return fd
    def verify():
        for path,fd in fds.items():
            if binding(path.lstat())!=binding(os.fstat(fd)):raise ValueError('Package repair path replaced')
        for path,(fd,isdir) in owned.items():
            valid(os.fstat(fd),isdir)
            if isdir:
                if set(os.listdir(fd))!=children[path]:raise ValueError('Unknown own package entries')
            else:
                os.lseek(fd,0,os.SEEK_SET);digest=hashlib.sha256();size=0
                while True:
                    raw=os.read(fd,65536)
                    if not raw:break
                    size+=len(raw)
                    if size>32*1024*1024:raise ValueError('Oversized repair file')
                    digest.update(raw)
                if digest.hexdigest()!=files[path]:raise ValueError('Own package bytes changed')
    try:
        for path in sorted(directories,key=lambda p:len(p.parts)):directory(path)
        for path,digest in files.items():
            read_verified(path,sha256=digest,installed=installed,uid=uid,limit=32*1024*1024)
            fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory(path.parent));fds[path]=fd;owned[path]=(fd,False)
        verify()  # No chmod before the entire package and directory inventory pass.
        for path,(fd,isdir) in sorted(owned.items(),key=lambda item:(not item[1][1],len(item[0].parts))):
            if any(binding(p.lstat())!=binding(os.fstat(f)) for p,f in fds.items()):raise ValueError('Package repair path replaced')
            current=os.fstat(fd);valid(current,isdir);mode=stat.S_IMODE(current.st_mode)
            if mode&0o022:os.fchmod(fd,mode&~0o022);os.fsync(fd);repaired+=1
        verify()
        if inventory(ROOT,states=states,uid=uid)!=expected:raise ValueError('Private package publication changed')
        return {'repaired':repaired,'version':info['version']}
    finally:
        for fd in reversed(list(fds.values())):os.close(fd)


def firmware_access(root='/var/lib/clean-your-tv-root', base='/var/luna-service2-dev', installed='/media/developer/apps/usr/palm', installation='/var/lib/clean-your-tv-installation', enable=True, lock_product=True, refresh=None, uid=0, automatic=False, repair=None, feature='firmware'):
    """Attach fixed feature APIs; retain legacy ACLs and updater contracts."""
    import contextlib, fcntl, hashlib, json, os, re, stat, subprocess, tempfile
    from pathlib import Path
    root,base,installed,installation=map(Path,(root,base,installed,installation))
    app='com.cleanyourtv.root.preview';service=app+'.service';group=service+'.control'
    features={
        'firmware':('homebrew-configuration','firmware-permissions',['org.webosbrew.hbchannel.service/getConfiguration','org.webosbrew.hbchannel.service/setConfiguration']),
        'theme-receiver':('theme-receiver','theme-receiver-permissions',[service+'/'+name for name in ('themeReceiverStart','themeReceiverStatus','themeReceiverRead','themeReceiverStop')])}
    if feature not in features or repair is not None and feature!='firmware':raise ValueError('Invalid permission feature')
    filename,receipt_name,methods=features[feature]
    api=root/'permissions'/(filename+'.api.json');receipt=root/(receipt_name+'.json')
    other=features['theme-receiver' if feature=='firmware' else 'firmware']
    other_api=root/'permissions'/(other[0]+'.api.json')
    manifest=base/'manifests.d'/(app+'.json')
    def digest(raw):return hashlib.sha256(raw).hexdigest()
    def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    content=encoded({group:methods})
    sdk_containers={Path(p) for p in ('/media/developer','/media/developer/apps','/media/developer/apps/usr','/media/developer/apps/usr/palm','/media/developer/apps/usr/palm/applications')}
    def directories(path,sdk=False):
        for parent in (path,*path.parents):
            info=parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0,uid) or (info.st_mode&0o022 and not (sdk and parent in sdk_containers)):raise ValueError('Unsafe firmware permission directory')
    def secure(path,sdk=False):
        directories(path.parent,sdk)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode&0o022 or info.st_size>4194304:raise ValueError('Unsafe firmware permission evidence')
            return stream.read(4194305)
    def read(path):return json.loads(secure(path))
    def atomic(path,data,mode=0o600,owner=None):
        fd,name=tempfile.mkstemp(prefix='.firmware-',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as stream:
                if owner is not None:os.fchown(stream.fileno(),*owner)
                os.fchmod(stream.fileno(),mode);stream.write(data);stream.flush();os.fsync(stream.fileno())
            os.replace(name,path);sync(path.parent)
        finally:
            if os.path.lexists(name):os.unlink(name)
    def sync(path):
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    def lock(path):
        fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=uid or info.st_nlink!=1 or info.st_mode&0o077:os.close(fd);raise ValueError('Unsafe firmware permission lock')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:os.close(fd);raise
        return fd
    if type(enable) is not bool or repair is not None and (not enable or automatic or not callable(repair)):raise ValueError('Invalid firmware permission action')
    for path in (root,base,installation):directories(path)
    directories(installed,sdk=True)
    with contextlib.ExitStack() as locks:
        if lock_product:
            fd=lock(installation/'ownership.lock');locks.callback(os.close,fd)
            lease=read(installation/'operation.json') if os.path.lexists(installation/'operation.json') else None
            if lease is not None and (not isinstance(lease,dict) or set(lease)!={'schema','id','owner','journal','stage','terminal'} or type(lease['schema']) is not int or lease['schema']!=1 or lease['terminal'] is not True or not isinstance(lease['id'],str) or not re.fullmatch('[a-f0-9]{32}',lease['id']) or any(not isinstance(lease[k],str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}',lease[k]) for k in ('owner','journal','stage'))):raise ValueError('Installation or recovery is pending')
        fd=lock(root/'firmware-permissions.lock');locks.callback(os.close,fd)
        journals=[(root/'deploy.json','stage',{'installed-recovery-only'}),(root/'profile-trial.json','state',{'restored'})]
        for folder in ('clean-your-tv-root-updater','clean-your-tv-system-updater'):
            state=root.parent/folder
            journals.extend(((state/'bootstrap.json','phase',{'complete'}),(state/'transaction.json','phase',{'complete','rolled-back','aborted'})))
            if os.path.lexists(state/'cytv-removal.json'):raise ValueError('Removal is pending')
        if lock_product:
            for path,field,finished in journals:
                if not os.path.lexists(path):continue
                value=read(path)
                if not isinstance(value,dict) or value.get(field) not in finished:raise ValueError('Component recovery is pending')
                if path.name=='transaction.json' and value.get('homeResumePhase')!=value.get('phase'):raise ValueError('Home restoration is pending')
            if any(os.path.lexists(root/name) for name in ('update-block.json','cytv-removal.json')):raise ValueError('Root recovery is pending')
        proof=read(root/'recovery-provision.json')
        if not isinstance(proof,dict) or proof.get('version')!=1 or proof.get('mode')!='recovery-only' or not isinstance(proof.get('files'),dict) or not proof['files']:raise ValueError('Missing Root recovery proof')
        for name,expected in proof['files'].items():
            path=Path(name)
            if not path.is_absolute() or '..' in path.parts or root not in path.parents or not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected) or digest(secure(path))!=expected:raise ValueError('Root recovery code changed')
        snapshot=read(root/'ls2-provision-snapshot.json')
        paths={key:base/folder/(service+suffix) for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json'))}
        if not isinstance(snapshot,dict) or snapshot.get('version')!=1 or snapshot.get('service')!=service or snapshot.get('phase') is not None or set(snapshot.get('files',{}))!={str(p) for p in paths.values()}:raise ValueError('Root provisioning is not active')
        for path in paths.values():
            entry=snapshot['files'][str(path)];meta=path.stat()
            if (not isinstance(entry,dict) or not isinstance(entry.get('original'),str) or digest(entry['original'].encode())!=entry.get('original_sha256') or digest(secure(path))!=entry.get('installed_sha256') or (meta.st_uid,meta.st_gid,stat.S_IMODE(meta.st_mode))!=(entry.get('uid'),entry.get('gid'),entry.get('mode'))):raise ValueError('Root registration drift')
        clients=read(paths['client']);original_clients=json.loads(snapshot['files'][str(paths['client'])]['original'])
        if not isinstance(clients,dict) or not isinstance(original_clients,dict) or {name for name,groups in clients.items() if isinstance(groups,list) and group in groups}!={app,app+'-*'} or any(isinstance(groups,list) and group in groups for groups in original_clients.values()):raise ValueError('Root Home group ownership changed')
        raw=secure(manifest);value=json.loads(raw);meta=manifest.stat()
        # Own-service receiver grants and revocation use protected LS2 identity;
        # firmware grants still require the independently checked SDK identity.
        info=json.loads(secure(installed/'applications'/app/'appinfo.json',sdk=True)) if enable and repair is None and feature=='firmware' else value
        version=info.get('version') if isinstance(info,dict) else None
        if not isinstance(info,dict) or info.get('id')!=app or not isinstance(version,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',version):raise ValueError('Root Home identity changed')
        normal={'version':version,'id':app,'serviceFiles':[str(paths['service'])],'apiPermissionFiles':[str(paths['api'])],
            'roleFiles':[str(paths['role']),str(base/'roles.d'/(app+'.app.json'))],
            'clientPermissionFiles':[str(paths['client']),str(base/'client-permissions.d'/(app+'.app.json'))]}
        baseline=normal
        fields={'schema','phase','api_sha256','original','original_sha256','version'}
        def valid_receipt(saved,expected):
            if (not isinstance(saved,dict) or set(saved)!=fields or type(saved['schema']) is not int or saved['schema']!=1 or saved['phase'] not in ('enabling','enabled','disabling','disabled') or saved['api_sha256']!=digest(expected) or not isinstance(saved['original'],str) or digest(saved['original'].encode())!=saved['original_sha256']):raise ValueError('Firmware permission receipt changed')
            prior=json.loads(saved['original'])
            if not isinstance(prior,dict) or prior.get('version')!=saved['version'] or dict(prior,version=version)!=baseline:raise ValueError('Firmware manifest provenance changed')
        # One writer coordinates both attachments. A sibling grant is retained
        # only with exact private bytes and its own resumable receipt.
        if str(other_api) in value.get('apiPermissionFiles',[]):
            other_content=encoded({group:other[2]})
            other_saved=read(root/(other[1]+'.json'));valid_receipt(other_saved,other_content)
            if other_saved['phase']=='disabled' or secure(other_api)!=other_content:raise ValueError('Sibling permission drift')
            normal=dict(baseline,apiPermissionFiles=[str(paths['api']),str(other_api)])
        granted=dict(normal,apiPermissionFiles=[str(paths['api'])]+[str(root/'permissions'/(spec[0]+'.api.json')) for spec in features.values() if spec[0]==filename or str(root/'permissions'/(spec[0]+'.api.json')) in normal['apiPermissionFiles']])
        if value not in (normal,granted):raise ValueError('Unknown SDK manifest')
        saved=read(receipt) if os.path.lexists(receipt) else None
        if saved is not None:
            valid_receipt(saved,content)
            if (saved['phase']=='disabling' and enable) or (saved['phase']=='enabling' and not enable):raise ValueError('Resume the same firmware permission action')
        elif value==granted or os.path.lexists(api):raise ValueError('Firmware permission collision')
        if os.path.lexists(api) and secure(api)!=content:raise ValueError('Firmware API drift')
        if automatic and saved is not None and saved['phase']=='disabled':return {'returnValue':True,'permissions_installed':False}
        if repair is not None:
            repair(version)  # All protected registration/provenance checks precede SDK mutation.
            checked=json.loads(secure(installed/'applications'/app/'appinfo.json',sdk=True))
            if not isinstance(checked,dict) or checked.get('id')!=app or checked.get('version')!=version:raise ValueError('Repaired SDK identity changed')
        if enable and saved is not None and saved['phase']=='enabled' and value==granted and os.path.lexists(api):return {'returnValue':True,'permissions_installed':True,'effective_verified':False,'reopen_home':True}
        if not enable and saved is None:return {'returnValue':True,'permissions_installed':False}
        if enable:
            if saved is None or value==normal and saved['version']!=version:
                original=raw if value==baseline else encoded(baseline)
                saved={'schema':1,'phase':'enabling','api_sha256':digest(content),'original':original.decode(),'original_sha256':digest(original),'version':version}
            else:saved=dict(saved,phase='enabling')
            atomic(receipt,encoded(saved))
            if not os.path.lexists(api.parent):api.parent.mkdir(mode=0o700);sync(api.parent.parent)
            directories(api.parent)
            if not os.path.lexists(api):atomic(api,content)
            if value!=granted:atomic(manifest,encoded(granted),stat.S_IMODE(meta.st_mode),(meta.st_uid,meta.st_gid))
        else:
            saved=dict(saved,phase='disabling');atomic(receipt,encoded(saved))
            original=saved['original'].encode() if saved['version']==version and normal==baseline else encoded(normal)
            if value!=normal:atomic(manifest,original,stat.S_IMODE(meta.st_mode),(meta.st_uid,meta.st_gid))
        if refresh is None:
            ctl=next((p for p in ('/usr/bin/ls-control','/usr/sbin/ls-control') if Path(p).is_file()),None)
            if not ctl:raise ValueError('LS2 scanner unavailable')
            subprocess.run([ctl,'scan-services'],check=True,timeout=15,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        else:refresh()
        expected=granted if enable else normal
        if read(manifest)!=expected:raise ValueError('Firmware manifest readback failed')
        if enable:
            if secure(api)!=content:raise ValueError('Firmware API readback failed')
            atomic(receipt,encoded(dict(saved,phase='enabled')))
        else:
            if os.path.lexists(api):api.unlink();sync(api.parent)
            atomic(receipt,encoded(dict(saved,phase='disabled')))
        return {'returnValue':True,'permissions_installed':enable,'effective_verified':False,'reopen_home':True}


def reconcile_firmware_access():
    ready=True
    for feature in ('firmware','theme-receiver'):
        try:
            firmware_access(lock_product=False,automatic=True,feature=feature)
        except Exception:
            # Access maintenance must never prevent Home, emergency or rollback recovery.
            ready=False
    return ready


def _restore_home(cancel_resume):
    try:
        inhibit(d.STATE)
    except Exception: pass  # Optional audio state must never block Home recovery.
    from intent_runtime import restore
    try:
        if cancel_resume:
            from update_guard import cancel
            cancel(d.STATE,d.EXPECTED_UID)
    finally:
        # Damaged updater evidence must never prevent explicit Home recovery.
        result = restore()
        result = d.main('recover') if result is None else result
    return result


def main(mode, transaction=None):
    if os.geteuid() != 0:
        raise PermissionError('Root required')
    if mode in ('enable','intent-trial','confirm','trial','emergency-trial','boot'):
        from update_guard import control, ProductPending
        # Automatic recovery restores safely without cancelling the updater
        # ticket; only explicit Off or emergency escape revokes Home resume.
        if mode == 'boot' and os.path.lexists(d.STATE/'update-block.json'):
            return _restore_home(cancel_resume=False)
        try:
            with control(d.STATE,d.EXPECTED_UID):
                return execute(mode,transaction)
        except ProductPending:
            if mode == 'boot': return _restore_home(cancel_resume=False)
            raise
    return execute(mode,transaction)


def execute(mode, transaction=None):
    if mode in ('suspend-update','finish-update','abort-update'):
        from update_guard import suspend, finish, abort
        operation = {'suspend-update':suspend,'finish-update':finish,'abort-update':abort}[mode]
        result = operation(transaction,d.STATE,d.EXPECTED_UID)
        if mode == 'finish-update': reconcile_firmware_access()
        return result
    if mode == 'provision-firmware-access':
        return firmware_access(lock_product=False,automatic=True)
    if mode == 'confirm':
        from intent_runtime import confirm
        return confirm(transaction)
    if mode == 'enable':
        from intent_runtime import enable
        return enable()
    if mode == 'intent-trial':
        from intent_runtime import start
        return start()
    if mode == 'emergency-trial':
        from emergency_trial import start
        return start()
    if mode == 'trial':
        from bounded_profile_trial import begin, spawn
        return begin(spawn)
    if mode == 'restore':
        return _restore_home(cancel_resume=True)
    if mode == 'boot':
        from intent_runtime import boot
        result = boot()
        result = d.main('boot') if result is None else result
        reconcile_firmware_access()
        # A feature-owned worker survives UI/JS service lifetimes. Never disturb Home recovery.
        if os.path.lexists(d.STATE/'audio-recovery/policy.json'):
            try:
                audio_main('boot')
            except Exception: pass
        return result
    if mode == 'status':
        from provision import verify
        result = d.main('status')
        try:
            result['recovery'] = verify()
        except (OSError, ValueError, TypeError) as exc:
            result['recovery'] = {'integrity_verified':False,'error':str(exc)}
        result['update_home_resume_available'] = True
        result['candidate'] = d.CANDIDATE
        result['persistent_enable_available'] = result['recovery'].get('integrity_verified',False)
        from intent_runtime import coordinator
        c = coordinator()
        result['intent'] = c.store.read() if c is not None else None
        return result
    raise ValueError('Expected status, trial, emergency-trial, restore, boot, enable, confirm, suspend-update, finish-update or abort-update')


# Optional audio recovery uses the same pinned CLI destination as Home recovery.
SOUND = 'luna://com.webos.service.audio/'
SETTINGS = 'luna://com.webos.settingsservice/'
POWER = 'luna://com.webos.service.tvpower/power/getPowerState'
UNSET = object()
COMMANDS = ('status', 'enable', 'disable', 'restart-earc', 'restore-hdmi', 'restore-setting', 'boot', 'worker')


class Store:
    def __init__(self, root=d.STATE):
        d.trusted_dir(Path(root))
        self.root = Path(root)/'audio-recovery'
        self.root.mkdir(mode=0o700, exist_ok=True)
        d.trusted_dir(self.root)

    def read(self, name):
        try: return d.safe_json(self.root/(name+'.json'))
        except FileNotFoundError: return None

    def save(self, name, value):
        fd, temporary = tempfile.mkstemp(dir=self.root, prefix='.audio-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.root/(name+'.json')); d.sync(self.root)
        finally:
            if os.path.lexists(temporary): os.unlink(temporary)

    def remove(self, name):
        if self.read(name) is not None:
            (self.root/(name+'.json')).unlink(); d.sync(self.root)

    @contextmanager
    def lock(self, name):
        fd = os.open(self.root/(name+'.lock'), os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != d.EXPECTED_UID
                    or info.st_nlink != 1 or info.st_mode & 0o022):
                raise ValueError('Unsafe audio lock')
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            yield
        finally: os.close(fd)

    def stop_token(self):
        value = self.read('stop')
        if value is None: return None
        if (not isinstance(value, dict) or set(value) != {'schema','token'} or value['schema'] != 1
                or not isinstance(value['token'],str) or not re.fullmatch('[0-9a-f]{32}',value['token'])):
            raise ValueError('Invalid audio stop latch')
        return value['token']

    def policy(self):
        value = self.read('policy')
        if value is None: return dict(schema=1, enabled=False, generation=0, acknowledgedStop=None)
        if (not isinstance(value, dict) or set(value) != {'schema','enabled','generation','acknowledgedStop'}
                or type(value['schema']) is not int or value['schema'] != 1
                or type(value['enabled']) is not bool or type(value['generation']) is not int
                or not 0 <= value['generation'] < 2**53
                or value['acknowledgedStop'] is not None and (not isinstance(value['acknowledgedStop'],str)
                    or not re.fullmatch('[0-9a-f]{32}',value['acknowledgedStop']))):
            raise ValueError('Invalid audio policy')
        if self.stop_token() != value['acknowledgedStop']: value = dict(value, enabled=False)
        return value

    def stop(self):
        self.save('stop', dict(schema=1, token=uuid.uuid4().hex))

    def configure(self, enabled, observed_stop=UNSET, expected=None):
        if type(enabled) is not bool: raise ValueError('Boolean required')
        # Acknowledge only evidence observed when this explicit request began.
        # A newer emergency token always wins, without unlink/check races.
        acknowledged = self.stop_token() if observed_stop is UNSET else observed_stop
        with self.lock('policy'):
            old = self.policy()
            if expected is not None and old != expected: return None
            value = dict(schema=1, enabled=enabled, generation=old['generation']+1,
                         acknowledgedStop=acknowledged if enabled else old['acknowledgedStop'])
            self.save('policy', value)
            return self.policy()

    def pending(self):
        value = self.read('pending')
        if value is not None and value != dict(schema=1, original='on'):
            raise ValueError('Invalid audio restoration receipt')
        return value


class WakeWindow:
    """Initial/reconnected Active snapshots never imply a standby transition."""
    def __init__(self, clock=time.monotonic, boot=False):
        self.clock, self.boot = clock, boot
        self.previous, self.started = None, None

    def event(self, state):
        if state == 'Active':
            if self.previous in ('Active Standby', 'Suspend', 'Standby') or self.previous is None and self.boot:
                self.started = self.clock()
        else: self.started = None
        self.previous = state
        self.boot = False

    def due(self):
        if self.started is None: return False
        elapsed = self.clock()-self.started
        if elapsed < 10: return False
        self.started = None
        return elapsed <= 30


def blocked():
    return (os.path.lexists(d.FAILSAFE) or os.path.lexists(d.STATE/'update-block.json')
            or not d.home_present(purpose='live'))


class Engine:
    def __init__(self, store, call=luna, sleep=time.sleep, clock=time.monotonic, blocked=blocked):
        self.store, self.call, self.sleep, self.clock, self.blocked = store, call, sleep, clock, blocked

    def sound(self):
        output = self.call(SOUND+'getSoundOutput', {})
        settings = self.call(SETTINGS+'getSystemSettings', {'category':'sound','keys':['soundOutput','eArcSupport']})
        if output.get('returnValue') is not True or settings.get('returnValue') is not True:
            raise ValueError('Audio read unavailable')
        configured = output.get('settingsSoundOutputs')
        # No guessed default, and no arbitrary selection from multiple routes.
        configured = configured[0] if isinstance(configured, list) and len(configured) == 1 else None
        persisted = settings.get('settings', {}).get('soundOutput')
        if configured is None: configured = persisted
        elif persisted is not None and persisted != configured: configured = None
        return dict(current=output.get('soundOutput'), configured=configured,
                    earc=settings.get('settings', {}).get('eArcSupport'))

    def active(self):
        reply = self.call(POWER, {})
        return reply.get('returnValue') is True and reply.get('state') == 'Active'

    def automatic_supported(self):
        try:
            reply = self.call(POWER, {'subscribe':True})
            return reply.get('returnValue') is True and reply.get('subscribed') is True and isinstance(reply.get('state'), str)
        except (OSError, ValueError, RuntimeError, TimeoutError): return False

    def write(self, setting):
        result = self.call(SETTINGS+'setSystemSettings', {'category':'sound','settings':{'eArcSupport':setting}})
        if result.get('returnValue') is not True: raise ValueError('Audio write rejected')

    def result(self, result):
        self.store.save('last', dict(result=result, uptime=self.clock()))
        return result

    def perform(self, operation, generation=None):
        if operation not in ('restart-earc','restore-hdmi','restore-setting'):
            raise ValueError('Unsupported audio operation')
        try:
            with self.store.lock('operation'):
                policy = self.store.policy()
                if self.blocked() or generation is not None and (not policy['enabled'] or generation != policy['generation']):
                    return self.result('canceled')
                pending = self.store.pending()
                if pending and operation != 'restore-setting': return self.result('needs-restore')
                if not self.active(): return self.result('unsupported')
                before = self.sound()
                if operation == 'restore-setting':
                    if not pending or before['earc'] not in ('on','off'): return self.result('unsupported')
                    with self.store.lock('policy'):
                        if self.blocked() or self.store.policy() != policy: return self.result('canceled')
                        if before['earc'] != 'on': self.write('on')
                    if self.sound()['earc'] != 'on': return self.result('needs-restore')
                    self.store.remove('pending')
                    return self.result('settings-restored')
                if operation == 'restore-hdmi':
                    if before['configured'] != 'external_arc' or before['current'] != 'tv_speaker':
                        return self.result('unsupported')
                    with self.store.lock('policy'):
                        if self.blocked() or self.store.policy() != policy: return self.result('canceled')
                        reply = self.call(SOUND+'setSoundOutput', {'soundOutput':'external_arc'})
                    if reply.get('returnValue') is not True or self.sound()['current'] != 'external_arc':
                        return self.result('unconfirmed')
                    return self.result('route-restored')
                if before != dict(current='external_arc',configured='external_arc',earc='on'):
                    return self.result('unsupported')
                # Serialize the cancellation check and first write with policy changes.
                # A failed disable request is never reported as a successful cancellation.
                uncertain = False
                with self.store.lock('policy'):
                    if self.blocked() or self.store.policy() != policy:
                        return self.result('canceled')
                    self.store.save('pending', dict(schema=1, original='on'))
                    try: self.write('off')
                    except Exception: uncertain = True
                if not uncertain:
                    if self.sound() != dict(current='external_arc',configured='external_arc',earc='off'):
                        return self.result('needs-restore')
                    self.sleep(2)
                # Cleanup does not depend on enabled/Active: disable or standby must not strand our write.
                current = self.sound()
                if current['current'] != 'external_arc' or current['configured'] != 'external_arc' or current['earc'] not in ('on','off'):
                    return self.result('needs-restore')
                if current['earc'] == 'off': self.write('on')
                if self.sound()['earc'] != 'on' or uncertain:
                    return self.result('needs-restore')
                self.store.remove('pending')
                return self.result('settings-restored')
        except BlockingIOError: return 'busy'
        except (OSError, ValueError, RuntimeError, TimeoutError):
            return self.result('needs-restore' if self.store.pending() else 'unavailable')

    def status(self):
        value = self.sound()
        pending = self.store.pending() is not None
        active = self.active() and not self.blocked()
        supported = self.automatic_supported()
        return dict(returnValue=True, enabled=self.store.policy()['enabled'],
                    observer=observer_live(self.store), autoSupported=supported,
                    canRestart=active and not pending and value == dict(current='external_arc',configured='external_arc',earc='on'),
                    canRestoreRoute=active and not pending and value['configured'] == 'external_arc' and value['current'] == 'tv_speaker',
                    needsRestore=pending, canRestoreSetting=active and pending and value['earc'] in ('on','off'),
                    mode='earc' if value['current'] == 'external_arc' and value['earc'] == 'on' else 'other',
                    last=self.store.read('last'))


def inhibit(root=d.STATE):
    # Old runtimes/never-enabled installations need no new state during emergency restore.
    if os.path.lexists(Path(root)/'audio-recovery'):
        Store(root).stop()


def process_live(store, name, maximum_age):
    try:
        ready = store.read(name)
        if not ready or set(ready) != {'pid','start','boot','uptime','generation','kind'}: return False
        from intent_runtime import boot_identity
        policy = store.policy()
        pid = ready['pid']
        if (not policy['enabled'] or type(pid) is not int or pid <= 0
                or ready['generation'] != policy['generation'] or ready['kind'] not in ('boot','watch')): return False
        command = (d.PROC/str(pid)/'cmdline').read_bytes().split(b'\0')
        return (ready['boot'] == boot_identity() and 0 <= time.monotonic()-ready['uptime'] < maximum_age
                and (d.PROC/str(pid)).stat().st_uid == d.EXPECTED_UID
                and command == [sys.executable.encode(), str(Path(__file__).resolve()).encode(), b'audio', b'worker',
                                str(policy['generation']).encode(), ready['kind'].encode(), b'']
                and d.process_start(pid) == ready['start'])
    except (OSError, ValueError, KeyError, TypeError): return False


def observer_live(store):
    return process_live(store, 'observer', 10)


def pending_live(store):
    return process_live(store, 'launch', 45)


def launch(store, boot=False):
    from intent_runtime import boot_identity
    with store.lock('launch'):
        if observer_live(store) or pending_live(store): return
        policy = store.policy()
        if not policy['enabled'] or store.pending(): return
        identity = boot_identity()
        consumed = store.read('cold-boot')
        cold = boot and consumed != {'boot':identity} and time.monotonic() < 120
        # Enabling manually consumes this boot too: a later boot callback is not a new power-on.
        store.save('cold-boot', dict(boot=identity))
        kind = 'boot' if cold else 'watch'
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'audio', 'worker', str(policy['generation']), kind],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 close_fds=True, start_new_session=True)
        store.save('launch', dict(pid=child.pid, start=d.process_start(child.pid), boot=identity,
                                 uptime=time.monotonic(), generation=policy['generation'], kind=kind))


def worker(store, generation=None, boot=False):
    from update_guard import control
    from intent_runtime import boot_identity
    with store.lock('worker'):
        policy = store.policy()
        if generation is not None and generation != policy['generation']: return
        if boot:
            from boot_gate import wait
            if not wait():
                store.configure(False, expected=policy); return
        policy = store.policy()
        if (not policy['enabled'] or store.pending()
                or generation is not None and generation != policy['generation']): return
        engine = Engine(store)
        for reconnect in range(3):
            window = WakeWindow(clock=time.monotonic, boot=boot and reconnect == 0)
            child = subprocess.Popen(['/usr/bin/luna-send','-i',POWER,'{"subscribe":true}'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            data = ''; primed = False; opened = time.monotonic(); last_ready = 0
            try:
                while True:
                    if store.policy() != policy: return
                    if blocked():
                        store.configure(False, expected=policy); return
                    now = time.monotonic()
                    if not primed and now-opened > 5: break
                    if select.select([child.stdout],[],[],.25)[0]:
                        chunk = os.read(child.stdout.fileno(),4096)
                        if not chunk: break
                        data += chunk.decode('utf8')
                        if len(data) > 65536: break
                        while data.strip():
                            data = data.lstrip()
                            try: message, end = json.JSONDecoder().raw_decode(data)
                            except ValueError: break
                            data = data[end:]
                            if (not isinstance(message, dict) or message.get('returnValue') is not True
                                    or not isinstance(message.get('state'), str)
                                    or not primed and message.get('subscribed') is not True):
                                store.configure(False, expected=policy); return
                            window.event(message['state']); primed = True
                    if primed and now-last_ready >= 2:
                        store.save('observer', dict(pid=os.getpid(), start=d.process_start(os.getpid()),
                                   boot=boot_identity(), uptime=now, generation=policy['generation'], kind='boot' if boot else 'watch'))
                        last_ready = now
                    if window.due():
                        try:
                            with control(d.STATE,d.EXPECTED_UID):
                                engine.perform('restart-earc', generation=policy['generation'])
                        except (OSError, ValueError, RuntimeError):
                            engine.result('canceled')
            finally:
                try: store.remove('observer')
                finally:
                    if child.poll() is None: child.terminate()
                    try: child.communicate(timeout=1)
                    except subprocess.TimeoutExpired: child.kill(); child.communicate()
            # Reconnect snapshots are never wake events; bounded retries only.
            time.sleep(1)
        store.configure(False, expected=policy)


def audio_main(command, generation=None, boot=False):
    if os.geteuid() != 0: raise PermissionError('Root required')
    if command not in COMMANDS: raise ValueError('Unknown audio command')
    store = Store()
    engine = Engine(store)
    if command == 'worker':
        worker(store, generation, boot); return dict(returnValue=True)
    if command == 'boot':
        launch(store, boot=True); return dict(returnValue=True)
    if command == 'status': return engine.status()
    if command == 'disable':
        store.stop(); return engine.status()
    # Snapshot before permission/readiness calls: newer emergency or disable wins.
    initial_policy, initial_stop = store.policy(), store.stop_token()
    from update_guard import control
    with control(d.STATE,d.EXPECTED_UID):
        if command == 'enable':
            if (blocked() or store.pending() or not engine.automatic_supported() or not engine.active()
                    or engine.sound() != dict(current='external_arc',configured='external_arc',earc='on')):
                return dict(returnValue=False, errorCode='unavailable')
            if blocked() or store.stop_token() != initial_stop:
                return dict(returnValue=False, errorCode='canceled')
            attempt = store.configure(True, observed_stop=initial_stop, expected=initial_policy)
            if attempt is None or not attempt['enabled']:
                return dict(returnValue=False, errorCode='canceled')
            try:
                launch(store)
                for _ in range(20):
                    if observer_live(store): return engine.status()
                    time.sleep(.1)
            except (OSError, ValueError, RuntimeError): pass
            store.configure(False, expected=attempt)
            return dict(returnValue=False, errorCode='unavailable')
        result = engine.perform(command)
        return dict(returnValue=result in ('settings-restored','route-restored'), result=result)



def audio_entry(args):
    try:
        if len(args) == 3 and args[0] == 'worker' and args[1].isdigit() and args[2] in ('boot','watch'):
            return audio_main('worker', int(args[1]), args[2] == 'boot')
        return audio_main(args[0] if len(args) == 1 and args[0] != 'worker' else '')
    except Exception:
        return dict(returnValue=False, errorCode='unavailable')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'audio':
        print(json.dumps(audio_entry(sys.argv[2:])), flush=True)
    else:
        try:
            result = main(sys.argv[1] if len(sys.argv) in (2,3) else '', sys.argv[2] if len(sys.argv) == 3 else None)
            print(json.dumps({'returnValue':True,'result':result}), flush=True)
            if isinstance(result, str) and result in ('recovering', 'conflict'):
                sys.exit(2)
        except Exception as exc:
            print(json.dumps({'returnValue':False,'error':str(exc)}), flush=True)
            sys.exit(1)
