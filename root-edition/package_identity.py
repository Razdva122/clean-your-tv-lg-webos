"""Read-only private byte authority for fixed SDK owners.

The private writer's current/transaction is the selector. SDK bytes never select
an anchor. Cache only decompressed expected inventories, never installed presence.
"""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

try:
    from updater.store import Store, encode
    from updater.package import members, archive
except ModuleNotFoundError:
    from system_updater.support.store import Store, encode
    from system_updater.support.package import members, archive
from package_data import read_verified

ROOT='com.cleanyourtv.root.preview'
UPDATER='com.cleanyourtv.root.updater'
SYSTEM='com.cleanyourtv.system.updater'
STATES={ROOT:Path('/var/lib/clean-your-tv-root'),UPDATER:Path('/var/lib/clean-your-tv-root-updater'),SYSTEM:Path('/var/lib/clean-your-tv-system-updater')}
INSTALLED=Path('/media/developer/apps')
FINISHED={'complete','rolled-back','aborted'}
_CACHE={}


class TransitionUnknown(ValueError):
    """Original writer must reconcile its journal; observation grants no replay."""


def digest(raw):return hashlib.sha256(raw).hexdigest()


def store(path,uid):
    result=Store.__new__(Store);result.root=str(path);result.uid=uid
    return result


def _record(path,name,uid):
    if not os.path.lexists(path):return None
    return store(path,uid).read(name)


def _sha(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):raise ValueError('Invalid private package digest')
    return value


def _descriptor(value):
    if (not isinstance(value,dict) or not isinstance(value.get('version'),str)
            or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',value['version'])
            or type(value.get('size')) is not int or not 0<value['size']<=64*1024*1024):
        raise ValueError('Missing private package descriptor')
    _sha(value.get('sha256'))
    writer=value.get('writer')
    if writer is not None:
        if (not isinstance(writer,dict) or set(writer) not in ({'owner','id'},{'owner','id','system'})
                or writer.get('owner') not in ('root-update','system-update') or not isinstance(writer.get('id'),str)
                or not re.fullmatch('[a-f0-9]{32}',writer['id'])
                or writer.get('system') is not None and (writer.get('owner')!='root-update' or not isinstance(writer['system'],str) or not re.fullmatch('[a-f0-9]{32}',writer['system']))):
            raise ValueError('Invalid private package writer')
    if value.get('local') is not True and not isinstance(value.get('proof'),dict) and not isinstance(value.get('url'),str):raise ValueError('Missing original package provenance')
    return value


def _same(a,b):
    return all(a.get(k)==b.get(k) for k in ('version','sha256','size'))


