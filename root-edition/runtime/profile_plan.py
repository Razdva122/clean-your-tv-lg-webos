"""Strict stock-baseline validation for the isolated Root candidate."""
import copy
import json

STOCK = 'com.webos.app.home'
CANDIDATE = 'com.cleanyourtv.root.preview'


def snapshot(reply, sam_home):
    try:
        if reply['returnValue'] is not True:
            raise ValueError('Profile read did not succeed')
        profiles = reply['profiles']
        home = profiles['defaultApps']['categories']['home']
        idle = profiles['idleApp']['appId']
        support = profiles['idleApp']['support']
        if not all(isinstance(x, str) and x.strip() == x and x for x in (home, idle, sam_home)):
            raise ValueError('Missing or malformed routing destination')
        if type(support) is not bool:
            raise ValueError('Missing idle support state')
        return {'sam_home': sam_home, 'profiles': copy.deepcopy({
            'defaultApps': profiles['defaultApps'], 'idleApp': profiles['idleApp']})}
    except (KeyError, TypeError) as exc:
        raise ValueError('Incomplete routing readback') from exc


def plan(reply, sam_home):
    baseline = snapshot(reply, sam_home)
    p = baseline['profiles']
    if (sam_home != STOCK or p['defaultApps']['categories']['home'] != STOCK
            or p['idleApp']['appId'] != STOCK or p['idleApp']['support'] is not True):
        raise ValueError('This trial requires the verified stock routing baseline')
    candidate_profile = copy.deepcopy(p)
    candidate_profile['defaultApps']['categories']['home'] = CANDIDATE
    candidate_profile['idleApp']['appId'] = CANDIDATE
    return {
        'ready_to_deploy': False,
        'baseline': baseline,
        'candidate_profile': candidate_profile,
        'requirements': [
            'Independent recovery of owned profile file and generated effective values',
            'Conflict-checked deletion of only the trial-owned profile',
            'Bounded rescan and readback of both profiles plus SAM Home',
            'Boot/failsafe recovery validated for this profile adapter',
            'Do not reuse the SAM-only guardian as profile recovery',
        ],
    }


def restored(baseline, reply, sam_home):
    """Fail closed on incomplete, failed or changed effective readback."""
    try:
        return snapshot(reply, sam_home) == baseline
    except ValueError:
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile_readback')
    parser.add_argument('--sam-home', required=True,
                        help='Independently observed SAM Home, not inferred from the profile')
    args = parser.parse_args()
    with open(args.profile_readback) as source:
        print(json.dumps(plan(json.load(source), args.sam_home), indent=2))
