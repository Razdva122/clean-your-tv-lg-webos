#!/usr/bin/env python3
"""Run a timing-balanced partition of the existing theme browser command chain."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SHARDS = 3


def partition(commands, timings):
    assignments = [[] for _ in range(SHARDS)]
    totals = [0] * SHARDS
    for index in sorted(range(len(commands)), key=lambda i: -timings.get(commands[i], 20)):
        shard = totals.index(min(totals))
        assignments[shard].append(index)
        totals[shard] += timings.get(commands[index], 20)
    return [[commands[index] for index in sorted(indices)] for indices in assignments]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shard', type=int, choices=range(1, SHARDS + 1))
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()

    scripts = json.loads((ROOT / 'package.json').read_text())['scripts']
    commands = scripts['test:themes:browser'].split(' && ')
    timings = json.loads((ROOT / 'tests/themes/browser-timings.json').read_text())
    shard = partition(commands, timings)[args.shard - 1]
    if not shard or not all(shard):
        parser.error('Empty browser theme shard')
    if args.list:
        print(json.dumps(shard))
        return
    for command in shard:
        print(f'Running {command}', flush=True)
        started = time.monotonic()
        subprocess.run(shlex.split(command), cwd=ROOT, check=True)
        print(f'{time.monotonic() - started:.1f}s {command}', flush=True)


if __name__ == '__main__':
    main()
