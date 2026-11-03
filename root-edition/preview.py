#!/usr/bin/env python3
"""Stage an isolated Root UI preview locally. Never connects to or activates a TV."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

APP_ID = 'com.cleanyourtv.root.preview'
SOURCE = Path(__file__).resolve().parents[1] / 'launcher'
# Explicit public-source inventory: never recursively copy a developer workspace.
FILES = (
    'appinfo.json', 'viewport.js', 'release-notes.js', 'system-updates.js', 'index.html', 'app.js', 'app-library.js', 'input-sources.js', 'input-preview.js','i18n.js', 'catalogs.js', 'i18n.css', 'style.css', 'theme-defaults.css', 'theme-policy.js', 'theme-runtime.js', 'home-layout.js', 'layout-panel.js', 'settings-categories.js', 'layout-panel.css',
    'brand-v2-icon.png', 'brand-v2-largeIcon.png', 'splash.png',
    'fonts/outfit-300.ttf', 'fonts/outfit-400.ttf', 'fonts/outfit-500.ttf', 'fonts/outfit-700.ttf', 'fonts/NotoSans.ttf', 'fonts/NotoSans-OFL.txt', 'fonts/NotoSansDevanagari.ttf', 'fonts/NotoSansDevanagari-OFL.txt', 'fonts/NotoSansKR.ttf', 'fonts/NotoSansKR-OFL.txt', 'fonts/NotoSansSC.ttf', 'fonts/NotoSansSC-OFL.txt', 'fonts/NotoSansTC.ttf', 'fonts/NotoSansTC-OFL.txt', 'fonts/OFL.txt',
)
FILES += tuple(['wallpaper.js', 'wallpaper.css', 'wallpaper-panel.js', 'wallpaper-panel.css', 'wallpaper-locales.js', 'wallpaper-media-cache.js', 'theme-data.js', 'theme-store.js', 'theme-manager.js', 'theme-receiver.js', 'theme-panel.js', 'theme-panel.css', 'theme-locales.js', 'builtin-theme-files.json'] + json.loads((SOURCE / 'builtin-theme-files.json').read_text()))
UI = Path(__file__).resolve().parent / 'ui'
UI_FILES = ('root-audio-locales.js', 'root-audio.js', 'root-locales.js', 'root-exit.js', 'root-firmware-control.js', 'root-firmware.js', 'root-settings.js', 'root-settings.css', 'root-profile-data.js', 'root-profile.js', 'root-updates.js')


def prepare(version='0.0.1', resolution=None):
    if resolution is not None and resolution not in ('1280x720', '1920x1080'):
        raise ValueError('Unsupported app graphics resolution')
    if not isinstance(version, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version) or len(version) > 32:
        raise ValueError('Invalid Root release version')
    files = {}
    for name in FILES:
        path = SOURCE / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(SOURCE.resolve()):
            raise ValueError('Missing or indirect source: ' + name)
        files[name] = path.read_bytes()
    info = json.loads(files['appinfo.json'])
    if (info.get('id'), info.get('type'), info.get('main')) != ('com.gathin.tvhome', 'web', 'index.html'):
        raise ValueError('Unexpected launcher manifest')
    if resolution is not None:
        info['resolution'] = resolution
    info['themeEngineVersion'] = info['version']
    info.update(id=APP_ID, title='Home Root', version=version, appCategory=['home'], icon='home-root-icon.png', largeIcon='home-root-largeIcon.png')
    for name in ('brand-v2-icon.png', 'brand-v2-largeIcon.png'):
        path = UI.parent / 'assets' / ('home.png' if name == 'brand-v2-icon.png' else 'home-large.png')
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(UI.parent.resolve()):
            raise ValueError('Missing or indirect Root icon: ' + name)
        files['home-root-icon.png' if name == 'brand-v2-icon.png' else 'home-root-largeIcon.png'] = path.read_bytes()
    for field in ('icon', 'largeIcon', 'splashBackground'):
        if info.get(field) not in files:
            raise ValueError('Unpackaged manifest resource: ' + field)
    html = files['index.html'].decode()
    # Older launcher sources may still include the now-inert compatibility entry.
    html = html.replace('<script src="native-bootstrap.js"></script>', '').replace('<script src="helper-control.js"></script>', '')
    tags = ['<script src="' + name + '"></script>' for name in (
        'renewal-panel.js',
        'user-data.js', 'update-panel.js')]
    tags.append('<link rel="stylesheet" href="renewal-panel.css">')
    for tag in tags:
        if html.count(tag) != 1:
            raise ValueError('Unexpected launcher HTML: ' + tag)
        html = html.replace(tag, '')
    # Root's independent profile bootstrap never loads ordinary updater/renewal code.
    entry = '<script src="profile-bootstrap.js"></script>'
    if html.count(entry) != 1:
        raise ValueError('Unexpected launcher entry')
    files['index.html'] = html.replace(entry, '<link rel="stylesheet" href="root-settings.css">\n  <script>window.ROOT_VERSION = ' + json.dumps(version) + ';</script>\n  <script src="root-locales.js"></script>\n  <script src="root-audio-locales.js"></script>\n  <script src="root-exit.js"></script>\n  <script src="root-firmware-control.js"></script>\n  <script src="root-firmware.js"></script>\n  <script src="root-audio.js"></script>\n  <script src="root-settings.js"></script>\n  <script src="root-updates.js"></script>\n  <script src="root-profile-data.js"></script>\n  <script src="root-profile.js"></script>').encode()
    files['appinfo.json'] = (json.dumps(info, indent=2) + '\n').encode()
    for name in UI_FILES:
        path = UI / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(UI.resolve()):
            raise ValueError('Missing or indirect Root UI: ' + name)
        files[name] = path.read_bytes()
    files['apps.js'] = b'window.TV_APPS = {apps: [], inputs: []};\n'
    config = {'columns': 5, 'dockApps': [], 'hiddenApps': ['com.gathin.tvhome', 'com.local.nativehome', APP_ID]}
    files['config.js'] = ('window.CONFIG = ' + json.dumps(config) + ';\n').encode()
    sys.path.insert(0, str(SOURCE.parent))
    from scripts.chinese_fonts import with_fonts
    return with_fonts(files)


def stage(output):
    files = prepare()
    # Exclusive creation: a previous build or user data is never overwritten.
    output.mkdir(parents=False, exist_ok=False)
    for name, data in files.items():
        path = output / 'app' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    inventory = {
        'application_id': APP_ID,
        'public_release_ready': False,
        'activates_system_home': False,
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    (output / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; parent must exist')
    args = parser.parse_args()
    try:
        stage(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, 'Preview staging failed: ' + str(exc) + '\n')
    print('Staged UI only. No installer, services, profile changes or startup hooks.')


if __name__ == '__main__':
    main()
