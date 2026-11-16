"""Durable edition update coordinator; every mutation is preceded by intent.

A missing terminal receipt is uncertainty, never permission to repeat or undo.
All TV effects, release trust and package inspection belong to the pinned adapter.
"""
import copy
import hashlib
import math
import json
import re
import uuid
from .support.store import encode
from .support.profile import validate as validate_root_profile

IDENTITIES = {'home':'com.gathin.tvhome','helper':'com.local.nativehome','updater':'com.cleanyourtv.updater',
              'root':'com.cleanyourtv.root.preview','root-updater':'com.cleanyourtv.root.updater','root-infrastructure':None}
SETS = {'no-root':('home','helper','updater'),'root':('root','root-updater','root-infrastructure')}
FINISHED = {'complete','rolled-back','aborted'}
PHASES = FINISHED | {'preparing','downloading','backed-up','suspending','installing','verifying','rolling-back','verifying-rollback','recovery-required'}
HEALTH_SECONDS = 120


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})',value):raise ValueError('Invalid version')
    return tuple(map(int,value.split('.')))


def release_set(value,edition):
    if not isinstance(value,dict) or value.get('edition')!=edition or edition not in SETS:raise ValueError('Invalid release edition')
    release=value.get('release')
    if not isinstance(release,str) or not release.startswith('v'):raise ValueError('Invalid release')
    version(release[1:]);components=value.get('components')
    if not isinstance(components,list) or len(components)!=len(SETS[edition]):raise ValueError('Incomplete release set')
    names=[]
    for c in components:
        if not isinstance(c,dict) or c.get('name') not in SETS[edition]:raise ValueError('Invalid component')
        name=c['name'];names.append(name);version(c.get('version'))
        if c.get('application')!=IDENTITIES[name] or c.get('kind')!=('infrastructure' if name=='root-infrastructure' else 'ipk'):raise ValueError('Component identity mismatch')
        if not isinstance(c.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',c['sha256']) or type(c.get('size')) is not int or not 0<c['size']<=64*1024*1024:raise ValueError('Invalid component digest/size')
    if len(set(names))!=len(names):raise ValueError('Duplicate component')
    result=copy.deepcopy(value);result['components'].sort(key=lambda c:SETS[edition].index(c['name']))
    return result


def validate_profile(value,edition):
    if edition not in SETS or not isinstance(value,dict):raise ValueError('Invalid profile edition')
    data=copy.deepcopy(value);renewal=data.pop('renewal',None)
    # Ordinary Home also stores the display layout preference.
    settings=data.get('settings',{})
    layout=settings.pop('tvhome.layout',None)
    checked=validate_root_profile(data)
    if layout is not None:
        if not isinstance(layout,str) or len(layout.encode('utf8'))>4*1024*1024:raise ValueError('Invalid profile layout')
        parsed=json.loads(layout)
        if not isinstance(parsed,dict) or parsed.get('version')!=1 or any(not isinstance(parsed.get(k),list) or len(parsed[k])>200 for k in ('ids','hidden','catalog')):raise ValueError('Invalid profile layout')
        if any(not isinstance(v,str) or len(v)>256 for k in ('ids','hidden') for v in parsed[k]):raise ValueError('Invalid layout app ID')
        if any(not isinstance(v,dict) or not isinstance(v.get('id'),str) or not isinstance(v.get('title'),str) or len(v['id'])>256 or len(v['title'])>256 for v in parsed['catalog']):raise ValueError('Invalid layout catalog')
        checked['settings']['tvhome.layout']=layout
    if renewal is not None:
        if edition!='no-root' or not isinstance(renewal,dict) or set(renewal)-{'enabled','last','lastRenewedAt','error'} or renewal.get('enabled') is not False:raise ValueError('Invalid renewal history')
        if len(encode(renewal))>4096:raise ValueError('Renewal history too large')
        for key in ('last','error'):
            if key in renewal and renewal[key] is not None and not isinstance(renewal[key],(str,dict)):raise ValueError('Invalid renewal history')
        checked['renewal']=copy.deepcopy(renewal)
    if len(encode(checked))>4*1024*1024:raise ValueError('Profile too large')
    return checked


class Manager:
    def __init__(self,store,io):self.store=store;self.io=io;self._launched=set()

    def _now(self):
        now=self.io.now()
        if type(now) not in (int,float) or not math.isfinite(now) or now<0:raise ValueError('Invalid clock')
        return now

    def _load(self):
        tx=self.store.read('transaction')
        if tx is None:return None
        if (not isinstance(tx,dict) or tx.get('schema')!=1 or tx.get('edition') not in SETS
                or not isinstance(tx.get('id'),str) or not re.fullmatch('[a-f0-9]{32}',tx['id'])
                or tx.get('phase') not in PHASES or tx.get('profile')!='profile-'+tx['id']
                or not isinstance(tx.get('profileDigest'),str) or not re.fullmatch('[a-f0-9]{64}',tx['profileDigest'])
                or type(tx.get('rollbackAttempted')) is not bool):raise ValueError('Corrupt system update journal')
        if 'resumeCycle' in tx and tx['resumeCycle']!='rollback':raise ValueError('Corrupt resume cycle')
        for key in ('created','updated'):
            if type(tx.get(key)) not in (int,float) or not math.isfinite(tx[key]) or tx[key]<0:raise ValueError('Corrupt journal clock')
        prior=release_set(tx.get('prior'),tx['edition']);candidate=release_set(tx.get('candidate'),tx['edition'])
        if tx.get('release')!=candidate['release'] or len(tx.get('components',[]))!=len(candidate['components']):raise ValueError('Corrupt journal release')
        for c,trusted in zip(tx['components'],candidate['components']):
            if c.get('name')!=trusted['name'] or c.get('version')!=trusted['version']:raise ValueError('Corrupt component journal')
            for leg in ('installEvidence','rollbackEvidence'):
                e=c.get(leg)
                if not isinstance(e,dict) or set(e)!={'intent','submitted','terminal'} or type(e['intent']) is not bool:raise ValueError('Corrupt component evidence')
                if e['submitted'] is not None and (not e['intent'] or not isinstance(e['submitted'],dict) or not e['submitted']):raise ValueError('Corrupt submission evidence')
                if e['terminal'] is not None and (e['submitted'] is None or not isinstance(e['terminal'],dict) or type(e['terminal'].get('success')) is not bool):raise ValueError('Corrupt terminal evidence')
                if leg=='rollbackEvidence' and e['intent'] and not tx['rollbackAttempted']:raise ValueError('Unexpected rollback intent')
        if tx['phase'] in ('verifying','complete') and not all(self._success(c['installEvidence']) for c in tx['components']):raise ValueError('Health without install proof')
        if tx['phase'] in ('verifying','verifying-rollback'):
            if type(tx.get('launched')) not in (int,float) or not math.isfinite(tx['launched']) or tx.get('deadline')!=tx['launched']+HEALTH_SECONDS:raise ValueError('Corrupt health deadline')
        return tx

    @staticmethod
    def _success(e):return isinstance(e['terminal'],dict) and e['terminal'].get('success') is True

    def _unknown(self, tx):
        if hasattr(self.io, 'screensaver_pending') and self.io.screensaver_pending(tx):
            return True
        return any(c['name']!='root-infrastructure' and c[leg]['intent'] and c[leg]['terminal'] is None
                   for c in tx['components'] for leg in ('installEvidence','rollbackEvidence'))

    def _can_rollback(self,tx):
        return not tx['rollbackAttempted'] and not self._unknown(tx) and any(c['installEvidence']['terminal'] is not None for c in tx['components']) and tx['phase'] not in ('rolled-back','aborted')

    def status(self):
        tx=self._load()
        if tx is not None:tx['canRollback']=self._can_rollback(tx)
        return tx

    def _save(self,tx,phase=None,error=None):
        if phase is not None:tx['phase']=phase
        if error is not None:tx['error']=str(error)[:1024]
        tx['updated']=self._now();tx.pop('canRollback',None);self.store.write('transaction',tx)
        result=copy.deepcopy(tx);result['canRollback']=self._can_rollback(tx);return result

    def _profile(self,tx):
        value=validate_profile(self.store.read(tx['profile']),tx['edition'])
        if hashlib.sha256(encode(value)).hexdigest()!=tx['profileDigest']:raise ValueError('Profile digest mismatch')
        return value

    def install(self,edition,release,profile):
        snapshot=validate_profile(profile,edition)
        if not isinstance(release,str) or not release.startswith('v'):raise ValueError('Invalid release')
        version(release[1:])
        with self.store.lock():
            old=self._load()
            if old and old['phase'] not in FINISHED:raise ValueError('Unfinished system update requires recovery')
            if old and old.get('homeResumePhase')!=old['phase']:
                result=self.io.finish(old);old['homeResume']=result;old['homeResumePhase']=old['phase'];self._save(old)
            self.io.check_legacy();offer=self.io.offer(edition)
            if not isinstance(offer,dict) or offer.get('canInstall') is not True:raise ValueError(offer.get('reason','Update unavailable'))
            candidate=release_set(offer.get('candidate'),edition);prior=release_set(offer.get('prior'),edition)
            if candidate['release']!=release or version(release[1:])<=version(prior['release'][1:]) or not self.io.verify_baseline(prior):raise ValueError('Installed baseline or signed offer changed')
            if any(version(c['version'])<version(p['version']) for c,p in zip(candidate['components'],prior['components'])):raise ValueError('Component downgrade is not permitted')
            identifier=uuid.uuid4().hex;name='profile-'+identifier;self.store.write(name,snapshot)
            if self.store.read(name)!=snapshot:raise ValueError('Profile readback failed')
            evidence=lambda:{'intent':False,'submitted':None,'terminal':None}
            now=self._now();tx={'schema':1,'id':identifier,'edition':edition,'release':release,'candidate':candidate,'prior':prior,
                'profile':name,'profileDigest':hashlib.sha256(encode(snapshot)).hexdigest(),'phase':'preparing','created':now,'updated':now,
                'rollbackAttempted':False,'components':[{'name':c['name'],'version':c['version'],'phase':'pending','installEvidence':evidence(),'rollbackEvidence':evidence()} for c in candidate['components']]}
            return self._save(tx)

    def _verify_set(self,release):
        return all(self.io.verify_installed(copy.deepcopy(c)) for c in release['components'])

    def _launcher_version(self,tx,rollback=False):
        target='root' if tx['edition']=='root' else 'home'
        return next(c['version'] for c in tx['prior' if rollback else 'candidate']['components'] if c['name']==target)

    def _launch(self,tx):
        key=(tx['id'],tx['phase'])
        if key not in self._launched:self.io.launch(tx['edition']);self._launched.add(key)

    def _begin_health(self,tx,rollback):
        if hasattr(self.io, 'sync_screensaver'):
            self.io.sync_screensaver(tx, rollback)
        selected=tx['prior' if rollback else 'candidate']
        if not self._verify_set(selected):return self._save(tx,'recovery-required' if rollback else 'rolling-back','Installed component verification failed')
        tx['launched']=self._now();tx['deadline']=tx['launched']+HEALTH_SECONDS
        self._save(tx,'verifying-rollback' if rollback else 'verifying');self._launch(tx);return self.status()

    def _apply(self,tx,index,rollback=False):
        c=tx['components'][index];leg='rollbackEvidence' if rollback else 'installEvidence';e=c[leg]
        if e['intent'] and c['name']!='root-infrastructure':
            if e['terminal'] is None:return self._save(tx,'recovery-required','Installer outcome unknown; no replay or rollback permitted')
            return tx
        selected=tx['prior' if rollback else 'candidate']['components'][index]
        self.io.check_legacy()
        resuming_local=c['name']=='root-infrastructure' and e['intent']
        if not resuming_local and not self.io.routing_safe():raise ValueError('LG Home routing and input suspension unconfirmed')
        # Rollback admission retains its original durable proof. The original
        # install records intent only after the adapter's read-only preflight.
        if rollback:e['intent']=True;c['phase']='rolling-back';self._save(tx)
        intent_recorded=False
        def intent():
            nonlocal intent_recorded
            if intent_recorded:raise ValueError('Duplicate installer intent callback')
            if not rollback:
                if e['intent'] and not resuming_local:raise ValueError('Original installer intent already exists')
                e['intent']=True;c['phase']='installing';self._save(tx)
            intent_recorded=True
        def submitted(value):
            if not intent_recorded:raise ValueError('Installer intent callback required before submission')
            if c['name']=='root-infrastructure' and e['submitted']==value:return
            if e['submitted'] is not None or not isinstance(value,dict) or not value:raise ValueError('Invalid installer submission')
            e['submitted']=copy.deepcopy(value);self._save(tx)
        def terminal(value):
            if not intent_recorded:raise ValueError('Installer intent callback required before terminal')
            if e['submitted'] is None or e['terminal'] is not None or not isinstance(value,dict) or type(value.get('success')) is not bool:raise ValueError('Invalid terminal proof')
            e['terminal']=copy.deepcopy(value);self._save(tx)
        try:
            self.io.install(copy.deepcopy(selected),submitted,terminal,intent)
            if not intent_recorded:raise ValueError('Installer intent callback was not invoked')
        except Exception as error:
            tx=self._load();e=tx['components'][index][leg]
            if e['terminal'] is None:return self._save(tx,'recovery-required',error)
            raise
        if e['terminal'] is None:return self._save(tx,'recovery-required','Installer outcome unknown; no replay or rollback permitted')
        if not self._success(e):return self._save(tx,'recovery-required' if rollback else 'rolling-back','Component installation failed')
        if not self.io.verify_installed(selected):return self._save(tx,'recovery-required' if rollback else 'rolling-back','Installed component verification failed')
        tx['components'][index]['phase']='rolled-back' if rollback else 'installed';return self._save(tx)

    def run(self):
        with self.store.lock():
            tx=self._load()
            if tx is None:return None
            if tx['phase'] in FINISHED or tx['phase']=='recovery-required':return self.status()
            try:self._profile(tx)
            except ValueError as error:return self._save(tx,'recovery-required',error)
            try:
                phase=tx['phase']
                if phase=='preparing':
                    self.io.check_legacy();return self._save(tx,'downloading')
                if phase=='downloading':
                    self.io.prepare(copy.deepcopy(tx['candidate']),copy.deepcopy(tx['prior']));return self._save(tx,'backed-up')
                if phase=='backed-up':
                    if not self.io.verify_baseline(tx['prior']):raise ValueError('Installed baseline changed')
                    self.io.check_legacy();return self._save(tx,'suspending')
                if phase=='suspending':
                    self.io.suspend(tx)
                    if not self.io.routing_safe():raise ValueError('LG Home routing and input suspension unconfirmed')
                    return self._save(tx,'installing')
                if phase=='installing':
                    for index,c in enumerate(tx['components']):
                        e=c['installEvidence']
                        if e['intent'] and e['terminal'] is None and c['name']!='root-infrastructure':return self._save(tx,'recovery-required','Installer outcome unknown; no replay or rollback permitted')
                        if e['terminal'] is None:return self._apply(tx,index)
                        if not self._success(e):return self._save(tx,'rolling-back','Component installation failed')
                    return self._begin_health(tx,False)
                if phase=='rolling-back':
                    # Reconcile deterministic local bytes before calling any
                    # Root runtime that might be only partly replaced.
                    for index,c in enumerate(tx['components']):
                        if c['name']=='root-infrastructure' and c['installEvidence']['intent'] and c['installEvidence']['terminal'] is None:return self._apply(tx,index)
                    if self._unknown(tx):return self._save(tx,'recovery-required','Installer outcome unknown; no rollback permitted')
                    if not tx['rollbackAttempted']:
                        self.io.suspend(tx)
                        if not self.io.routing_safe():raise ValueError('LG Home restoration unconfirmed')
                        tx['rollbackAttempted']=True;self._save(tx)
                    for index in reversed(range(len(tx['components']))):
                        c=tx['components'][index]
                        if not c['installEvidence']['intent']:continue
                        e=c['rollbackEvidence']
                        if e['intent'] and e['terminal'] is None and c['name']!='root-infrastructure':return self._save(tx,'recovery-required','Rollback outcome unknown; no retry permitted')
                        if e['terminal'] is None:return self._apply(tx,index,True)
                        if not self._success(e):return self._save(tx,'recovery-required','Rollback failed; no retry permitted')
                    return self._begin_health(tx,True)
                if phase in ('verifying','verifying-rollback'):
                    rollback=phase=='verifying-rollback';receipt=self.store.read(('healthy-rollback-' if rollback else 'healthy-')+tx['id']);now=self._now()
                    if receipt is not None:
                        if receipt.get('transaction')!=tx['id'] or receipt.get('version')!=self._launcher_version(tx,rollback) or type(receipt.get('at')) not in (int,float) or not tx['launched']<=receipt['at']<tx['deadline']:raise ValueError('Invalid health receipt')
                        selected=tx['prior' if rollback else 'candidate']
                        if not self._verify_set(selected):raise ValueError('Health component verification failed')
                        if hasattr(self.io, 'verify_screensaver') and not self.io.verify_screensaver(tx, rollback):
                            raise ValueError('Health screensaver package verification failed')
                        self.store.write('current-'+tx['edition'],selected);return self._save(tx,'rolled-back' if rollback else 'complete')
                    if now<tx['launched'] or now>=tx['deadline']:return self._save(tx,'recovery-required' if rollback else 'rolling-back','Launcher profile readiness timed out')
                    self._launch(tx);return self.status()
            except Exception as error:
                durable=self._load()
                if self._unknown(durable):return self._save(durable,'recovery-required',error)
                if not any(c['installEvidence']['intent'] for c in durable['components']):return self._save(durable,'aborted',error)
                if durable['phase']=='rolling-back':return self._save(durable,'recovery-required',error)
                return self._save(durable,'recovery-required' if durable['rollbackAttempted'] else 'rolling-back',error)

    def component_removed(self):
        """Stop at a phase boundary; never reinstall an externally removed package."""
        with self.store.lock():
            tx=self._load()
            if tx is None or tx['phase'] in FINISHED:return tx
            error='CYTV component removed; recovery evidence retained'
            try:
                self.io.suspend(tx)
            except Exception as exc:
                return self._save(tx,'recovery-required',error+': '+str(exc))
            return self._save(tx,'aborted' if not any(c['installEvidence']['intent'] for c in tx['components']) else 'recovery-required',error)

    def reconcile(self):return self.run()

    def rollback(self):
        with self.store.lock():
            tx=self._load()
            if tx is None or tx['phase'] in ('rolled-back','aborted'):return self.status()
            if not self._can_rollback(tx):
                if self._unknown(tx):return self._save(tx,'recovery-required','Installer outcome unknown; no rollback permitted')
                raise ValueError('Rollback unavailable')
            self._profile(tx)
            if tx['phase']=='complete':
                if not self._verify_set(tx['candidate']):raise ValueError('Installed release changed since completion')
                if tx.get('homeResumePhase')!='complete':
                    tx['homeResume']=self.io.finish(tx);tx['homeResumePhase']='complete';self._save(tx)
                tx['resumeCycle']='rollback'
            return self._save(tx,'rolling-back')

    def restore_profile(self,edition):
        tx=self._load()
        if tx is None or tx['edition']!=edition or tx['phase'] not in ('verifying','verifying-rollback','complete','rolled-back'):return None
        rollback=tx['phase'] in ('verifying-rollback','rolled-back')
        return {'profile':self._profile(tx),'transaction':tx['id'],'version':self._launcher_version(tx,rollback),'phase':tx['phase']}

    def healthy(self,edition,transaction,version):
        tx=self._load()
        if tx is None or tx['edition']!=edition or tx['id']!=transaction or tx['phase'] not in ('verifying','verifying-rollback'):raise ValueError('Stale health signal')
        rollback=tx['phase']=='verifying-rollback';now=self._now()
        if self._launcher_version(tx,rollback)!=version or not tx['launched']<=now<tx['deadline']:raise ValueError('Stale health version or deadline')
        self._profile(tx);value={'transaction':transaction,'version':version,'at':now}
        self.store.write(('healthy-rollback-' if rollback else 'healthy-')+transaction,value);return value
