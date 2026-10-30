#!/usr/bin/env python3
"""Plan releases and assemble verified public CI artifacts, without signing keys."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import plistlib
import re
import runpy
import shutil
import subprocess
import struct
import sys
import tarfile
import tempfile
import zipfile

INPUTS = runpy.run_path(str(Path(__file__).with_name('release-inputs.py')))

ROOT = Path(os.environ.get('RELEASE_SOURCE_ROOT', Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(ROOT))
from cytv import package


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}', value):
        raise ValueError('Invalid release/component version')
    return tuple(map(int, value.split('.')))


def plan_release(versions, commit, releases, validate_only=False):
    for key in ('release', 'cytv', 'home', 'helper', 'root', 'updater'): version(versions[key])
    if not re.fullmatch('[a-f0-9]{40}', commit): raise ValueError('Invalid source commit')
    tag = 'v' + versions['release']
    existing = next((r for r in releases if r['tag_name'] == tag), None)
    if existing and not existing['draft']:
        return validate_only
    if existing and existing['target_commitish'] != commit:
        raise ValueError('Release draft targets a different commit')
    for release in releases:
        if not release['draft'] and not release['prerelease'] and re.fullmatch(r'v\d+\.\d+\.\d+', release['tag_name']) and version(release['tag_name'][1:]) > version(versions['release']):
            raise ValueError('A newer stable release exists')
    return True


def validate_build_run(run, commit, root=ROOT):
    if (not re.fullmatch('[a-f0-9]{40}', commit) or run['conclusion'] != 'success' or run['status'] != 'completed' or
        run['head_branch'] not in ('main', 'release/next') or
        run['event'] not in ('push', 'workflow_dispatch') or
        run['path'] != '.github/workflows/cytv.yml' or
        run['head_repository']['full_name'] != 'Razdva122/clean-your-tv-lg-webos'):
        raise ValueError('Release requires successful trusted main builds from the exact source commit')
    if run['head_branch'] == 'main':
        if run['head_sha'] != commit:
            raise ValueError('Release requires successful trusted main builds from the exact source commit')
        return  # Historical builds remain usable for manual validation/retries.
    def revision(ref):
        return subprocess.check_output(['git', 'rev-parse', ref], cwd=root, text=True).strip()
    try:
        candidate = revision(commit + '^2')
        pin = INPUTS['pin_at'](candidate, root)
        if pin:
            if run.get('id') != pin['run_id'] or run['head_sha'] != pin['source'] or run.get('run_attempt') != pin['attempt']:
                raise ValueError('Candidate build does not match the committed build pin')
            INPUTS['verify_inputs'](pin['source'], candidate, root)
        elif candidate != run['head_sha']:
            raise ValueError('Candidate must be the exact second parent of the release merge')
        if revision(commit + '^{tree}') != revision(candidate + '^{tree}'):
            raise ValueError('Release merge tree differs from the built candidate tree')
    except subprocess.CalledProcessError as error:
        raise ValueError('Release source must be a merge of the built candidate') from error


def github(path, *, pages=False):
    args = ['gh', 'api', 'repos/Razdva122/clean-your-tv-lg-webos/' + path]
    if pages:
        args += ['--paginate', '--slurp']
    result = json.loads(subprocess.check_output(args))
    return [item for page in result for item in (page['jobs'] if isinstance(page, dict) else page)] if pages else result


def selected_homebrew_approval(root=ROOT):
    path=root/'homebrew/release.json'
    if not path.exists(): return None
    approval=json.loads(path.read_text())
    tag='v'+json.loads((root/'release-versions.json').read_text())['release']
    if approval.get('release') != tag: return None
    return approval


def validate_homebrew_job(jobs, accepted):
    if accepted and not any(job['name']=='homebrew' and job['conclusion']=='success' for job in jobs):
        raise ValueError('Accepted Homebrew installer requires a successful exact candidate build')


def resolve_build_source(commit, build_run=None):
    if build_run:
        run = github('actions/runs/' + str(build_run))
    else:
        candidate = subprocess.check_output(['git', 'rev-parse', commit + '^2'], cwd=ROOT, text=True).strip()
        pin = INPUTS['pin_at'](candidate, ROOT)
        if pin:
            return resolve_build_source(commit, pin['run_id'])
        runs = github('actions/workflows/cytv.yml/runs?branch=release%2Fnext&status=success&head_sha=' + candidate + '&per_page=100')['workflow_runs']
        if not runs:
            raise ValueError('No successful build exists for the exact release candidate')
        run = max(runs, key=lambda item: item['id'])
    validate_build_run(run, commit)
    flow = runpy.run_path(str(Path(__file__).with_name('release-flow.py')))
    jobs=github('actions/runs/' + str(run['id']) + '/jobs?filter=latest&per_page=100', pages=True)
    flow['validate_build_jobs'](jobs)
    validate_homebrew_job(jobs, selected_homebrew_approval() is not None)
    return run


def verify_embedded(data, versions):
    manifest = json.loads(data('payload.json'))
    if not manifest['files']: raise ValueError('Empty installer payload')
    for name, digest in manifest['files'].items():
        package.safe_name(name)
        if hashlib.sha256(data(name)).hexdigest() != digest:
            raise ValueError('Embedded payload hash mismatch: ' + name)
    if manifest['home_version'] != versions['home'] or manifest['helper_version'] != versions['helper'] or json.loads(data('root/release.json'))['version'] != versions['root']:
        raise ValueError('Embedded payload version mismatch')
    root = json.loads(data('root/bundle.json'))['package']
    for filename, app, key in [('launcher.ipk', 'com.gathin.tvhome', 'home'), ('helper.ipk', 'com.local.nativehome', 'helper'), ('root/' + root, package.ROOT_APP, 'root')]:
        info = json.loads(package.data_files(data(filename))['usr/palm/applications/' + app + '/appinfo.json'])
        if info['id'] != app or info['version'] != versions[key]:
            raise ValueError('Embedded application version mismatch: ' + app)
    return len(manifest['files'])


def open_deb_tar(parts, prefix):
    names = [n for n in parts if n.startswith(prefix + '.tar.')]
    if len(names) != 1: raise ValueError('Invalid Debian archive')
    name = names[0]
    raw = parts[name]
    # Python 3.12 has no stdlib zstd reader; Ubuntu's dpkg uses zstd by default.
    if name.endswith('.zst'):
        raw = subprocess.check_output(['zstd', '-q', '-d', '-c'], input=raw)
    return tarfile.open(fileobj=io.BytesIO(raw))


def verify_windows_desktop(path, versions):
    """Reject CLI executables, wrong versions and mismatched embedded TV files."""
    with zipfile.ZipFile(path) as archive:
        metadata = json.loads(archive.read('cytv-desktop/version.json'))
        if metadata != {'cytv': versions['cytv'], 'platform': 'windows-x64', 'entrypoint': 'cytv-desktop.exe'}:
            raise ValueError('Windows desktop version or entrypoint mismatch')
        executable = archive.read('cytv-desktop/cytv-desktop.exe')
        if len(executable) < 64 or executable[:2] != b'MZ':
            raise ValueError('Invalid Windows desktop executable')
        pe = struct.unpack_from('<I', executable, 60)[0]
        if (pe + 94 > len(executable) or executable[pe:pe+4] != b'PE\0\0'
                or struct.unpack_from('<H', executable, pe + 4)[0] != 0x8664
                or struct.unpack_from('<H', executable, pe + 24)[0] != 0x20b
                or struct.unpack_from('<H', executable, pe + 92)[0] != 2):
            raise ValueError('Windows desktop executable must be an x64 GUI application')
        return verify_embedded(lambda name: archive.read('cytv-desktop/_internal/payload/' + name), versions)


def verify_android_package(path, report, versions, commit):
    """Require the APK checked by the trusted build job, including its signer."""
    metadata = json.loads(Path(report).read_text())
    expected = {'schema': 1, 'source_commit': commit, 'versions': versions,
                'android_version_name': versions['android'], 'android_version_code': versions['android_version_code'],
                'package': 'com.cleanyourtv.android', 'abi': 'arm64-v8a', 'min_sdk': 24, 'target_sdk': 35,
                'debuggable': False,
                'signer_sha256': (ROOT / 'android/preview-certificate.sha256').read_text().strip(),
                'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    if metadata != expected or metadata.get('debuggable') is not False:
        raise ValueError('Android APK provenance, version, signer or hash mismatch')
    with zipfile.ZipFile(path) as archive:
        if json.loads(archive.read('assets/cytv-build.json')) != {'schema': 1, 'source_commit': commit, 'versions': versions}:
            raise ValueError('Android embedded source provenance mismatch')
        return verify_embedded(lambda name: archive.read('assets/payload/' + name), versions)


def assemble_homebrew(artifacts, output, approval):
    """Unaccepted CI artifacts never enter the public release asset directory."""
    if approval is None: return None
    gate=runpy.run_path(str(ROOT / 'scripts/homebrew-manifest.py'))
    folder=artifacts/'homebrew-candidate'
    metadata=(folder/gate['MANIFEST_NAME']).read_bytes()
    value=json.loads(metadata)
    name=value['ipkUrl'].rsplit('/',1)[1]
    package.safe_name(name)
    raw=(folder/name).read_bytes()
    gate['verify_accepted'](raw,metadata,approval)
    (output/name).write_bytes(raw)
    (output/gate['MANIFEST_NAME']).write_bytes(metadata)
    return approval


def assemble(artifacts, output, versions, commit, build_commit=None):
    from PyInstaller.archive.readers import CArchiveReader
    builder = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))
    output.mkdir(parents=True, exist_ok=False)
    paths = {
        'cytv-windows-x64.exe': 'cytv-windows-x64/cytv.exe',
        'cytv-windows-x64-desktop.zip': 'cytv-windows-x64-desktop/cytv-windows-x64-desktop.zip',
        'cytv-android-arm64.apk': 'cytv-android-arm64/cytv-android-arm64.apk',
        'cytv-android-arm64.build.json': 'cytv-android-arm64/cytv-android-arm64.build.json',
        'cytv-linux-x64': 'cytv-linux-x64/cytv',
        'cytv-linux-x64.deb': 'cytv-linux-x64-desktop/cytv-linux-x64.deb',
        'cytv-macos-arm64': 'cytv-macos-arm64/cytv',
        'cytv-macos-arm64.zip': 'cytv-macos-arm64-desktop/cytv-macos-arm64.zip',
        'cytv-macos-x64': 'cytv-macos-x64/cytv',
        'cytv-macos-x64.zip': 'cytv-macos-x64-desktop/cytv-macos-x64.zip'}
    for name, source in paths.items(): shutil.copyfile(artifacts / source, output / name)
    checks = []
    def checked(data, name):
        count = verify_embedded(data, versions)
        checks.append({'asset': name, 'payload_files_verified': count})
        print('Verified', name, ':', count, 'payload hashes and component versions')
    arm_payload = None
    for name in ('cytv-windows-x64.exe', 'cytv-linux-x64', 'cytv-macos-arm64', 'cytv-macos-x64'):
        archive = CArchiveReader(str(output / name))
        names = {n.replace('\\', '/'): n for n in archive.toc}
        data = lambda name: archive.extract(names['payload/' + name])
        checked(data, name)
        if name == 'cytv-macos-arm64':
            arm_payload = {n[len('payload/'):]: archive.extract(original) for n, original in names.items() if n.startswith('payload/')}
    for name in ('cytv-macos-arm64.zip', 'cytv-macos-x64.zip'):
        with zipfile.ZipFile(output / name) as archive:
            if plistlib.loads(archive.read('cytv.app/Contents/Info.plist'))['CFBundleShortVersionString'] != versions['cytv']:
                raise ValueError('Desktop installer version mismatch')
            checked(lambda n: archive.read('cytv.app/Contents/Resources/payload/' + n), name)
    windows_gui = 'cytv-windows-x64-desktop.zip'
    count = verify_windows_desktop(output / windows_gui, versions)
    checks.append({'asset': windows_gui, 'payload_files_verified': count})
    print('Verified', windows_gui, ':', count, 'payload hashes and component versions; x64 GUI subsystem')
    android = 'cytv-android-arm64.apk'
    count = verify_android_package(output / android, output / 'cytv-android-arm64.build.json', versions, build_commit or commit)
    checks.append({'asset': android, 'payload_files_verified': count})
    print('Verified', android, ':', count, 'payload hashes and component versions; signed ARM64 preview')
    parts = package.read_ar((output / 'cytv-linux-x64.deb').read_bytes())
    with open_deb_tar(parts, 'control') as archive:
        control = archive.extractfile(next(m for m in archive if m.name in ('control', './control'))).read().decode()
        if '\nVersion: ' + versions['cytv'] + '\n' not in control: raise ValueError('Debian version mismatch')
    with open_deb_tar(parts, 'data') as archive:
        prefix = next(m.name[:-len('payload.json')] for m in archive if m.name.endswith('/payload/payload.json'))
        checked(lambda n: archive.extractfile(prefix + n).read(), 'cytv-linux-x64.deb')
    with tempfile.TemporaryDirectory(prefix='cytv-bundles-') as tmp:
        tmp = Path(tmp); payload = tmp / 'payload'; payload.mkdir()
        for name, raw in arm_payload.items():
            path = payload / package.safe_name(name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        package.verify_payload(payload)
        builder['verify_release_versions'](payload, versions)
        updater = (payload / 'updater.ipk').read_bytes()
        system_builder = runpy.run_path(str(ROOT / 'system-updater/build.py'))
        note = 'docs/RELEASE-' + versions['release'] + '.md'
        system_manifests=system_builder['prepare_release'](payload, output, 'v'+versions['release'], (ROOT / note).read_text()[:3800])
        system_files={c['url'].rsplit('/',1)[1] for manifest in system_manifests.values() for c in manifest['components']}
        runpy.run_path(str(ROOT/'scripts/prepare-release.py'))['verify_system_assets'](
            system_manifests,{'tag':'v'+versions['release'],'versions':versions},
            {name:(output/name).read_bytes() for name in system_files})
        with zipfile.ZipFile(output / ('clean-your-tv-no-root-' + versions['home'] + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(payload / 'launcher.ipk', 'com.gathin.tvhome_' + versions['home'] + '_all.ipk')
            archive.write(payload / 'helper.ipk', 'com.local.nativehome_' + versions['helper'] + '_arm.ipk')
            archive.writestr('com.cleanyourtv.updater_' + versions['updater'] + '_all.ipk', updater)
            for name in ('docs/MANUAL_INSTALL.md', 'docs/INSTALL.md', 'docs/CLI.md', note, 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'scripts/update-permissions.cjs', 'scripts/lib/update-permissions.cjs', 'updater-service/permissions.js'):
                archive.write(ROOT / name, name)
        staging = tmp / ('clean-your-tv-root-' + versions['root']); staging.mkdir()
        source = subprocess.check_output(['git', 'archive', commit], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(source)) as archive: archive.extractall(staging, filter='data')
        (staging / 'build').mkdir()
        shutil.copytree(payload / 'root', staging / 'build/root-candidate')
        shutil.copytree(payload / 'root-updater', staging / 'build/root-updater')
        shutil.copytree(payload / 'system-updater', staging / 'build/system-updater')
        with zipfile.ZipFile(output / ('clean-your-tv-no-root-' + versions['home'] + '.zip'),'a',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((payload/'system-updater').rglob('*')):
                if path.is_file():archive.write(path,'system-updater/'+path.relative_to(payload/'system-updater').as_posix())
        with tarfile.open(output / (staging.name + '.tar.gz'), 'w:gz') as archive: archive.add(staging, arcname=staging.name)
    shutil.copyfile(ROOT / note, output / 'RELEASE-NOTES.md')
    build_run = os.environ.get('SOURCE_BUILD_RUN', os.environ.get('GITHUB_RUN_ID', ''))
    info = {'tag': 'v' + versions['release'], 'source_commit': commit, 'build_source_commit': build_commit or commit, 'versions': versions,
            'release_date': datetime.now(timezone.utc).date().isoformat(),
            'ci_build_run': {'id': build_run, 'url': os.environ.get('GITHUB_SERVER_URL', 'https://github.com') + '/' + os.environ.get('GITHUB_REPOSITORY', 'Razdva122/clean-your-tv-lg-webos') + '/actions/runs/' + build_run, 'conclusion': 'success'},
            'ci_test_run': {'id': build_run, 'conclusion': 'success', 'workflow': 'cytv.yml / validation'},
            'embedded_payload_verification': checks,
            'hardware_evidence': json.loads((ROOT / 'release-plan.json').read_text()).get('acceptance', 'No physical acceptance recorded.'),
            'acceptance_build': json.loads((ROOT / 'release-plan.json').read_text()).get('acceptance_build')}
    approval = assemble_homebrew(artifacts, output, selected_homebrew_approval())
    if approval is not None: info['homebrew'] = approval
    (output / 'BUILD-INFO.json').write_text(json.dumps(info, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in sorted(output.iterdir())))
    print('Prepared', len(list(output.iterdir())), 'unsigned release assets from', commit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--build-source', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--build-run', type=int)
    parser.add_argument('--source-commit', help='Exact main merge commit to publish')
    parser.add_argument('--build-commit', help='Verified candidate commit that produced the artifacts')
    parser.add_argument('--require-unpublished', action='store_true')
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.build_source:
        if not args.source_commit: parser.error('--source-commit is required')
        run = resolve_build_source(args.source_commit, args.build_run)
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('commit=' + args.source_commit + '\nbuild_commit=' + run['head_sha'] + '\nbuild_run=' + str(run['id']) + '\n')
        return
    versions = json.loads((ROOT / 'release-versions.json').read_text())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if args.plan:
        if not args.build_run: parser.error('--build-run is required for planning')
        run = json.loads(subprocess.check_output(['gh', 'api', 'repos/Razdva122/clean-your-tv-lg-webos/actions/runs/' + str(args.build_run)]))
        validate_build_run(run, commit)
        raw = subprocess.check_output(['gh', 'api', '--paginate', '--slurp', 'repos/Razdva122/clean-your-tv-lg-webos/releases?per_page=100'])
        releases = [r for page in json.loads(raw) for r in page]
        planned = plan_release(versions, commit, releases, args.validate_only)
        if args.require_unpublished and not planned: raise ValueError('Release is already published; refusing to overwrite assets')
        if planned and not args.validate_only:
            tag = 'v' + versions['release']
            refs = json.loads(subprocess.check_output(['gh', 'api', 'repos/Razdva122/clean-your-tv-lg-webos/git/matching-refs/tags/' + tag]))
            if any(r['ref'] == 'refs/tags/' + tag for r in refs):
                tagged = json.loads(subprocess.check_output(['gh', 'api', 'repos/Razdva122/clean-your-tv-lg-webos/commits/' + tag]))
                if tagged['sha'] != commit: raise ValueError('Existing release tag targets a different commit')
        note = ROOT / ('docs/RELEASE-' + versions['release'] + '.md')
        if planned and not note.is_file(): raise ValueError('Release notes file is required')
        result = 'release=' + str(planned).lower() + '\ntag=v' + versions['release'] + '\ncommit=' + commit + '\nbuild_commit=' + run['head_sha'] + '\nbuild_run=' + str(args.build_run) + '\n'
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output: output.write(result)
        print(result, end='')
    else:
        if not args.artifacts or not args.output: parser.error('--artifacts and --output are required')
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(): raise ValueError('Release source checkout must be clean')
        if args.build_commit and args.build_commit != commit:
            # Recheck the binding immediately before consuming candidate artifacts.
            run = resolve_build_source(commit, int(os.environ['SOURCE_BUILD_RUN']))
            if run['head_sha'] != args.build_commit:
                raise ValueError('Build source changed before assembly')
        assemble(args.artifacts, args.output, versions, commit, args.build_commit)


if __name__ == '__main__':
    main()
