"""Exercise the two No-root Updater package entry points in a disposable checkout."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class UpdateUiPackageTests(unittest.TestCase):
    def test_updater_builders_share_public_app_and_service_files(self):
        from cytv.package import data_files

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('scripts/lib', 'launcher/fonts', 'root-edition/ui', 'docs'):
                (root/folder).mkdir(parents=True)
            tracked = subprocess.check_output(
                ['git', 'ls-files', '--', 'updater-app', 'updater-service', 'launcher/fonts/NotoSans*'],
                cwd=ROOT, text=True).splitlines()
            for name in tracked:
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, root/name)
            for name in ('package.json', 'release-versions.json', 'scripts/build-cytv.py',
                         'scripts/build-updater.sh', 'scripts/tv_web_build.py', 'scripts/chinese_fonts.py',
                         'scripts/compile-tv-web.cjs', 'scripts/helper_build.py', 'scripts/compile-helper.cjs',
                         'scripts/no_root_assets.py', 'scripts/update-permissions.cjs',
                         'scripts/lib/update-permissions.cjs', 'root-edition/ui/root-locales.js', 'docs/UPDATES.md'):
                shutil.copyfile(ROOT/name, root/name)
            for name in ('system-updates.js', 'release-notes.js', 'settings-panel.css', 'renewal-panel.css',
                         'i18n.js', 'i18n.css', 'catalogs.js', 'user-data.js'):
                shutil.copyfile(ROOT/'launcher'/name, root/'launcher'/name)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'add', '--', 'updater-app', 'updater-service'], cwd=root, check=True)

            (root/'updater-app/local-notes.txt').write_text('Local app notes\n')
            (root/'updater-app/local-draft.json').write_text('Unfinished local config\n')
            (root/'updater-app/local-config.json').write_text('{"note":"Local app configuration"}\n')
            (root/'updater-service/local-notes.txt').write_text('Local service notes\n')
            (root/'updater-service/local-config.json').write_text('{"note":"Local service configuration"}\n')
            (root/'launcher/fonts/NotoSans-local.txt').write_text('Local font notes\n')
            state = root/'updater-service/state'
            state.mkdir()
            (state/'profile.json').write_text('{}\n')

            packager = root/'packager'
            packager.write_text('#!/bin/sh\n'
                                'test "$1" = --no-minify && test -s "$2/settings-panel.css" && '
                                'test -s "$2/renewal-panel.css"\n')
            packager.chmod(0o755)
            env = dict(os.environ, ARES_PACKAGE=str(packager), NODE_PATH=str(ROOT/'node_modules'),
                       PYTHONPATH=str(ROOT), PYTHON=sys.executable)
            result = subprocess.run(['bash', 'scripts/build-updater.sh'], cwd=root, env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            for folder in ('updater-app', 'updater-service'):
                self.assertFalse((root/'build'/folder/'local-notes.txt').exists())
                self.assertFalse((root/'build'/folder/'local-config.json').exists())
            self.assertFalse((root/'build/updater-app/fonts/NotoSans-local.txt').exists())
            self.assertFalse((root/'build/updater-service/state').exists())

            result = subprocess.run([sys.executable, '-c',
                                    "from pathlib import Path; import runpy; "
                                    "runpy.run_path('scripts/build-cytv.py')['stage_updater'](Path('dist'))"],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            packaged = data_files((root/'dist/updater.ipk').read_bytes())
            for folder, prefix in (
                ('updater-app', 'usr/palm/applications/com.cleanyourtv.updater/'),
                ('updater-service', 'usr/palm/services/com.cleanyourtv.updater.service/'),
            ):
                stage = root/'build'/folder
                staged = {p.relative_to(stage).as_posix(): p.read_bytes() for p in stage.rglob('*') if p.is_file()}
                members = {n.removeprefix(prefix): b for n, b in packaged.items() if n.startswith(prefix)}
                self.assertEqual(staged.keys(), members.keys())
                for name, data in staged.items():
                    with self.subTest(folder=folder, name=name):
                        self.assertEqual(data, members[name])

            app = root/'build/updater-app'
            stylesheet = (app/'settings-panel.css').read_text()
            self.assertTrue((app/'system-updates.js').is_file())
            self.assertTrue((app/'release-notes.js').is_file())
            self.assertIn('#renewalPanel', stylesheet)
            self.assertNotRegex(stylesheet, r'\binset\s*:')
            self.assertTrue((app/'compat-polyfills.js').is_file())
            self.assertIn('compat-polyfills.js', (app/'index.html').read_text())
            for name in ('ca-bundle.crt', 'ca-LICENSE.txt', 'release-public.pem'):
                self.assertEqual((root/'build/updater-service'/name).read_bytes(),
                                 (root/'updater-service'/name).read_bytes())
            kit = root/'dist/updater-setup'
            self.assertEqual({p.relative_to(kit).as_posix() for p in kit.rglob('*') if p.is_file()},
                             {'README.md', 'scripts/update-permissions.cjs',
                              'scripts/lib/update-permissions.cjs', 'updater-service/permissions.js'})
