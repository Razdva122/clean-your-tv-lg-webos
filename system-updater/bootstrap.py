"""Stable entry point for signed engine transitions and product API dispatch.

The registered service and startup hook always execute this provisioned copy.
Product engines run in verified slots and cannot supply an executable path via RPC.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import uuid
from .activation import Slots
from .core import version, FINISHED
from .support.store import Store, encode
from .support.package import safe_bytes

STATE = Path('/var/lib/clean-your-tv-system-updater')
CODE = STATE / 'code'
FIELDS = {'check': {'edition'}, 'status': set(), 'install': {'edition', 'release', 'profile'},
          'healthy': {'edition', 'transaction', 'version'}, 'restoreProfile': {'edition'},
          'rollback': set(), 'reconcile': set(), 'repair': {'edition','profile'}}
TERMINAL = {'complete', 'aborted'}


def policy(method, payload=None, code=CODE):
    if method not in ('offer', 'verify', 'package'): raise ValueError('Invalid engine operation')
    result = subprocess.run(['/usr/bin/node', str(code/'system_updater/engine-policy.js'), method],
                            input=encode(payload or {}), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=80, check=False)
    limit = 64*1024*1024 if method == 'package' else 524288
    if result.returncode or len(result.stdout) > limit:
        raise ValueError('System updater information could not be verified. Nothing was installed.')
    return result.stdout if method == 'package' else json.loads(result.stdout)


def pinned_integrity(state=STATE, *, allow_removal=False):
    store = Store(state)
    receipt = store.read('infrastructure')
    if not isinstance(receipt, dict) or receipt.get('schema') != 1 or not receipt.get('code'):
        raise ValueError('Missing bootstrap infrastructure receipt')
    for name, expected in receipt['code'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('Unsafe bootstrap inventory')
        if hashlib.sha256(safe_bytes(state/'code'/name, limit=4*1024*1024, uid=0)).hexdigest() != expected:
            raise ValueError('Bootstrap infrastructure changed')
    if not allow_removal and os.path.lexists(state/'cytv-removal.json'): raise ValueError('System updater removal is pending')
    from python_binding import verify_binding
    verify_binding(state)
    return receipt


class Bootstrap:
    def __init__(self, state=STATE, uid=0):
        self.state = Path(state)
        self.code = self.state/'code'
        self.product = Store(self.state, uid=uid)
        self.store = Store(self.state/'engine-state', uid=uid)
        self.slots = Slots(self.store, self.code, lambda proof: policy('verify', {'proof': proof}, self.code))

    def call(self, code, method, payload=None):
        result = subprocess.run([sys.executable, '-B', str(code/'engine-entry.py'), method],
                                input=encode(payload or {}), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=90, check=False)
        if len(result.stdout) > 8*1024*1024: raise ValueError('Oversized engine response')
        try: response = json.loads(result.stdout)
        except ValueError: raise ValueError('System updater engine did not reply') from None
        if result.returncode or response.get('returnValue') is not True:
            raise ValueError(response.get('errorText', 'System updater engine failed'))
        return response.get('result')

    def current_version(self):
        active = self.store.read('active')
        if active: return policy('verify', {'proof': active['proof']}, self.code)['engine']['version']
        binding = self.product.read('bootstrap-bundle')
        value = binding.get('bundle', {}).get('engine_version') if binding else None
        version(value)
        return value

    def transaction(self):
        tx = self.store.read('transaction')
        if tx is None: return None
        if (tx.get('schema') != 1 or tx.get('edition') not in ('root','no-root')
                or tx.get('phase') not in ('preparing','staging','activating','ready','migrating','handoff','complete','aborted','recovery-required')
                or not isinstance(tx.get('id'),str) or not re.fullmatch('[a-f0-9]{32}',tx['id'])
                or not isinstance(tx.get('lease'),str) or not re.fullmatch('[a-f0-9]{32}',tx['lease'])
                or not isinstance(tx.get('profileDigest'),str) or not re.fullmatch('[a-f0-9]{64}',tx['profileDigest'])
                or tx.get('profile') != 'profile-' + tx['id']):
            raise ValueError('Invalid engine transaction')
        return tx

    def active_transition(self):
        tx = self.transaction()
        return tx if tx and tx['phase'] not in TERMINAL else None

    def save(self, tx, phase, error=None):
        tx = dict(tx, phase=phase)
        if error is not None: tx['error'] = str(error)[:512]
        else: tx.pop('error', None)
        self.store.write('transaction', tx)
        return tx

    def capability(self, edition):
        return {'selfUpdate':True,'engineVersion':self.current_version(),'executor':'root','edition':edition}

    def summary(self, tx):
        rollback = tx['phase'] not in TERMINAL and self.product.read('transaction') == tx['previousTransaction']
        migration=self.store.read('supervisor-migration')
        if migration and migration.get('operation')==tx['id']:
            evidence=migration['forwardEvidence']
            if evidence['intent'] and evidence['terminal'] is None:rollback=False
        return dict(self.capability(tx['edition']), id=tx['id'], release=tx['release'],
                    phase=tx['phase'] if tx['phase'] in TERMINAL|{'recovery-required'} else 'preparing',
                    canRollback=rollback, error=tx.get('error'), engineUpdate=True, repair=tx.get('repair',False))

    def offer(self, edition):
        baseline=self.call(self.slots.active(),'engine-state',{'edition':edition})
        if (not isinstance(baseline,dict) or set(baseline)!={'edition','release','resolution','components'}
                or baseline['edition']!=edition or baseline['resolution'] not in ('1920x1080','1280x720')
                or not isinstance(baseline['release'],str) or not baseline['release'].startswith('v')
                or not isinstance(baseline['components'],list) or not 1<=len(baseline['components'])<=32):
            raise ValueError('Invalid installed engine summary')
        version(baseline['release'][1:])
        seen=set()
        for component in baseline['components']:
            if (not isinstance(component,dict) or set(component)!={'name','version'}
                    or not isinstance(component['name'],str) or not re.fullmatch('[a-z][a-z0-9-]{0,63}',component['name'])
                    or component['name'] in seen):raise ValueError('Invalid installed engine components')
            seen.add(component['name']);version(component['version'])
        resolution=baseline['resolution']
        variant = edition + ('-720p' if resolution == '1280x720' else '')
        found = policy('offer', code=self.code)
        engine = found['catalog']['engine']; candidate = found['catalog']['releases'][variant]
        if sys.version_info[:3] < version(engine['minimumPython']): raise ValueError('Installed Python does not support this updater')
        node = subprocess.run(['/usr/bin/node','--version'], stdout=subprocess.PIPE, check=True, timeout=5).stdout.decode().strip().lstrip('v')
        if version(node)[0] < engine['minimumNode']: raise ValueError('Installed TV runtime does not support this updater')
        installed_engine = version(self.current_version())
        offered_engine = version(engine['version'])
        if offered_engine < installed_engine: raise ValueError('Engine downgrade refused')
        components = [{ 'name':c['name'], 'version':c['version'],
            'installed':next((p['version'] for p in baseline['components'] if p['name']==c['name']),None)}
            for c in candidate['components']]
        for component in components:
            if component['installed'] and version(component['version'])<version(component['installed']):raise ValueError('Component downgrade refused')
        product = version(candidate['release'][1:]) > version(baseline['release'][1:]) and any(c['installed']!=c['version'] for c in components)
        engine_update = offered_engine > installed_engine
        available = product or engine_update
        return {'edition':edition, 'release':candidate['release'], 'notes':candidate['notes'],
                'components':components, 'canInstall':available, 'reason':'available' if available else 'current',
                'proof':found['proof'], 'variant':variant, 'engine':engine,
                'engineOnly':not product, 'canRepair':not engine_update, **self.capability(edition)}

    def reserve(self, payload, repair=False):
        from installation import device_operation
        self.reconcile_terminal()
        old = self.product.read('transaction')
        if old and (old.get('phase') not in FINISHED or old.get('homeResumePhase') != old.get('phase')):
            raise ValueError('Finish the existing product update before changing its engine')
        if self.active_transition(): raise ValueError('Finish the existing engine update in Recovery')
        offer = self.offer(payload['edition'])
        if repair and not offer['canRepair']:
            raise ValueError('Signed same-version System Updater package is unavailable')
        if not repair and (not offer['canInstall'] or offer['release'] != payload['release']): raise ValueError('Signed update offer changed')
        profile = self.call(self.slots.active(),'engine-profile',{'edition':payload['edition'],'profile':payload['profile']})
        if not isinstance(profile,dict) or len(encode(profile))>4*1024*1024:raise ValueError('Invalid captured profile')
        with device_operation('system-engine', recovery=True) as lease:
            # Recheck inside the shared operation lock.
            current = self.product.read('transaction')
            if current != old or self.active_transition(): raise ValueError('Update ownership changed')
            identifier = uuid.uuid4().hex
            self.store.write('profile-'+identifier, profile)
            tx = dict(schema=1, id=identifier, lease=lease['id'], edition=payload['edition'], release=offer['release'], repair=repair, engineOnly=repair or offer['engineOnly'],
                      previousGeneration=self.store.read('supervisor-generation'),
                      variant=offer['variant'], proof=offer['proof'], profile='profile-'+identifier,
                      profileDigest=hashlib.sha256(encode(profile)).hexdigest(),
                      previousTransaction=old, phase='preparing')
            self.store.write('transaction', tx)
        self.wake()
        return self.summary(tx)

    def wake(self):
        subprocess.Popen([sys.executable, '-B', str(self.code/'run-system-updater.py'), 'worker'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)

    def reconcile_terminal(self):
        """Close only the exact owner whose terminal journal reached disk first."""
        from installation import Ownership
        tx=self.transaction()
        if not tx or tx['phase'] not in TERMINAL:return False
        owner=Ownership();lease=owner.status()
        if not lease or lease['owner']!='system-engine' or lease['terminal']:return False
        if lease['id']!=tx['lease']:raise ValueError('Terminal engine journal belongs to another lease')
        with owner.operation('system-engine','transaction.json',resume=lease['id']) as record:
            if self.transaction()!=tx or self.product.read('transaction')!=tx['previousTransaction']:
                raise ValueError('Terminal engine state changed before ownership completion')
            migration=self.store.read('supervisor-migration')
            trial=self.store.read('trial')
            if tx['phase']=='complete':
                if (not tx.get('engineOnly') or not migration or migration.get('operation')!=tx['id']
                        or migration.get('phase')!='complete' or not trial or trial.get('operation')!=tx['id']
                        or trial.get('confirmed') is not True or self.store.read('active')!=trial['candidate']):
                    raise ValueError('Engine completion proof is incomplete')
                from .supervisor_io import generation_inventory
                generation_inventory(self.state,self.store.uid)
                self.slots.active()
            else:
                if migration and migration.get('operation')==tx['id'] and migration.get('phase') not in ('aborted','rolled-back'):
                    raise ValueError('Supervisor rollback is not terminal')
                if trial and trial.get('operation')==tx['id']:
                    if trial.get('cancelled') is not True or self.store.read('active')!=trial['previous']:
                        raise ValueError('Engine cancellation proof is incomplete')
                    self.slots.active()
            owner.stage(record,tx['phase'],terminal=True)
        return True

    def worker(self):
        from installation import Ownership, pending_journals
        owner = Ownership()
        tx = self.active_transition()
        if not tx:
            if self.reconcile_terminal():return
            os.execv(sys.executable, [sys.executable, '-B', str(self.slots.active()/'engine-entry.py'), 'worker'])
        if tx['phase'] == 'recovery-required': return
        lease = owner.status()
        if not lease or lease['id']!=tx.get('lease') or lease['owner'] not in ('system-engine','system-update'):
            raise ValueError('Engine update ownership missing')
        if lease['owner'] == 'system-update':
            product = self.product.read('transaction')
            if not product or product.get('id') != tx['id']: raise ValueError('Engine handoff conflict')
            self.save(tx, 'complete')
            os.execv(sys.executable, [sys.executable, '-B', str(self.slots.active()/'engine-entry.py'), 'worker'])
        def eligible():
            nonlocal tx
            current=self.active_transition()
            if not current or current['id']!=tx['id'] or current['lease']!=lease['id']:
                raise ValueError('Engine ownership changed before worker admission')
            tx=current
            # An exact prepared child transaction can coexist only during handoff.
            product = self.product.read('transaction')
            if product != tx['previousTransaction'] and (not product or product.get('id') != tx['id']):
                raise ValueError('Product transaction changed during engine replacement')
            pending_journals('system-engine', read=lambda path:
                tx['previousTransaction'] if str(path)==str(self.state/'transaction.json') else __import__('installation').read_journal(path))
        with owner.operation('system-engine', 'transaction.json', resume=lease['id'], check=eligible) as record:
            if tx['phase']=='recovery-required':return
            try:
                catalog = policy('verify', {'proof':tx['proof']}, self.code)
                profile = self.store.read(tx['profile'])
                if hashlib.sha256(encode(profile)).hexdigest() != tx['profileDigest']: raise ValueError('Saved engine profile changed')
                if tx['phase'] in ('preparing','staging'):
                    tx = self.save(tx, 'staging')
                    raw = policy('package', {'proof':tx['proof']}, self.code)
                    import shutil
                    if shutil.disk_usage(self.state).free < len(raw)*4 + 128*1024*1024: raise ValueError('Insufficient space for updater recovery')
                    slot = self.slots.stage(tx['proof'], raw)
                    self.slots.begin(tx['id'], slot)
                    tx = self.save(tx, 'activating')
                trial = self.store.read('trial')
                if not trial or trial['operation'] != tx['id']: raise ValueError('Engine activation journal missing')
                slot = self.slots.verify_slot(trial['candidate'])
                if tx['phase'] == 'activating':
                    ready = self.call(slot, 'engine-health', {'operation':tx['id']})
                    if ready != {'operation':tx['id'], 'ready':True}: raise ValueError('Engine readiness mismatch')
                    self.slots.confirm(tx['id'])
                    tx = self.save(tx, 'ready')
                if tx['phase'] in ('ready','migrating'):
                    tx = self.save(tx, 'migrating')
                    from .supervisor_io import SupervisorIO
                    from .bootstrap_migration import Migration
                    io = SupervisorIO(self, slot)
                    migration = Migration(self.store, io)
                    candidate, prior = io.descriptors()
                    migration.begin(tx['id'], candidate, prior, repair=tx.get('repair',False))
                    result = migration.run()
                    if result['phase'] != 'complete':raise ValueError(result.get('error') or 'Supervisor migration requires recovery')
                    if tx.get('engineOnly'):
                        tx = self.save(tx, 'complete')
                        owner.stage(record, 'complete', terminal=True)
                        return
                    tx = self.save(tx, 'handoff')
                if tx['phase'] == 'handoff':
                    tx = self.save(tx, 'handoff')
                    prepared = self.call(slot, 'engine-reserve', {'operation':tx['id']})
                    if not prepared or prepared.get('id') != tx['id']: raise ValueError('Product reservation mismatch')
                    # The single shared mutex protects transfer. A crash before this
                    # write returns here; after it, the exact product worker resumes.
                    successor = dict(record, owner='system-update', journal='transaction.json', stage=prepared['phase'], terminal=False)
                    owner.store.write('operation', successor)
                    self.save(tx, 'complete')
                elif tx['phase'] == 'recovery-required': return
            except Exception as error:
                # Ownership transfer is the commit boundary. Once it happened,
                # the child journal owns recovery; never overwrite that lease.
                if owner.status().get('owner') == 'system-update':
                    raise
                tx['resumePhase'] = tx['phase']
                failed = self.save(tx, 'recovery-required', error)
                owner.stage(record, failed['phase'], terminal=False)
                return
        os.execv(sys.executable, [sys.executable, '-B', str(self.slots.active()/'engine-entry.py'), 'worker'])

    def recover(self, abort=False):
        from installation import Ownership
        owner = Ownership()
        lease = owner.status()
        if lease and lease['owner']=='system-update' and not abort:
            tx=self.active_transition();product=self.product.read('transaction')
            if tx and tx['lease']==lease['id'] and product and product.get('id')==tx['id']:
                self.wake();return self.summary(tx)
        if not lease or lease['owner'] != 'system-engine' or lease['terminal']:
            raise ValueError('Original engine ownership required')
        with owner.operation('system-engine', 'transaction.json', resume=lease['id']) as record:
            tx = self.active_transition()
            if not tx or tx.get('lease')!=record['id']: raise ValueError('Engine transition no longer pending')
            current = self.product.read('transaction')
            if current != tx['previousTransaction'] and (not current or current.get('id') != tx['id']):
                raise ValueError('Product transaction changed during recovery')
            if abort:
                if current != tx['previousTransaction']:
                    raise ValueError('Product update already reserved; resume its original handoff')
                trial = self.store.read('trial')
                migration=self.store.read('supervisor-migration')
                if migration and migration.get('operation')==tx['id']:
                    from .supervisor_io import SupervisorIO
                    from .bootstrap_migration import Migration
                    slot=self.slots.verify_slot(trial['candidate'])
                    manager=Migration(self.store,SupervisorIO(self,slot))
                    manager.rollback()
                    result=manager.run()
                    if result['phase'] not in ('aborted','rolled-back'):raise ValueError(result.get('error') or 'Supervisor rollback pending')
                if trial and trial.get('operation') == tx['id']: self.slots.cancel(tx['id'])
                tx = self.save(tx, 'aborted')
                owner.stage(record, 'aborted', terminal=True)
            elif tx['phase'] == 'recovery-required':
                phase = tx.get('resumePhase')
                if phase not in ('preparing','staging','activating','ready','migrating','handoff'):
                    raise ValueError('Unknown engine recovery phase')
                tx = self.save(tx, phase)
                owner.stage(record, phase, terminal=False)
        if not abort: self.wake()
        return self.summary(tx)

    def handle(self, method, payload):
        if method not in FIELDS or not isinstance(payload,dict) or set(payload)!=FIELDS[method]: raise ValueError('Invalid bootstrap request')
        if 'edition' in payload and payload['edition'] not in ('root','no-root'): raise ValueError('Invalid edition')
        tx = self.active_transition()
        if method == 'status':
            last=self.transaction()
            if tx:return self.summary(tx)
        if method == 'check':
            offer = self.offer(payload['edition'])
            return {k:v for k,v in offer.items() if k not in ('proof','variant','engine','engineOnly')}
        if method == 'install': return self.reserve(payload)
        if method == 'repair': return self.reserve(payload,repair=True)
        if method == 'reconcile' and tx: return self.recover()
        if method == 'reconcile' and self.reconcile_terminal():return self.handle('status', {})
        if method == 'rollback' and tx: return self.recover(abort=True)
        if tx and method not in ('restoreProfile',): raise ValueError('System updater replacement is pending')
        result=self.call(self.slots.active(), method, payload)
        if method=='status':
            if result is None and last and last.get('engineOnly'):return self.summary(last)
            if isinstance(result,dict):
                result.update(self.capability(result['edition']))
                if last and last.get('engineOnly'):
                    result['lastEngineUpdate']={'id':last['id'],'phase':last['phase'],'repair':last.get('repair',False)}
        return result


def entry():
    try:
        if os.geteuid() != 0: raise PermissionError('Root System Updater required')
        method = sys.argv[1] if len(sys.argv)==2 else None
        pinned_integrity(allow_removal=method=='own-package')
        runtime = Bootstrap()
        if method == 'worker': return runtime.worker()
        if method == 'own-package':
            from .supervisor_io import generation_inventory
            print(json.dumps({'returnValue':True,'result':generation_inventory(STATE)}),flush=True);return
        if method == 'engine-recovery':
            print(json.dumps({'returnValue':True,'result':engine_recovery_allowed(STATE)}),flush=True);return
        raw = sys.stdin.buffer.read(4*1024*1024+1)
        if len(raw)>4*1024*1024: raise ValueError('Bootstrap request too large')
        result = runtime.handle(method, json.loads(raw or b'{}'))
        print(json.dumps({'returnValue':True,'result':result},allow_nan=False),flush=True)
    except Exception as error:
        print(json.dumps({'returnValue':False,'errorText':str(error)[:512]}),flush=True)
        sys.exit(1)


def engine_recovery_allowed(state=STATE):
    from installation import Ownership
    pinned_integrity(state)
    runtime=Bootstrap(state)
    tx=runtime.active_transition()
    owner=Ownership().status()
    if not tx or not owner or owner['id']!=tx.get('lease') or owner['owner']!='system-engine' or owner['terminal'] or owner['journal']!='transaction.json':return False
    migration=runtime.store.read('supervisor-migration')
    if migration and migration.get('phase') not in ('complete','rolled-back','aborted'):
        from .bootstrap_migration import Migration
        if Migration(runtime.store,None)._load()['operation']!=tx['id']:raise ValueError('Foreign supervisor migration')
    return True


def service_entry():
    """Permanent root-owned dispatcher: verify the selected service before exec."""
    if os.geteuid()!=0:raise PermissionError('Root service required')
    pinned_integrity()
    runtime=Bootstrap()
    from .supervisor_io import generation_inventory
    generation_inventory(STATE)
    generation=runtime.store.read('supervisor-generation')
    selected=runtime.slots.verify_slot(generation['slot']) if generation and generation['slot'] else CODE
    os.chdir(selected)
    os.environ['NODE_PATH']='/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules'
    os.execv('/usr/bin/node',['/usr/bin/node','/usr/palm/services/jsservicelauncher/bootstrap-node.js','--',
        str(STATE/'bootstrap.pid'),'/var/palm/ls2-dev',str(selected)])
