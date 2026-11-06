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
import subprocess
import sys
import selectors
import time
from urllib.parse import urlencode
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = runpy.run_path(str(ROOT / 'scripts/release-inputs.py'))
RUNTIME = {'ui', 'tv-runtime', 'setup', 'installer', 'android', 'preview'}
KINDS = {'runtime': RUNTIME, 'browser': {'browser-core', 'browser-themes'}, 'optional': {'optional-python'}}
SHA = re.compile('[0-9a-f]{40}')
DIGEST = re.compile('[0-9a-f]{64}')
ARCHIVE_LIMIT = 128 * 1024
JSON_LIMIT = 64 * 1024


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
        units -= {'ui', 'android', 'preview'}
    return sorted(units)


def keys(snapshot, tree, kind, platform, shard, units, environment):
    return {unit: digest([snapshot, tree if unit == 'setup' else None,
                          kind, unit, platform, shard, environment]) for unit in units}


def context(kind, platform, shard, units, environment, root=ROOT):
    if platform not in ('ubuntu-latest', 'macos-latest'):
        raise ValueError('Unknown runner platform')
    checkout = INPUTS['git']('rev-parse', 'HEAD', root=root).decode().strip()
    tree = INPUTS['git']('rev-parse', 'HEAD^{tree}', root=root).decode().strip()
    source = INPUTS['snapshot'](checkout, root)
    selected = normalize(kind, units, shard)
    identity = digest([source, kind, platform, shard, environment])
    return dict(kind=kind, os=platform, shard=shard, units=selected, checkout=checkout,
                tree=tree, environment=environment, artifact=f'cytv-evidence-v1-{kind}-{platform}-{shard.replace("/", "-")}-{identity}',
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
    if not isinstance(value, dict) or set(value) != required or type(value['schema']) is not int or value['schema'] != 1:
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


def job_name(ctx):
    return (f'runtime ({ctx["os"]}, {ctx["shard"].split("/")[0]})'
            if ctx['kind'] == 'runtime' else 'browser' if ctx['kind'] == 'browser' else 'optional-python')


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
            or artifact['workflow_run'].get('head_sha') != run['head_sha']
            or not INPUTS['test_cache_hit'](run['id'], current, repo, run['head_branch'], api)):
        raise ValueError('Run is not current same-repository successful PR evidence')
    response = api(f'actions/runs/{run["id"]}/attempts/{receipt["attempt"]}/jobs?per_page=100')
    if response['total_count'] != len(response['jobs']):
        raise ValueError('Incomplete job listing')
    jobs = [job for job in response['jobs'] if job['id'] == receipt['job']]
    if (len(jobs) != 1 or jobs[0]['name'] != job_name(ctx)
            or jobs[0]['status'] != 'completed' or jobs[0]['conclusion'] != 'success'
            or jobs[0]['run_id'] != run['id'] or jobs[0].get('run_attempt', receipt['attempt']) != receipt['attempt']):
        raise ValueError('Missing successful originating job')
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
    if ctx['environment'].get('browser', '') is None:
        return {'missing': ctx['units'], 'reused': {}}
    reused = {}
    deadline = time.monotonic() + 60
    def bounded_api(*args, **kwargs):
        if time.monotonic() >= deadline:
            raise TimeoutError('Evidence lookup budget exhausted')
        value = api(*args, **kwargs)
        if time.monotonic() >= deadline:
            raise TimeoutError('Evidence lookup budget exhausted')
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
                reused.update(validate_receipt(ctx, receipt, artifact, repo, current, bounded_api))
            except Exception:
                # Untrusted/malformed or unavailable evidence is only a cache miss.
                continue
            if set(reused) == set(ctx['units']):
                break
    except Exception:
        pass  # Discovery is optional; actual tests remain mandatory.
    return {'missing': sorted(set(ctx['units']) - set(reused)), 'reused': reused}


def make_receipt(ctx, repo, run, attempt, job):
    if ctx['environment'].get('browser', '') is None:
        raise ValueError('Cannot attest an unavailable browser fingerprint')
    return dict(schema=1, repository=repo, run=run, attempt=attempt, job=job,
                checkout=ctx['checkout'], tree=ctx['tree'], kind=ctx['kind'], os=ctx['os'],
                shard=ctx['shard'], keys={unit: ctx['keys'][unit] for unit in ctx['units']})


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=60).strip()


def environment(kind, shard='1/4'):
    result = {name: os.environ.get(name, '') for name in ('RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion')}
    result.update(python=sys.version, node=command('node', '--version'),
                  dependencies=command(sys.executable, '-m', 'pip', 'freeze'),
                  compiler=command('cc', '--version'), system=command('uname', '-sr'),
                  day=datetime.now(timezone.utc).date().isoformat())
    if kind != 'optional':
        # npm ci is source pinned; retain actual installed dependency identity too.
        result['npm'] = hashlib.sha256(command('npm', 'ls', '--all', '--json').encode()).hexdigest()
    if kind == 'browser' or (kind == 'runtime' and shard == '1/4'):
        # Primary runtime preview/Homebrew checks use system Chrome, independently
        # of the separate Chromium browser job. Unknown versions never grant reuse.
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
        deadline = time.monotonic() + 20
        raw = bytearray()
        try:
            with selectors.DefaultSelector() as reader:
                reader.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not reader.select(remaining):
                        raise TimeoutError('GitHub API evidence deadline')
                    chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(raw)))
                    if not chunk:
                        break
                    raw.extend(chunk)
                    if len(raw) > limit:
                        raise ValueError('API response exceeds evidence limit')
            if process.wait(timeout=max(0.01, deadline - time.monotonic())):
                raise ValueError('GitHub API failed')
            return bytes(raw) if binary else strict_json(bytes(raw))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
    return api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'record'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--kind', choices=KINDS)
    parser.add_argument('--os', choices=('ubuntu-latest', 'macos-latest'))
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
        if (os.environ['GITHUB_EVENT_NAME'] != 'pull_request' or attempt != 1
                or event.get('pull_request', {}).get('head', {}).get('repo', {}).get('full_name') != repo):
            raise ValueError('Only same-repository first-attempt PRs may produce evidence')
        ctx = strict_json((args.directory / 'plan.json').read_bytes())
        if not ctx['units']:
            raise ValueError('No fresh work to record')
        jobs = api(f'actions/runs/{current}/attempts/{attempt}/jobs?per_page=100')
        matches = [job for job in jobs['jobs'] if job['name'] == job_name(ctx) and job['status'] == 'in_progress']
        if jobs['total_count'] != len(jobs['jobs']) or len(matches) != 1:
            raise ValueError('Cannot identify originating job')
        receipt = make_receipt(ctx, repo, current, attempt, matches[0]['id'])
        (args.directory / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
