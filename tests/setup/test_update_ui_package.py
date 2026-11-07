"""The independent recovery app must ship the stylesheet its HTML loads."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class UpdateUiPackageTests(unittest.TestCase):
    def test_standalone_recovery_build_includes_shared_dialog_styles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('scripts/lib', 'launcher/fonts', 'root-edition/ui', 'docs', 'updater-service'):
                (root/folder).mkdir(parents=True)
            shutil.copytree(ROOT/'updater-app', root/'updater-app')
            shutil.copy(ROOT/'scripts/build-updater.sh', root/'scripts/build-updater.sh')
            for name in ('tv_web_build.py', 'chinese_fonts.py', 'compile-tv-web.cjs', 'helper_build.py', 'compile-helper.cjs'):
                shutil.copy(ROOT/'scripts'/name, root/'scripts'/name)
            shutil.copy(ROOT/'package.json', root/'package.json')
            for name in ('system-updates.js', 'release-notes.js', 'renewal-panel.css', 'i18n.js', 'i18n.css', 'catalogs.js', 'user-data.js'):
                shutil.copy(ROOT/'launcher'/name, root/'launcher'/name)
            # The service is compiled for the TV's Node, so its script fixtures must parse.
            for name in ('service.js', 'permissions.js', 'services.json', 'release-public.pem', 'ca-bundle.crt', 'ca-LICENSE.txt'):
                (root/'updater-service'/name).write_text("'use strict';\n" if name.endswith('.js') else 'fixture')
            for name in ('scripts/update-permissions.cjs', 'scripts/lib/update-permissions.cjs',
                         'root-edition/ui/root-locales.js', 'launcher/fonts/NotoSans.ttf', 'docs/UPDATES.md'):
                (root/name).write_text('fixture')
            packager = root/'packager'
            packager.write_text('#!/bin/sh\ntest -s "$1/renewal-panel.css"\n')
            packager.chmod(0o755)
            result = subprocess.run(['bash', 'scripts/build-updater.sh'], cwd=root,
                                    env=dict(os.environ, ARES_PACKAGE=str(packager), NODE_PATH=str(ROOT/'node_modules')), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            stylesheet = (root/'build/updater-app/renewal-panel.css').read_text()
            self.assertTrue((root/'build/updater-app/system-updates.js').is_file())
            self.assertTrue((root/'build/updater-app/release-notes.js').is_file())
            self.assertIn('#renewalPanel', stylesheet)
            self.assertNotRegex(stylesheet, r'\binset\s*:')
            self.assertTrue((root/'build/updater-app/compat-polyfills.js').is_file())
            self.assertEqual((root/'build/updater-service/ca-bundle.crt').read_text(), 'fixture')
            self.assertEqual((root/'build/updater-service/ca-LICENSE.txt').read_text(), 'fixture')
            self.assertIn('compat-polyfills.js', (root/'build/updater-app/index.html').read_text())
