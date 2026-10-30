#!/usr/bin/env python3
"""Compile isolated TV UI, or explicitly deliver protected signed Root QA artifacts.

UI never installs Root or accesses its services. Candidate packages remain preliminary
QA and use the installed production verifier, profile handling and rollback worker.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP_ID = 'com.cleanyourtv.dev.ui'
MARKER = '.cytv-dev-ui.json'
REPO = 'Razdva122/clean-your-tv-lg-webos'
MAX_ARCHIVE = 200 * 1024 * 1024


def read_file(path, limit=64 * 1024 * 1024):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
        raise ValueError('Regular bounded input required')
    return path.read_bytes()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ui_files():
    """Use the existing explicit Root UI inventory, never its production identity."""
    files = runpy.run_path(str(ROOT / 'root-edition/preview.py'))['prepare']()
    info = json.loads(files['appinfo.json'])
    info.update(id=APP_ID, title='Home UI Development', requiredACG=[], version='0.0.1')
    info.pop('appCategory', None)
    files['appinfo.json'] = (json.dumps(info, indent=2) + '\n').encode()
    inventory = json.loads(read_file(ROOT / 'preview/reference-apps/inventory.json'))
    inventory['referenceApps'] = True
    files['apps.js'] = ('window.TV_APPS = ' + json.dumps(inventory) + ';\n').encode()
    files['bridge.js'] = read_file(ROOT / 'preview/bridge.js')
    for name, raw in list(files.items()):
        if name.endswith(('.js', '.html')):
            # A separate namespace also protects profiles when hosted CLI origins
            # are reused. All product reads/writes see only this development store.
            files[name] = re.sub(rb'\blocalStorage\b', b'window.CYTV_DEV_STORAGE', raw)
            files[name] = re.sub(rb'\bindexedDB\b', b'CYTV_DEV_INDEXEDDB', files[name])
    files['dev-bridge.js'] = b'''(function () {
  'use strict';
  var storage = window.localStorage, prefix = 'cytv.dev.ui.';
  function locked(name, value) { Object.defineProperty(window, name, {value:value, writable:false, configurable:false}); }
  locked('CYTV_DEV_STORAGE', Object.freeze({
    getItem:function (key) { return storage.getItem(prefix + key); },
    setItem:function (key, value) { storage.setItem(prefix + key, value); },
    removeItem:function (key) { storage.removeItem(prefix + key); }
  }));
  var database = window.indexedDB;
  locked('CYTV_DEV_INDEXEDDB', database ? Object.freeze({
    open:function (name, version) { return version === undefined ? database.open(prefix + name) : database.open(prefix + name, version); },
    deleteDatabase:function (name) { return database.deleteDatabase(prefix + name); }
  }) : null);
  function unavailable() { return {cancel:function () {}}; }
  function DisabledBridge() {}
  DisabledBridge.prototype.call = unavailable; DisabledBridge.prototype.cancel = unavailable;
  window.PalmServiceBridge = DisabledBridge;
  locked('webOS', Object.freeze({service:Object.freeze({request:unavailable})}));
  locked('PalmSystem', Object.freeze({}));
  locked('webOSSystem', Object.freeze({}));
}());\n'''
    files['dev-lock.js'] = b'''(function () {
  'use strict';
  var mock = window.PalmServiceBridge;
  if (typeof mock !== 'function' || window.CYTV_BROWSER_PREVIEW !== true) throw Error('Development bridge unavailable');
  Object.freeze(mock.prototype); Object.freeze(mock);
  Object.defineProperty(window, 'PalmServiceBridge', {value:mock, writable:false, configurable:false});
}());\n'''
    html = files['index.html'].decode()
    if html.count('<head>') != 1:
        raise ValueError('Unexpected preview HTML')
    policy = "default-src 'self' data:; img-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'"
    files['index.html'] = html.replace('<head>', '<head>\n<meta http-equiv="Content-Security-Policy" content="' + policy + '">', 1).encode()
    # Include the simulation's only relative icon fallback without directory escape.
    files['bridge.js'] = files['bridge.js'].replace(b'../preview/icons/browser.svg', b'preview/icons/browser.svg')
    files['preview/icons/browser.svg'] = read_file(ROOT / 'preview/icons/browser.svg')
    scripts = []
    def inert_script(match):
        attrs, code = match.groups()
        source = re.fullmatch(r'\s+src="([A-Za-z0-9._/-]+)"\s*', attrs)
        if source:
            name = source[1]
            if name not in files: raise ValueError('Unpackaged preview script')
        elif not attrs.strip():
            name = 'dev-inline-' + str(len(scripts)) + '.js'
            files[name] = code.encode()
        else:
            raise ValueError('Unsupported preview script attributes')
        scripts.append('<script src="' + name + '"></script>')
        return ''
    html = re.sub(r'<script\b([^>]*)>([\s\S]*?)</script\s*>', inert_script, files['index.html'].decode())
    # One script owns isolation and parser insertion. A readonly native global or
    # any failed guard stops this file before *any* product script is reachable.
    files['dev-entry.js'] = (files['dev-bridge.js'] + files['bridge.js'] + files['dev-lock.js']
                             + ('\ndocument.write(' + json.dumps(''.join(scripts)) + ');\n').encode())
    files['index.html'] = html.replace('</body>', '<script src="dev-entry.js"></script>\n</body>', 1).encode()
    return files


def stage_ui(output, compiler=None):
    output = Path(output).absolute()
    if any(p.is_symlink() and p not in (Path('/var'), Path('/tmp')) for p in [output, *output.parents]) or output.is_symlink():
        raise ValueError('Indirect output path refused')
    protected = [ROOT / name for name in ('launcher', 'root-edition', 'preview', 'scripts', 'tests', 'docs', '.git')]
    resolved = output.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve().is_relative_to(resolved) or any(resolved.is_relative_to(p.resolve()) for p in protected):
        raise ValueError('UI output must be separate from source')
    if output.exists() and (not output.is_dir() or not (output / MARKER).is_file()
                            or json.loads(read_file(output / MARKER, 1024)) != {'app_id': APP_ID}):
        raise ValueError('Refusing to replace unmanaged output')
    if compiler is None:
        compiler = runpy.run_path(str(ROOT / 'scripts/tv_web_build.py'))['compile_web']
    files = compiler(ui_files())
    output.parent.mkdir(parents=True, exist_ok=True)
    # Compile and validate every file before exposing a new generation. The hosted
    # CLI is stopped during the directory swap; a failed compile preserves it.
    with tempfile.TemporaryDirectory(prefix='.tv-dev-', dir=output.parent) as tmp:
        staged, old = Path(tmp) / 'new', Path(tmp) / 'old'
        staged.mkdir()
        for name, raw in files.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe staged asset')
            target = staged / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (staged / MARKER).write_text(json.dumps({'app_id': APP_ID}) + '\n')
        if output.exists(): output.rename(old)
        try:
            staged.rename(output)
        except BaseException:
            if old.exists(): old.rename(output)
            raise
    return output


def require_device_consent(owner_present):
    if not owner_present:
        raise ValueError('Explicit --owner-present is required for any TV connection')


def hosted_command(output, device):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', device or ''):
        raise ValueError('Invalid named webOS CLI device')
    return ['ares-launch', '--hosted', str(output), '-d', device]


def source_revision():
    paths = [ROOT / folder for folder in ('launcher', 'root-edition/ui', 'root-edition/assets', 'preview')]
    paths += [ROOT / 'root-edition/preview.py', Path(__file__), ROOT / 'scripts/compile-tv-web.cjs', ROOT / 'scripts/tv_web_build.py', ROOT / 'scripts/check-tv-web.cjs', ROOT / 'package.json', ROOT / 'package-lock.json']
    stamps = []
    for path in paths:
        for item in sorted(path.rglob('*')) if path.is_dir() else [path]:
            if item.is_file():
                entry = item.stat()
                stamps.append((str(item), entry.st_mtime_ns, entry.st_size))
    return digest(json.dumps(stamps).encode())


def stop_hosted(process):
    if process and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


def ui(args):
    if args.stage_only:
        if args.watch or args.device: raise ValueError('--stage-only cannot connect or watch')
        stage_ui(args.output)
        print('Compiled isolated UI: ' + str(args.output) + '; no TV connection or acceptance.')
        return
    require_device_consent(args.owner_present)
    command = hosted_command(args.output.absolute(), args.device)
    revision = source_revision()
    stage_ui(args.output)
    process = subprocess.Popen(command, cwd=ROOT)
    print('Hosted UI simulation; native TV services disabled. Stop with Ctrl+C.', flush=True)
    try:
        if not args.watch:
            if process.wait() != 0: raise ValueError('webOS hosted launch failed')
            return
        while True:
            time.sleep(0.5)
            if process.poll() is not None:
                raise ValueError('Hosted CLI exited; verify TV connection before restarting')
            current = source_revision()
            if current == revision: continue
            # Debounce editor writes. Failed compilation keeps the running generation.
            time.sleep(0.3)
            revision = source_revision()
            try:
                compiled = runpy.run_path(str(ROOT / 'scripts/tv_web_build.py'))['compile_web'](ui_files())
            except (RuntimeError, ValueError, OSError) as error:
                print('Rebuild refused; previous UI retained: ' + str(error), file=sys.stderr)
                continue
            stop_hosted(process)
            stage_ui(args.output, compiler=lambda _: compiled)
            process = subprocess.Popen(command, cwd=ROOT)
            print('Compiled UI reloaded; TV functions remain simulated.', flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        stop_hosted(process)


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + REPO + '/' + path]))


def dispatch(workflow, branch, source, inputs):
    query = 'actions/workflows/' + workflow + '/runs?event=workflow_dispatch&per_page=100'
    before = {run['id'] for run in api(query)['workflow_runs']}
    subprocess.run(['gh', 'workflow', 'run', workflow, '--repo', REPO, '--ref', branch,
                    *[part for key, value in inputs.items() for part in ('-f', key + '=' + str(value))]], check=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        matches = [r for r in api(query)['workflow_runs'] if r['id'] not in before
                   and r.get('head_branch') == branch and r.get('head_sha') == source]
        if len(matches) > 1: raise ValueError('Ambiguous dispatch; resume with the exact --run-id or --sign-run-id')
        if matches: return matches[0]['id']
        time.sleep(3)
    raise ValueError('Dispatch not observed; inspect Actions and resume with exact run ID')


def wait_run(run_id, workflow, branch, source):
    subprocess.run(['gh', 'run', 'watch', str(run_id), '--repo', REPO, '--exit-status'], check=True)
    run = api('actions/runs/' + str(run_id))
    if (run.get('path') != '.github/workflows/' + workflow or run.get('head_branch') != branch
            or run.get('head_sha') != source or run.get('event') != 'workflow_dispatch'
            or run.get('head_repository', {}).get('full_name') != REPO
            or (run.get('status'), run.get('conclusion')) != ('completed', 'success')
            or type(run.get('run_attempt')) is not int or run['run_attempt'] <= 0):
        raise ValueError('Exact successful dispatched workflow required')
    return run


def signed_artifact(run, metadata):
    artifacts = api('actions/runs/' + str(run['id']) + '/artifacts?per_page=100')['artifacts']
    expected = 'signed-root-candidate-' + str(metadata['run_id']) + '-' + str(metadata['attempt'])
    matches = [a for a in artifacts if a.get('name') == expected]
    if len(matches) != 1: raise ValueError('Exact signed candidate artifact required')
    artifact = matches[0]
    if (artifact.get('expired') is not False or type(artifact.get('id')) is not int or artifact['id'] <= 0
            or type(artifact.get('size_in_bytes')) is not int or not 0 < artifact['size_in_bytes'] <= MAX_ARCHIVE
            or not isinstance(artifact.get('digest'), str)
            or not re.fullmatch(r'sha256:[a-f0-9]{64}', artifact['digest'])
            or artifact.get('workflow_run', {}).get('id') != run['id']
            or artifact['workflow_run'].get('head_sha') != run['head_sha']):
        raise ValueError('Signed artifact provenance missing')
    return artifact


def download_signed(run, metadata, output):
    artifact = signed_artifact(run, metadata)
    with tempfile.TemporaryDirectory(prefix='tv-signed-') as tmp:
        archive = Path(tmp) / 'signed.zip'
        with archive.open('wb') as stream:
            subprocess.run(['gh', 'api', 'repos/' + REPO + '/actions/artifacts/' + str(artifact['id']) + '/zip'], stdout=stream, check=True)
        if archive.stat().st_size != artifact['size_in_bytes'] or digest(read_file(archive, MAX_ARCHIVE)) != artifact['digest'][7:]:
            raise ValueError('Signed artifact digest mismatch')
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist()
            names = [entry.filename for entry in entries]
            if (len(names) != 6 or len(set(names)) != 6 or any(Path(n).name != n or '\\' in n for n in names)
                    or not {'manifest.json', 'PROVENANCE.json', 'system-update-root.json'} <= set(names)
                    or any(e.is_dir() or stat.S_ISLNK(e.external_attr >> 16) or e.file_size > 64 * 1024 * 1024 for e in entries)):
                raise ValueError('Unsafe signed artifact layout')
            output.mkdir(parents=True, exist_ok=False, mode=0o700)
            for entry in entries: (output / entry.filename).write_bytes(zipped.read(entry))
    return {'run_id': run['id'], 'attempt': run['run_attempt'], 'source': run['head_sha'], 'artifact': artifact}


def verify_bundle(folder, metadata):
    folder = Path(folder)
    if json.loads(read_file(folder / 'PROVENANCE.json', 65536)) != metadata:
        raise ValueError('Signed provenance differs from selected build')
    raw = read_file(folder / 'system-update-root.json', 131072)
    program = "const fs=require('fs'),p=require('./system-updater/policy');process.stdout.write(JSON.stringify(p.verify(JSON.parse(fs.readFileSync(0,'utf8')),fs.readFileSync('updater-service/release-public.pem'))));"
    manifest = json.loads(subprocess.check_output(['node', '-e', program], input=raw, cwd=ROOT))
    if manifest != json.loads(read_file(folder / 'manifest.json', 65536)):
        raise ValueError('Signed manifest differs from build')
    if (metadata.get('direct_tv') is not True or metadata.get('preliminary') is not True
            or metadata.get('workflow') != '.github/workflows/tv-candidate.yml'
            or metadata.get('public_key_sha256') != digest(read_file(ROOT / 'updater-service/release-public.pem'))
            or manifest.get('release') != metadata.get('release') or manifest.get('edition') != 'root'):
        raise ValueError('Direct preliminary provenance and trusted key required')
    helper = runpy.run_path(str(ROOT / 'scripts/root-candidate-feeds.py'))
    if manifest.get('notes') != helper['notes_for'](metadata): raise ValueError('Signed source binding mismatch')
    package_files = {}
    for component in manifest['components']:
        name = component['url'].rsplit('/', 1)[-1]
        if Path(name).name != name: raise ValueError('Unsafe component filename')
        expected_version = metadata['versions']['updater' if component['name'] == 'root-updater' else 'root']
        if component['version'] != expected_version: raise ValueError('Candidate component version mismatch')
        package = read_file(folder / name)
        if len(package) != component['size'] or digest(package) != component['sha256']:
            raise ValueError('Candidate package digest mismatch')
        package_files[name] = component['sha256']
    if package_files != metadata.get('files') or {p.name for p in folder.iterdir()} != set(package_files) | {'PROVENANCE.json', 'manifest.json', 'system-update-root.json'}:
        raise ValueError('Candidate package inventory mismatch')
    return manifest


def candidate(args):
    if not re.fullmatch('[a-f0-9]{40}', args.source_sha or ''): raise ValueError('Exact --source-sha required')
    if not re.fullmatch(r'v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})', args.tag or ''):
        raise ValueError('Numeric unpublished --tag required')
    if any(value is not None and value <= 0 for value in (args.run_id, args.sign_run_id)):
        raise ValueError('Positive workflow run IDs required')
    if args.branch.startswith(('-', 'refs/')) or subprocess.run(['git', 'check-ref-format', 'refs/heads/' + args.branch], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise ValueError('Named candidate branch required')
    if args.output.exists(): raise ValueError('Candidate output must be a new private directory')
    build_id = args.run_id or dispatch('tv-candidate.yml', args.branch, args.source_sha, {'source_sha': args.source_sha})
    wait_run(build_id, 'tv-candidate.yml', args.branch, args.source_sha)
    helper = runpy.run_path(str(ROOT / 'scripts/root-candidate-feeds.py'))
    metadata = helper['inspect_build'](build_id, args.tag, preliminary=True, direct_tv=True, source_sha=args.source_sha, branch=args.branch)
    print('Verified direct build ' + str(build_id) + ':' + str(metadata['attempt']) + '; requesting protected QA signing.', flush=True)
    signing_head = (api('actions/runs/' + str(args.sign_run_id))['head_sha'] if args.sign_run_id
                    else api('git/ref/heads/release/next')['object']['sha'])
    signing_id = args.sign_run_id or dispatch('publish-release.yml', 'release/next', signing_head, {
        'tag': args.tag, 'publish': 'false', 'preliminary_root_qa': 'true', 'direct_tv_qa': 'true',
        'candidate_build_run': build_id, 'candidate_source_sha': args.source_sha, 'candidate_branch': args.branch})
    run = wait_run(signing_id, 'publish-release.yml', 'release/next', signing_head)
    delivery = download_signed(run, metadata, args.output)
    try:
        signed_metadata = json.loads(read_file(args.output / 'PROVENANCE.json', 65536))
        if {k:v for k,v in signed_metadata.items() if k != 'files'} != metadata:
            raise ValueError('Signed build provenance differs from selected build')
        manifest = verify_bundle(args.output, signed_metadata)
        helper['recheck'](metadata)
        current = api('actions/runs/' + str(signing_id))
        if (current.get('run_attempt') != run['run_attempt'] or current.get('conclusion') != 'success'
                or signed_artifact(current, metadata) != delivery['artifact']):
            raise ValueError('Signing attempt changed')
    except BaseException:
        # Preserve downloaded evidence for diagnosis, but never mark it verified.
        raise
    (args.output / 'DELIVERY.json').write_text(json.dumps(delivery, indent=2) + '\n')
    print('Verified signed preliminary Root QA: ' + manifest['release'] + ' at ' + str(args.output) + '; no TV connection or final release acceptance.')


def acceptance_request(folder, manifest, action, profile=None):
    if action not in ('preflight', 'install') or action == 'install' and not isinstance(profile, dict):
        raise ValueError('Install requires the actual current UI-captured profile')
    folder = Path(folder)
    raw = read_file(folder / 'system-update-root.json', 131072)
    request = {'action': action, 'release': manifest['release'], 'envelopeSha256': digest(raw),
               'envelope': base64.b64encode(raw).decode(),
               'packages': {c['name']: base64.b64encode(read_file(folder / c['url'].rsplit('/', 1)[-1])).decode() for c in manifest['components']}}
    if action == 'install': request['profile'] = profile
    return request


def select_installed_python(remote, profile, store):
    from cytv.operations import Installer, SYSTEM_UPDATER_STATE
    return Installer(remote, store, profile, ROOT, {})._python(SYSTEM_UPDATER_STATE)


def admit(remote, profile, request, store):
    from cytv.operations import Installer
    python = select_installed_python(remote, profile, store)
    # Controller text is a shell-quoted -c argument; sensitive request stays stdin.
    # No remote executable upload, mutable source imports or candidate code runs.
    command = Installer._python_command([python, '-I', '-B', '-c', read_file(ROOT / 'scripts/root-candidate-acceptance.py').decode()])
    reply = json.loads(remote.run(command, data=json.dumps(request, allow_nan=False).encode(), timeout=600))
    if reply.get('returnValue') is not True or not isinstance(reply.get('result'), dict):
        raise ValueError('Device admission refused; preserve recovery state and inspect cytv status')
    return reply['result']


def device(args):
    require_device_consent(args.owner_present)
    from cytv.state import Store, target
    from cytv.transport import SSH
    folder = args.bundle
    # DELIVERY lives outside the strict signing bundle during verification.
    delivery = json.loads(read_file(folder / 'DELIVERY.json', 65536))
    metadata = json.loads(read_file(folder / 'PROVENANCE.json', 65536))
    helper = runpy.run_path(str(ROOT / 'scripts/root-candidate-feeds.py'))
    helper['recheck']({k:v for k,v in metadata.items() if k != 'files'})
    signing = api('actions/runs/' + str(delivery['run_id']))
    if (signing.get('run_attempt') != delivery['attempt'] or signing.get('head_sha') != delivery['source']
            or signing.get('path') != '.github/workflows/publish-release.yml'
            or signing.get('head_branch') != 'release/next' or signing.get('event') != 'workflow_dispatch'
            or signing.get('head_repository', {}).get('full_name') != REPO
            or signed_artifact(signing, metadata) != delivery.get('artifact')
            or (signing.get('status'), signing.get('conclusion')) != ('completed', 'success')):
        raise ValueError('Signing run changed')
    with tempfile.TemporaryDirectory(prefix='tv-admission-') as tmp:
        copied = Path(tmp) / 'bundle'; copied.mkdir()
        for item in folder.iterdir():
            if item.name != 'DELIVERY.json': (copied / item.name).write_bytes(read_file(item))
        manifest = verify_bundle(copied, metadata)
        store = Store(args.data_dir)
        matches = [p for p in store.profiles() if p['edition'] == 'root' and p['host'] == target(args.host, 'root')['host']]
        if len(matches) != 1: raise ValueError('Exactly one existing trusted Root connection profile required')
        connection = matches[0]
        profile = None
        if args.action == 'install':
            if not args.profile: raise ValueError('--profile from current RootProfile.capture({system:true}) required')
            if args.profile.stat().st_mode & 0o077: raise ValueError('UI profile must have private permissions (chmod 600)')
            profile = json.loads(read_file(args.profile, 16 * 1024 * 1024))
        def refuse_secret(_): raise ValueError('Saved identity or existing SSH agent authentication required')
        with store.lock(connection):
            if store.pending(connection): raise ValueError('Unresolved installer operation; inspect cytv status first')
            remote = SSH.connect(connection, store.device_dir(connection), refuse_secret, lambda *_: False)
            try:
                preflight = admit(remote, connection, acceptance_request(copied, manifest, 'preflight'), store)
                if args.action == 'preflight': print(json.dumps(preflight)); return
                result = admit(remote, connection, acceptance_request(copied, manifest, 'install', profile), store)
                print(json.dumps(result))
                print('Install admitted to the original worker. Observe ordinary System Updater status, real UI health and rollback; completion is unverified.')
            finally:
                remote.close()


def main():
    os.umask(0o077)
    if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='command', required=True)
    local = actions.add_parser('ui', help='compiled UI simulation; no production TV service access')
    local.add_argument('--output', type=Path, default=ROOT / 'build/tv-dev-ui')
    local.add_argument('--stage-only', action='store_true', help='offline compile only; no CLI/device connection')
    local.add_argument('--device', help='existing named ares device')
    local.add_argument('--watch', action='store_true', help='recompile changed sources; reload only complete builds')
    local.add_argument('--owner-present', action='store_true', help='owner authorized and present for hosted TV launch')
    qa = actions.add_parser('candidate', help='dispatch, wait, download and verify protected signed preliminary Root QA')
    qa.add_argument('--branch', required=True)
    qa.add_argument('--source-sha', required=True)
    qa.add_argument('--tag', required=True)
    qa.add_argument('--run-id', type=int, help='resume exact direct build instead of dispatching')
    qa.add_argument('--sign-run-id', type=int, help='resume exact protected signing run')
    qa.add_argument('--output', type=Path, required=True, help='new private artifact directory')
    for action in ('preflight', 'install'):
        remote = actions.add_parser(action, help='explicit TV ' + action + ' through existing trusted admission')
        remote.set_defaults(action=action)
        remote.add_argument('--bundle', type=Path, required=True)
        remote.add_argument('--host', required=True, help='host in an existing trusted Root cytv profile')
        remote.add_argument('--data-dir', type=Path, help='existing cytv profile store; defaults to normal cytv location')
        remote.add_argument('--owner-present', action='store_true', help='owner authorized and present for this action')
        if action == 'install': remote.add_argument('--profile', type=Path, required=True, help='private JSON from current running Root UI, never a fabricated/historical profile')
    args = parser.parse_args()
    try:
        if args.command == 'ui': ui(args)
        elif args.command == 'candidate': candidate(args)
        else: device(args)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, 'TV development command refused: ' + str(error) + '\n')


if __name__ == '__main__': main()
