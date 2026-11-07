"""Fixed TV effects for the independent, root-owned system supervisor."""
import base64
import hashlib
import importlib.util
import json
import io
import tarfile
import uuid
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import subprocess
import time
from package_identity import identity, owners_present, TransitionUnknown, ROOT, UPDATER, SYSTEM
from .core import IDENTITIES, SETS, release_set, version
from .support.package import archive, members, safe_bytes, verify_payload
from .support.luna import call

STATE=Path('/var/lib/clean-your-tv-system-updater')
ROOT_STATE=Path('/var/lib/clean-your-tv-root')
ROOT_UPDATER=Path('/var/lib/clean-your-tv-root-updater')
INSTALLED=Path('/media/developer/apps')
VERIFICATION_ERROR='Update information could not be verified. Nothing was installed.'


class OfferUnavailable(ValueError):
    def __init__(self,reason):
        self.reason=reason
        super().__init__('Update information is not available yet. Nothing was installed.' if reason=='feed-unavailable' else 'Could not connect to the update server. Nothing was installed.')


def digest(raw):return hashlib.sha256(raw).hexdigest()


def package_archive(raw):
    """Accept harmless directory records in published ordinary IPKs."""
    files={};directories=set();seen=set();total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as stream:
        for member in stream:
            name=member.name;path=PurePosixPath(name)
            if not name or path.is_absolute() or str(path)!=name or '..' in path.parts or '\\' in name or '\x00' in name or name in seen or len(seen)>=8192:raise ValueError('Unsafe IPK payload')
            seen.add(name)
            if member.isdir():
                if member.size:raise ValueError('Nonempty package directory')
                directories.add(name);continue
            if not member.isfile() or member.size>32*1024*1024:raise ValueError('Unsafe IPK entry')
            total+=member.size
            if total>64*1024*1024:raise ValueError('Oversized IPK payload')
            files[name]=stream.extractfile(member).read(member.size+1)
            if len(files[name])!=member.size:raise ValueError('Truncated IPK entry')
    # A directory may only be an ancestor of a real, permitted file.
    ancestors={str(p) for name in files for p in PurePosixPath(name).parents if str(p)!='.'}
    if directories-ancestors or any(str(p) in files for name in files for p in PurePosixPath(name).parents):raise ValueError('Foreign package directory')
    return files


