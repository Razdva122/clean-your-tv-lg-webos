#!/usr/bin/env python3
"""Conservative, data-only source equivalence for previously built candidates."""
import json
import hashlib
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALL_SCENARIOS = {'ui-controls', 'controls', 'startup', 'update-recovery'}
METADATA_FILES = frozenset((
    'release-plan.json', 'README.md',
    # External guides are not consumed by installer or TV payload builders.
    # The publication-time source archive picks up their final contents, like docs/.
    # Audit packaging before extending this list; embedded guides/notices stay inputs.
    'android/README.md', 'android/STABLE-READINESS.md',
    'root-edition/README.md', 'root-edition/STATUS.md',
    'root-edition/TESTING.md', 'root-edition/UPDATES.md',
    'root-edition/runtime/README.md',
))


def metadata_path(path):
    # Do not exempt arbitrary Markdown: notices and embedded guides are packaged.
    return path in METADATA_FILES or (path.startswith('docs/') and path.endswith('.md'))


def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root)


def build_pin(plan):
    if 'build' not in plan:
        return None
    pin = plan['build']
    if (not isinstance(pin, dict) or set(pin) != {'run_id', 'attempt', 'source'}
            or type(pin['run_id']) is not int or pin['run_id'] <= 0
            or type(pin['attempt']) is not int or pin['attempt'] <= 0
            or not isinstance(pin['source'], str) or not re.fullmatch('[a-f0-9]{40}', pin['source'])):
        raise ValueError('Invalid build pin: expected positive run_id/attempt and full source SHA')
    return pin


def snapshot(commit, root=ROOT):
    if not isinstance(commit, str) or not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Invalid source SHA')
    entries = {}
    for item in git('ls-tree', '-r', '-z', commit, root=root).split(b'\0'):
        if item:
            identity, name = item.split(b'\t', 1)
            path = name.decode('utf-8')
            mode, kind, blob = identity.decode().split()
            if mode == '100644' and kind == 'blob' and metadata_path(path):
                continue
            entries[path] = (mode, kind, blob)
    return entries


def verify_inputs(source, candidate, root=ROOT):
    before, after = snapshot(source, root), snapshot(candidate, root)
    if subprocess.run(['git', 'merge-base', '--is-ancestor', source, candidate], cwd=root,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise ValueError('Build source must be an ancestor of the candidate')
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    if changed:
        raise ValueError('Candidate build inputs changed; rebuild required: ' + ', '.join(changed))


def pin_at(candidate, root=ROOT):
    if not git('ls-tree', candidate, 'release-plan.json', root=root).strip():
        return None  # Historical exact-source builds predate the plan.
    return build_pin(json.loads(git('show', candidate + ':release-plan.json', root=root)))


def acceptance_scope(paths):
    """Recommend retests; hashes, preconditions and human observations remain required."""
    selected = set()
    for path in paths:
        if metadata_path(path):
            continue
        if path.startswith(('launcher/', 'root-edition/ui/', 'updater-app/')) and Path(path).suffix in ('.css', '.svg', '.png', '.woff', '.woff2'):
            selected.add('ui-controls')
        elif path.startswith(('native/', 'root-edition/service/', 'root-edition/input/')):
            selected.update(('controls', 'startup', 'update-recovery'))
        elif path.startswith(('cytv/', 'android/', 'homebrew/', 'updater-service/',
                              'root-edition/updater/', 'system-updater/')):
            selected.add('update-recovery')
        else:
            selected.update(ALL_SCENARIOS)
    return selected


def test_key(commit, selection, environment, root=ROOT):
    """A success marker is reusable only for the same merged inputs and runtime."""
    raw = json.dumps([snapshot(commit, root), selection, environment], sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def test_cache_hit(run_id, current_id, repo, branch, provider):
    """A newer failed/running attempt overrides an older cached success."""
    from urllib.parse import urlencode
    def successful(run):
        return (run.get('status') == 'completed' and run.get('conclusion') == 'success'
                and run.get('event') == 'pull_request' and run.get('head_branch') == branch
                and run.get('path') == '.github/workflows/tests.yml'
                and run.get('head_repository', {}).get('full_name') == repo)
    original = provider('actions/runs/' + str(run_id))
    if not successful(original):
        return False
    query = urlencode({'branch': branch, 'event': 'pull_request', 'per_page': 100})
    runs = provider('actions/workflows/tests.yml/runs?' + query)['workflow_runs']
    prior = [run for run in runs if run['id'] != current_id and run.get('head_branch') == branch
             and run.get('head_repository', {}).get('full_name') == repo]
    return bool(prior and successful(max(prior, key=lambda run: run['id'])))


if __name__ == '__main__':
    import argparse
    from datetime import datetime, timezone
    import os
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--test-key', action='store_true')
    mode.add_argument('--check-test-cache', type=Path)
    args = parser.parse_args()
    if args.test_key:
        environment = {name: os.environ.get(name, '') for name in ('RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion')}
        environment.update(python=sys.version, node=subprocess.check_output(['node', '--version'], text=True).strip(),
                           dependencies=subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True),
                           day=datetime.now(timezone.utc).date().isoformat())
        value = test_key(git('rev-parse', 'HEAD').decode().strip(), os.environ['TEST_SELECTION'], environment)
        output_line = 'key=' + value
    else:
        def provider(path):
            return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + os.environ['GITHUB_REPOSITORY'] + '/' + path],
                                                     stderr=subprocess.DEVNULL, timeout=20))
        try:
            raw = (args.check_test_cache / 'run').read_text().strip()
            hit = bool(re.fullmatch('[1-9][0-9]{0,19}', raw)) and test_cache_hit(
                int(raw), int(os.environ['GITHUB_RUN_ID']), os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_HEAD_REF'], provider)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            hit = False  # Cache/API outages must execute tests, never grant success.
        output_line = 'hit=' + str(hit).lower()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(output_line + '\n')
