"""UI integration boundary: production host code, simulated SSH device replies.

This does not execute or certify the TV cleanup engine. Its exact final reply
models authoritative device evidence so UI/Store/diagnostic wiring is testable.
"""
import hashlib
import json
import shlex

from cytv import diagnostics, state
from cytv.no_root_gate import ROOT_BINDING


def prepare(fixture, outcome='complete'):
    fixture.profile = state.target('192.0.2.10', 'root')
    fixture.store.save(fixture.profile)
    directory = fixture.store.device_dir(fixture.profile)
    (directory/'known_hosts').write_bytes(b'original pin')
    fixture.store.begin(fixture.profile, 'install', product_operation='d'*32,
                        stage='pending', failure={'reason':'unknown'})
    original = (directory/'operation.json').read_bytes()
    diagnostics.create_report(fixture.store, 'install', fixture.profile,
                              'install-packages', Exception('PRIVATE ORIGINAL ERROR'))
    for component in ('root', 'root-updater'):
        bundle = fixture.payload/component
        bundle.mkdir(exist_ok=True)
        source = b'fixed simulated device support'
        (bundle/'install_driver.py').write_bytes(source)
        (bundle/'bundle.json').write_text(json.dumps({'files':{
            'install_driver.py':hashlib.sha256(source).hexdigest()}}))
    gate = fixture.payload/'installer-support/lifecycle-gate'
    gate.parent.mkdir(exist_ok=True)
    gate.write_bytes(b'fixed simulated gate')
    fixture.manifest['files']['installer-support/lifecycle-gate'] = hashlib.sha256(gate.read_bytes()).hexdigest()
    fixture.device_removals = []
    original_run = fixture.remote.run
    def run(command, **kwargs):
        words = shlex.split(command)
        if '-e' in words and words[words.index('-e')+1] == ROOT_BINDING:
            fixture.remote.calls.append(('run', command))
            return json.dumps({'mode':'absent'})
        if 'CYTV_SYSTEM_PYTHON' in command:
            return 'CYTV_SYSTEM_PYTHON'
        if any(word.endswith('/install_driver.py') for word in words):
            fixture.remote.calls.append(('run', command))
            action = words[next(i for i, word in enumerate(words) if word.endswith('/install_driver.py'))+1]
            operation = words[words.index('--operation')+1]
            if action == 'clean-remove':
                pending = fixture.store.pending(fixture.profile)
                assert words[words.index('--removal-intent')+1] == pending['removal_operation']
                fixture.device_removals.append(operation)
                complete = outcome == 'complete'
                return json.dumps({'operation':operation, 'state':'complete' if complete else 'recovery_required',
                    'stage':'verified-clean' if complete else 'private-cleanup', 'current':complete,
                    'reason':'removal-verified' if complete else 'private-cleanup-incomplete',
                    'result':{'removed':complete,'private_cleanup_verified':complete,
                              'applications_services_startup_removed':complete}})
        return original_run(command, **kwargs)
    fixture.remote.run = run
    return original
