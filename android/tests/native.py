"""Run the installed native fixtures on an explicitly selected emulator.

adb may exit zero even when instrumentation reports failure. Require our runner's
success marker as well. These fixtures never connect to a TV.
"""
import argparse
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--upgrade', choices=('seed', 'verify'))
    args = parser.parse_args()
    if not re.fullmatch(r'emulator-\d+', args.serial):
        parser.error('Synthetic fixtures must run on an emulator, not a physical device')
    command = [args.adb, '-s', args.serial, 'shell', 'am', 'instrument', '-w']
    markers = (
        'PASS: both editions, single operation, bounded replay, pending prompts and stale answers',
        'PASS: packaged Python bridge, loopback inspection and synthetic status terminal result',
    )
    if args.upgrade:
        command += ['-e', 'upgrade', args.upgrade]
        markers = (f'PASS: upgrade fixture {args.upgrade}; no TV commands',)
    command.append('com.cleanyourtv.android.test/com.cleanyourtv.android.OperationChecks')
    result = subprocess.run(command, text=True, capture_output=True, timeout=120, check=True)
    print(result.stdout, end='')
    if not all(marker in result.stdout for marker in markers) or 'FAIL:' in result.stdout:
        raise SystemExit('Native Android checks did not report success\n' + result.stderr)


if __name__ == '__main__':
    main()
