#!/usr/bin/env python3
"""Stage an isolated Root UI preview locally. Never connects to or activates a TV."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.home_assets import ROOT_HOME_FILES as FILES, ROOT_UI_FILES as UI_FILES

APP_ID = 'com.cleanyourtv.root.preview'
SOURCE = Path(__file__).resolve().parents[1] / 'launcher'
UI = Path(__file__).resolve().parent / 'ui'


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
    from scripts.screensaver_package import settings_script
    files['screensaver-config.js'] = settings_script()
    info = json.loads(files['appinfo.json'])
    if (info.get('id'), info.get('type'), info.get('main')) != ('com.gathin.tvhome', 'web', 'index.html'):
        raise ValueError('Unexpected launcher manifest')
    if resolution is not None:
        info['resolution'] = resolution
    info['themeEngineVersion'] = info['version']
    info.update(id=APP_ID, title='Home Root', version=version, appCategory=['home'], icon='home-root-icon.png', largeIcon='home-root-largeIcon.png')
    info.update(defaultWindowType='card', transparent=False,
                noSplashOnLaunch=True, spinnerOnLaunch=False)
    info.pop('splashBackground', None)
    info.pop('handlesRelaunch', None)
    info.pop('keepAlive', None)
    for name in ('brand-v2-icon.png', 'brand-v2-largeIcon.png'):
        path = UI.parent / 'assets' / ('home.png' if name == 'brand-v2-icon.png' else 'home-large.png')
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(UI.parent.resolve()):
            raise ValueError('Missing or indirect Root icon: ' + name)
        files['home-root-icon.png' if name == 'brand-v2-icon.png' else 'home-root-largeIcon.png'] = path.read_bytes()
    for field in ('icon', 'largeIcon'):
        if info.get(field) not in files:
            raise ValueError('Unpackaged manifest resource: ' + field)
    html = files['index.html'].decode()
    # Older launcher sources may still include the now-inert compatibility entry.
    html = html.replace('<script src="native-bootstrap.js"></script>', '').replace('<script src="helper-control.js"></script>', '')
    tags = ['<script src="' + name + '"></script>' for name in (
        'renewal-panel.js',
        'user-data.js', 'update-panel.js')]
    tags.extend('<link rel="stylesheet" href="' + name + '">' for name in (
        'settings-panel.css', 'renewal-panel.css'))
    for tag in tags:
        # Prettier uses an optional HTML void-element closing slash.
        pattern = re.escape(tag[:-1]) + r'\s*/?>' if tag.startswith('<link ') else re.escape(tag)
        if len(re.findall(pattern, html)) != 1:
            raise ValueError('Unexpected launcher HTML: ' + tag)
        html = re.sub(pattern, '', html)
    # Root's independent profile bootstrap never loads ordinary updater/renewal code.
    entry = '<script src="profile-bootstrap.js"></script>'
    if html.count(entry) != 1:
        raise ValueError('Unexpected launcher entry')
    files['index.html'] = html.replace(entry, '<link rel="stylesheet" href="settings-panel.css">\n  <link rel="stylesheet" href="root-settings.css">\n  <script>window.ROOT_VERSION = ' + json.dumps(version) + ';</script>\n  <script src="root-locales.js"></script>\n  <script src="root-audio-locales.js"></script>\n  <script src="root-exit.js"></script>\n  <script src="root-firmware-control.js"></script>\n  <script src="root-firmware.js"></script>\n  <script src="root-audio.js"></script>\n  <script src="root-settings.js"></script>\n  <script src="root-updates.js"></script>\n  <script src="tv-name.js"></script>\n  <script src="root-profile-data.js"></script>\n  <script src="root-profile.js"></script>').encode()
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
