#!/usr/bin/env python3
"""Reuse authenticated successes for identical test units; any doubt runs tests."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import stat
import shutil
import subprocess
import sys
import platform as host_platform
import queue
import threading
import time
from urllib.parse import urlencode
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = runpy.run_path(str(ROOT / 'scripts/release-inputs.py'))
RUNTIME = {'ui', 'tv-runtime', 'setup', 'installer', 'android', 'preview'}
KINDS = {'runtime': RUNTIME, 'browser': {'browser-core', 'browser-themes'}, 'optional': {'optional-python'},
         'desktop': {'installer-host'}}
DESKTOP_JOBS = {
    'windows-latest': 'build (windows-latest, cytv-windows-x64, dist/cytv.exe)',
    'ubuntu-22.04': 'build (ubuntu-22.04, cytv-linux-x64, dist/cytv)',
    'macos-15': 'build (macos-15, cytv-macos-arm64, dist/cytv)',
    'macos-15-intel': 'build (macos-15-intel, cytv-macos-x64, dist/cytv)',
}
PLATFORMS = {'runtime': {'ubuntu-latest', 'macos-latest'},
             'browser': {'ubuntu-latest', 'macos-latest'},
             'optional': {'ubuntu-latest', 'macos-latest'}, 'desktop': set(DESKTOP_JOBS)}
SHA = re.compile('[0-9a-f]{40}')
DIGEST = re.compile('[0-9a-f]{64}')
ARCHIVE_LIMIT = 128 * 1024
JSON_LIMIT = 64 * 1024
POLICY_VERSION = 2


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def normalize(kind, units, shard):
    units = set(units.split())
    if kind == 'runtime' and 'tv' in units:
        units.remove('tv')
        units.update(('ui', 'tv-runtime'))
    if kind not in KINDS or not units <= KINDS[kind] or not re.fullmatch('[1-4]/4', shard):
        raise ValueError('Invalid test selection')
    if kind != 'runtime' and shard != '1/4':
        raise ValueError('Browser/optional evidence has no runtime partition')
    if kind == 'runtime' and shard != '1/4':
        units -= {'ui', 'android'}
    if kind == 'runtime' and shard != '2/4':
        units.discard('preview')
    return sorted(units)


def test_units(path, entry):
    """Narrow only audited executable test families, never product dependencies.

    Family-wide coverage includes every shard: discovery order can repartition
    tests. Unknown helpers, fixtures, initializers, CI/release self-tests and all
    themes stay global. Audit cross-family imports before extending this policy.
    """
    if entry[:2] not in (('100644', 'blob'), ('100755', 'blob')) or '/fixtures/' in path:
        return None
    if re.fullmatch(r'tests/cytv/test_[^/]+\.py', path) or path == 'tests/cytv/clean_removal_fixture.py':
        units = {'installer', 'installer-host'}
        if Path(path).name in {'test_desktop_recovery.py', 'test_operations.py',
                              'test_no_root_integration.py', 'test_no_root_observer.py',
                              'clean_removal_fixture.py'}:
            units.update(('android', 'browser-core'))
        if path == 'tests/cytv/test_python_runtime.py':
            units.add('optional-python')
        return units
    # Installer tests import Root/system-updater test fixtures and base classes.
    if re.fullmatch(r'(root-edition/tests|tests/system_updates)/test_[^/]+\.(py|cjs)', path):
        return {'tv-runtime', 'installer', 'installer-host'}
    if (re.fullmatch(r'homebrew/tests/test_[^/]+\.py', path)
            or path in {'homebrew/tests/runtime.cjs', 'homebrew/tests/bridge.cjs', 'homebrew/tests/ui.cjs'}):
        return {'installer'}
    if (re.fullmatch(r'android/tests/test_[^/]+\.py', path)
            or path == 'android/tests/auto-recovery-journey.cjs'):
        return {'android', 'browser-core'}
    if (re.fullmatch(r'tests/updates/[^/]+\.cjs', path)
            or (re.fullmatch(r'tests/apps/[^/]+\.cjs', path) and path != 'tests/apps/ui.cjs')
            or (re.fullmatch(r'tests/i18n/[^/]+\.cjs', path) and path != 'tests/i18n/browser.cjs')):
        return {'tv-runtime'}
    if path in {'tests/showcase/registry.cjs', 'tests/showcase/submission-security.cjs',
                'tests/showcase/remote.cjs', 'tests/home-presentation-ui.cjs',
                'tests/root-decoder-ui.cjs', 'tests/preview-presentation-ui.cjs',
                'tests/preview-bridge.cjs', 'tests/preview-themes-ui.cjs', 'tests/test_preview.py'}:
        return {'preview'}
    return None


def keys(snapshot, tree, kind, platform, shard, units, environment):
    owners = {path: test_units(path, entry) for path, entry in snapshot.items()}
    return {unit: digest([POLICY_VERSION,
                          {path: entry for path, entry in snapshot.items()
                           if unit == 'setup' or owners[path] is None or unit in owners[path]},
                          tree if unit == 'setup' else None,
                          kind, unit, platform, shard, environment]) for unit in units}


def context(kind, platform, shard, units, environment, root=ROOT):
    if kind not in PLATFORMS or platform not in PLATFORMS[kind]:
        raise ValueError('Unknown runner platform')
    checkout = INPUTS['git']('rev-parse', 'HEAD', root=root).decode().strip()
    tree = INPUTS['git']('rev-parse', 'HEAD^{tree}', root=root).decode().strip()
    source = INPUTS['snapshot'](checkout, root)
    selected = normalize(kind, units, shard)
    identity = digest([POLICY_VERSION, kind, platform, shard, environment])
    return dict(kind=kind, os=platform, shard=shard, units=selected, checkout=checkout,
                tree=tree, environment=environment, artifact=f'cytv-evidence-v2-{kind}-{platform}-{shard.replace("/", "-")}-{identity}',
                keys=keys(source, tree, kind, platform, shard, selected, environment))


def strict_json(raw):
    def pairs(items):
        result = {}
        for name, value in items:
            if name in result:
                raise ValueError('Duplicate JSON field')
            result[name] = value
        return result
    def nonfinite(_value):
        raise ValueError('Non-finite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def receipt_from_archive(raw, artifact):
    if (len(raw) > ARCHIVE_LIMIT or len(raw) != artifact['size_in_bytes']
            or artifact['digest'] != 'sha256:' + hashlib.sha256(raw).hexdigest()):
        raise ValueError('Artifact digest/size mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) != 1:
            raise ValueError('Expected one flat receipt')
        entry = entries[0]
        mode = entry.external_attr >> 16
        if (entry.filename != 'receipt.json' or entry.file_size > JSON_LIMIT
                or entry.flag_bits & 1 or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))):
            raise ValueError('Unsafe receipt archive')
        value = strict_json(archive.read(entry))
    required = {'schema', 'repository', 'run', 'attempt', 'job', 'checkout', 'tree', 'kind', 'os', 'shard', 'keys'}
    if not isinstance(value, dict) or set(value) != required or type(value['schema']) is not int or value['schema'] != 2:
        raise ValueError('Unknown receipt schema')
    if any(type(value[name]) is not int or value[name] <= 0 for name in ('run', 'attempt', 'job')):
        raise ValueError('Invalid receipt provenance')
    if any(not isinstance(value[name], str) or not SHA.fullmatch(value[name]) for name in ('checkout', 'tree')):
        raise ValueError('Invalid receipt source')
    if (value['kind'] not in KINDS or not isinstance(value['keys'], dict) or not value['keys']
            or not set(value['keys']) <= KINDS[value['kind']]
            or any(not isinstance(key, str) or not DIGEST.fullmatch(key) for key in value['keys'].values())):
        raise ValueError('Invalid receipt units')
    normalize(value['kind'], ' '.join(value['keys']), value['shard'])
    return value


def job_name(ctx, candidate=False):
    if ctx['kind'] == 'desktop':
        return DESKTOP_JOBS[ctx['os']]
    name = (f'runtime ({ctx["os"]}, {ctx["shard"].split("/")[0]})'
            if ctx['kind'] == 'runtime' else 'browser' if ctx['kind'] == 'browser' else 'optional-python')
    return 'validation / ' + name if candidate else name


def run_jobs(run, api):
    response = api(f'actions/runs/{run["id"]}/attempts/{run["run_attempt"]}/jobs?per_page=100')
    if response['total_count'] != len(response['jobs']):
        raise ValueError('Incomplete job listing')
    return response['jobs']


def candidate_run(run, repo):
    return (run.get('repository', {}).get('full_name') == repo
            and run.get('head_repository', {}).get('full_name') == repo
            and run.get('event') == 'workflow_dispatch' and run.get('head_branch') == 'release/next'
            and run.get('path') == '.github/workflows/cytv.yml' and run.get('run_attempt') == 1
            and run.get('status') == 'completed' and run.get('conclusion') in ('success', 'failure'))


def full_candidate_jobs(jobs):
    def unique(name, conclusions):
        matches = [job for job in jobs if job['name'] == name]
        return (len(matches) == 1 and matches[0]['status'] == 'completed'
                and matches[0]['conclusion'] in conclusions)
    return (unique('scope', ('success',))
            and unique('validation / full-release', ('success', 'failure')))


def candidate_cache_hit(run, current, repo, ctx, jobs, api):
    if not candidate_run(run, repo) or not full_candidate_jobs(jobs):
        return False
    query = urlencode({'branch': 'release/next', 'event': 'workflow_dispatch', 'per_page': 100})
    runs = api('actions/workflows/cytv.yml/runs?' + query)['workflow_runs']
    prior = [item for item in runs if item['id'] < current
             and item.get('head_branch') == 'release/next'
             and item.get('head_repository', {}).get('full_name') == repo]
    if not prior:
        return False
    latest = max(prior, key=lambda item: item['id'])
    if not candidate_run(latest, repo):
        return False
    latest_jobs = jobs if latest['id'] == run['id'] else run_jobs(latest, api)
    matching = [job for job in latest_jobs if job['name'] == job_name(ctx, candidate=True)]
    return (full_candidate_jobs(latest_jobs) and len(matching) == 1
            and matching[0]['status'] == 'completed' and matching[0]['conclusion'] == 'success')


def remote_snapshot(tree):
    if tree.get('truncated') is not False or not isinstance(tree.get('tree'), list):
        raise ValueError('Incomplete remote tree')
    result = {}
    for entry in tree['tree']:
        path, mode, kind, sha = (entry[name] for name in ('path', 'mode', 'type', 'sha'))
        if kind == 'tree':
            continue
        if (not isinstance(path, str) or path in result or not SHA.fullmatch(sha)
                or (mode, kind) not in {('100644', 'blob'), ('100755', 'blob'), ('120000', 'blob'), ('160000', 'commit')}):
            raise ValueError('Malformed remote tree')
        if mode == '100644' and kind == 'blob' and INPUTS['metadata_path'](path):
            continue
        result[path] = (mode, kind, sha)
    return result


def validate_receipt(ctx, receipt, artifact, repo, current, api):
    if (receipt['repository'] != repo or receipt['run'] == current or receipt['attempt'] != 1
            or any(receipt[name] != ctx[name] for name in ('kind', 'os', 'shard'))):
        raise ValueError('Different receipt context')
    run = api('actions/runs/' + str(receipt['run']))
    if (run['id'] != receipt['run'] or run['run_attempt'] != receipt['attempt']
            or run.get('repository', {}).get('full_name') != repo
            or artifact.get('workflow_run', {}).get('id') != run['id']
            or artifact['workflow_run'].get('head_sha') != run['head_sha']):
        raise ValueError('Different artifact/run provenance')
    jobs = run_jobs(run, api)
    candidate = run.get('path') == '.github/workflows/cytv.yml'
    valid_run = (candidate_cache_hit(run, current, repo, ctx, jobs, api) if candidate else
                 ctx['kind'] != 'desktop' and INPUTS['test_cache_hit'](run['id'], current, repo, run['head_branch'], api))
    if not valid_run:
        raise ValueError('Run is not current same-repository successful evidence')
    matches = [job for job in jobs if job['id'] == receipt['job']]
    if (len(matches) != 1 or matches[0]['name'] != job_name(ctx, candidate)
            or matches[0]['status'] != 'completed' or matches[0]['conclusion'] != 'success'
            or matches[0]['run_id'] != run['id'] or matches[0].get('run_attempt', receipt['attempt']) != receipt['attempt']):
        raise ValueError('Missing successful originating job')
    if candidate and receipt['checkout'] != run['head_sha']:
        raise ValueError('Candidate checkout must be exact dispatch source')
    commit = api('commits/' + receipt['checkout'])
    if (commit['sha'] != receipt['checkout'] or commit['commit']['tree']['sha'] != receipt['tree']
            or (receipt['checkout'] != run['head_sha'] and
                (len(commit['parents']) != 2 or commit['parents'][1]['sha'] != run['head_sha']))):
        raise ValueError('Not the tested PR checkout')
    source = remote_snapshot(api('git/trees/' + receipt['tree'] + '?recursive=1'))
    expected = keys(source, receipt['tree'], ctx['kind'], ctx['os'], ctx['shard'], receipt['keys'], ctx['environment'])
    accepted = [unit for unit in ctx['units'] if unit in expected
                and receipt['keys'][unit] == expected[unit] == ctx['keys'][unit]]
    return {unit: f'https://github.com/{repo}/actions/runs/{run["id"]}/job/{receipt["job"]}' for unit in accepted}


def select_missing(ctx, repo, current, api):
    if ctx['environment'].get('browser', '') is None or ctx['environment'].get('identity_ready') is False:
        return {'missing': ctx['units'], 'reused': {}}
    reused = {}
    started = time.monotonic()
    deadline = started + 60
    # One lookup observes one bounded API snapshot; never persist mutable run state.
    responses = {}
    requests = cache_hits = rejected_keys = 0
    def bounded_api(path, binary=False):
        nonlocal requests, cache_hits
        if time.monotonic() >= deadline:
            raise TimeoutError('Evidence lookup budget exhausted')
        if not binary and path in responses:
            cache_hits += 1
            return responses[path]
        requests += 1
        value = api(path, binary=binary)
        if time.monotonic() >= deadline:
            raise TimeoutError('Evidence lookup budget exhausted')
        if not binary:
            responses[path] = value
        return value
    try:
        # Bounded recent discovery: older/missing evidence executes, never grants coverage.
        query = urlencode({'name': ctx['artifact'], 'per_page': 100})
        artifacts = bounded_api('actions/artifacts?' + query)['artifacts']
        for artifact in artifacts:
            if time.monotonic() >= deadline:
                break
            if artifact.get('name') != ctx['artifact'] or artifact.get('expired') is not False:
                continue
            try:
                size = artifact['size_in_bytes']
                if type(size) is not int or not 0 < size <= ARCHIVE_LIMIT:
                    continue
                receipt = receipt_from_archive(bounded_api(f'actions/artifacts/{artifact["id"]}/zip', binary=True), artifact)
                # A mismatch can only reject work. Matching keys still require every
                # provenance, latest-run, job and authenticated-tree check below.
                if not any(receipt['keys'].get(unit) == ctx['keys'][unit]
                           for unit in ctx['units'] if unit not in reused):
                    rejected_keys += 1
                    continue
                reused.update(validate_receipt(ctx, receipt, artifact, repo, current, bounded_api))
            except Exception:
                # Untrusted/malformed or unavailable evidence is only a cache miss.
                continue
            if set(reused) == set(ctx['units']):
                break
    except Exception:
        pass  # Discovery is optional; actual tests remain mandatory.
    print(f'Evidence lookup: {time.monotonic() - started:.2f}s, {requests} API requests, '
          f'{cache_hits} cached responses, {rejected_keys} nonmatching receipts')
    return {'missing': sorted(set(ctx['units']) - set(reused)), 'reused': reused}


def make_receipt(ctx, repo, run, attempt, job):
    if ctx['environment'].get('browser', '') is None or ctx['environment'].get('identity_ready') is False:
        raise ValueError('Cannot attest unavailable browser/tool fingerprints')
    return dict(schema=2, repository=repo, run=run, attempt=attempt, job=job,
                checkout=ctx['checkout'], tree=ctx['tree'], kind=ctx['kind'], os=ctx['os'],
                shard=ctx['shard'], keys={unit: ctx['keys'][unit] for unit in ctx['units']})


def command(*args):
    return subprocess.check_output([shutil.which(args[0]) or args[0], *args[1:]],
                                   text=True, stderr=subprocess.DEVNULL, timeout=60).strip()


def environment(kind, shard='1/4'):
    def observed(*args):
        try:
            return command(*args)
        except (OSError, subprocess.SubprocessError):
            if kind != 'desktop':
                raise
            return None
    result = {name: os.environ.get(name, '') for name in ('RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion')}
    result.update(python=sys.version, node=observed('node', '--version'),
                  dependencies=observed(sys.executable, '-m', 'pip', 'freeze'),
                  system=host_platform.platform() if kind == 'desktop' else command('uname', '-sr'),
                  day=datetime.now(timezone.utc).date().isoformat())
    if kind == 'desktop':
        for name, args in (('git', ('git', '--version')),
                           ('zig', (sys.executable, '-m', 'ziglang', 'version'))):
            try:
                result[name] = command(*args)
            except (OSError, subprocess.SubprocessError):
                result[name] = None
        result['compiler_path'] = shutil.which('cc')
        result['compiler'] = observed('cc', '--version') if result['compiler_path'] else None
        try:
            shell = Path('/bin/sh')
            if sys.platform == 'win32':
                git = shutil.which('git')
                if git is None:
                    raise ValueError('Missing Git shell installation')
                # Match the local SSH fixture; a PATH shell may be a WSL launcher.
                shell = Path(git).resolve().parent.parent / 'bin' / 'sh.exe'
            if command(str(shell), '-c', 'printf cytv-ci-shell') != 'cytv-ci-shell':
                raise ValueError('Unusable local SSH shell')
            with shell.open('rb') as binary:
                result['shell'] = dict(path=str(shell), resolved=str(shell.resolve()),
                                       sha256=hashlib.file_digest(binary, 'sha256').hexdigest())
        except (OSError, ValueError, subprocess.SubprocessError):
            result['shell'] = None

    else:
        result['compiler'] = command('cc', '--version')
    if kind != 'optional':
        # npm ci is source pinned; retain actual installed dependency identity too.
        npm = observed('npm', 'ls', '--all', '--json')
        result['npm'] = hashlib.sha256(npm.encode()).hexdigest() if npm else None
    if kind == 'desktop':
        result['qt_platform'] = os.environ.get('QT_QPA_PLATFORM', '')
        if result['RUNNER_OS'] == 'Linux':
            try:
                result['desktop_libraries'] = command('dpkg-query', '-W', '-f=${Package}=${Version}\n',
                    'libegl1', 'libopengl0', 'libxcb-cursor0', 'libxkbcommon-x11-0',
                    'libxcb-icccm4', 'libxcb-keysyms1', 'libxcb-render-util0', 'xvfb', 'xauth')
            except (OSError, subprocess.SubprocessError):
                result['desktop_libraries'] = None
        required = ('RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion', 'python', 'node',
                    'dependencies', 'npm', 'git', 'zig', 'system', 'shell')
        result['identity_ready'] = (all(result[name] for name in required)
                                    and result.get('desktop_libraries', True) is not None
                                    and (result['compiler_path'] is None or bool(result['compiler'])))
    if kind == 'browser' or (kind == 'runtime' and shard in ('1/4', '2/4')):
        # Keep UI (1) bound conservatively; Homebrew and preview (2) use Chrome,
        # independently of the Chromium browser job. Unknown versions never grant reuse.
        result['browser'] = None
        try:
            result['playwright'] = command('node', '-e', "process.stdout.write(require('playwright/package.json').version)")
            if kind == 'browser':
                executable = command('node', '-e', "process.stdout.write(require('playwright').chromium.executablePath())")
                result['browser'] = command(executable, '--version')
            else:
                result['browser_channel'] = os.environ.get('BROWSER_CHANNEL') or 'chrome'
                result['browser'] = command('node', '-e', """
