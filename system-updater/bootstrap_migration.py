"""Durable own-package migration, driven by a surviving verified engine worker.

The caller holds the original system-engine ownership lease for every mutation.
IO.prepare authenticates/caches both complete packages before any submission;
IO.install uses the independent installer observer and the callbacks below.
IO.terminal must validate that observer's exact original application/path/client
completion, not a version or an empty installer status. IO.publish atomically
publishes a separate generation receipt; original provisioning receipts remain
the recovery trust anchor. IO.activate switches registration and checks a real
service round trip. Both publication and activation must be idempotent.

No interrupted submission can be replayed or rolled back without its original
durable terminal evidence. Keeping a working recovery executable is not evidence
that the package manager finished its previous request.
"""
import copy
import re

JOURNAL = 'supervisor-migration'
TERMINAL = {'complete', 'rolled-back', 'aborted'}
STAGES = {'prepared', 'submitting', 'installed', 'publishing', 'activating'}


def _descriptor(value):
    if (not isinstance(value, dict) or set(value) != {'version', 'sha256', 'size'}
            or not isinstance(value['version'], str)
            or not re.fullmatch(r'(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})', value['version'])
            or not isinstance(value['sha256'], str)
            or not re.fullmatch('[a-f0-9]{64}', value['sha256'])
            or type(value['size']) is not int or not 0 < value['size'] <= 32*1024*1024):
        raise ValueError('Invalid supervisor package descriptor')
    return value


def _evidence(value):
    if (not isinstance(value, dict) or set(value) != {'intent', 'accepted', 'terminal'}
            or type(value['intent']) is not bool
            or any(value[k] is not None and not isinstance(value[k], dict)
                   for k in ('accepted', 'terminal'))
            or not value['intent'] and any(value[k] is not None for k in ('accepted', 'terminal'))):
        raise ValueError('Invalid supervisor submission evidence')
    return value


