"""Run with: python3 -m unittest discover -s tests -p test_preview.py"""
import base64
import hashlib
import struct
import importlib.util
from html.parser import HTMLParser
import json
from pathlib import Path
import threading
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]


class PreviewTest(unittest.TestCase):
    def test_reference_inventory_preserves_native_metadata_and_original_png_bytes(self):
        spec = importlib.util.spec_from_file_location('preview', ROOT / 'scripts/preview.py')
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        data = preview.inventory()
        metadata = json.loads((ROOT / 'preview/reference-apps/metadata.json').read_text())
        expected_ids = ['netflix', 'youtube.leanback.v4', 'com.apple.appletv',
                        'com.apple.applemusic', 'tv.twitch.tv.starshot.lg',
                        'com.emby.app', 'cdp-30', 'org.jellyfin.webos',
                        'mgg4.5.channelplus', 'com.webos.app.browser']
        self.assertTrue(data['referenceApps'])
        self.assertEqual([app['id'] for app in data['apps']], expected_ids)
        self.assertEqual([app['id'] for app in metadata['apps']], expected_ids)
        for app, reference in zip(data['apps'], metadata['apps']):
            self.assertEqual(app['title'], reference['title'])
            self.assertEqual(app['iconColor'], reference['iconColor'])
            icon = reference['icon']
            encoded = app['icon'].removeprefix('data:image/png;base64,')
            original = (ROOT / 'preview/reference-apps' / icon['path']).read_bytes()
            self.assertEqual(base64.b64decode(encoded, validate=True), original)
            self.assertEqual(len(original), icon['size'])
            self.assertEqual(hashlib.sha256(original).hexdigest(), icon['sha256'])
            self.assertEqual(original[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', original[16:24]), (icon['width'], icon['height']))

    def test_static_export_works_under_a_github_pages_project_path(self):
        spec = importlib.util.spec_from_file_location('preview', ROOT / 'scripts/preview.py')
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        self.assertTrue(hasattr(preview, 'export_site'), 'static Pages export is missing')

        class Resources(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urls = []

            def handle_starttag(self, tag, attrs):
                for key, value in attrs:
                    if key in ('src', 'href') and not value.startswith('data:'):
                        self.urls.append(value)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'clean-your-tv-lg-webos'
            preview.export_site(output)
            for page in ['index.html', 'launcher/index.html', 'root-launcher/index.html']:
                resources = Resources()
                resources.feed((output / page).read_text())
                self.assertTrue(resources.urls)
                for resource in resources.urls:
                    url = urljoin('/clean-your-tv-lg-webos/' + page, resource)
                    self.assertTrue(url.startswith('/clean-your-tv-lg-webos/'), url)
                    self.assertTrue((Path(directory) / url.lstrip('/')).is_file(), url)
            apps = json.loads((output / 'launcher/apps.js').read_text().removeprefix('window.TV_APPS = ').rstrip(';\n'))
            self.assertEqual(apps, preview.inventory())
            for file in (ROOT / 'preview/reference-apps').rglob('*'):
                if file.is_file():
                    self.assertEqual((output / file.relative_to(ROOT)).read_bytes(), file.read_bytes())
            for edition in ('launcher', 'root-launcher'):
                config = (output / edition / 'config.js').read_text()
                self.assertIn('window.CONFIG = ', config)
                self.assertIn('window.CONFIG.dockApps = ' + json.dumps([app['id'] for app in apps['apps'][:5]]) + ';', config)
            root_apps = json.loads((output / 'root-launcher/apps.js').read_text().removeprefix('window.TV_APPS = ').rstrip(';\n'))
            self.assertEqual(root_apps, apps)
            for edition in ('launcher', 'root-launcher'):
                for weight in (300, 400, 500, 700):
                    self.assertEqual((output / edition / ('fonts/outfit-%s.ttf' % weight)).read_bytes(),
                                     (ROOT / ('launcher/fonts/outfit-%s.ttf' % weight)).read_bytes())
            self.assertTrue((output / 'root-launcher/root-settings.js').is_file())
            self.assertFalse((output / 'root-launcher/native-bootstrap.js').exists())
            self.assertFalse((output / 'root-launcher/renewal-panel.js').exists())
            self.assertFalse((output / '.lgtv-key.json').exists())
            self.assertFalse((output / 'scripts').exists())
            self.assertFalse((output / 'themes').exists())
            self.assertNotIn('themes/index.html', (output / 'index.html').read_text())
            self.assertNotIn('__THEME_SHOWCASE_LINK__', (output / 'index.html').read_text())
            themes = json.loads((output / 'preview/themes.json').read_bytes())
            catalog = (ROOT / 'launcher/theme-catalog.json').read_bytes()
            self.assertEqual(themes['themes'], json.loads(catalog)['themes'])
            self.assertTrue(themes['packages'], 'inline preview retains reviewed theme packages')
            for edition in ('launcher', 'root-launcher'):
                self.assertEqual((output / edition / 'theme-catalog.json').read_bytes(), catalog)

    def test_static_export_refuses_retired_catalog_output_without_deleting_it(self):
        spec = importlib.util.spec_from_file_location('preview', ROOT / 'scripts/preview.py')
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            retired = output / 'themes'
            retired.mkdir(parents=True)
            (retired / 'index.html').write_text('existing output must not be deleted')
            with self.assertRaisesRegex(ValueError, 'fresh'):
                preview.export_site(output)
            self.assertEqual((retired / 'index.html').read_text(), 'existing output must not be deleted')
            self.assertFalse((output / 'index.html').exists())
            linked = Path(directory) / 'linked-site'
            linked.mkdir()
            (linked / 'themes').symlink_to(retired, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'fresh'):
                preview.export_site(linked)
            self.assertTrue((linked / 'themes').is_symlink())

    def test_retired_showcase_flag_cannot_publish_a_separate_catalog(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/preview.py'), '--build', str(output), '--showcase'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_preview_serves_launcher_without_exposing_workspace(self):
        script = ROOT / 'scripts/preview.py'
        self.assertTrue(script.is_file(), 'local preview server is not implemented')
        spec = importlib.util.spec_from_file_location('preview', script)
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        server = preview.make_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        try:
            def get(path):
                with urlopen(base + path) as response:
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    return response.read().decode()

            self.assertIn('launcher/index.html', get('/'))
            root = get('/root-launcher/index.html')
            self.assertIn('root-settings.js', root)
            self.assertNotIn('native-bootstrap.js', root)
            self.assertNotIn('profile-bootstrap.js', root)
            self.assertEqual(json.loads(get('/root-launcher/apps.js').removeprefix('window.TV_APPS = ').rstrip(';\n'))['apps'][0]['id'], 'netflix')
            page = get('/launcher/index.html')
            self.assertLess(page.index('/preview/bridge.js'), page.index('profile-bootstrap.js'))
            self.assertEqual(get('/launcher/style.css'), (ROOT / 'launcher/style.css').read_text())
            apps = json.loads(get('/launcher/apps.js').removeprefix('window.TV_APPS = ').rstrip(';\n'))
            self.assertTrue(apps['referenceApps'])
            self.assertEqual(len(apps['apps']), 10)
            for app in apps['apps']:
                self.assertTrue(app['icon'].startswith('data:image/png;base64,'))
            with urlopen(base + '/preview/reference-apps/icons/youtube.png') as response:
                self.assertEqual(response.headers['Content-Type'], 'image/png')
                self.assertEqual(response.read(), (ROOT / 'preview/reference-apps/icons/youtube.png').read_bytes())
            # A saved source must change the version; unchanged sources must not.
            with tempfile.TemporaryDirectory() as directory, patch.object(preview, 'ROOT', Path(directory)):
                style = Path(directory) / 'launcher/style.css'
                style.parent.mkdir()
                style.write_text('body { color: white; }')
                before = get('/preview/version')
                self.assertEqual(get('/preview/version'), before)
                style.write_text('body { color: black; background: white; }')
                self.assertNotEqual(get('/preview/version'), before)
                root_profile = Path(directory) / 'root-edition/ui/root-profile.js'
                root_profile.parent.mkdir(parents=True)
                before_profile = get('/preview/version')
                root_profile.write_text('/* changed Root bootstrap */')
                self.assertNotEqual(get('/preview/version'), before_profile)
                reference = Path(directory) / 'preview/reference-apps/inventory.json'
                reference.parent.mkdir(parents=True)
                before_reference = get('/preview/version')
                reference.write_text('{\"apps\": []}')
                self.assertNotEqual(get('/preview/version'), before_reference)
            for path in ['/README.md', '/.lgtv-key.json', '/launcher/../config.js',
                         '/launcher/%2e%2e/.env', '/launcher/icons/private.png', '/scripts/build.sh',
                         '/preview/icons/%2e%2e/bridge.js', '/preview/icons/private.png',
                         '/preview/reference-apps/%2e%2e/bridge.js', '/preview/reference-apps/icons/private.png']:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
                error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