const {chromium}=require('playwright');
(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
  try { process.stdout.write(browser.version()); } finally { await browser.close(); }
})().catch(()=>process.exit(1));
""")
            if not result['browser']:
                result['browser'] = None
        except (OSError, subprocess.SubprocessError):
            result['browser'] = None
    if kind == 'optional':
        result['arm'] = command('dpkg-query', '-W', '-f=${Package}=${Version}\n', 'qemu-user', 'libc6-armel-cross', 'libgcc-s1-armel-cross')
    return result


def github_api(repo):
    def api(path, binary=False):
        # gh follows the API's archive redirect; no producer URL or code is executed.
        limit = ARCHIVE_LIMIT if binary else 8 * 1024 * 1024
        process = subprocess.Popen(['gh', 'api', f'repos/{repo}/{path}'],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        # Windows pipes cannot use selectors. A single bounded reader owns stdout;
        # killing the child on timeout/error releases its blocking read on every OS.
        result = queue.Queue(maxsize=1)
        def read():
            raw = bytearray()
            try:
                while True:
                    chunk = process.stdout.read(min(65536, limit + 1 - len(raw)))
                    if not chunk:
                        break
                    raw.extend(chunk)
                    if len(raw) > limit:
                        raise ValueError('API response exceeds evidence limit')
                result.put(bytes(raw))
            except Exception as error:
                result.put(error)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        deadline = time.monotonic() + 20
        try:
            try:
                raw = result.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise TimeoutError('GitHub API evidence deadline') from None
            if isinstance(raw, Exception):
                raise raw
            if process.wait(timeout=max(0.01, deadline - time.monotonic())):
                raise ValueError('GitHub API failed')
            return raw if binary else strict_json(raw)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            reader.join(timeout=1)
            if not reader.is_alive():
                process.stdout.close()

    return api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'record'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--kind', choices=KINDS)
    parser.add_argument('--os', choices=sorted(set().union(*PLATFORMS.values())))
    parser.add_argument('--shard', default='1/4')
    parser.add_argument('--units', default='')
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    repo = os.environ['GITHUB_REPOSITORY']
    current, attempt = int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])
    api = github_api(repo)
    if args.action == 'plan':
        if args.kind is None or args.os is None:
            parser.error('plan requires --kind and --os')
        event = strict_json(Path(os.environ['GITHUB_EVENT_PATH']).read_bytes())
        same_repo = (os.environ['GITHUB_EVENT_NAME'] != 'pull_request' or
                     event.get('pull_request', {}).get('head', {}).get('repo', {}).get('full_name') == repo)
        ctx = context(args.kind, args.os, args.shard, args.units, environment(args.kind, args.shard))
        selected = select_missing(ctx, repo, current, api) if attempt == 1 and same_repo else {'missing': ctx['units'], 'reused': {}}
        ctx['units'] = selected['missing']  # Receipts never attest transitively reused units.
        (args.directory / 'plan.json').write_text(json.dumps(ctx))
        lines = [f'{unit}: reused {url}' for unit, url in selected['reused'].items()]
        lines += [f'{unit}: fresh (no matching authenticated success)' for unit in selected['missing']]
        print('\n'.join(lines) or 'No test units selected for this shard')
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
                output.write('\n'.join('- ' + line for line in lines) + '\n')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('missing=' + ' '.join(selected['missing']) + '\n')
            output.write('fresh=' + str(bool(selected['missing'])).lower() + '\n')
            output.write('artifact=' + ctx['artifact'] + '\n')
    else:
        # The workflow calls record only after every fresh command/privileged check succeeds.
        event = strict_json(Path(os.environ['GITHUB_EVENT_PATH']).read_bytes())
        pr = (os.environ['GITHUB_EVENT_NAME'] == 'pull_request'
              and event.get('pull_request', {}).get('head', {}).get('repo', {}).get('full_name') == repo)
        candidate = (os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
                     and event.get('inputs', {}).get('full_candidate') in (True, 'true'))
        if attempt != 1 or not (pr or candidate):
            raise ValueError('Only same-repository first-attempt PRs or full candidates may produce evidence')
        ctx = strict_json((args.directory / 'plan.json').read_bytes())
        if not ctx['units']:
            raise ValueError('No fresh work to record')
        if candidate:
            run = api(f'actions/runs/{current}')
            if (run.get('id') != current or run.get('run_attempt') != attempt
                    or run.get('event') != 'workflow_dispatch' or run.get('head_branch') != 'release/next'
                    or run.get('path') != '.github/workflows/cytv.yml'
                    or run.get('repository', {}).get('full_name') != repo
                    or run.get('head_repository', {}).get('full_name') != repo
                    or run.get('head_sha') != ctx['checkout']):
                raise ValueError('Not an exact same-repository full candidate')
        elif ctx['kind'] == 'desktop':
            raise ValueError('Desktop receipts require a full candidate')
        jobs = api(f'actions/runs/{current}/attempts/{attempt}/jobs?per_page=100')
        matches = [job for job in jobs['jobs'] if job['name'] == job_name(ctx, candidate) and job['status'] == 'in_progress']
        if jobs['total_count'] != len(jobs['jobs']) or len(matches) != 1:
            raise ValueError('Cannot identify originating job')
        receipt = make_receipt(ctx, repo, current, attempt, matches[0]['id'])
        (args.directory / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