class Device:
    def __init__(self,store,code=None,root_state=ROOT_STATE,root_updater=ROOT_UPDATER,installed=INSTALLED,uid=0):
        self.store=store;self.state=Path(store.root);self.code=Path(code or Path(__file__).resolve().parents[1]);self.uid=uid
        self.root_state=Path(root_state);self.root_updater=Path(root_updater);self.installed_root=Path(installed)
        self.legacy_states=[self.root_updater/'transaction.json',self.installed_root/'usr/palm/services/com.cleanyourtv.updater.service/state/transaction.json']

    def require_normal_root(self):
        if any(os.path.lexists(self.root_state/name) for name in ('home-backend.json','c1-gate','c1-keyfilter','runtime/c1_gate.py','runtime/c1_keyfilter.py','runtime/c1-home-gate','runtime/c1-keyfilter-guard')):
            raise ValueError('Experimental C1 routing is excluded from normal System Updates')

    def owner_identity(self,owner,purpose='worker'):
        return identity(owner,purpose=purpose,installed=self.installed_root,uid=self.uid,
                        states={ROOT:self.root_state,UPDATER:self.root_updater,SYSTEM:self.state})

    def components_present(self):
        owners=[SYSTEM]
        tx=self.store.read('transaction')
        if tx and tx.get('edition')=='root':owners.extend((ROOT,UPDATER))
        return owners_present(owners,self.owner_identity)

    def require_components(self):
        if not self.components_present():raise ValueError('CYTV component removed; retained recovery requires inspection')

    def integrity(self,*,enforce=True):
        self.require_normal_root()
        if os.path.lexists(self.state/'cytv-removal.json'):raise ValueError('System updater removal is in progress. Continue removal from the computer.')
        receipt=self.store.read('infrastructure')
        if not isinstance(receipt,dict) or receipt.get('schema')!=1 or not isinstance(receipt.get('code'),dict) or not receipt['code']:raise ValueError('One-time System Updater setup required')
        for name,expected in receipt['code'].items():
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or str(path)!=name or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Unsafe supervisor inventory')
            if digest(safe_bytes(self.code/name,limit=4*1024*1024,uid=self.uid))!=expected:raise ValueError('Supervisor infrastructure changed')
        from python_binding import verify_binding
        verify_binding(self.state)
        if enforce:self.enforce_legacy_lockdown()
        return receipt

    def fetch(self,method,payload=None,binary=False):
        if method not in ('offer','verify','package'):raise ValueError('Invalid verifier operation')
        try:
            result=subprocess.run(['/usr/bin/node',str(self.code/'system_updater/policy.js'),method],input=json.dumps(payload or {}).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=80,check=True)
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired,OSError) as error:
            reason='verification-error'
            if isinstance(error,subprocess.TimeoutExpired):reason='connection-error'
            elif isinstance(error,subprocess.CalledProcessError):
                try:
                    raw=error.stdout or b''
                    value=json.loads(raw) if len(raw)<=131072 else None
                    if isinstance(value,dict) and set(value)=={'error'} and value['error'] in ('feed-unavailable','connection-error'):reason=value['error']
                except (ValueError,TypeError):pass
            if method=='offer' and reason in ('feed-unavailable','connection-error'):raise OfferUnavailable(reason) from None
            if reason=='connection-error':raise ValueError('Could not connect to the update server. Nothing was installed.') from None
            raise ValueError(VERIFICATION_ERROR) from None
        if len(result.stdout)>(64*1024*1024 if binary else 131072):raise ValueError(VERIFICATION_ERROR)
        try:return result.stdout if binary else json.loads(result.stdout)
        except (ValueError,TypeError):raise ValueError(VERIFICATION_ERROR) from None

    def _verify_release(self,value,edition):
        checked=release_set(value,edition)
        if 'proof' in checked:
            trusted=release_set(self.fetch('verify',{'proof':checked['proof']}),edition)
            if {k:v for k,v in checked.items() if k!='proof'}!=trusted:raise ValueError('Saved signed release mismatch')
        else:
            baseline=self.store.read('baseline')
            if not baseline or checked!=release_set(baseline,edition):raise ValueError('Untrusted local baseline')
            if any(c.get('local') is not True for c in checked['components']):raise ValueError('Missing local baseline provenance')
        return checked

    def _baseline(self,edition):
        value=self.store.read('current-'+edition) or self.store.read('baseline')
        return self._verify_release(value,edition)

    def installed(self,application):
        if application not in IDENTITIES.values() or application is None:raise ValueError('Foreign application')
        value=(self.owner_identity(application) if application in (ROOT,UPDATER,SYSTEM) else json.loads(safe_bytes(self.installed_root/('usr/palm/applications/'+application+'/appinfo.json'),limit=65536)))
        if value.get('id')!=application:raise ValueError('Installed application identity mismatch')
        version(value.get('version'));return value['version']

    def verify_baseline(self,baseline):
        self._verify_release(baseline,baseline['edition'])
        return all(self.verify_installed(c) for c in baseline['components'])

    @staticmethod
    def graphics_resolution():
        # UHD is graphics capability evidence; never infer from the current app viewport.
        reply=call('luna://com.webos.service.tv.systemproperty/getSystemInfo',{'keys':['UHD']})
        if isinstance(reply,dict) and reply.get('returnValue') is True:
            value=reply.get('UHD')
            if value is True or type(value) is str and value=='true':return '1920x1080'
            if value is False or type(value) is str and value=='false':return '1280x720'
        raise ValueError('TV graphics capability could not be verified')

    def offer(self,edition):
        resolution=self.graphics_resolution()
        self.require_components()
        self.integrity()
        if edition not in SETS:raise ValueError('Invalid edition')
        value=self.fetch('offer',{'edition':edition,'resolution':resolution})
        try:candidate=self._verify_release(value['candidate'],edition)
        except (ValueError,KeyError,TypeError):raise ValueError(VERIFICATION_ERROR) from None
        self.require_graphics(candidate,resolution)
        prior=self._baseline(edition);reason='available'
        if any(version(c['version'])<version(p['version']) for c,p in zip(candidate['components'],prior['components'])):reason='component-downgrade'
        elif version(candidate['release'][1:])<=version(prior['release'][1:]) or all(c['version']==p['version'] for c,p in zip(candidate['components'],prior['components'])):reason='current'
        else:
            try:
                self.check_legacy()
                if not self.verify_baseline(prior):raise ValueError('Installed baseline changed')
                for c in prior['components']:self.inspect(self.cache_bytes(c),c)
                for c in candidate['components']:
                    if c['kind']=='infrastructure':
                        raw=(self.cache_bytes(c) if os.path.lexists(self.cached(c)) else
                             self.fetch('package',{'proof':candidate['proof'],'name':c['name']},binary=True))
                        self.inspect(raw,c)
            except Exception as error:reason=str(error)
        components=[]
        for c in candidate['components']:
            old=next(v for v in prior['components'] if v['name']==c['name'])
            installed=old['version'] if c['kind']=='infrastructure' else self.installed(c['application'])
            components.append({'name':c['name'],'installed':installed,'version':c['version']})
        return {'edition':edition,'release':candidate['release'],'notes':candidate['notes'],'components':components,'canInstall':reason=='available','reason':reason,'candidate':candidate,'prior':prior}

    @staticmethod
    def require_graphics(candidate,resolution):
        name='root' if candidate['edition']=='root' else 'home'
        component=next(c for c in candidate['components'] if c['name']==name)
        suffix='_720p' if resolution=='1280x720' else ''
        expected='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/'+candidate['release']+'/'+IDENTITIES[name]+'_'+component['version']+suffix+'_all.ipk'
        if component.get('url')!=expected:raise ValueError('Signed graphics variant mismatch')

    def check(self,edition):
        try:offer=self.offer(edition)
        except OfferUnavailable as error:
            try:prior=self._baseline(edition)
            except (ValueError,KeyError,TypeError):raise ValueError(VERIFICATION_ERROR) from None
            components=[{'name':c['name'],'installed':c['version'] if c['kind']=='infrastructure' else self.installed(c['application']),'version':None} for c in prior['components']]
            return {'edition':edition,'release':None,'notes':'','components':components,'canInstall':False,'reason':error.reason}
        return {k:v for k,v in offer.items() if k not in ('candidate','prior')}

    def check_legacy(self):
        self.enforce_legacy_lockdown()
        for path in self.legacy_states:
            if not os.path.lexists(path):continue
            value=json.loads(safe_bytes(path,limit=5*1024*1024))
            phase=value.get('phase',value.get('status'))
            if phase not in ('complete','completed','rolled-back','aborted','idle'):raise ValueError('Legacy updater transaction requires recovery')
            if path==self.root_updater/'transaction.json' and value.get('homeResumePhase')!=phase:raise ValueError('Legacy Root Home recovery pending')

    def cached(self,c):
        if not isinstance(c.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',c['sha256']):raise ValueError('Invalid cache identity')
        return self.state/'cache'/c['sha256']

    def cache_bytes(self,c):return safe_bytes(self.cached(c),limit=64*1024*1024,uid=self.uid)

    def _infra_inventory(self):
        pinned=json.loads(safe_bytes(self.code/'infrastructure-paths.json',limit=65536,uid=self.uid))
        if not isinstance(pinned,list) or not pinned or len(set(pinned))!=len(pinned):raise ValueError('Invalid pinned infrastructure inventory')
        for name in pinned:
            if isinstance(name,str) and name.startswith('support/') and name not in ('support/python_binding.py','support/python_boot.js','support/package_data.py','support/package_identity.py','support/updater/store.py','support/updater/package.py','support/startup_guard.py'):raise ValueError('Foreign infrastructure support path')
            if not isinstance(name,str):raise ValueError('Unsafe managed infrastructure path')
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or str(path)!=name or len(path.parts)<2 or path.parts[0] not in ('runtime','service','updater','support'):raise ValueError('Unsafe managed infrastructure path')
        baseline=self.store.read('baseline')
        if not baseline or baseline.get('edition')!='root':raise ValueError('Root infrastructure baseline unavailable')
        c=next((c for c in baseline['components'] if c['name']=='root-infrastructure'),None)
        if not c or not isinstance(c.get('files'),dict):raise ValueError('Missing infrastructure baseline inventory')
        absent=c.get('absent',[])
        if not isinstance(absent,list) or any(not isinstance(name,str) for name in absent) or len(set(absent))!=len(absent) or set(c['files'])&set(absent) or set(c['files'])|set(absent)!=set(pinned):raise ValueError('Baseline does not partition pinned infrastructure inventory')
        return set(pinned)

    def inspect(self,raw,c):
        if len(raw)!=c['size'] or digest(raw)!=c['sha256']:raise ValueError('Package hash mismatch')
        if c['kind']=='infrastructure':
            if c['name']!='root-infrastructure' or c.get('application') is not None:raise ValueError('Foreign infrastructure component')
            files=archive(raw)
            inventory=self._infra_inventory();hashes={name:digest(value) for name,value in files.items()}
            if c.get('local') is True:
                absent=c.get('absent',[]);recorded=c.get('files')
                if not isinstance(recorded,dict) or not isinstance(absent,list) or any(not isinstance(n,str) for n in absent) or len(set(absent))!=len(absent) or set(recorded)&set(absent) or set(recorded)|set(absent)!=inventory or hashes!=recorded:raise ValueError('Local infrastructure inventory/hash mismatch')
            elif set(files)!=inventory:raise ValueError('Infrastructure inventory changed; computer migration required')
            return hashes
        app=IDENTITIES.get(c['name'])
        if not app or c.get('application')!=app:raise ValueError('Foreign application component')
        parts=members(raw);files=package_archive(parts['data.tar.gz']);control=package_archive(parts['control.tar.gz'])
        if set(control)!={'control'}:raise ValueError('Package scripts are forbidden')
        lines=control['control'].decode('utf8').splitlines()
        if lines.count('Package: '+app)!=1 or lines.count('Version: '+c['version'])!=1:raise ValueError('Package control identity mismatch')
        prefix='usr/palm/applications/'+app+'/';info='usr/palm/packages/'+app+'/packageinfo.json'
        services={app+'.service'}
        if app=='com.gathin.tvhome':services={'com.gathin.tvhome.renewal'}
        service_prefixes=tuple('usr/palm/services/'+s+'/' for s in services)
        if any(not (name.startswith(prefix) or name.startswith(service_prefixes) or name==info) for name in files):raise ValueError('Foreign package payload')
        state_markers={prefix+'state/.keep','usr/palm/services/'+app+'.service/state/.keep'} if app=='com.local.nativehome' else set()
        if any('/state/' in name and (name not in state_markers or files[name]!=b'') for name in files):raise ValueError('Mutable state in package payload')
        appinfo=json.loads(files.get(prefix+'appinfo.json',b'{}'));pkg=json.loads(files.get(info,b'{}'))
        if appinfo.get('id')!=app or appinfo.get('version')!=c['version'] or pkg.get('id')!=app or pkg.get('app')!=app or pkg.get('version')!=c['version'] or not isinstance(pkg.get('services'),list) or set(pkg['services'])-services:raise ValueError('Package application identity mismatch')
        if c['name'] in ('home','root') and appinfo.get('systemUpdateProtocol')!=1:raise ValueError('Launcher profile/health protocol incompatible')
        if c['name'] in ('home','root') and 'url' in c:
            expected='1280x720' if c['url'].endswith('_720p_all.ipk') else '1920x1080'
            if appinfo.get('resolution','1920x1080')!=expected:raise ValueError('Package graphics variant mismatch')
        main=appinfo.get('main')
        if not isinstance(main,str) or prefix+main not in files:raise ValueError('Missing package entry point')
        return {name:digest(value) for name,value in files.items()}

    def prepare(self,candidate,prior):
        self.require_normal_root()
        self.require_graphics(candidate,self.graphics_resolution())
        self.require_components()
        self.integrity();self._verify_release(candidate,candidate['edition']);self._verify_release(prior,prior['edition'])
        for c in prior['components']:self.inspect(self.cache_bytes(c),c)
        required=sum(c['size'] for c in candidate['components'])+128*1024*1024
        if shutil.disk_usage(self.state).free<required:raise ValueError('Insufficient space for complete update and rollback')
        for c in candidate['components']:
            target=self.cached(c)
            if os.path.lexists(target):self.inspect(self.cache_bytes(c),c);continue
            raw=self.fetch('package',{'proof':candidate['proof'],'name':c['name']},binary=True);self.inspect(raw,c)
            self.atomic(target,raw,0o600,exclusive=True)
        for c in candidate['components']+prior['components']:self.inspect(self.cache_bytes(c),c)

    @staticmethod
    def sync(path):
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)

    def atomic(self,path,raw,mode=0o600,exclusive=False,owner=None):
        path=Path(path)
        if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Indirect write destination')
        if exclusive and os.path.lexists(path):raise FileExistsError(path)
        temporary=path.with_name('.system-update-'+uuid.uuid4().hex)
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
        try:
            with os.fdopen(fd,'wb') as out:
                out.write(raw);out.flush();os.fchmod(out.fileno(),mode)
                if owner is not None:os.fchown(out.fileno(),*owner)
                os.fsync(out.fileno())
            os.replace(temporary,path);self.sync(path.parent)
        finally:
            if temporary.exists():temporary.unlink()

    def _infra_path(self,name):
        if name not in self._infra_inventory():raise ValueError('Foreign infrastructure destination')
        kind,relative=name.split('/',1)
        if kind=='support':
            if name not in ('support/python_binding.py','support/python_boot.js','support/package_data.py','support/package_identity.py','support/updater/store.py','support/updater/package.py','support/startup_guard.py'):raise ValueError('Foreign infrastructure support path')
            return self.root_state/relative
        return (self.root_updater/'code' if kind=='updater' else self.root_state/kind)/relative

    def _refresh_root_receipts(self,hashes):
        proof_path=self.root_state/'recovery-provision.json';proof=json.loads(safe_bytes(proof_path,limit=1024*1024,uid=self.uid))
        if proof.get('mode')!='recovery-only' or not isinstance(proof.get('files'),dict):raise ValueError('Invalid recovery provisioning receipt')
        inventory=self._infra_inventory()
        if set(hashes)-inventory:raise ValueError('Foreign infrastructure receipt path')
        for name in inventory:
            if name.startswith(('runtime/','service/','support/')):
                path=str(self._infra_path(name))
                if name in hashes:proof['files'][path]=hashes[name]
                else:proof['files'].pop(path,None)
        proof_raw=json.dumps(proof,sort_keys=True,separators=(',',':')).encode();self.atomic(proof_path,proof_raw)
        from .support.store import Store
        root_store=Store(self.root_updater,uid=self.uid);receipt=root_store.read('infrastructure')
        if not isinstance(receipt,dict) or not isinstance(receipt.get('code'),dict):raise ValueError('Missing Root updater receipt')
        updater={name.split('/',1)[1]:h for name,h in hashes.items() if name.startswith('updater/')}
        allowed={name.split('/',1)[1] for name in inventory if name.startswith('updater/')}
        if set(receipt['code'])-allowed or set(updater)-allowed:raise ValueError('Root updater receipt inventory mismatch')
        receipt['code']=updater;receipt['recovery_sha256']=digest(proof_raw);root_store.write('infrastructure',receipt)

    def _trusted_component(self,c):
        tx=self.store.read('transaction')
        if not tx:raise ValueError('No reserved update')
        for key in ('candidate','prior'):
            release=tx[key]
            if any(saved==c for saved in release['components']):self._verify_release(release,tx['edition']);return
        raise ValueError('Component outside reserved release')

    def install(self,c,on_submit,on_terminal,on_intent):
        self.require_normal_root()
        tx=self.store.read('transaction')
        rollback=isinstance(tx,dict) and tx.get('phase')=='rolling-back' and tx.get('rollbackAttempted') is True
        if rollback:
            from .core import Manager
            tx=Manager(self.store,self)._load()
            index=next(i for i,p in enumerate(tx['prior']['components']) if p['name']==c['name'])
            prior=tx['prior']['components'][index];leg=tx['components'][index]['rollbackEvidence']
            if (any(c.get(k)!=prior.get(k) for k in ('version','sha256','size')) or not leg['intent']
                    or c['kind']!='infrastructure' and leg['submitted'] is not None or leg['terminal'] is not None
                    or any(e['installEvidence']['intent'] and e['installEvidence']['terminal'] is None and e['name']!='root-infrastructure' for e in tx['components'])):
                raise ValueError('Original System rollback proof required')
            try:self.require_components()
            except TransitionUnknown:pass  # Complete owner observation; only this original rollback may proceed.
        else:self.require_components()
        self.integrity(enforce=False)
        self._trusted_component(c);raw=self.cache_bytes(c);hashes=self.inspect(raw,c)
        if c['kind']=='infrastructure':self.validate_infrastructure_transition()
        # Only the original synchronous Manager call can persist this intent.
        # All preflight is read-only; lockdown and other effects follow intent.
        on_intent()
        self.enforce_legacy_lockdown()
        if c['kind']=='infrastructure':
            # Infrastructure writes have a durable intent in core and per-file
            # atomic replacement. Restart reconciles only known before/after bytes.
            self._stop_service_processes(str(self.root_state/'service'))
            on_submit({'component':c['name'],'sha256':c['sha256']})
            files=archive(raw)
            for name,value in files.items():
                path=self._infra_path(name)
                mode=stat.S_IMODE(path.stat().st_mode) if os.path.lexists(path) else (0o700 if name=='service/boot-recover.sh' else 0o600)
                if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Indirect managed infrastructure destination')
                if not path.parent.exists():
                    path.parent.mkdir(parents=True,mode=0o700);self.sync(path.parent.parent)
                self.atomic(path,value,mode)
            # A local rollback can remove only paths explicitly absent before
            # bootstrap, and only while bytes still match the trusted candidate.
            tx=self.store.read('transaction');candidate=next(item for item in tx['candidate']['components'] if item['name']=='root-infrastructure')
            candidate_hashes=self.inspect(self.cache_bytes(candidate),candidate)
            for name in c.get('absent',[]):
                path=self._infra_path(name)
                if not os.path.lexists(path):continue
                if digest(safe_bytes(path,uid=self.uid))!=candidate_hashes[name]:raise ValueError('Candidate-created infrastructure changed; refuse removal')
                path.unlink();self.sync(path.parent)
            self._refresh_root_receipts(hashes);self.repair_registrations();self.restart_root_service();on_terminal({'success':True,'sha256':c['sha256']});return
        self.snapshot_mutable()
        from observed_install import install
        result=install(c['application'],str(self.cached(c)),timeout=180,
                       on_ready=lambda:on_submit({'application':c['application'],'sha256':c['sha256']}),
                       on_accepted=lambda e:self.store.write('installer-accepted',e))
        if result.get('completed') is not True:raise RuntimeError('Installer outcome unknown')
        # Persist terminal proof before any post-install restoration can fail.
        on_terminal({'success':True,'event':result['event']})
        self.restore_mutable();self.repair_registrations()

    def verify_installed(self,c):
        hashes=self.inspect(self.cache_bytes(c),c)
        if c['kind']=='infrastructure':
            return (all(digest(safe_bytes(self._infra_path(name),uid=self.uid))==expected for name,expected in hashes.items())
                    and all(not os.path.lexists(self._infra_path(name)) for name in c.get('absent',[])))
        verify_payload(self.installed_root,hashes,uid=self.uid)
        if c['application'] in (ROOT,UPDATER):
            from package_data import read_verified
            info='usr/palm/applications/'+c['application']+'/appinfo.json'
            return json.loads(read_verified(self.installed_root/info,sha256=hashes[info],installed=self.installed_root,uid=self.uid))['version']==c['version']
        return self.installed(c['application'])==c['version']

    def runtime(self,mode,transaction=None):
        if mode not in ('status','suspend-update','finish-update','abort-update'):raise ValueError('Foreign runtime operation')
        from python_binding import command
        args=[command(self.root_state),str(self.root_state/'runtime/cli.py'),mode]
        if transaction is not None:
            if not re.fullmatch('[a-f0-9]{32}',transaction):raise ValueError('Invalid transaction')
            args.append(transaction)
        result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=630 if mode=='suspend-update' else 45,check=True)
        value=json.loads(result.stdout)
        if value.get('returnValue') is not True:raise ValueError('Root recovery operation failed')
        return value.get('result')

    def _guard(self):
        spec=importlib.util.spec_from_file_location('system_update_guard',self.root_state/'runtime/update_guard.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def _root_integrity(self):
        self.require_normal_root()
        from python_binding import verify_binding
        verify_binding(self.root_state);verify_binding(self.root_updater)
        proof_raw=safe_bytes(self.root_state/'recovery-provision.json',limit=1024*1024,uid=self.uid);proof=json.loads(proof_raw)
        from .support.store import Store
        receipt=Store(self.root_updater,uid=self.uid).read('infrastructure')
        if proof.get('mode')!='recovery-only' or not receipt or receipt.get('recovery_sha256')!=digest(proof_raw):raise ValueError('Root recovery receipt mismatch')
        for name,expected in proof['files'].items():
            path=Path(name)
            if not path.is_relative_to(self.root_state) or digest(safe_bytes(path,limit=4*1024*1024,uid=self.uid))!=expected:raise ValueError('Root recovery integrity failed')
        for name,expected in receipt['code'].items():
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or str(p)!=name or digest(safe_bytes(self.root_updater/'code'/name,limit=4*1024*1024,uid=self.uid))!=expected:raise ValueError('Root updater integrity failed')

    def suspend(self,tx):
        self.require_normal_root()
        self.check_legacy();self.snapshot_mutable()
        if tx['edition']=='root':
            self._root_integrity();self._guard().reserve(tx['id'],self.root_state,uid=self.uid)
            if self.runtime('suspend-update',tx['id']) not in ('restored','absent'):raise ValueError('Root suspension unconfirmed')
        else:
            self._pause_renewal(tx);self._suspend_helper(tx)
        self.rpc('luna://com.webos.applicationManager/launch',{'id':'com.webos.app.home'})

    def routing_safe(self):
        tx=self.store.read('transaction')
        if not tx:return False
        if tx['edition']=='root':
            value=self.runtime('status');intent=value.get('intent');effective=value.get('effective',{});profiles=effective.get('profiles',{})
            routes=[effective.get('sam_home'),profiles.get('defaultApps',{}).get('categories',{}).get('home'),profiles.get('idleApp',{}).get('appId')]
            return (not intent or intent.get('phase')=='disabled') and routes==['com.webos.app.home']*3 and profiles.get('idleApp',{}).get('support') is True
        return not self._helper_processes()

    def _mutable_paths(self):
        app=self.installed_root/'usr/palm/applications/com.local.nativehome/state'
        service=self.installed_root/'usr/palm/services/com.local.nativehome.service/state'
        renewal=self.installed_root/'usr/palm/services/com.gathin.tvhome.renewal/state'
        return [app/name for name in ('home-control.json','blocked','ssap-key.json','apps.json')]+[service/'startup-state.json']+[renewal/name for name in ('settings.json','renewal.json')]

    def snapshot_mutable(self):
        tx=self.store.read('transaction')
        if not tx or tx['edition']!='no-root':return
        name='mutable-'+tx['id'];snapshot=self.store.read(name) or {}
        for path in self._mutable_paths():
            if not os.path.lexists(path):continue
            raw=safe_bytes(path,limit=1024*1024);info=path.stat()
            directory=path.parent.stat()
            snapshot[str(path)]={'parent':{'uid':directory.st_uid,'gid':directory.st_gid,'mode':stat.S_IMODE(directory.st_mode)},'bytes':base64.b64encode(raw).decode(),'uid':info.st_uid,'gid':info.st_gid,'mode':stat.S_IMODE(info.st_mode)}
        self.store.write(name,snapshot)

    def restore_mutable(self):
        tx=self.store.read('transaction')
        if not tx or tx['edition']!='no-root':return
        snapshot=self.store.read('mutable-'+tx['id']) or {};allowed={str(p) for p in self._mutable_paths()}
        for name,record in snapshot.items():
            if name not in allowed:raise ValueError('Foreign mutable state')
            path=Path(name)
            # New preference files and emergency markers always win.
            if os.path.lexists(path):continue
            if not path.parent.exists():
                record_parent=record.get('parent')
                if not record_parent or not path.parent.parent.is_dir() or any(p.is_symlink() for p in (path.parent.parent,*path.parent.parent.parents)):raise ValueError('Missing mutable state directory metadata')
                path.parent.mkdir(mode=0o700)
                os.chown(path.parent,record_parent['uid'],record_parent['gid']);os.chmod(path.parent,record_parent['mode']);self.sync(path.parent.parent)
            self.atomic(path,base64.b64decode(record['bytes'],validate=True),record['mode'],owner=(record['uid'],record['gid']))

    def _helper_processes(self):
        home=str(self.installed_root/'usr/palm/applications/com.local.nativehome')
        result=[]
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                args=(entry/'cmdline').read_bytes().split(b'\0');decoded=[v.decode('utf8') for v in args if v]
                if home+'/native.js' in decoded or (decoded and decoded[0] in (home+'/relay','com.local.nativehome')):result.append((int(entry.name),home+'/native.js' in decoded,self._process_start(int(entry.name))))
            except (FileNotFoundError,ProcessLookupError):continue
        return result

    @staticmethod
    def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    def _suspend_helper(self,tx):
        ticket_name='helper-resume-'+self._cycle(tx);ticket=self.store.read(ticket_name)
        helper=self.installed_root/'usr/palm/applications/com.local.nativehome'
        pref=helper/'state/home-control.json';blocked=helper/'state/blocked'
        startup=self.installed_root/'usr/palm/services/com.local.nativehome.service/state/startup-state.json'
        if ticket is None:
            settings=None
            if os.path.lexists(pref):settings=digest(safe_bytes(pref,limit=65536))
            ticket={'boot':self.boot(),'preference':settings,'startupPreference':digest(safe_bytes(startup,limit=65536)) if os.path.lexists(startup) else None,'running':bool(self._helper_processes()),'blocked':os.path.lexists(blocked),'attempted':False,'suspended':False}
            if os.path.lexists(startup):
                raw=safe_bytes(startup,limit=65536);info=startup.stat();parsed=json.loads(raw)
                if not isinstance(parsed,dict) or type(parsed.get('enabled')) is not bool:raise ValueError('Invalid Helper startup preference')
                ticket['startupOriginal']={'bytes':base64.b64encode(raw).decode(),'uid':info.st_uid,'gid':info.st_gid,'mode':stat.S_IMODE(info.st_mode)}
                paused=dict(parsed,enabled=False,systemUpdate=self._cycle(tx));ticket['startupPaused']=json.dumps(paused,separators=(',',':'))
                ticket['startupPreference']=digest(ticket['startupPaused'].encode())
            self.store.write(ticket_name,ticket)
        if 'startupPaused' in ticket and os.path.lexists(startup):
            current=safe_bytes(startup,limit=65536)
            original=base64.b64decode(ticket['startupOriginal']['bytes'],validate=True)
            if current==original:
                record=ticket['startupOriginal'];self.atomic(startup,ticket['startupPaused'].encode(),record['mode'],owner=(record['uid'],record['gid']))
            elif current!=ticket['startupPaused'].encode():
                changed=json.loads(current)
                if not isinstance(changed,dict) or changed.get('enabled') is not False:raise ValueError('Helper startup preference changed during suspension')
                # Explicit off arriving during candidate startup remains the
                # authoritative preference during automatic rollback as well.
                ticket['startupCancelled']=True;ticket['startupPreference']=digest(current);self.store.write(ticket_name,ticket)
        self.snapshot_mutable()
        # Stop the controller before its relay so it cannot turn planned worker
        # termination into an emergency latch. Killing the relay releases grabs.
        processes=self._helper_processes()
        for pid,controller,start in processes:
            if controller:self._signal_checked(pid,start,signal.SIGSTOP)
        for pid,controller,start in processes:
            if not controller:
                try:self._signal_checked(pid,start,signal.SIGKILL)
                except ProcessLookupError:pass
        for pid,controller,start in processes:
            if controller:
                try:self._signal_checked(pid,start,signal.SIGKILL)
                except ProcessLookupError:pass
        end=time.monotonic()+5
        while self._helper_processes() and time.monotonic()<end:time.sleep(.05)
        if self._helper_processes():raise ValueError('Helper input ownership remains active')
        if processes:
            result=subprocess.run([str(helper/'relay'),'cleanup'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=False)
            if result.returncode!=0:raise ValueError('Held remote keys could not be released')
        ticket['suspended']=True;self.store.write(ticket_name,ticket)

    def repair_registrations(self):
        # IPK replacement may reset app service registrations. Restore only the
        # original or installed bytes recorded by explicit computer provision.
        tx=self.store.read('transaction')
        stores=(self.state,self.root_updater) if tx and tx['edition']=='root' else (self.state,)
        for store_root in stores:
            if not (store_root/'registration.json').exists():continue
            from .support.store import Store
            receipt=Store(store_root,uid=self.uid).read('registration')
            for name,record in receipt.get('files',{}).items():
                path=Path(name)
                if not str(path).startswith('/var/luna-service2-dev/') or path.name not in ('com.cleanyourtv.system.updater.service.service','com.cleanyourtv.system.updater.service.service.json','com.cleanyourtv.system.updater.service.api.json','com.cleanyourtv.root.updater.service.service','com.cleanyourtv.root.updater.service.service.json','com.cleanyourtv.root.updater.service.api.json'):raise ValueError('Foreign registration receipt')
                current=safe_bytes(path,limit=65536,uid=self.uid);installed=record['installed'].encode();original=record.get('original')
                if current!=installed:
                    if original is None or current!=original.encode():raise ValueError('Service registration conflict')
                    self.atomic(path,installed,stat.S_IMODE(path.stat().st_mode))
        tx=self.store.read('transaction')
        if tx and tx['edition']=='root':
            self._root_integrity()
            # The provision module and its contract are in the verified Root
            # updater inventory; its plan contains only fixed Root LS2 paths.
            spec=importlib.util.spec_from_file_location('system_root_provision',self.root_updater/'code/provision.py');provision=importlib.util.module_from_spec(spec);spec.loader.exec_module(provision)
            snapshot=json.loads(safe_bytes(self.root_state/'ls2-provision-snapshot.json',limit=65536,uid=self.uid))
            if snapshot.get('phase') is not None:raise ValueError('Root removal in progress')
            original={key:snapshot['files'][str(path)]['original'] for key,path in provision.FILES.items()};planned=provision.plan(original,provision.snapshot_capabilities(snapshot)) if 'capabilities' in snapshot else provision.plan(original)
            for key,path in provision.FILES.items():
                record=snapshot['files'][str(path)];current=safe_bytes(path,limit=65536,uid=self.uid)
                if digest(planned[key])!=record['installed_sha256'] or digest(current) not in (record['original_sha256'],record['installed_sha256']):raise ValueError('Root service registration conflict')
                if current!=planned[key]:self.atomic(path,planned[key],record['mode'],owner=(record['uid'],record['gid']))
            provision.refresh()
        else:self.scan_services()
        self.enforce_legacy_lockdown()

    def finish(self,tx):
        self.require_normal_root()
        self.require_components()
        if tx['phase'] not in ('complete','rolled-back','aborted'):raise ValueError('Update not finished')
        if tx['edition']=='root':
            if tx['phase']!='aborted':self.sync_root_baseline(tx)
            self._root_integrity();value=self.runtime('abort-update' if tx['phase']=='aborted' else 'finish-update',tx['id'])
            if not isinstance(value,dict) or value.get('status') not in ('restored','skipped','cancelled','failed','unchanged','attempted'):raise ValueError('Root Home resume unconfirmed')
            return value
        self.restore_mutable();renewal=self._finish_renewal(tx);name='helper-resume-'+self._cycle(tx);ticket=self.store.read(name)
        if ticket is None:return {'status':'unchanged'}
        helper=self.installed_root/'usr/palm/applications/com.local.nativehome';pref=helper/'state/home-control.json'
        current=digest(safe_bytes(pref,limit=65536)) if os.path.lexists(pref) else None
        startup=self.installed_root/'usr/palm/services/com.local.nativehome.service/state/startup-state.json'
        startup_current=digest(safe_bytes(startup,limit=65536)) if os.path.lexists(startup) else None
        startup_unchanged=startup_current==ticket.get('startupPreference')
        if startup_unchanged and not ticket.get('startupCancelled') and 'startupOriginal' in ticket and ticket['boot']==self.boot():
            record=ticket['startupOriginal'];self.atomic(startup,base64.b64decode(record['bytes'],validate=True),record['mode'],owner=(record['uid'],record['gid']))
            self.snapshot_mutable()
        if ticket.get('attempted'):return {'status':'attempted'}
        if tx['phase']=='aborted' or not ticket.get('suspended') or not ticket.get('running') or ticket.get('blocked') or os.path.lexists(helper/'state/blocked') or ticket['boot']!=self.boot() or current!=ticket['preference'] or not startup_unchanged or ticket.get('startupCancelled'):return {'status':'skipped'}
        ticket['attempted']=True;self.store.write(name,ticket)
        self.rpc('luna://com.webos.applicationManager/launch',{'id':'com.local.nativehome','params':{'nativeHomeAuto':True}})
        return {'status':'attempted'}

    def launch(self,edition):
        self.require_components()
        return self.rpc('luna://com.webos.applicationManager/launch',{'id':IDENTITIES['root' if edition=='root' else 'home']})

    @staticmethod
    def now():return time.time()

    def rpc(self,uri,payload):return call(uri,payload)

    def _renewal_settings(self):return self.installed_root/'usr/palm/services/com.gathin.tvhome.renewal/state/settings.json'

    def _stop_renewal(self):
        self._stop_service_processes(str(self.installed_root/'usr/palm/services/com.gathin.tvhome.renewal'))

    def _stop_service_processes(self,target):
        processes=[]
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                pid=int(entry.name);start=self._process_start(pid)
                args=[a for a in (entry/'cmdline').read_bytes().split(b'\0') if a]
                matches=any(a.decode('utf8') in (target,target+'/service.js') for a in args)
                # webos-service rewrites argv to its bus ID. Require all fixed
                # process bindings before treating that title as our Root worker.
                if not matches and target==str(self.root_state/'service') and args==[b'com.cleanyourtv.root.preview.service']:
                    matches=(entry.stat().st_uid==self.uid and os.readlink(entry/'cwd')==target and os.readlink(entry/'exe')=='/usr/bin/node')
                if matches:
                    if self._process_start(pid)!=start:raise ValueError('Service process changed during inspection')
                    processes.append((pid,start))
            except FileNotFoundError:continue
        for pid,start in processes:self._signal_checked(pid,start,signal.SIGSTOP)
        for pid,start in processes:self._signal_checked(pid,start,signal.SIGKILL)

    def _cancel_renewal(self):
        # Activity-not-found is already cancelled; all other failures block.
        import select
        p=subprocess.Popen(['/usr/bin/luna-send','-n','1','luna://com.palm.activitymanager/cancel',json.dumps({'activityName':'com.gathin.tvhome.renewal.hourly'})],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        raw=b'';end=time.monotonic()+15
        try:
            while time.monotonic()<end:
                if not select.select([p.stdout],[],[],max(0,end-time.monotonic()))[0]:break
                chunk=os.read(p.stdout.fileno(),4096)
                if not chunk:break
                raw+=chunk
                if len(raw)>65536:raise ValueError('Oversized activity response')
                try:reply=json.loads(raw)
                except ValueError:continue
                if reply.get('returnValue') is True or reply.get('errorCode')==2:return
                raise ValueError('Renewal cancellation unconfirmed')
            raise ValueError('Renewal cancellation timed out')
        finally:
            if p.poll() is None:p.terminate()
            try:p.communicate(timeout=1)
            except subprocess.TimeoutExpired:p.kill();p.communicate()

    def _pause_renewal(self,tx):
        self._stop_renewal();path=self._renewal_settings();name='renewal-pause-'+self._cycle(tx);ticket=self.store.read(name)
        if not path.exists():
            parent=path.parent.parent;owner=parent.stat();path.parent.mkdir(mode=0o700,exist_ok=True)
            os.chown(path.parent,owner.st_uid,owner.st_gid)
            self.atomic(path,b'{"enabled":false}',owner=(owner.st_uid,owner.st_gid))
        raw=safe_bytes(path,limit=65536);state=json.loads(raw);info=path.stat()
        if not isinstance(state,dict) or type(state.get('enabled')) is not bool:raise ValueError('Invalid renewal settings')
        pause=state.get('updatePause')
        if pause is not None and (not isinstance(pause,dict) or pause.get('id')!=self._cycle(tx)):raise ValueError('Another updater owns renewal pause')
        if ticket is None:
            ticket={'boot':self.boot(),'wasEnabled':state['enabled'],'confirmed':False,'attempted':False,'original':base64.b64encode(raw).decode()}
            self.store.write(name,ticket)
        if pause is None:
            state['enabled']=False;state['updatePause']={'id':self._cycle(tx),'wasEnabled':ticket['wasEnabled'],'confirmed':True}
            self.atomic(path,json.dumps(state,separators=(',',':')).encode(),stat.S_IMODE(info.st_mode),owner=(info.st_uid,info.st_gid))
        elif state['enabled'] is not False:raise ValueError('Renewal remained enabled while paused')
        self._cancel_renewal();ticket['confirmed']=True;self.store.write(name,ticket)
        self.snapshot_mutable()

    def _finish_renewal(self,tx):
        name='renewal-pause-'+self._cycle(tx);ticket=self.store.read(name)
        if ticket is None:return {'status':'unchanged'}
        if 'outcome' in ticket:return ticket['outcome']
        if ticket.get('attempted'):return {'status':'attempted'}
        self._stop_renewal();path=self._renewal_settings();raw=safe_bytes(path,limit=65536);state=json.loads(raw);info=path.stat();pause=state.get('updatePause')
        if not isinstance(pause,dict) or pause.get('id')!=self._cycle(tx):
            outcome={'status':'skipped'};ticket['outcome']=outcome;self.store.write(name,ticket);return outcome
        resume=ticket.get('confirmed') is True and ticket['boot']==self.boot() and ticket.get('wasEnabled') is True and pause.get('wasEnabled') is True and state.get('enabled') is False
        # Persist the single resume attempt before releasing the pause. A reboot
        # in this window leaves renewal off and never repeats an enable call.
        ticket['attempted']=True;self.store.write(name,ticket)
        state['enabled']=False;state.pop('updatePause',None);state['completedUpdate']=self._cycle(tx)
        written=json.dumps(state,separators=(',',':')).encode();self.atomic(path,written,stat.S_IMODE(info.st_mode),owner=(info.st_uid,info.st_gid))
        self.snapshot_mutable();outcome={'status':'skipped'}
        # Any newly written preference after pause release wins.
        if resume and safe_bytes(path,limit=65536)==written:
            response=self.rpc('luna://com.gathin.tvhome.renewal/enable',{})
            if not response.get('state',{}).get('enabled') is True:raise ValueError('Renewal preference resume unconfirmed')
            outcome={'status':'restored'}
        ticket['outcome']=outcome;self.store.write(name,ticket);return outcome

    @staticmethod
    def _process_start(pid):
        fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return fields[19]

    def _signal_checked(self,pid,start,sig):
        try:
            if self._process_start(pid)!=start:raise ValueError('Process identity changed during suspension')
            os.kill(pid,sig)
        except (FileNotFoundError,ProcessLookupError):return

    def validate_infrastructure_transition(self):
        tx=self.store.read('transaction')
        if not tx or tx.get('edition')!='root':raise ValueError('No Root infrastructure reservation')
        expected=[]
        for leg in ('prior','candidate'):
            c=next(c for c in tx[leg]['components'] if c['name']=='root-infrastructure')
            expected.append(self.inspect(self.cache_bytes(c),c))
        prior=next(c for c in tx['prior']['components'] if c['name']=='root-infrastructure');absent=set(prior.get('absent',[]))
        for name in self._infra_inventory():
            path=self._infra_path(name)
            if not os.path.lexists(path):
                if name not in absent:raise ValueError('Required managed infrastructure is missing')
                continue
            current=digest(safe_bytes(path,limit=32*1024*1024,uid=self.uid))
            if current not in (expected[0].get(name),expected[1].get(name)):raise ValueError('Managed infrastructure conflict; computer recovery required')

    def sync_root_baseline(self,tx):
        if tx.get('edition')!='root' or tx.get('phase') not in ('complete','rolled-back'):return
        selected=tx['prior' if tx['phase']=='rolled-back' else 'candidate']
        c=next(c for c in selected['components'] if c['name']=='root');raw=self.cache_bytes(c);self.inspect(raw,c)
        from .support.store import Store
        store=Store(self.root_updater,uid=self.uid);cache=self.root_updater/'cache';cache.mkdir(mode=0o700,exist_ok=True)
        target=cache/(c['sha256']+'.ipk')
        if target.exists():
            if safe_bytes(target,limit=64*1024*1024,uid=self.uid)!=raw:raise ValueError('Legacy recovery cache conflict')
        else:self.atomic(target,raw,exclusive=True)
        store.write('current',{'version':c['version'],'sha256':c['sha256'],'size':c['size'],'local':True,'writer':{'owner':'system-update','id':tx['id']}})
        own=next(c for c in selected['components'] if c['name']=='root-updater')
        raw=self.cache_bytes(own);hashes=self.inspect(raw,own)
        verify_payload(self.installed_root,hashes,uid=self.uid)
        with tarfile.open(fileobj=io.BytesIO(members(raw)['data.tar.gz']),mode='r:gz') as archive:
            executable=sorted(m.name for m in archive if m.isfile() and m.mode&0o111)
        store.write('installed-package',{'schema':1,'files':hashes,'executable':executable})

    @staticmethod
    def _cycle(tx):return tx['id']+('-rollback' if tx.get('resumeCycle')=='rollback' else '')

    @staticmethod
    def _legacy_lockdown_paths():
        paths=set()
        for base in ('/var/luna-service2-dev','/var/luna-service2'):
            paths.add(base+'/api-permissions.d/com.cleanyourtv.updater.permissions.json')
            paths.add(base+'/com.cleanyourtv.updater.permissions.receipt.json')
        paths.add('/var/luna-service2-dev/api-permissions.d/com.cleanyourtv.root.updater.service.api.json')
        paths.add('/var/lib/clean-your-tv-root-updater/registration.json')
        return paths

    def scan_services(self):
        executable=next((p for p in (Path('/usr/bin/ls-control'),Path('/usr/sbin/ls-control')) if p.is_file()),None)
        if executable is None:raise ValueError('ls-control unavailable')
        subprocess.run([str(executable),'scan-services'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=True)

    def enforce_legacy_lockdown(self):
        if os.path.lexists(self.state/'cytv-removal.json'):raise ValueError('System updater removal is in progress. Continue removal from the computer.')
        receipt=self.store.read('legacy-lockdown')
        if not isinstance(receipt,dict) or receipt.get('schema')!=1 or not isinstance(receipt.get('files'),dict):raise ValueError('Legacy updater exclusion setup required')
        writes=[];allowed=self._legacy_lockdown_paths()
        for name,record in receipt['files'].items():
            if name not in allowed or not isinstance(record,dict) or set(record)!={'original','disabled','mode'} or not isinstance(record['original'],str) or not isinstance(record['disabled'],str) or type(record['mode']) is not int or record['mode'] & ~0o777:raise ValueError('Unsafe legacy exclusion receipt')
            path=Path(name);raw=safe_bytes(path,limit=1024*1024,uid=self.uid);before=record['original'].encode();after=record['disabled'].encode()
            if raw not in (before,after):raise ValueError('Legacy updater permissions changed; computer recovery required')
            if raw!=after:writes.append((path,after,record['mode']))
        # Validate the entire owned set before revoking/restoring any one file.
        for path,raw,mode in writes:self.atomic(path,raw,mode)
        if writes:self.scan_services()

    def restart_root_service(self):
        self._root_integrity()
        self._stop_service_processes(str(self.root_state/'service'))
        response=self.rpc('luna://com.cleanyourtv.root.preview.service/status',{})
        if response.get('root') is not True:raise ValueError('Updated Root recovery service is not running as root')
