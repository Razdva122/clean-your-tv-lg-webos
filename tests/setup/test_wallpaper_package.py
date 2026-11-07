import runpy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILES = ['wallpaper.js', 'wallpaper.css', 'wallpaper-panel.js', 'wallpaper-panel.css', 'wallpaper-locales.js', 'wallpaper-media-cache.js', 'personal-wallpaper.js', 'wallpaper-qr.js', 'wallpaper-library.js', 'wallpaper-stream.js']

class WallpaperPackageTest(unittest.TestCase):
    def test_explicit_public_inventories_include_all_wallpaper_modules(self):
        preview = runpy.run_path(str(ROOT / 'scripts/preview.py'))
        root_preview = runpy.run_path(str(ROOT / 'root-edition/preview.py'))
        build = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))
        inventories = {
            'No-root browser preview': preview['LAUNCHER_FILES'],
            'Root browser preview': preview['ROOT_LAUNCHER_FILES'],
            'Root package sources': root_preview['FILES'],
            'No-root package sources': build['tracked_files']('launcher'),
        }
        for name, files in inventories.items():
            for asset in FILES:
                self.assertIn(asset, files, (name, asset))

    def test_bootstrap_and_trusted_media_csp(self):
        html = (ROOT / 'launcher/index.html').read_text()
        for asset in FILES:
            self.assertIn('"' + asset + '"', html)
        self.assertLess(html.index('src="wallpaper.js"'), html.index('src="theme-runtime.js"'))
        self.assertLess(html.index('src="wallpaper-media-cache.js"'), html.index('src="theme-manager.js"'))
        self.assertLess(html.index('src="wallpaper-panel.js"'), html.index('src="renewal-panel.js"'))
        self.assertIn("media-src 'self' blob: http://127.0.0.1:*", (ROOT / 'scripts/tv-dev.py').read_text())

    def test_legacy_root_restore_clears_theme_preferences(self):
        source = (ROOT / 'root-edition/ui/root-profile.js').read_text()
        self.assertIn("removeItem('tvhome.wallpaper.preferences.v1')", source)

if __name__ == '__main__':
    unittest.main()