def _evidence(value,system=False):
    keys={'intent','submitted','terminal'} if system else {'submitted','terminal'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('Invalid private installer evidence')
    if system and type(value['intent']) is not bool:raise ValueError('Invalid private installer intent')
    submitted,terminal=value['submitted'],value['terminal']
    if submitted is not None and (not isinstance(submitted,dict) or not submitted or (system and not value['intent'])):raise ValueError('Invalid private submission')
    if terminal is not None and (submitted is None or not isinstance(terminal,dict) or type(terminal.get('success')) is not bool):raise ValueError('Invalid private terminal')
    return terminal is not None and terminal['success'] is True


def _journal(tx,system=False):
    phases=FINISHED|{'preparing','downloading','backed-up','restoring-route','suspending','installing','awaiting-launch','verifying','rolling-back','verifying-rollback','recovery-required'}
    if system:phases-= {'restoring-route','awaiting-launch'}
    else:phases.discard('suspending')
    if (not isinstance(tx,dict) or tx.get('schema')!=1 or not isinstance(tx.get('id'),str)
            or not re.fullmatch('[a-f0-9]{32}',tx['id']) or tx.get('phase') not in phases
            or type(tx.get('rollbackAttempted')) is not bool or tx.get('profile')!='profile-'+tx['id']):raise ValueError('Invalid private transaction')
    _sha(tx.get('profileDigest'))
    for key in ('created','updated'):
        if type(tx.get(key)) not in (int,float) or not math.isfinite(tx[key]) or tx[key]<0:raise ValueError('Invalid private transaction clock')
    if system:
        if tx.get('edition') not in ('root','no-root'):raise ValueError('Invalid private transaction edition')
        expected=('root','root-updater','root-infrastructure') if tx['edition']=='root' else ('home','helper','updater')
        for key in ('prior','candidate'):
            release=tx.get(key)
            if (not isinstance(release,dict) or release.get('edition')!=tx['edition'] or release.get('schema')!=1
                    or not isinstance(release.get('components'),list) or tuple(c.get('name') for c in release['components'])!=expected):raise ValueError('Invalid private release')
            for c in release['components']:_descriptor(c)
        if not isinstance(tx.get('components'),list) or tuple(c.get('name') for c in tx['components'])!=expected:raise ValueError('Invalid private component journal')
        for c,target in zip(tx['components'],tx['candidate']['components']):
            if c.get('version')!=target['version']:raise ValueError('Conflicting private component journal')
            installed=_evidence(c.get('installEvidence'),True);rolled=_evidence(c.get('rollbackEvidence'),True)
            if c['rollbackEvidence']['intent'] and not tx['rollbackAttempted']:raise ValueError('Unexpected private rollback intent')
            if tx['phase'] in ('verifying','complete') and (not installed or tx['rollbackAttempted']):raise ValueError('System health without terminal proof')
            if tx['phase'] in ('verifying-rollback','rolled-back') and c['installEvidence']['intent'] and not rolled:raise ValueError('System rollback health without proof')
            if tx['phase']=='aborted' and c['installEvidence']['intent']:raise ValueError('System aborted after intent')
    else:
        _descriptor(tx.get('prior'));_descriptor(tx.get('candidate'))
        _evidence(tx.get('installEvidence'));_evidence(tx.get('rollbackEvidence'))
        if tx['rollbackAttempted'] and tx['installEvidence']['terminal'] is None:raise ValueError('Rollback without original terminal')
        if not tx['rollbackAttempted'] and any(v is not None for v in tx['rollbackEvidence'].values()):raise ValueError('Unexpected private rollback evidence')
        if tx['phase'] in ('preparing','downloading','backed-up','restoring-route','aborted') and (tx['rollbackAttempted'] or any(v is not None for v in tx['installEvidence'].values())):raise ValueError('Installer evidence before submission phase')
    return tx


def _retained_rollback_pending(tx):
    # The original supervisor declares rollback before suspending Home. Until
    # suspension finishes, its fully committed candidate still owns live health.
    # This never admits normal activation or any interrupted mutation.
    return (tx['phase']=='rolling-back' and tx.get('resumeCycle')=='rollback'
            and tx.get('homeResumePhase')=='complete' and not tx['rollbackAttempted']
            and all(_evidence(c['installEvidence'],True)
                    and c['rollbackEvidence']==dict(intent=False,submitted=None,terminal=None)
                    for c in tx['components']))


def _select(tx,prior,candidate,evidence,purpose,system=False):
    phase=tx['phase'];installed=_evidence(evidence['installEvidence'],system);rolled=_evidence(evidence['rollbackEvidence'],system)
    rollback=evidence['rollbackEvidence'];install=evidence['installEvidence']
    if rollback['submitted'] is not None and not tx['rollbackAttempted']:raise ValueError('Unexpected private rollback')
    if phase=='complete':
        if not installed or tx['rollbackAttempted']:raise ValueError('Completion without terminal install')
        return candidate
    if phase=='rolled-back':
        # System leaves components that were never submitted unchanged.
        if not rolled and not (system and not install['intent']):raise ValueError('Rollback without terminal proof')
        return prior
    if phase=='aborted':
        if install['submitted'] is not None or (system and install['intent']):raise ValueError('Aborted after submission')
        return prior
    if purpose=='live' and system and _retained_rollback_pending(tx):return candidate
    if purpose in ('current','live'):
        # Existing active health may observe the unchanged committed prior until
        # the writer actually captures/suspends intent. This grants no rearm.
        preparing=('preparing','downloading','backed-up','suspending' if system else 'restoring-route')
        if purpose=='live' and phase in preparing and not tx['rollbackAttempted'] and install['submitted'] is None and install['terminal'] is None and not (system and install['intent']):return prior
        raise TransitionUnknown('Package transition inhibits normal rearm')
    if phase=='recovery-required':raise TransitionUnknown('Private transaction requires recovery')
    # Intent with no terminal is unknown even if either package happens to match.
    if ((system and rollback['intent'] or rollback['submitted'] is not None) and rollback['terminal'] is None
            or (system and install['intent'] or install['submitted'] is not None) and install['terminal'] is None):
        raise TransitionUnknown('Original installer outcome unknown')
    if tx['rollbackAttempted']:
        if rolled:return prior
        if rollback['terminal'] is not None:raise TransitionUnknown('Rollback failed')
        if system and not install['intent']:return prior
        # A proved installed candidate may remain while rollback has not submitted.
        if installed:return candidate
        raise TransitionUnknown('Rollback identity unproven')
    if installed:return candidate
    if install['terminal'] is not None:raise TransitionUnknown('Failed install requires original recovery')
    if phase in ('awaiting-launch','verifying','verifying-rollback'):raise ValueError('Health without terminal proof')
    return prior


def _inventory(owner,files):
    prefixes=('usr/palm/applications/'+owner+'/', 'usr/palm/services/'+owner+'.service/')
    info='usr/palm/packages/'+owner+'/packageinfo.json'
    if not isinstance(files,dict) or not 0<len(files)<=4096:raise ValueError('Missing private installed inventory')
    for name,expected in files.items():
        p=PurePosixPath(name)
        if (str(p)!=name or p.is_absolute() or '..' in p.parts or not (name.startswith(prefixes) or name==info)):
            raise ValueError('Foreign private package inventory')
        _sha(expected)
    if 'usr/palm/applications/'+owner+'/appinfo.json' not in files or info not in files:raise ValueError('Incomplete private identity inventory')
    return files


def _package(owner,path,descriptor,uid):
    """Strictly recheck private cache path identity on every observation."""
    descriptor=_descriptor(descriptor);path=Path(path)
    checked=store(path.parent,uid);directory=checked._directory()
    try:
        try:fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        except FileNotFoundError as error:raise ValueError('Private package cache missing') from error
        try:
            before=os.fstat(fd)
            def valid(s):
                if not stat.S_ISREG(s.st_mode) or s.st_uid!=uid or s.st_mode&0o022 or s.st_nlink!=1 or s.st_size!=descriptor['size']:raise ValueError('Unsafe private package cache')
            def binding(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_uid)
            valid(before);key=(str(path),owner,encode(descriptor),binding(before))
            if key in _CACHE:files=_CACHE[key]
            else:
                chunks=[];remaining=before.st_size+1
                while remaining:
                    raw=os.read(fd,min(65536,remaining))
                    if not raw:break
                    chunks.append(raw);remaining-=len(raw)
                raw=b''.join(chunks)
                if len(raw)!=descriptor['size'] or digest(raw)!=descriptor['sha256']:raise ValueError('Private package digest mismatch')
                parts=members(raw);payload=archive(parts['data.tar.gz']);control=archive(parts['control.tar.gz'])
                if set(control)!={'control'}:raise ValueError('Package scripts forbidden')
                lines=control['control'].decode().splitlines()
                if lines.count('Package: '+owner)!=1 or lines.count('Version: '+descriptor['version'])!=1:raise ValueError('Private package control mismatch')
                files=_inventory(owner,{n:digest(b) for n,b in payload.items()})
                _metadata(owner,payload['usr/palm/applications/'+owner+'/appinfo.json'],payload['usr/palm/packages/'+owner+'/packageinfo.json'],descriptor['version'])
                # Bound memory across successive releases; no persistent new current.
                if len(_CACHE)>=12:_CACHE.clear()
                _CACHE[key]=files
            after=os.fstat(fd);now=path.lstat();valid(after);valid(now)
            if binding(before)!=binding(after) or binding(before)!=binding(now):raise ValueError('Private cache replaced')
            if (os.fstat(directory).st_dev,os.fstat(directory).st_ino)!=(path.parent.lstat().st_dev,path.parent.lstat().st_ino):raise ValueError('Private cache directory replaced')
            return dict(files)
        finally:os.close(fd)
    finally:os.close(directory)


def _metadata(owner,appraw,pkgraw,version=None):
    app,pkg=json.loads(appraw),json.loads(pkgraw)
    if (not isinstance(app,dict) or not isinstance(pkg,dict) or app.get('id')!=owner or app.get('type')!='web'
            or pkg.get('id')!=owner or pkg.get('app')!=owner or not isinstance(app.get('version'),str)
            or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',app['version']) or pkg.get('version')!=app['version']
            or version is not None and app['version']!=version):raise ValueError('Package metadata identity mismatch')
    return app


def bootstrap_inventory(root,*,uid=0):
    """Explicit provisioning only; never a fallback for ordinary observations."""
    root=Path(root)
    from installation import terminal_install
    try:
        from updater.package import safe_bytes
    except ModuleNotFoundError:
        from system_updater.support.package import safe_bytes
    deploy=_record(root,'deploy',uid);bundle=_record(root,'bundle',uid)
    stage=deploy.get('stage') if isinstance(deploy,dict) else None
    stages={'install-observed','payload-verified','installed-recovery-only'}|{'provision-'+step+'-'+phase for step in ('apply','resume_pending','refresh','finalize') for phase in ('starting','complete')}
    if (not isinstance(deploy,dict) or deploy.get('app')!=ROOT or stage not in stages
            or not terminal_install(_record(root,'install-terminal',uid),ROOT)
            or not isinstance(bundle,dict) or not isinstance(bundle.get('files'),dict)):
        raise ValueError('Original Root bootstrap proof required')
    raw=safe_bytes(root/'release.json',uid=uid)
    if digest(raw)!=bundle['files'].get('release.json'):raise ValueError('Original Root release changed')
    release=json.loads(raw)
    if (release.get('application_id')!=ROOT or not isinstance(release.get('version'),str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',release['version']) or bundle.get('package')!=ROOT+'_'+release['version']+'_all.ipk'):raise ValueError('Foreign original Root release')
    return dict(_inventory(ROOT,release.get('files')))


def inventory(owner,*,purpose='current',states=None,uid=0):
    if owner not in STATES or purpose not in ('current','worker','admission','live'):raise ValueError('Invalid package identity purpose')
    if purpose=='live' and owner!=ROOT:raise ValueError('Live health belongs only to Root')
    states=STATES if states is None else states
    root,updater,system=(Path(states[o]) for o in (ROOT,UPDATER,SYSTEM))
    if owner==SYSTEM:
        binding=_record(system,'bootstrap-bundle',uid);receipt=_record(system,'installed-package',uid)
        terminal=_record(system,'installed-terminal',uid);bootstrap=_record(system,'bootstrap',uid)
        from installation import terminal_install
        if (not isinstance(binding,dict) or binding.get('schema')!=1 or not isinstance(receipt,dict) or set(receipt)!={'schema','package','files'} or receipt.get('schema')!=1
                or not terminal_install(terminal,SYSTEM) or not isinstance(bootstrap,dict) or bootstrap.get('phase')!='complete'):
            raise ValueError('System own-package proof requires authenticated provisioning')
        descriptor=receipt.get('package');_descriptor(descriptor)
        if binding.get('package')!={k:descriptor[k] for k in ('sha256','size')}:raise ValueError('Conflicting System own-package pin')
        files=_package(owner,system/'cache'/(descriptor['sha256']+'.ipk'),descriptor,uid)
        if files!=receipt.get('files'):raise ValueError('System own-package inventory mismatch')
        return files
    current=_record(updater,'current',uid)
    root_tx=_record(updater,'transaction',uid)
    if root_tx is not None:root_tx=_journal(root_tx)
    sys_tx=_record(system,'transaction',uid)
    if sys_tx is not None:sys_tx=_journal(sys_tx,True)
    if sys_tx is not None and sys_tx['edition']=='root':
        if purpose=='live' and sys_tx['phase'] not in FINISHED and not _retained_rollback_pending(sys_tx) and any(c[leg]['intent'] for c in sys_tx['components'] for leg in ('installEvidence','rollbackEvidence')):
            raise TransitionUnknown('System mutation inhibits live presence')
        name='root' if owner==ROOT else 'root-updater'
        index=('root','root-updater','root-infrastructure').index(name)
        prior,candidate=(sys_tx[k]['components'][index] for k in ('prior','candidate'))
        evidence=sys_tx['components'][index]
        selected=_select(sys_tx,prior,candidate,evidence,purpose,True)
        # A mere captured baseline never supersedes a standalone writer. The
        # original System transaction must actually have submitted this component.
        wrote=evidence['installEvidence']['terminal'] is not None
        active=sys_tx['phase'] not in FINISHED or sys_tx.get('homeResumePhase')!=sys_tx['phase']
        if active or wrote:
            if active:
                if root_tx and root_tx['phase'] not in FINISHED:raise ValueError('Conflicting private writers')
                if owner==ROOT:
                    _descriptor(current)
                    if not any(_same(current,c) for c in (prior,selected)):
                        # An explicitly captured prior IPK may have different
                        # archive/control bytes. Compare only independently
                        # checked private inventories, never matching SDK bytes.
                        original=_package(owner,updater/'cache'/(current['sha256']+'.ipk'),current,uid)
                        baseline=_package(owner,system/'cache'/prior['sha256'],prior,uid)
                        if original!=baseline:raise ValueError('Conflicting Root publication')
                    if (purpose=='current' or purpose=='live' and (sys_tx['phase'] in FINISHED or _retained_rollback_pending(sys_tx))) and (not _same(current,selected) or current.get('writer')!={'owner':'system-update','id':sys_tx['id']}):
                        raise TransitionUnknown('System current publication pending')
                return _package(owner,system/'cache'/selected['sha256'],selected,uid)
            if owner==UPDATER:return _package(owner,system/'cache'/selected['sha256'],selected,uid)
            _descriptor(current);writer=current.get('writer',{})
            system_current=_same(current,selected) and writer=={'owner':'system-update','id':sys_tx['id']}
            standalone=writer.get('owner')=='root-update' and writer.get('system')==sys_tx['id']
            if not system_current and not standalone:raise ValueError('System and Root current disagree')
            # A private standalone prior records which System publication it
            # followed. Carry that exact id across consecutive standalone runs;
            # versions and timestamps cannot decide which writer is newer.
            follows=root_tx is not None and _same(current,root_tx['prior']) and writer==root_tx['prior'].get('writer',{})
            if follows or standalone:
                if root_tx is None:raise ValueError('Standalone current writer proof missing')
                selected_root=_select(root_tx,root_tx['prior'],root_tx['candidate'],root_tx,purpose)
                if root_tx['phase'] in FINISHED:
                    if not _same(current,selected_root):raise ValueError('Root current and terminal disagree')
                    if root_tx['phase'] in ('complete','rolled-back') and writer.get('id')!=root_tx['id']:raise ValueError('Root publication writer mismatch')
                elif not any(_same(current,c) for c in (root_tx['prior'],selected_root)):raise ValueError('Root publication conflict')
                return _package(owner,updater/'cache'/(selected_root['sha256']+'.ipk'),selected_root,uid)
            return _package(owner,system/'cache'/selected['sha256'],selected,uid)
    if owner==ROOT:
        current=_descriptor(current)
        selected=current
        if root_tx and current.get('writer',{}).get('owner')=='system-update':
            follows=_same(current,root_tx['prior']) and current.get('writer')==root_tx['prior'].get('writer')
            if not follows:
                if root_tx['phase'] not in FINISHED:raise ValueError('Conflicting standalone writer')
                root_tx=None  # Finished pre-System journal cannot override current.
        if root_tx:
            selected=_select(root_tx,root_tx['prior'],root_tx['candidate'],root_tx,purpose)
            if root_tx['phase'] in FINISHED and not _same(current,selected):raise ValueError('Root current and terminal disagree')
            if root_tx['phase'] not in FINISHED and not any(_same(current,c) for c in (root_tx['prior'],selected)):raise ValueError('Root current publication conflict')
        return _package(owner,updater/'cache'/(selected['sha256']+'.ipk'),selected,uid)
    receipt=_record(updater,'installed-package',uid)
    if (not isinstance(receipt,dict) or set(receipt)!={'schema','files','executable'} or receipt.get('schema')!=1
            or not isinstance(receipt.get('executable'),list) or len(set(receipt['executable']))!=len(receipt['executable'])
            or not isinstance(receipt.get('files'),dict) or any(n not in receipt['files'] for n in receipt['executable'])):
        raise ValueError('Root Updater own-package proof requires migration/provisioning')
    return dict(_inventory(owner,receipt.get('files')))


def owners_present(owners,observe):
    """Check the whole product before deferring any touched transition."""
    missing=False;unknown=None;failure=None
    for owner in owners:
        try:observe(owner)
        except TransitionUnknown as error:
            if unknown is None:unknown=error
        except FileNotFoundError:missing=True
        except Exception as error:
            if failure is None:failure=error
    if failure is not None:raise failure
    if missing:return False
    if unknown is not None:raise unknown
    return True


def worker_allowed(owner,*,states=None,uid=0):
    """Do not wake a standalone writer while the System writer owns recovery."""
    if owner!=UPDATER:return True
    states=STATES if states is None else states
    tx=_record(Path(states[SYSTEM]),'transaction',uid)
    if tx is None:return True
    tx=_journal(tx,True)
    return tx['phase'] in FINISHED and tx.get('homeResumePhase')==tx['phase']


def identity(owner,*,purpose='current',states=None,installed=INSTALLED,uid=0,full=False):
    files=inventory(owner,purpose=purpose,states=states,uid=uid)
    if purpose=='live':
        active_states=STATES if states is None else states
        tx=_record(Path(active_states[SYSTEM]),'transaction',uid)
        # This short pre-suspension exception must verify the entire still
        # committed candidate, including payload beyond the SDK metadata.
        if tx is not None and tx.get('phase')=='rolling-back':full=True
    app='usr/palm/applications/'+owner+'/appinfo.json';pkg='usr/palm/packages/'+owner+'/packageinfo.json'
    try:
        raw={name:read_verified(Path(installed)/name,sha256=files[name],installed=installed,uid=uid,limit=32*1024*1024)
             for name in (files if full else (app,pkg))}
    except (OSError,ValueError) as error:
        # An owned replacement window is neither ordinary presence nor proved
        # external deletion. Only its original private manager may reconcile it.
        active_states=STATES if states is None else states
        if purpose=='worker':
            sources=[(UPDATER,False)] if owner==ROOT else []
            if owner in (ROOT,UPDATER):sources.append((SYSTEM,True))
            for writer,system in sources:
                tx=_record(Path(active_states[writer]),'transaction',uid)
                if tx is None:continue
                tx=_journal(tx,system)
                if tx['phase'] in FINISHED:continue
                if system:
                    if tx['edition']!='root':continue
                    component=tx['components'][0 if owner==ROOT else 1]
                    touched=any(component[leg]['intent'] for leg in ('installEvidence','rollbackEvidence'))
                else:touched=tx['phase']=='installing' or tx['installEvidence']['submitted'] is not None or tx['rollbackAttempted']
                if touched:raise TransitionUnknown('Installed transition DATA requires original worker verification') from error
        raise
    return _metadata(owner,raw[app],raw[pkg])
