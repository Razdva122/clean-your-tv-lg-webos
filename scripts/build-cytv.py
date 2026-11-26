#!/usr/bin/env python3
"""Build public TV payload and a native single-file cytv executable. Never contacts a TV."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cytv import package
from cytv.tv_sources import stage_sources
from scripts.tv_web_build import build_lock, compile_web
from scripts.helper_build import compile_helper
from scripts.home_assets import THEME_FILES
from scripts.no_root_assets import renewal_service_assets, updater_sources


def tracked_files(prefix):
    result = subprocess.run(['git', 'ls-files', '--', prefix], cwd=ROOT, capture_output=True, check=True, text=True)
    files = {}
    # Explicit public runtime dependencies may be new files in a source checkout.
    # Do not include arbitrary untracked files or local profile data.
    required = {'native/app': ['native/app/helper-entry.js', 'native/app/stop-generation.h', 'native/app/state-permissions.js', 'native/app/contract-events.js', 'native/app/home-control.js', 'native/app/websocket.js'],
                'renewal-service': ['renewal-service/home-control.js', 'renewal-service/diagnostics.js', 'renewal-service/ca-bundle.crt', 'renewal-service/ca-LICENSE.txt'],
                'launcher': ['launcher/viewport.js', 'launcher/system-updates.js', 'launcher/helper-control.js', 'launcher/release-notes.js', 'launcher/app-library.js', 'launcher/input-sources.js', 'launcher/input-preview.js','launcher/i18n.js', 'launcher/catalogs.js', 'launcher/i18n.css', 'launcher/theme-defaults.css', 'launcher/theme-policy.js', 'launcher/theme-runtime.js', 'launcher/home-layout.js', 'launcher/layout-panel.js', 'launcher/settings-categories.js', 'launcher/layout-panel.css', 'launcher/settings-panel.css',
                             'launcher/fonts/outfit-300.ttf', 'launcher/fonts/outfit-400.ttf',
                             'launcher/fonts/outfit-500.ttf', 'launcher/fonts/outfit-700.ttf',
                             'launcher/fonts/NotoSans.ttf', 'launcher/fonts/NotoSans-OFL.txt',
                             'launcher/fonts/NotoSansDevanagari.ttf', 'launcher/fonts/NotoSansDevanagari-OFL.txt',
                             'launcher/fonts/NotoSansKR.ttf', 'launcher/fonts/NotoSansKR-OFL.txt',
                             'launcher/fonts/NotoSansSC.ttf', 'launcher/fonts/NotoSansSC-OFL.txt',
                             'launcher/fonts/NotoSansTC.ttf', 'launcher/fonts/NotoSansTC-OFL.txt'],
                'native/service': ['native/service/app-inventory.js']}
    if prefix == 'launcher':
        required[prefix] += ['launcher/' + name for name in THEME_FILES]
        required[prefix] += ['launcher/screensaver-' + name for name in ('idle.js', 'personal.js', 'settings.js', 'settings.css')]
    if prefix == 'native/app':
        required[prefix] += ['native/app/screensaver-' + name + '.js' for name in ('controller', 'lg', 'owner')]
    for name in sorted(set(result.stdout.splitlines()) | set(required.get(prefix, []))):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or indirect public source: ' + name)
        files[str(Path(name).relative_to(prefix)).replace('\\', '/')] = path.read_bytes()
    return files


def helper_sources():
    app = {name: raw for name, raw in tracked_files('native/app').items()
           if not name.startswith('state/')
           and (name.endswith(('.js', '.json', '.png')) or name.startswith('vendor/'))}
    service = {name: raw for name, raw in tracked_files('native/service').items()
               if not name.startswith('state/') and name.endswith(('.js', '.json'))}
    return app, service


def compile_helper_sources(app, service):
    if 'screensaver-controller.js' in app:
        from scripts.screensaver_package import runtime_files
        app = {**app, **runtime_files()}
    if 'app-inventory.js' in service:
        app = {**app, 'app-inventory.js': service['app-inventory.js']}
    # Each jail needs its own copy of the shared modules.
    service = {**service, **{name: app[name] for name in ('state-permissions.js', 'contract-events.js')}}
    return compile_helper(app), compile_helper(service)


def stage_helper(app_dir, service_dir):
    app, service = compile_helper_sources(*helper_sources())
    for directory, files in ((app_dir, app), (service_dir, service)):
        for name, raw in files.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)


def pack_app(appfiles, servicefiles, architecture='all', helper=False):
    if helper:
        appfiles, servicefiles = compile_helper_sources(appfiles, servicefiles)
    info = json.loads(appfiles['appinfo.json'])
    if info.get('type') == 'web':
        if 'screensaver-settings.js' in appfiles:
            from scripts.screensaver_package import settings_script
            appfiles = dict(appfiles, **{'screensaver-config.js': settings_script()})
        appfiles = compile_web(appfiles)
    app, version = info['id'], info['version']
    service = json.loads(servicefiles['services.json'])['id']
    if service == 'com.gathin.tvhome.renewal':
        servicefiles = {**servicefiles, **renewal_service_assets(ROOT)}
    if not helper:
        # Packaged services run on the TV's own Node (0.12 on webOS 3.x), like Helper:
        # uncompiled async functions stop them from loading at all.
        servicefiles = compile_helper(servicefiles)
    files = {'usr/palm/applications/' + app + '/' + n: b for n, b in appfiles.items()}
    if app == 'com.gathin.tvhome':
        from scripts.screensaver_package import add_root_resources
        add_root_resources(files, 'usr/palm/applications/' + app + '/')
    files.update({'usr/palm/services/' + service + '/' + n: b for n, b in servicefiles.items()})
    files['usr/palm/packages/' + app + '/packageinfo.json'] = json.dumps({
        'id': app, 'version': version, 'app': app, 'services': [service]}).encode()
    if service == 'com.gathin.tvhome.renewal':
        files['usr/palm/services/' + service + '/state/home-control/.keep'] = b''
    executables = set()
    if helper:
        executables = {'usr/palm/applications/' + app + '/' + n for n in ('detach', 'relay', 'resume')}
        files['usr/palm/applications/' + app + '/state/.keep'] = b''
        files['usr/palm/services/' + service + '/state/.keep'] = b''
    return package.ipk(app, version, files, executables, helper_state=helper,
                       architecture=architecture, shared_directories=True)


GRAPHICS = {'1920x1080': {'launcher': 'launcher.ipk', 'root': 'root'},
            '1280x720': {'launcher': 'launcher-720p.ipk', 'root': 'root-720p'}}
C1_GRAPHICS = {'1920x1080': 'root-c1', '1280x720': 'root-c1-720p'}
ROOT_BACKENDS = {'c1-native-gate': {'experimental': True, 'hardware_validated': False,
                                  'admission_schema': 3, 'graphics': C1_GRAPHICS}}


def stage_c1_root(payload, work, version, run=subprocess.run, *, scratch=None):
    """Compile once with the existing pinned build-only Zig dependency."""
    scratch = Path(work if scratch is None else scratch)
    helper = scratch / 'c1-keyfilter-guard'
    environment = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(Path(work) / 'zig-global-cache'),
                       ZIG_LOCAL_CACHE_DIR=str(Path(work) / 'zig-cache'))
    run([sys.executable, '-m', 'ziglang', 'cc', '-target', 'arm-linux-musleabi',
         '-Os', '-static', '-s', 'root-edition/gate/keyfilter.c', '-o', str(helper)],
        cwd=ROOT, env=environment, check=True)
    recovery = scratch / 'c1-home-gate'
    run([sys.executable, '-m', 'ziglang', 'cc', '-target', 'arm-linux-musleabi',
         '-Os', '-static', '-s', 'root-edition/gate/gate.c', '-o', str(recovery)],
        cwd=ROOT, env=environment, check=True)
    stage_keyfilter_variants(payload, version, helper, run=run, mount_recovery=recovery)
    return helper


def stage_keyfilter_variants(payload, version, helper, run=subprocess.run, legacy_node_beta=False, mount_recovery=None):
    for graphics, folder in C1_GRAPHICS.items():
        run([sys.executable, 'root-edition/build.py', '--output', str(Path(payload) / folder),
             '--version', version, '--resolution', graphics, '--experimental-c1-keyfilter', str(helper),
             *(['--legacy-node-beta'] if legacy_node_beta else []),
             *(['--c1-mount-recovery', str(mount_recovery)] if mount_recovery is not None else [])],
            cwd=ROOT, check=True)


def stage_legacy_root_beta(payload, version, keyfilter_guard, run=subprocess.run):
    target = Path(payload)/'legacy-root-beta'
    target.mkdir()
    for graphics, paths in GRAPHICS.items():
        run([sys.executable, 'root-edition/build.py', '--output', str(target/paths['root']),
             '--version', version, '--resolution', graphics, '--legacy-node-beta'], cwd=ROOT, check=True)
    for script, folder in [('root-edition/build_updater.py','root-updater'), ('system-updater/build.py','system-updater')]:
        run([sys.executable, script, '--output', str(target/folder), '--legacy-node-beta'], cwd=ROOT, check=True)
    stage_keyfilter_variants(target, version, keyfilter_guard, run=run, legacy_node_beta=True)
    shutil.copy2(Path(payload)/'fallback.png', target/'fallback.png')
    shutil.copytree(Path(payload)/'installer-support', target/'installer-support')
    manifest = {'schema':1, 'graphics':GRAPHICS, 'runtime_variant':'node012-beta', 'root_backends':ROOT_BACKENDS,
                'files':{p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(target.rglob('*')) if p.is_file()}}
    (target/'payload.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding='utf-8')
    package.verify_payload(target)



def verify_release_versions(payload, versions):
    from cytv import __version__
    if __version__ != versions['cytv']:
        raise ValueError('cytv version does not match release metadata')
    if (payload/'updater.ipk').exists():
        files=package.data_files((payload/'updater.ipk').read_bytes())
        for name in ('usr/palm/applications/com.cleanyourtv.updater/appinfo.json','usr/palm/services/com.cleanyourtv.updater.service/package.json'):
            if json.loads(files[name])['version']!=versions['updater']:raise ValueError('No-root Updater version mismatch')
    for graphics, paths in GRAPHICS.items():
        for kind, app in (('launcher', 'com.gathin.tvhome'), ('root', package.ROOT_APP)):
            folder=payload/paths[kind]
            raw=(folder/json.loads((folder/'bundle.json').read_text())['package']).read_bytes() if kind=='root' else folder.read_bytes()
            files=package.data_files(raw);info=json.loads(files['usr/palm/applications/'+app+'/appinfo.json'])
            service=app+'.service' if kind=='root' else 'com.gathin.tvhome.renewal'
            if json.loads(files['usr/palm/services/'+service+'/package.json']).get('version')!=versions['root' if kind=='root' else 'home']:raise ValueError('Embedded application/service version mismatch')
            if info.get('id')!=app or info.get('version')!=versions['root' if kind=='root' else 'home'] or info.get('resolution')!=graphics:raise ValueError('Embedded graphics resolution/version mismatch')
    root = payload / 'root'
    bundle = json.loads((root / 'bundle.json').read_text())
    if json.loads((root / 'release.json').read_text())['version'] != versions['root']:
        raise ValueError('Root release version does not match release metadata')
    for filename, app, service, version in (
        ('launcher.ipk', 'com.gathin.tvhome', 'com.gathin.tvhome.renewal', versions['home']),
        ('helper.ipk', 'com.local.nativehome', 'com.local.nativehome.service', versions['helper']),
        ('root/' + bundle['package'], package.ROOT_APP, package.ROOT_APP + '.service', versions['root']),
    ):
        files = package.data_files((payload / filename).read_bytes())
        info = json.loads(files['usr/palm/applications/' + app + '/appinfo.json'])
        metadata = json.loads(files['usr/palm/services/' + service + '/package.json'])
        if info['id'] != app or info['version'] != version or metadata['version'] != version:
            raise ValueError('Embedded application/service version does not match release metadata: ' + app)


def stage_brand_assets(payload):
    for packaged, master in (('brand-symbol.svg', 'symbol-reversed.svg'),
                             ('brand-stacked.svg', 'logo-stacked-dark.svg')):
        (payload / packaged).write_bytes((ROOT / 'assets/brand' / master).read_bytes())


def stage_installer_docs(payload):
    target = payload / 'setup-guide'
    target.mkdir(exist_ok=True)
    for name in ('sign-in.png', 'dev-mode.png', 'key-server.png', 'README.md'):
        shutil.copy2(ROOT / 'android/app/src/main/assets/ui/guide' / name, target / name)
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        (payload / name).write_bytes((ROOT / name).read_bytes())


def stage_theme_previews(payload):
    target = payload / 'setup-themes'
    target.mkdir(exist_ok=True)
    for name, source in (('classic.png', 'showcase/assets/classic-preview.png'),
                         ('liquid-glass.jpg', 'themes/liquid-glass/assets/preview.jpg'),
                         ('ribbon.jpg', 'themes/ribbon/assets/preview.jpg')):
        shutil.copy2(ROOT / source, target / name)


# Preserve exact published Helper packages while their versions remain selected.
HELPER_0_6_16_SHA256 = 'ccabf56c814d2aaf35853d95be2aac67614a67b79e223151b93260d58b82f5f1'
HELPER_0_6_17_SHA256 = '165d933c17f1ed24f0ab65986293c7488b0b5d875db5f7b1215e46f24d422f92'

HELPER_0_6_19_SHA256 = '52510c9115a518a05849f6618516b41886aea54b7f74ea4763ffeeaf63c03e7b'

def helper_baseline(version):
    expected = {'0.6.16': HELPER_0_6_16_SHA256, '0.6.17': HELPER_0_6_17_SHA256,
                '0.6.19': HELPER_0_6_19_SHA256}.get(version)
    if expected is None:
        return None
    data = (ROOT / ('native/published/com.local.nativehome_' + version + '_arm.ipk')).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Published Helper baseline hash mismatch')
    return data


def stage_updater(payload):
    app, service = updater_sources(ROOT)
    versions = json.loads((ROOT / 'release-versions.json').read_text())
    if json.loads(app['appinfo.json'])['version'] != versions['updater']:
        raise ValueError('No-root Updater version mismatch')
    (payload / 'updater.ipk').write_bytes(pack_app(app, service))


def stage_installer_support(payload, work):
    """Independent static support; never alter a pinned Helper package."""
    target = Path(payload) / 'installer-support'
    target.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(Path(work) / 'zig-global-cache'),
                       ZIG_LOCAL_CACHE_DIR=str(Path(work) / 'zig-cache'))
    name = 'lifecycle-gate'
    subprocess.run([sys.executable, '-m', 'ziglang', 'cc', '-target', 'arm-linux-musleabi',
                    '-std=c99', '-Wall', '-Wextra', '-Werror', '-Os', '-static', '-s',
                    'native/installer/' + name + '.c', '-o', str(target / name)],
                   cwd=ROOT, env=environment, check=True)


def _prepare_payload(payload, work, versions, *, single_tile=False):
    # Compiler intermediates stay local to this attempt. Only Zig's own caches
    # are shared, so a child left running cannot write into a later attempt.
    scratch = payload.parent
    stage_installer_support(payload, work)
    helper = None if single_tile else helper_baseline(versions['helper'])
    if helper is None:
        import ziglang
        zig = Path(ziglang.__file__).parent / ('zig.exe' if os.name == 'nt' else 'zig')
        environment = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(work / 'zig-global-cache'), ZIG_LOCAL_CACHE_DIR=str(work / 'zig-cache'))
        app, service = helper_sources()
        if single_tile:
            info = json.loads(app['appinfo.json'])
            app['appinfo.json'] = json.dumps(dict(info, visible=False, cytvProductGeneration=2)).encode()
        for name, sources in {
            'detach': ['native/app/detach.c'],
            'relay': ['native/prototype/relay.c', 'native/prototype/filter.c'],
            'resume': ['native/app/resume.c'],
        }.items():
            output = scratch / name
            subprocess.run([str(zig), 'cc', '-target', 'arm-linux-musleabi', '-Os', '-static', '-s',
                            *sources, '-o', str(output)], cwd=ROOT, env=environment, check=True)
            app[name] = output.read_bytes()
        helper = pack_app(app, service, architecture='arm', helper=True)
    (payload / 'helper.ipk').write_bytes(helper)
    from scripts.screensaver_package import build as screensaver_package
    (payload / 'screensaver.ipk').write_bytes(screensaver_package())
    launcher = {n: b for n, b in tracked_files('launcher').items() if n != 'apps.js' and not n.startswith('icons/')}
    if single_tile:
        head = b'<head>'
        if launcher['index.html'].count(head) != 1:
            raise ValueError('Missing Home document head')
        launcher['index.html'] = launcher['index.html'].replace(head, head + b'<script>window.CYTVProductGeneration=2;</script>', 1)
    launcher['config.js'] = b'window.CONFIG = {columns:5,dockApps:[],hiddenApps:["com.gathin.tvhome","com.local.nativehome"]};\n'
    launcher['apps.js'] = b'window.TV_APPS = {apps:[],inputs:[]};\n'
    renewal = {n: b for n, b in tracked_files('renewal-service').items() if not n.startswith('state/')}
    for graphics, paths in GRAPHICS.items():
        app=dict(launcher);info=json.loads(app['appinfo.json']);info['resolution']=graphics
        if single_tile:
            info.update(visible=False, cytvProductGeneration=2)
        app['appinfo.json']=(json.dumps(info,indent=2)+'\n').encode()
        (payload / paths['launcher']).write_bytes(pack_app(app, renewal))
    from scripts.chinese_fonts import with_fonts
    launcher = with_fonts(launcher)
    (payload / 'fonts').mkdir()
    for name, data in launcher.items():
        if name.startswith('fonts/Noto'):
            (payload / name).write_bytes(data)
    (payload / 'fallback.png').write_bytes(launcher['brand-v2-icon.png'])
    (payload / 'installer.png').write_bytes((ROOT / 'assets/icons/installer.png').read_bytes())
    stage_brand_assets(payload)
    stage_installer_docs(payload)
    stage_theme_previews(payload)
    for graphics, paths in GRAPHICS.items():
        subprocess.run([sys.executable, 'root-edition/build.py', '--output', str(payload / paths['root']), '--version', versions['root'], '--resolution', graphics,
                        *(['--single-tile'] if single_tile else [])], cwd=ROOT, check=True)
    keyfilter_guard = stage_c1_root(payload, work, versions['root'], scratch=scratch)
    subprocess.run([sys.executable, 'root-edition/build_updater.py', '--output', str(payload / 'root-updater')], cwd=ROOT, check=True)
    stage_updater(payload)
    subprocess.run([sys.executable,'system-updater/build.py','--output',str(payload/'system-updater'),
                    *(['--single-tile'] if single_tile else [])],cwd=ROOT,check=True)
    stage_legacy_root_beta(payload, versions['root'], keyfilter_guard)
    if single_tile:
        from homebrew.build import build_tile
        for edition, name in package.TILE_FILES.items():
            build_tile(payload / name, versions['release'], edition)
    shutil.copytree(ROOT / 'cytv/licenses', payload / 'licenses/Qt', dirs_exist_ok=True)
    # Ship dependency license metadata as well as application notices in the executable.
    import importlib.metadata
    for name in ('paramiko', 'websockets', 'cryptography', 'bcrypt', 'PyNaCl', 'cffi', 'psutil', 'PySide6-Essentials', 'shiboken6'):
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            if name in ('PySide6-Essentials', 'shiboken6'):
                continue
            raise
        for item in distribution.files or ():
            if any('license' in part.lower() or part.lower() == 'copying' for part in item.parts):
                path = Path(distribution.locate_file(item))
                if path.is_file():
                    target = payload / 'licenses' / name / path.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(path.read_bytes())
    manifest = {'schema': 1, 'launcher': 'launcher.ipk', 'helper': 'helper.ipk', 'graphics': GRAPHICS,
                'legacy_root_beta': 'legacy-root-beta',
                'screensaver': package.SCREENSAVER_IPK,
                'screensaver_version': json.loads((ROOT / 'screensaver/appinfo.json').read_text())['version'],
                'home_version': json.loads(launcher['appinfo.json'])['version'],
                'helper_version': versions['helper'],
                'root_backends': ROOT_BACKENDS,
                'files': {p.relative_to(payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(payload.rglob('*')) if p.is_file()}}
    if single_tile:
        manifest['single_tile'] = {**package.TILE_FILES, 'version': versions['release']}
    (payload / 'payload.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


@contextmanager
def _payload_build(*, single_tile=False):
    work = ROOT / 'build/cytv'
    workspace = work / '.cytv-payload-build'
    if workspace.resolve() != workspace:
        raise ValueError('Indirect payload build directory: ' + str(workspace))
    workspace.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock = workspace / '.cytv-payload-build-v1.lock'
    if any(workspace.iterdir()) and not lock.exists():
        raise ValueError('Unmanaged payload build directory: ' + str(workspace))

    output, previous, attempts = work / 'payload', workspace / 'previous', workspace / 'attempts'
    with build_lock(lock):
        if any(path.name not in (lock.name, previous.name, attempts.name) for path in workspace.iterdir()):
            raise ValueError('Unmanaged payload build directory: ' + str(workspace))
        for path in (output, previous, attempts):
            if path.is_symlink() or (path.exists() and (not path.is_dir() or path.resolve() != path)):
                raise ValueError('Invalid payload build directory: ' + str(path))

        # After an interruption between renames, restore the previous payload.
        if previous.exists():
            if output.exists():
                shutil.rmtree(previous)
            else:
                previous.rename(output)
        if attempts.exists():
            shutil.rmtree(attempts)
        attempts.mkdir()
        try:
            staged = Path(tempfile.mkdtemp(dir=attempts)) / 'payload'
            staged.mkdir()
            versions = json.loads((ROOT / 'release-versions.json').read_text())
            if single_tile:
                _prepare_payload(staged, work, versions, single_tile=True)
            else:
                _prepare_payload(staged, work, versions)
            package.verify_payload(staged)
            verify_release_versions(staged, versions)
            # Replace whole directories. Unlocked readers can briefly see
            # an absent path between these renames, never the unverified tree.
            if output.exists():
                output.rename(previous)
            staged.rename(output)
        except BaseException:
            if previous.exists() and not output.exists():
                previous.rename(output)
            raise
        finally:
            shutil.rmtree(attempts)
        if previous.exists():
            shutil.rmtree(previous)

        yield output


def build_payload():
    with _payload_build() as payload:
        return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload-only', action='store_true', help='Build and verify TV assets, without freezing')
    parser.add_argument('--desktop', action='store_true', help='Also build the Windows GUI ZIP, macOS app or Debian package')
    parser.add_argument('--single-tile', action='store_true', help='Build the single-entry candidate installer payload')
    args = parser.parse_args()
    with _payload_build(single_tile=args.single_tile) as payload:
        print('Public TV payload verified:', payload)
        if not args.payload_only:
            build_host(payload, args.desktop)


def build_host(payload, desktop):
    trusted = ROOT / 'build/cytv/trusted-js'
    stage_sources(trusted)
    environment = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / 'build/cytv/pyinstaller-cache'))
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--console',
                    '--exclude-module', 'imageio_ffmpeg',
                    '--name', 'cytv', *(['--icon', str(ROOT / 'assets/icons/installer.ico')] if os.name == 'nt' else []),
                    '--paths', str(ROOT), '--add-data', str(payload) + os.pathsep + 'payload',
                    '--add-data', str(trusted) + os.pathsep + 'cytv/tv',
                    '--workpath', str(ROOT / 'build/cytv/freeze'), '--specpath', str(ROOT / 'build/cytv'),
                    '--distpath', str(ROOT / 'dist'), str(ROOT / 'cytv/__main__.py')], cwd=ROOT, env=environment, check=True)
    executable = ROOT / 'dist' / ('cytv.exe' if os.name == 'nt' else 'cytv')
    subprocess.run([str(executable), '--version'], check=True)
    subprocess.run([str(executable), '--check-payload'], check=True)
    subprocess.run([str(executable), '--check-runtime'], check=True)
    print('Built:', executable)
    if desktop:
        from desktop_packaging import build_desktop
        from cytv import __version__
        build_desktop(ROOT, payload, environment, __version__)


if __name__ == '__main__':
    main()
