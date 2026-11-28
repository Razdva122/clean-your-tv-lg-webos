"""Check the source assembly before compiling the private single-package Home."""
import json
from pathlib import Path
import re
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
build = runpy.run_path(str(ROOT / 'single-home/build.py'))
sources = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))['tracked_files']


class ProductHome(unittest.TestCase):
    def test_product_entry_and_offline_theme_assets(self):
        app = build['product_app'](sources)
        manifest = json.loads(app['appinfo.json'])
        product = json.loads((ROOT / 'launcher/appinfo.json').read_bytes())
        self.assertEqual(manifest['themeEngineVersion'], product.get('themeEngineVersion', product['version']))
        self.assertEqual(manifest['id'], build['APP'])
        self.assertIn(b'id="homeSurface"', app[manifest['main']])
        self.assertIn(b'id="pairArea"', app['setup/index.html'])
        for name in ('app.js', 'style.css', 'theme-panel.js', 'theme-manager.js', 'layout-panel.js',
                     'builtin-themes.json', *json.loads((ROOT / 'launcher/builtin-theme-files.json').read_bytes())):
            self.assertEqual(app[name], (ROOT / 'launcher' / name).read_bytes(), name)
        for ref in re.findall(rb'(?:href|src)="([^"]+\.(?:css|js))"', app[manifest['main']]):
            self.assertIn(ref.decode(), app)
        for name in ('native-bootstrap.js', 'helper-control.js', 'theme-receiver.js', 'system-updates.js'):
            self.assertNotIn(name, app)
        self.assertNotIn(b'com.gathin.tvhome.renewal', app['profile-bootstrap.js'])


if __name__ == '__main__':
    unittest.main()
