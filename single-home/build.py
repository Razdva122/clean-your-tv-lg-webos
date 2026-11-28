#!/usr/bin/env python3
"""Build the isolated one-tile pilot or a private Homebrew feed for its exact IPK."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cytv import package
from homebrew.build import ipk_control_lines

APP = 'io.github.razdva122.cytvhomepilot'
SERVICE = APP + '.service'
SOURCE = 'https://github.com/Razdva122/clean-your-tv-lg-webos'


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def version_number(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value):
        raise ValueError('Use a numeric three-part pilot version')
    return value


def inspect(raw):
    files = package.data_files(raw)
    app_dir = f'usr/palm/applications/{APP}/'
    pkg_dir = f'usr/palm/packages/{APP}/'
    svc_dir = f'usr/palm/services/{SERVICE}/'
    if not all(name.startswith((app_dir, pkg_dir, svc_dir)) for name in files):
        raise ValueError('Package contains another application or service')
    app = json.loads(files[app_dir + 'appinfo.json'])
    service = json.loads(files[svc_dir + 'package.json'])
    registration = json.loads(files[svc_dir + 'services.json'])
    metadata = json.loads(files[pkg_dir + 'packageinfo.json'])
    version = version_number(app['version'])
    control = dict(line.split(': ', 1) for line in ipk_control_lines(raw) if ': ' in line)
    if (app['id'] != APP or app['type'] != 'web' or app.get('visible') is False
            or (service['name'], service['version']) != (SERVICE, version)
            or registration['id'] != SERVICE or [s['name'] for s in registration['services']] != [SERVICE]
            or metadata != {'id': APP, 'version': version, 'app': APP, 'services': [SERVICE]}
            or (control['Package'], control['Version'], control['Architecture']) != (APP, version, 'all')):
        raise ValueError('Mismatched pilot identity, version or service registration')
    for directory, name in ((app_dir, app['main']), (svc_dir, service['main'])):
        if not files[directory + package.safe_name(name)]:
            raise ValueError('Empty entry point')
    return app, files[app_dir + package.safe_name(app['icon'])], sum(map(len, files.values()))


# These integrations depend on the other editions' services. The pilot ships
# the product rendering and editing code and provides its own settings host.
OTHER_EDITION_ASSETS = {
    'native-bootstrap.js', 'helper-control.js', 'install-settings.js',
    'input-sources.js', 'input-preview.js', 'browser-profile.js',
    'theme-receiver.js', 'wallpaper-media-cache.js', 'release-notes.js',
    'system-updates.js', 'update-panel.js', 'screensaver-settings.css',
    'screensaver-config.js', 'screensaver-idle.js', 'screensaver-personal.js',
    'screensaver-settings.js', 'weather-transport.js',
}


def product_app(sources):
    app = {name: data for name, data in sources('launcher').items()
           if name not in OTHER_EDITION_ASSETS and not name.startswith('icons/')}
    setup = sources('single-home/app')
    pilot = json.loads(setup.pop('appinfo.json'))
    product = json.loads(app['appinfo.json'])
    pilot['themeEngineVersion'] = product.get('themeEngineVersion', product['version'])
    pilot['requiredACG'] = sorted(set(product['requiredACG']) | set(pilot['requiredACG']))
    product.pop('systemUpdateProtocol', None)
    app['appinfo.json'] = encode({**product, **pilot, 'icon': product['icon'], 'largeIcon': product['largeIcon']})
    app.update({'setup/' + name: data for name, data in setup.items()})
    app['apps.js'] = b'window.TV_APPS = {apps: [], inputs: []};\n'
    adapter = ROOT / 'single-home/launcher'
    app['profile-bootstrap.js'] = (adapter / 'profile-bootstrap.js').read_bytes()
    app['renewal-panel.js'] = (adapter / 'settings.js').read_bytes()
    # Keep the product markup and load order verbatim for the included modules.
    def include(match):
        return b'' if match[1].decode() in OTHER_EDITION_ASSETS else match[0]
    app['index.html'] = re.sub(rb'<script src="([^"]+)"></script>', include, app['index.html'])
    app['index.html'] = re.sub(rb'<link rel="stylesheet" href="([^"]+)"\s*/>', include, app['index.html'])
    return app


def build(output, version):
    build_tools = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))
    sources = build_tools['tracked_files']
    app = product_app(sources)
    service = sources('single-home/service')
    service.update({'vendor/' + name: data for name, data in sources('native/app/vendor').items()})
    service['app-inventory.js'] = (ROOT / 'native/service/app-inventory.js').read_bytes()
    service['websocket.js'] = (ROOT / 'native/app/websocket.js').read_bytes()
    info = json.loads(app['appinfo.json'])
    version = version_number(version or info['version'])
    app['appinfo.json'] = encode(dict(info, version=version))
    service['package.json'] = encode(dict(json.loads(service['package.json']), version=version))
    raw = build_tools['pack_app'](app, service)
    inspect(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(raw)
    print(f'{output.name}  {len(raw)} bytes  SHA-256 {hashlib.sha256(raw).hexdigest()}')


def catalog(ipk, output, base):
    base = base.rstrip('/')
    uri = urlsplit(base)
    if (uri.scheme not in ('http', 'https') or not uri.hostname or uri.username is not None
            or uri.password is not None or uri.query or uri.fragment):
        raise ValueError('Expected an HTTP(S) base URL')
    raw = ipk.read_bytes()
    info, icon, total = inspect(raw)
    digest = hashlib.sha256(raw).hexdigest()
    filename = f"{APP}_{info['version']}_all.ipk"
    asset = f'{base}/{digest}'
    title = info['title']
    description = 'Private development build of the single-tile Home app.'
    card = {'id': APP, 'title': title, 'shortDescription': description,
            'iconUri': asset + '/icon.png', 'manifestUrl': asset + '/manifest.json'}
    manifest = {'id': APP, 'title': title, 'version': info['version'], 'type': 'web',
                'appDescription': description, 'rootRequired': False, 'sourceUrl': SOURCE,
                'iconUri': card['iconUri'], 'ipkUrl': asset + '/' + filename,
                'ipkHash': {'sha256': digest}, 'ipkSize': len(raw), 'installedSize': total}
    if output.exists():
        raise ValueError('Select a new private feed directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / 'feed'
        folder = stage / digest
        folder.mkdir(parents=True)
        (folder / filename).write_bytes(raw)
        (folder / 'icon.png').write_bytes(icon)
        (folder / 'manifest.json').write_bytes(encode(manifest))
        (stage / 'apps.json').write_bytes(encode({'packages': [card]}))
        stage.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    pack = commands.add_parser('build')
    pack.add_argument('--output', type=Path, required=True)
    pack.add_argument('--version')
    feed = commands.add_parser('catalog')
    feed.add_argument('--ipk', type=Path, required=True)
    feed.add_argument('--output', type=Path, required=True)
    feed.add_argument('--base-url', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            build(args.output, args.version)
        else:
            catalog(args.ipk, args.output, args.base_url)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Cannot {args.command} pilot: {exc}\n')
