"""Profile recovery policy with injected I/O. No deployment or TV activation.

Caller must hold one transaction lock and durably save the journal. remove_owned
must verify the fixed file's ownership/type/digest and preserve conflicts. All
service operations must have bounded deadlines. These are adapter obligations,
not guarantees supplied by this pure policy module.
"""
import copy
import hashlib
import json
from profile_plan import plan, STOCK, CANDIDATE

REAL_HOME = CANDIDATE
def payload_for(candidate, baseline=None):
    if candidate != CANDIDATE: raise ValueError('Unsupported candidate')
    profiles = ({'defaultApps': {'categories': {}}, 'idleApp': {}}
                if baseline is None else copy.deepcopy(baseline['profiles']))
    profiles['defaultApps']['categories']['home'] = candidate
    profiles['idleApp']['appId'] = candidate
    return (json.dumps(profiles, sort_keys=True) + '\n').encode()

PAYLOAD = payload_for(CANDIDATE)
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
STATES = ('pending', 'recovering', 'restored', 'conflict')


def prepare(reply, sam_home, candidate=CANDIDATE):
    baseline = plan(reply, sam_home)['baseline']
    return {'version': 2, 'armed': True, 'state': 'pending',
            'candidate':candidate, 'payload_sha256': hashlib.sha256(payload_for(candidate, baseline)).hexdigest(),
            'baseline': baseline}


def journal_payload(journal):
    version = journal.get('version')
    if type(version) is not int or version not in (1, 2):
        raise ValueError('Unknown profile recovery version')
    return payload_for(journal.get('candidate', CANDIDATE),
                       journal['baseline'] if version == 2 else None)


def validate(journal):
    if (journal.get('armed') is not True or journal.get('state') not in STATES):
        raise ValueError('Invalid profile recovery journal')
    try:
        b = journal['baseline']
        plan({'returnValue': True, 'profiles': b['profiles']}, b['sam_home'])
        if journal.get('payload_sha256') != hashlib.sha256(journal_payload(journal)).hexdigest():
            raise ValueError('Invalid profile payload digest')
    except (KeyError, TypeError) as exc:
        raise ValueError('Invalid baseline') from exc


def recover(journal, remove_owned, refresh, read, write_sam, save):
    validate(journal)
    if journal['state'] in ('restored', 'conflict'):
        return journal['state']

    def record(state):
        updated = dict(journal, state=state)
        if state == 'restored' and journal['version'] == 2:
            # Only after removal and exact baseline readback: old runtimes must
            # accept this terminal record during retained-version rollback.
            updated.update(version=1, payload_sha256=DIGEST,
                           completed_payload_sha256=journal['payload_sha256'])
        save(updated)
        journal.update(updated)
        return state

    record('recovering')  # Durable before deletion, even if previous apply crashed.
    try:
        removal = remove_owned()
    except OSError:
        return 'recovering'
    if removal == 'conflict':
        return record('conflict')
    if removal not in ('removed', 'absent'):
        raise ValueError('Invalid owned-file removal result')
    # Missing candidate is not proof the generated profile or consumer cache reset.
    try:
        refresh()
    except Exception:
        pass  # The response can be lost after a successful refresh. Read back.
    try:
        current = read()
    except Exception:
        return 'recovering'
    sam = current.get('sam_home')
    if sam not in (STOCK, journal.get('candidate', CANDIDATE)):
        return record('conflict')
    if sam == journal.get('candidate', CANDIDATE):
        try:
            write_sam(STOCK)
        except Exception:
            pass
        try:
            current = read()
        except Exception:
            return 'recovering'
    if current == journal['baseline']:
        return record('restored')
    return 'recovering'
