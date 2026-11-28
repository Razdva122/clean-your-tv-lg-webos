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


def build(output, version):
    build_tools = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))
    sources = build_tools['tracked_files']
    app = sources('single-home/app')
    service = sources('single-home/service')
    service.update({'vendor/' + name: data for name, data in sources('native/app/vendor').items()})
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
