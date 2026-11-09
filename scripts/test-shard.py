#!/usr/bin/env python3
"""Run a deterministic partition of unittest discovery, without third-party runners."""
import argparse
import json
from pathlib import Path
import re
import sys
import unittest


def shard_value(value):
    if not re.fullmatch(r'[1-9][0-9]{0,2}/[1-9][0-9]{0,2}', value):
        raise argparse.ArgumentTypeError('Invalid shard; expected INDEX/COUNT (1 <= INDEX <= COUNT <= 999)')
    index, count = map(int, value.split('/'))
    if index > count:
        raise argparse.ArgumentTypeError('Invalid shard; INDEX exceeds COUNT')
    return index, count


def cases(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from cases(test)
        else:
            yield test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', default='1/1', type=shard_value)
    parser.add_argument('-s', '--start-directory', required=True)
    parser.add_argument('-p', '--pattern', default='test*.py')
    parser.add_argument('--list', action='store_true', help='Print selected test IDs as JSON without running fixtures')
    parser.add_argument('--timings', help='Write per-test, shared-fixture and skip details as JSON')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    # Match `python -m unittest discover`: repository imports remain available.
    sys.path.insert(0, str(Path.cwd()))
    loader = unittest.TestLoader()
    suite = loader.discover(args.start_directory, pattern=args.pattern)
    if loader.errors:
        print('\n'.join(loader.errors), file=sys.stderr)
        return 1
    discovered = list(cases(suite))
    if not discovered:
        print('No tests discovered in ' + args.start_directory, file=sys.stderr)
        return 1
    index, count = args.shard
    # Preserve discovery order so unittest keeps module/class fixtures grouped.
    selected = discovered[index - 1::count]
    if args.list:
        print(json.dumps([test.id() for test in selected]))
        return 0
    print(f'{args.start_directory}: shard {index}/{count}, '
          f'{len(selected)}/{len(discovered)} tests', file=sys.stderr, flush=True)
    if args.timings:
        from ci_test_timing import TimingSuite, run
        result = run(TimingSuite(selected), args.timings, directory=args.start_directory,
                     shard=f'{index}/{count}', verbosity=2 if args.verbose else 1)
    else:
        result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(unittest.TestSuite(selected))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
