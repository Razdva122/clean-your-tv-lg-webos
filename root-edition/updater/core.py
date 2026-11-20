"""Durable Root app updates. A terminal backend receipt is never inferred.

The adapter owns manifest trust, cache verification and backend event matching.
Each run holds the process lock for bounded external work, never for user input.
Health receipts and immutable profile restoration deliberately avoid that lock.
"""
import copy
import hashlib
import math
import re
import uuid
from .profile import validate
from .store import encode, health_receipt_name, validate_health_receipt

PHASES = {'preparing', 'downloading', 'backed-up', 'restoring-route',
          'installing', 'awaiting-launch', 'verifying', 'complete',
          'rolling-back', 'verifying-rollback', 'rolled-back', 'recovery-required', 'aborted'}
FINISHED = {'complete', 'rolled-back', 'aborted'}
HEALTH_SECONDS = 120


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise ValueError('invalid version')
    return tuple(map(int, value.split('.')))


def _descriptor(value):
    if not isinstance(value, dict): raise ValueError('missing package descriptor')
    _version(value.get('version'))
    return copy.deepcopy(value)


class Manager:
    def __init__(self, store, io):
        self.store = store
        self.io = io
        self._launched = set()

    def _now(self):
        value = self.io.now()
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('invalid clock')
        return value

    def _load(self):
        tx = self.store.read('transaction')
        if tx is None: return None
        if (not isinstance(tx, dict) or tx.get('schema') != 1
                or not isinstance(tx.get('id'), str)
                or not re.fullmatch(r'[0-9a-f]{32}', tx['id'])
                or tx.get('phase') not in PHASES
                or tx.get('profile') != 'profile-' + tx['id']
                or not isinstance(tx.get('profileDigest'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', tx['profileDigest'])
                or type(tx.get('rollbackAttempted')) is not bool):
            raise ValueError('corrupt update journal')
        prior = _descriptor(tx.get('prior'))
        candidate = _descriptor(tx.get('candidate'))
        if _version(candidate['version']) <= _version(prior['version']):
            raise ValueError('corrupt package versions')
        for key in ('created', 'updated'):
            value = tx.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('corrupt journal time')
        for leg in ('installEvidence', 'rollbackEvidence'):
            evidence = tx.get(leg)
            if not isinstance(evidence, dict) or set(evidence) != {'submitted', 'terminal'}:
                raise ValueError('corrupt installer evidence')
            submitted, terminal = evidence['submitted'], evidence['terminal']
            if submitted is not None and (not isinstance(submitted, dict) or not submitted):
                raise ValueError('corrupt submission evidence')
            if terminal is not None and (submitted is None or not isinstance(terminal, dict)
                    or type(terminal.get('success')) is not bool):
                raise ValueError('corrupt terminal evidence')
        if tx['rollbackAttempted'] and tx['installEvidence']['terminal'] is None:
            raise ValueError('rollback without original terminal proof')
        if (not tx['rollbackAttempted'] and
                (tx['rollbackEvidence']['submitted'] is not None or tx['rollbackEvidence']['terminal'] is not None)):
            raise ValueError('rollback evidence without attempt')
        if tx['phase'] in {'preparing', 'downloading', 'backed-up', 'restoring-route', 'aborted'}:
            if (tx['installEvidence']['submitted'] is not None
                    or tx['installEvidence']['terminal'] is not None or tx['rollbackAttempted']):
                raise ValueError('installer evidence in preinstall phase')
        if tx['phase'] == 'aborted' and (tx['installEvidence']['submitted'] is not None
                or tx['installEvidence']['terminal'] is not None or tx['rollbackAttempted']):
            raise ValueError('aborted transaction has installer evidence')
        if tx['phase'] in {'awaiting-launch', 'verifying', 'complete'}:
            if not self._success(tx['installEvidence']):
                raise ValueError('launch without terminal success')
            if tx['rollbackAttempted']:raise ValueError('candidate phase after rollback submission')
        if tx['phase'] in {'rolled-back','verifying-rollback'} and not self._success(tx['rollbackEvidence']):
            raise ValueError('rollback without terminal success')
        if tx['phase'] in {'verifying','verifying-rollback'}:
            start, deadline = tx.get('launched'), tx.get('deadline')
            if (type(start) not in (int, float) or type(deadline) not in (int, float)
                    or not math.isfinite(start) or not math.isfinite(deadline)
                    or start < 0 or deadline != start + HEALTH_SECONDS):
                raise ValueError('corrupt health deadline')
        return tx

    def status(self):
        return self._load()

    def _save(self, tx, phase=None, error=None):
        if phase is not None: tx['phase'] = phase
        if error is not None: tx['error'] = str(error)[:1024]
        tx['updated'] = self._now()
        self.store.write('transaction', tx)
        return copy.deepcopy(tx)

    def _profile(self, tx):
        value = validate(self.store.read(tx['profile']))
        if hashlib.sha256(encode(value)).hexdigest() != tx['profileDigest']:
            raise ValueError('profile digest mismatch')
        return value

    def install(self, version, profile):
        snapshot = validate(profile)
        _version(version)
        # Finish outside the transaction lock: the adapter serializes its own
        # bounded Home recovery. Never orphan its reservation with a new journal.
        previous=self._load()
        if previous and previous['phase'] in FINISHED and previous.get('homeResumePhase')!=previous['phase']:
            self.io.finish(previous)
        with self.store.lock():
            current = self._load()
            if current and current['phase'] in FINISHED and current.get('homeResumePhase')!=current['phase']:
                raise ValueError('Home recovery pending; refresh Recovery status before another update')
            if current and current['phase'] not in FINISHED:
                self._profile(current)
                if current['phase'] != 'recovery-required' and current['candidate']['version'] == version:
                    return current
                raise ValueError('unfinished update requires recovery')
            offer = self.io.offer()
            if not isinstance(offer, dict) or offer.get('canInstall') is False:
                raise ValueError(offer.get('reason', 'update unavailable') if isinstance(offer, dict) else 'invalid offer')
            candidate = _descriptor(offer.get('candidate'))
            prior = _descriptor(offer.get('prior') or self.store.read('current'))
            installed = self.io.installed()
            if (not isinstance(installed, dict) or installed.get('version') != prior['version']
                    or candidate['version'] != version
                    or _version(version) <= _version(prior['version'])):
                raise ValueError('installed baseline or update offer changed')
            identifier = uuid.uuid4().hex
            name = 'profile-' + identifier
            self.store.write(name, snapshot)
            if self.store.read(name) != snapshot: raise ValueError('profile readback failed')
            now = self._now()
            tx = {'schema': 1, 'id': identifier, 'prior': prior, 'candidate': candidate,
                  'profile': name, 'profileDigest': hashlib.sha256(encode(snapshot)).hexdigest(),
                  'phase': 'preparing', 'created': now, 'updated': now,
                  'oldRoute': None, 'rollbackAttempted': False,
                  'installEvidence': {'submitted': None, 'terminal': None},
                  'rollbackEvidence': {'submitted': None, 'terminal': None}}
            return self._save(tx)

    @staticmethod
    def _success(evidence):
        return isinstance(evidence.get('terminal'), dict) and evidence['terminal'].get('success') is True

    def _safe_route(self):
        result = self.io.restore_route()
        status = self.io.routing_status()
        if result is False or not isinstance(status, dict) or status.get('active') is not False:
            raise ValueError('LG Home route restoration unconfirmed')
        if status.get('safe') is False: raise ValueError('LG Home route unsafe')

    def _install(self, tx, rollback=False):
        leg = 'rollbackEvidence' if rollback else 'installEvidence'
        manifest = tx['prior'] if rollback else tx['candidate']
        evidence = tx[leg]

        def submitted(value):
            if evidence['submitted'] is not None or not isinstance(value, dict) or not value:
                raise ValueError('invalid duplicate submission evidence')
            evidence['submitted'] = copy.deepcopy(value)
            self._save(tx)

        def terminal(value):
            if (evidence['submitted'] is None or evidence['terminal'] is not None
                    or not isinstance(value, dict) or type(value.get('success')) is not bool):
                raise ValueError('invalid terminal evidence')
            evidence['terminal'] = copy.deepcopy(value)
            self._save(tx)

        try:
            self.io.install(copy.deepcopy(manifest), submitted, terminal)
        except Exception as error:
            # Only a successfully persisted receipt can establish termination.
            durable = self._load()
            if durable[leg]['terminal'] is None:
                return self._save(durable, 'recovery-required', error)
            tx = durable
        return self._terminal(tx, rollback)

    def _terminal(self, tx, rollback=False):
        evidence = tx['rollbackEvidence' if rollback else 'installEvidence']
        if evidence['terminal'] is None:
            return self._save(tx, 'recovery-required', 'installer outcome unknown; terminal evidence required')
        if self._success(evidence) and hasattr(self.io, 'sync_screensaver'):
            self.io.sync_screensaver(tx, rollback)
        if rollback:
            if not self._success(evidence):
                return self._save(tx, 'recovery-required', 'rollback failed; no retry permitted')
            if not self.io.verify_installed(tx['prior']):
                return self._save(tx, 'recovery-required', 'rollback identity verification failed')
            self._profile(tx)
            tx['launched']=self._now();tx['deadline']=tx['launched']+HEALTH_SECONDS
            self._save(tx, 'verifying-rollback')
            self._launch(tx)
            return tx
        if self._success(evidence): return self._save(tx, 'awaiting-launch')
        return self._save(tx, 'rolling-back', 'application installation failed')

    def _launch(self,tx):
        key=(tx['id'],tx['phase'])
        # Launch is idempotent and reconciled once per worker incarnation. The
        # durable deadline is retained after restart; installation is not replayed.
        if key not in self._launched:
            self.io.launch();self._launched.add(key)

    def run(self):
        with self.store.lock():
            tx = self._load()
            if tx is None: return None
            try:
                self._profile(tx)
            except ValueError as error:
                return self._save(tx, 'recovery-required', error)
            phase = tx['phase']
            if phase in FINISHED or phase == 'recovery-required': return tx
            try:
                if phase == 'preparing':
                    status = self.io.routing_status()
                    if not isinstance(status, dict) or type(status.get('active')) is not bool:
                        raise ValueError('invalid routing status')
                    tx['oldRoute'] = copy.deepcopy(status)
                    return self._save(tx, 'downloading')
                if phase == 'downloading':
                    prepared = self.io.prepare(copy.deepcopy(tx['candidate']), copy.deepcopy(tx['prior']))
                    if prepared is not None:
                        if not isinstance(prepared, dict): raise ValueError('invalid prepared packages')
                        for name in ('candidate', 'prior'):
                            value = _descriptor(prepared.get(name))
                            # A cache may add a local reference, never replace trusted identity.
                            if any(value.get(key) != original for key, original in tx[name].items()):
                                raise ValueError('prepared package identity changed')
                            tx[name] = value
                    return self._save(tx, 'backed-up')
                if phase == 'backed-up':
                    if self.io.installed().get('version') != tx['prior']['version']:
                        raise ValueError('installed baseline changed before installation')
                    return self._save(tx, 'restoring-route')
                if phase == 'restoring-route':
                    self._safe_route()
                    if self.io.installed().get('version') != tx['prior']['version']:
                        raise ValueError('installed baseline changed before submission')
                    self._save(tx, 'installing')
                    return self._install(tx)
                if phase == 'installing': return self._terminal(tx)
                if phase == 'awaiting-launch':
                    if not self.io.verify_installed(tx['candidate']):
                        return self._save(tx, 'rolling-back', 'installed application identity mismatch')
                    tx['launched'] = self._now()
                    tx['deadline'] = tx['launched'] + HEALTH_SECONDS
                    self._save(tx, 'verifying')
                    self._launch(tx)
                    return tx
                if phase in ('verifying','verifying-rollback'):
                    now = self._now()
                    rollback=phase=='verifying-rollback'
                    ready=self._receipt(tx,'ready')
                    confirmed=rollback or self._receipt(tx,'confirm')
                    if ready and confirmed and now>=tx['launched']:
                        selected=tx['prior' if rollback else 'candidate']
                        if not self.io.verify_installed(selected):
                            return self._save(tx,'recovery-required' if rollback else 'rolling-back','confirmed application identity mismatch')
                        previous=tx['prior'].get('writer',{})
                        system=previous.get('id') if previous.get('owner')=='system-update' else previous.get('system')
                        self.store.write('current',dict(selected,writer={'owner':'root-update','id':tx['id'],'system':system}))
                        return self._save(tx,'rolled-back' if rollback else 'complete')
                    if now < tx['launched'] or now >= tx['deadline']:
                        return self._save(tx,'recovery-required' if rollback else 'rolling-back','restored profile readiness unconfirmed' if rollback else 'application health confirmation timed out')
                    self._launch(tx)
                    return tx
                if phase == 'rolling-back':
                    if hasattr(self.io, 'screensaver_pending') and self.io.screensaver_pending(tx):
                        return self._save(tx, 'recovery-required', 'Screensaver package outcome unconfirmed')
                    if tx['installEvidence']['terminal'] is None:
                        return self._save(tx, 'recovery-required', 'original installer outcome unknown')
                    if tx['rollbackAttempted']: return self._terminal(tx, True)
                    self._safe_route()
                    tx['rollbackAttempted'] = True
                    self._save(tx)
                    return self._install(tx, True)
            except Exception as error:
                # Reload after external callbacks: stale memory must not erase proof.
                durable = self._load()
                if (durable['phase'] in {'awaiting-launch', 'verifying'}
                        and self._success(durable['installEvidence']) and not durable['rollbackAttempted']):
                    return self._save(durable, 'rolling-back', error)
                if (durable['phase'] in {'preparing', 'downloading', 'backed-up', 'restoring-route'}
                        and durable['installEvidence']['submitted'] is None):
                    return self._save(durable, 'aborted', error)
                return self._save(durable, 'recovery-required', error)

    def _receipt(self, tx, kind):
        value = self.store.read(self._receipt_name(tx,kind))
        if value is None: return None
        validate_health_receipt(value, tx['id'])
        if (value['version'] != tx['prior' if tx['phase']=='verifying-rollback' else 'candidate']['version']
                or not tx['launched'] <= value['at'] < tx['deadline']):
            raise ValueError('invalid health receipt')
        return value

    @staticmethod
    def _receipt_name(tx,kind):
        return health_receipt_name(tx['id'], kind, tx['phase'] == 'verifying-rollback')

    def _health(self, transaction, version, kind):
        tx = self._load()
        if (tx is None or tx['id'] != transaction or tx['phase'] not in ('verifying','verifying-rollback')
                or tx['prior' if tx['phase']=='verifying-rollback' else 'candidate']['version'] != version
                or (kind=='confirm' and tx['phase']!='verifying')):
            raise ValueError('stale health signal')
        self._profile(tx)
        now = self._now()
        if not tx['launched'] <= now < tx['deadline']: raise ValueError('health deadline expired')
        if kind == 'confirm' and not self._receipt(tx, 'ready'):
            raise ValueError('application is not ready')
        value = {'transaction': transaction, 'version': version, 'at': now}
        self.store.write(self._receipt_name(tx,kind), value)
        return value

    def ready(self, transaction, version): return self._health(transaction, version, 'ready')

    def confirm(self, transaction, version): return self._health(transaction, version, 'confirm')

    def component_removed(self):
        """Stop at a phase boundary; never reinstall an externally removed package."""
        with self.store.lock():
            tx=self._load()
            if tx is None or tx['phase'] in FINISHED:return tx
            error='CYTV component removed; recovery evidence retained'
            try:
                self._safe_route()
            except Exception as exc:
                return self._save(tx,'recovery-required',error+': '+str(exc))
            return self._save(tx,'aborted' if tx['installEvidence']['submitted'] is None and tx['phase'] in ('preparing','downloading','backed-up','restoring-route') else 'recovery-required',error)

    def reconcile(self):
        return self.run()

    def rollback(self):
        with self.store.lock():
            tx = self._load()
            if tx is None or tx['phase'] in {'rolled-back', 'aborted'}: return tx
            if tx['rollbackAttempted']:
                return tx
            if hasattr(self.io, 'screensaver_pending') and self.io.screensaver_pending(tx):
                return self._save(tx, 'recovery-required', 'Screensaver package outcome unconfirmed')
            if tx['phase'] == 'complete' and self.io.installed().get('version') != tx['candidate']['version']:
                raise ValueError('installed version changed since confirmed update')
            if tx['installEvidence']['terminal'] is None:
                if tx['phase'] in {'installing', 'recovery-required'}:
                    return self._save(tx, 'recovery-required', 'original installer outcome unknown')
                raise ValueError('installation has not terminated')
            self._profile(tx)
            return self._save(tx, 'rolling-back')

    def restore_profile(self):
        tx = self._load()
        if tx is None: return None
        candidate = tx['phase'] in {'awaiting-launch', 'verifying', 'complete'}
        return {'profile': self._profile(tx), 'transaction': tx['id'],
                'version': tx['candidate' if candidate else 'prior']['version'],
                'phase': tx['phase']}
