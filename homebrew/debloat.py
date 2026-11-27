"""Apply only selected LG preferences through the on-TV product workflow."""
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess
import sys
from time import sleep

from cytv.debloat_policy import SETTINGS, valid_value, valid_record

SERVICE = 'luna://com.webos.settingsservice/'
RECEIPT = 'homebrew-debloat'
ACTIONS = ('debloat-status', 'debloat', 'debloat-restore')


def selection(action, raw):
    keys = [] if raw is None else raw.split(',')
    if action not in ACTIONS or (action == 'debloat-status') != (not keys):
        raise ValueError('invalid Debloat request')
    if len(keys) != len(set(keys)) or any(key not in SETTINGS for key in keys):
        raise ValueError('invalid Debloat selection')
    return keys


def read_receipt(store):
    receipt = store.read(RECEIPT)
    if receipt is None:
        return {}
    if (not isinstance(receipt, dict) or set(receipt) != {'schema', 'settings'}
            or type(receipt['schema']) is not int or receipt['schema'] != 1
            or not isinstance(receipt['settings'], dict)):
        raise ValueError('invalid Debloat receipt')
    for key, record in receipt['settings'].items():
        if (key not in SETTINGS or not isinstance(record, dict) or set(record) != {'original', 'target'}
                or not valid_record(key, record)):
            raise ValueError('invalid Debloat setting receipt')
    return receipt['settings']


def read_settings(invoke, category, keys, timeout):
    try:
        reply = invoke(SERVICE + 'getSystemSettings', {'category': category, 'keys': keys}, timeout)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return {}
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        return {}
    settings = reply.get('settings')
    return {key: settings[key] for key in keys if valid_value(key, settings.get(key))} if isinstance(settings, dict) else {}


def write_setting(invoke, category, key, value):
    try:
        reply = invoke(SERVICE + 'setSystemSettings', {'category': category, 'settings': {key: value}}, 2)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        reason = (getattr(error, 'luna', None) or {}).get('reason')
        if reason in ('negative-reply', 'permission-denied'):
            return 'write-rejected'
        return 'write-unavailable'
    if isinstance(reply, dict) and reply.get('returnValue') is True:
        return None
    return 'write-rejected' if isinstance(reply, dict) and reply.get('returnValue') is False else 'write-unavailable'


def change_settings(action, keys, store, settings, invoke):
    results, status = {}, {}
    restore = action == 'debloat-restore'

    def record(key, actual, outcome):
        results[key] = outcome
        status[key] = {'value': actual, 'saved': key in settings}

    for key in keys:
        category, _, target = SETTINGS[key]
        current = read_settings(invoke, category, [key], 2).get(key)
        if current is None or (restore and key not in settings):
            record(key, current, 'restore-unavailable' if restore else 'unavailable')
            continue
        wanted = settings[key]['original'] if restore else target
        actual = current
        if current == wanted:
            outcome = 'restore-already' if restore else 'already'
        else:
            if key not in settings:
                next_settings = {**settings, key: {'original': current, 'target': target}}
                try:
                    store.write(RECEIPT, {'schema': 1, 'settings': next_settings})
                except (OSError, ValueError):
                    record(key, actual, 'journal-failed')
                    continue
                settings = next_settings
            error = write_setting(invoke, category, key, wanted)
            actual = read_settings(invoke, category, [key], 1).get(key)
            if error:
                record(key, actual, 'restore-failed' if restore else error)
                continue
            if actual != wanted:
                sleep(0.25)
                actual = read_settings(invoke, category, [key], 1).get(key)
            if actual == wanted:
                outcome = 'restored' if restore else 'verified'
            elif restore:
                outcome = 'restore-unverified'
            else:
                outcome = 'verify-unavailable' if actual is None else 'verify-mismatch'
        if outcome in ('restored', 'restore-already'):
            next_settings = settings.copy()
            del next_settings[key]
            try:
                store.write(RECEIPT, {'schema': 1, 'settings': next_settings})
            except (OSError, ValueError):
                record(key, actual, 'journal-failed')
                continue
            settings = next_settings
        record(key, actual, outcome)
    return results, status


def run(action, keys, ownership, device, invoke):
    from installation import Busy

    selection(action, ','.join(keys) if keys else None)
    result = {'state': 'debloat'}
    try:
        # Share the product mutex without replacing the original install or
        # update receipt. Recovery and removal still receive the same lease.
        with ownership._lock(create=False):
            lease = ownership.status()
            if not lease or not lease['terminal']:
                return dict(result, code='not_available')
            installed = device.inspect()
            if installed.get('state') != 'installed' or installed.get('tile_protocol') != 1:
                return dict(result, code='not_available')
            try:
                settings = read_receipt(ownership.store)
            except (OSError, ValueError):
                return dict(result, code='journal_failed')
            if action != 'debloat-status':
                results, current = change_settings(action, keys, ownership.store, settings, invoke)
                return dict(result, results=results, settings=current)
            groups = defaultdict(list)
            for key, (category, _, _) in SETTINGS.items():
                groups[category].append(key)
            current = {}
            for category, group in groups.items():
                values = read_settings(invoke, category, group, 2)
                if len(group) > 1:
                    for missing in set(group) - values.keys():
                        values.update(read_settings(invoke, category, [missing], 2))
                current.update(values)
            return dict(result, settings={key: {'value': current.get(key), 'saved': key in settings} for key in SETTINGS})
    except Busy:
        return dict(result, code='busy')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return dict(result, code='not_available')


def main(argv):
    if not argv or len(argv) > 2 or os.geteuid() != 0:
        raise ValueError('invalid Debloat request')
    action = argv[0]
    keys = selection(action, argv[1] if len(argv) == 2 else None)
    # The Homebrew bootstrap stages this fixed sibling with the same inventory.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'root-updater'))
    from install_device import LocalDevice, checked_store
    from installation import Ownership, STATE
    from updater.luna import call

    print(json.dumps(run(action, keys, Ownership(checked_store(STATE)), LocalDevice(), call)))


if __name__ == '__main__':
    main(sys.argv[1:])
