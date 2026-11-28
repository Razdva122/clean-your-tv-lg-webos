#!/usr/bin/env python3
"""Replay remote loss before broker expiry when the candidate changes the guardian."""
from pathlib import Path
import subprocess
import sys
import unittest


def main():
    changed = subprocess.check_output([
        'git', 'diff', '--name-only', '--no-renames', 'origin/main...HEAD', '--',
        'root-edition/gate/keyfilter.c', 'root-edition/gate/*.h',
        'root-edition/tests/test_keyfilter_guard.py', 'scripts/check-candidate-guardian.py',
    ], text=True)
    if not changed:
        print('Guardian shutdown inputs match the release baseline. Skipping the focused replay.')
        return 0

    print('Changed guardian shutdown inputs:\n' + changed, flush=True)
    sys.path.insert(0, str(Path('root-edition/tests').resolve()))
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_keyfilter_guard.KeyfilterGuardTests.test_remote_disappears_before_broker_during_verified_shutdown',
        'test_keyfilter_guard.KeyfilterGuardTests.test_remote_disappears_before_broker_without_verified_shutdown',
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print('Guardian preflight requires both shutdown scenarios to run.', file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
