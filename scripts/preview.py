#!/usr/bin/env python3
"""Serve the real launcher and reviewed themes with original webOS app reference data. Requires Node.js and installed build dependencies."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import shutil
import runpy
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parents[1]

def preview_themes():
    return subprocess.check_output(['node', str(ROOT / 'scripts/build-preview-themes.cjs')], cwd=ROOT)

LAUNCHER_FILES = {
    'index.html', 'style.css', 'theme-defaults.css', 'theme-policy.js', 'theme-runtime.js', 'home-layout.js', 'layout-panel.js', 'settings-categories.js', 'layout-panel.css', 'renewal-panel.css', 'app.js', 'app-library.js', 'config.js',
    'user-data.js', 'release-notes.js', 'system-updates.js', 'update-panel.js', 'renewal-panel.js', 'helper-control.js', 'profile-bootstrap.js',
    'native-bootstrap.js', 'i18n.js', 'catalogs.js', 'i18n.css', 'fonts/outfit-300.ttf', 'fonts/outfit-400.ttf', 'fonts/outfit-500.ttf', 'fonts/outfit-700.ttf', 'fonts/NotoSans.ttf', 'fonts/NotoSans-OFL.txt', 'fonts/NotoSansDevanagari.ttf', 'fonts/NotoSansDevanagari-OFL.txt', 'fonts/NotoSansKR.ttf', 'fonts/NotoSansKR-OFL.txt', 'fonts/NotoSansSC.ttf', 'fonts/NotoSansSC-OFL.txt', 'fonts/NotoSansTC.ttf', 'fonts/NotoSansTC-OFL.txt', 'fonts/OFL.txt',
}
THEME_FILES = ['theme-data.js', 'theme-store.js', 'theme-manager.js', 'theme-receiver.js', 'theme-panel.js', 'theme-panel.css', 'theme-locales.js', 'builtin-theme-files.json'] + json.loads((ROOT / 'launcher/builtin-theme-files.json').read_text())
LAUNCHER_FILES.update(['appinfo.json'] + THEME_FILES)
ROOT_LAUNCHER_FILES = {
    'index.html', 'app.js', 'app-library.js', 'style.css', 'theme-defaults.css', 'theme-policy.js', 'theme-runtime.js', 'home-layout.js', 'layout-panel.js', 'settings-categories.js', 'layout-panel.css', 'config.js', 'apps.js',
    'fonts/outfit-300.ttf', 'fonts/outfit-400.ttf', 'fonts/outfit-500.ttf', 'fonts/outfit-700.ttf', 'fonts/NotoSans.ttf', 'fonts/NotoSans-OFL.txt', 'fonts/NotoSansDevanagari.ttf', 'fonts/NotoSansDevanagari-OFL.txt', 'fonts/NotoSansKR.ttf', 'fonts/NotoSansKR-OFL.txt', 'fonts/NotoSansSC.ttf', 'fonts/NotoSansSC-OFL.txt', 'fonts/NotoSansTC.ttf', 'fonts/NotoSansTC-OFL.txt', 'fonts/OFL.txt',
    'i18n.js', 'catalogs.js', 'i18n.css', 'root-locales.js', 'root-exit.js', 'root-firmware-control.js', 'root-firmware.js', 'root-audio.js', 'root-audio-locales.js', 'root-settings.js', 'root-settings.css',
    'root-profile-data.js', 'root-profile.js', 'release-notes.js', 'system-updates.js', 'root-updates.js',
}
# Legacy synthetic icons remain available for isolated bridge fixtures.
ICON_FILES = {path.name for path in (ROOT / 'preview/icons').glob('*.svg')}
REFERENCE_FILES = {'reference-apps/' + str(path.relative_to(ROOT / 'preview/reference-apps'))
                   for path in (ROOT / 'preview/reference-apps').rglob('*') if path.is_file()}


ROOT_LAUNCHER_FILES.update(['appinfo.json'] + THEME_FILES)


def inventory():
    data = json.loads((ROOT / 'preview/reference-apps/inventory.json').read_text(encoding='utf-8'))
    data['referenceApps'] = True
    return data


def preview_config(original):
    # Use the ordinary dock defaults, without replacing any saved user layout.
    dock = [app['id'] for app in inventory()['apps'][:5]]
    return original + ('\nwindow.CONFIG.dockApps = ' + json.dumps(dock) + ';\n').encode()


def revision():
    files = [ROOT / 'launcher' / name for name in sorted(LAUNCHER_FILES)]
    files += [ROOT / 'root-edition/preview.py']
    files += [ROOT / 'root-edition/ui' / name for name in ('root-locales.js', 'root-exit.js', 'root-firmware-control.js', 'root-firmware.js', 'root-audio.js', 'root-audio-locales.js', 'root-settings.js', 'root-settings.css', 'root-profile-data.js', 'root-profile.js', 'root-updates.js')]
    files += [ROOT / 'preview/index.html', ROOT / 'preview/bridge.js', ROOT / 'preview/live-reload.js', ROOT / 'preview/themes.js', ROOT / 'scripts/build-preview-themes.cjs']
    files += list((ROOT / 'showcase/registry').glob('*.json'))
    files += [ROOT / 'showcase/order.json']
    files += [ROOT / 'preview/icons' / name for name in sorted(ICON_FILES)]
    files += [ROOT / 'preview' / name for name in sorted(REFERENCE_FILES)]
    stamps = []
    for file in files:
        try:
            stat = file.stat()
            stamps.append((stat.st_mtime_ns, stat.st_size))
        except FileNotFoundError:
            stamps.append(None)
    return hashlib.sha256(json.dumps(stamps).encode()).hexdigest()


def launcher_html():
    return (ROOT / 'launcher/index.html').read_text().replace(
        '<head>', '<head>\n  <script src="../preview/bridge.js"></script>', 1)


def root_launcher():
    # Reuse the isolated Root UI staging, without any installer or runtime services.
    staged = runpy.run_path(str(ROOT / 'root-edition/preview.py'))['prepare'](json.loads((ROOT / 'launcher/appinfo.json').read_text())['version'])
    files = {name: staged[name] for name in ROOT_LAUNCHER_FILES}
    files['config.js'] = preview_config(files['config.js'])
    files['apps.js'] = ('window.TV_APPS = ' + json.dumps(inventory()) + ';\n').encode()
    files['index.html'] = files['index.html'].replace(
        b'<head>', b'<head>\n  <script src="../preview/bridge.js"></script>', 1)
    return files


def preview_html(live=True):
    script = ('<script src="preview/live-reload.js" data-version="' + revision() + '"></script>') if live else ''
    page = (ROOT / 'preview/index.html').read_text().replace('__LIVE_RELOAD__', script)
    return page if live else page.replace('live reload enabled', 'latest main build').replace('Home · Local Preview', 'Home · Preview')


def export_site(destination):
    destination = Path(destination)
    if (destination / 'themes').exists() or (destination / 'themes').is_symlink():
        raise ValueError('Use a fresh preview export directory; retired themes output must not be published.')
    destination.mkdir(parents=True, exist_ok=True)
    for name in sorted(LAUNCHER_FILES):
        target = destination / 'launcher' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == 'index.html':
            target.write_text(launcher_html(), encoding='utf-8')
        elif name == 'config.js':
            target.write_bytes(preview_config((ROOT / 'launcher' / name).read_bytes()))
        else:
            shutil.copyfile(ROOT / 'launcher' / name, target)
    (destination / 'launcher/apps.js').write_text('window.TV_APPS = ' + json.dumps(inventory()) + ';\n', encoding='utf-8')
    for name in ['bridge.js', 'themes.js', 'icons/SOURCES.txt', 'icons/LICENSE-LUCIDE.txt'] + ['icons/' + name for name in sorted(ICON_FILES)] + sorted(REFERENCE_FILES):
        target = destination / 'preview' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'preview' / name, target)
    for name, data in root_launcher().items():
        target = destination / 'root-launcher' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / 'preview/themes.json').write_bytes(preview_themes())
    (destination / 'index.html').write_text(preview_html(live=False), encoding='utf-8')
    (destination / '.nojekyll').touch()
    for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
        shutil.copyfile(ROOT / name, destination / name)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        file = None
        if path == '/preview/themes.json':
            self.respond(preview_themes(), 'application/json; charset=utf-8')
            return
        if path == '/preview/version':
            self.respond(revision().encode(), 'text/plain; charset=utf-8')
            return
        if path.startswith('/root-launcher/') and path[len('/root-launcher/'):] in ROOT_LAUNCHER_FILES:
            name = path[len('/root-launcher/'):]
            self.respond(root_launcher()[name], mimetypes.guess_type(name)[0] or 'application/octet-stream')
            return
        if path == '/':
            file = ROOT / 'preview/index.html'
        elif path in ('/preview/bridge.js', '/preview/themes.js', '/preview/live-reload.js', '/preview/settings.html', '/preview/update-overflow.html'):
            file = ROOT / path.lstrip('/')
        elif path.startswith('/preview/') and path[len('/preview/'):] in REFERENCE_FILES:
            file = ROOT / path.lstrip('/')
        elif path.startswith('/preview/icons/') and path[len('/preview/icons/'):] in ICON_FILES:
            file = ROOT / path.lstrip('/')
        elif path == '/launcher/config.js':
            self.respond(preview_config((ROOT / 'launcher/config.js').read_bytes()),
                         'text/javascript; charset=utf-8')
            return
        elif path == '/launcher/apps.js':
            self.respond(('window.TV_APPS = ' + json.dumps(inventory()) + ';\n').encode(),
                         'text/javascript; charset=utf-8')
            return
        elif path.startswith('/launcher/') and path[len('/launcher/'):] in LAUNCHER_FILES:
            file = ROOT / path.lstrip('/')
        if file is None:
            self.send_error(404)
            return
        try:
            body = file.read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        if path == '/':
            body = preview_html().encode('utf-8')
        if path == '/launcher/index.html':
            body = launcher_html().encode('utf-8')
        mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        self.respond(body, mime)

    def respond(self, body, mime):
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def log_request(self, code='-', size='-'):
        if urlsplit(self.path).path != '/preview/version':
            super().log_request(code, size)


def make_server(port):
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true', help='open preview in the default browser')
    parser.add_argument('--build', type=Path, metavar='DIRECTORY', help='export a static preview for GitHub Pages')
    args = parser.parse_args()
    if args.build:
        export_site(args.build)
        print(f'Static preview: {args.build}')
        return
    with make_server(args.port) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'Launcher preview: {url}\nStop: Ctrl+C', flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