class Migration:
    def __init__(self, store, io):
        self.store, self.io = store, io

    def _load(self):
        tx = self.store.read(JOURNAL)
        if tx is None:
            return None
        if (not isinstance(tx, dict) or set(tx) != {'schema', 'operation', 'candidate', 'prior',
                'phase', 'resume', 'rollback', 'repair', 'forwardEvidence', 'rollbackEvidence', 'error'}
                or type(tx['schema']) is not int or tx['schema'] != 1
                or not isinstance(tx['operation'], str)
                or not re.fullmatch('[a-f0-9]{32}', tx['operation'])
                or tx['phase'] not in STAGES | TERMINAL | {'recovery-required'}
                or tx['resume'] not in STAGES or type(tx['rollback']) is not bool or type(tx['repair']) is not bool
                or tx['error'] is not None and not isinstance(tx['error'], str)):
            raise ValueError('Invalid supervisor migration journal')
        _descriptor(tx['candidate']); _descriptor(tx['prior'])
        _evidence(tx['forwardEvidence']); _evidence(tx['rollbackEvidence'])
        return tx

    def _save(self, tx, phase=None, error=None):
        if phase is not None:
            tx['phase'] = phase
            if phase in STAGES:
                tx['resume'] = phase
        tx['error'] = str(error)[:512] if error is not None else None
        self.store.write(JOURNAL, tx)
        return self.status()

    @staticmethod
    def _target(tx):
        return tx['prior'] if tx['rollback'] else tx['candidate']

    @staticmethod
    def _leg(tx):
        return tx['rollbackEvidence'] if tx['rollback'] else tx['forwardEvidence']

    def _known(self, tx):
        evidence = self._leg(tx)
        return evidence['terminal'] is not None and self.io.terminal(evidence['terminal'], self._target(tx)) is True

    def status(self):
        tx = self._load()
        if tx is None:
            return None
        safe = not tx['rollback'] and (not tx['forwardEvidence']['intent'] or self._known(tx))
        return {'operation': tx['operation'], 'phase': tx['phase'],
                'canRollback': safe and tx['phase'] not in ('aborted', 'rolled-back'),
                'rollback': tx['rollback'], 'error': tx['error']}

    def begin(self, operation, candidate, prior, *, repair=False):
        if not isinstance(operation, str) or not re.fullmatch('[a-f0-9]{32}', operation):
            raise ValueError('Invalid supervisor migration operation')
        _descriptor(candidate); _descriptor(prior)
        if type(repair) is not bool:
            raise ValueError('Invalid supervisor repair request')
        current = self._load()
        if current and current['operation'] == operation:
            if (current['candidate'], current['prior'], current['repair']) != (candidate, prior, repair):
                raise ValueError('Original supervisor migration changed')
            return self.status()
        if current and current['phase'] not in TERMINAL:
            raise ValueError('Original supervisor migration requires recovery')
        versions = lambda item: tuple(map(int, item['version'].split('.')))
        if versions(candidate) < versions(prior) or (candidate['version'] == prior['version'] and candidate != prior):
            raise ValueError('Supervisor package changed without a version increase')
        evidence = {'intent': False, 'accepted': None, 'terminal': None}
        tx = {'schema': 1, 'operation': operation, 'candidate': copy.deepcopy(candidate),
              'prior': copy.deepcopy(prior), 'phase': 'prepared', 'resume': 'prepared',
              'rollback': False, 'repair': repair, 'forwardEvidence': copy.deepcopy(evidence),
              'rollbackEvidence': copy.deepcopy(evidence), 'error': None}
        return self._save(tx)

    def run(self):
        tx = self._load()
        if tx is None or tx['phase'] in TERMINAL:
            return self.status()
        try:
            if tx['phase'] == 'recovery-required':
                self._save(tx, tx['resume'])
            target = self._target(tx)
            evidence = self._leg(tx)
            if (tx['phase'] in ('installed', 'publishing', 'activating')
                    and (tx['candidate'] != tx['prior'] or tx['repair']) and not self._known(tx)):
                raise ValueError('Original supervisor terminal proof required before publication')
            if tx['phase'] == 'prepared':
                self.io.prepare(tx['candidate'], tx['prior'])
                if tx['candidate'] == tx['prior'] and not tx['repair']:
                    if self.io.verify_installed(target) is not True:
                        raise ValueError('Unchanged supervisor package readback failed')
                    self._save(tx, 'installed')
                else:
                    def intent():
                        if evidence['intent']:
                            raise ValueError('Supervisor package submission already started')
                        evidence['intent'] = True
                        self._save(tx, 'submitting')

                    def accepted(value):
                        if not evidence['intent'] or evidence['terminal'] is not None or not isinstance(value, dict):
                            raise ValueError('Unexpected supervisor acceptance')
                        evidence['accepted'] = copy.deepcopy(value)
                        self._save(tx)

                    def terminal(value):
                        if not evidence['intent'] or self.io.terminal(value, target) is not True:
                            raise ValueError('Original supervisor terminal proof required')
                        evidence['terminal'] = copy.deepcopy(value)
                        self._save(tx)

                    self.io.install(target, intent, accepted, terminal)
                    if not evidence['intent']:
                        raise ValueError('Supervisor installer did not record submission intent')
            if tx['phase'] == 'submitting':
                if not self._known(tx):
                    raise ValueError('Supervisor install outcome unknown; original terminal required')
                self._save(tx, 'installed')
            if tx['phase'] == 'installed':
                if self.io.verify_installed(target) is not True:
                    raise ValueError('Supervisor package readback failed')
                self._save(tx, 'publishing')
            if tx['phase'] == 'publishing':
                if self.io.verify_installed(target) is not True:
                    raise ValueError('Supervisor package changed before publication')
                self.io.publish(copy.deepcopy(tx))
                self._save(tx, 'activating')
            if tx['phase'] == 'activating':
                if self.io.verify_installed(target) is not True:
                    raise ValueError('Supervisor package changed before activation')
                self.io.activate(copy.deepcopy(tx))
                self._save(tx, 'rolled-back' if tx['rollback'] else 'complete')
        except Exception as error:
            self._save(tx, 'recovery-required', error)
        return self.status()

    def rollback(self):
        tx = self._load()
        if tx is None or tx['phase'] in ('aborted', 'rolled-back') or tx['rollback']:
            return self.status()
        if not tx['forwardEvidence']['intent']:
            if tx['candidate'] == tx['prior'] and tx['resume'] in ('publishing', 'activating'):
                tx['rollback'] = True
                return self._save(tx, 'prepared')
            return self._save(tx, 'aborted')
        if not self._known(tx):
            raise ValueError('Unknown supervisor install cannot be rolled back')
        if self.io.verify_installed(tx['candidate']) is not True:
            raise ValueError('Supervisor candidate changed before rollback')
        tx['rollback'] = True
        return self._save(tx, 'prepared')
