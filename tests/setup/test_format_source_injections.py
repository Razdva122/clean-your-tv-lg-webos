"""Build-time source injections must survive formatting without missing silently."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]


class PageAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.local = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        url = attrs.get('src') if tag == 'script' else None
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            url = attrs.get('href')
        if url:
            parts = urlsplit(url)
            if not parts.scheme and not parts.netloc and parts.path:
                self.local.append(unquote(parts.path))


class FormattedSourceInjectionTests(unittest.TestCase):
    def test_root_updater_bundles_the_private_cleanup_program(self):
        from cytv.no_root_cleanup import PRIVATE_CLEANUP_PROGRAM
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve() / 'bundle'
            subprocess.run([sys.executable, str(ROOT / 'root-edition/build_updater.py'),
                            '--output', str(output)], cwd=ROOT, check=True, capture_output=True)
            literal = ('var privateCleanupSource=' + json.dumps(PRIVATE_CLEANUP_PROGRAM) + ';').encode()
            self.assertEqual((output / 'cleanup_tail.js').read_bytes().count(literal), 1)
            self.assertEqual((output / 'cleanup_no_root_private.js').read_text(), PRIVATE_CLEANUP_PROGRAM)

    def test_root_lab_rewrites_the_whole_formatted_policy(self):
        transform = runpy.run_path(str(ROOT / 'scripts/build-root-update-lab.py'))['transform']
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            fetch = source / 'root-edition/updater/fetch.js'
            fetch.parent.mkdir(parents=True)
            fetch.write_bytes((ROOT / 'root-edition/updater/fetch.js').read_bytes())
            (source / 'root-edition/update_manifest.py').write_text(
                (ROOT / 'root-edition/update_manifest.py').read_text())
            transform(source)
            subprocess.run(['node', '--check', str(fetch)], check=True, capture_output=True)
            subprocess.run(['node', '-e', """
const assert = require('node:assert/strict');
const fetch = require(process.argv[1]);
assert(fetch.allowed('http://127.0.0.1:18997/releases/latest/download/root-update.json'));
assert(fetch.allowed('http://127.0.0.1:18997/releases/download/v0.1.1/com.cleanyourtv.root.updatetest_0.1.1_all.ipk'));
for (const url of ['https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/root-update.json',
  'http://127.0.0.1:18997/unrelated', 'http://127.0.0.1:18998/releases/latest/download/root-update.json',
  'http://127.0.0.1:18997/releases/latest/download/root-update.json?unexpected=1']) assert(!fetch.allowed(url), url);
""", str(fetch)], check=True, capture_output=True)
            text = fetch.read_text()
            self.assertIn("http=require('http')", text)
            self.assertIn('req=http.get(', text)

    def test_no_root_lab_rewrites_formatted_services_without_real_activity(self):
        run = subprocess.run
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            for directory in ('launcher', 'renewal-service', 'updater-app', 'updater-service',
                              'theme-receiver'):
                shutil.copytree(ROOT / directory, source / directory,
                                ignore=shutil.ignore_patterns('state', 'node_modules'))
            for name in ('scripts/build-update-lab.py', 'scripts/no_root_assets.py',
                         'scripts/theme_receiver.py', 'scripts/update-permissions.cjs',
                         'scripts/lib/update-permissions.cjs', 'docs/UPDATES.md',
                         'root-edition/ui/root-locales.js', 'native/app/state-permissions.js',
                         'native/app/contract-events.js', 'screensaver/settings.js'):
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())

            def package_or_run(args, **kwargs):
                if args[0] != 'fixture-ares-package':
                    return run(args, **kwargs)
                info = json.loads((Path(args[1]) / 'appinfo.json').read_text())
                package = Path(args[args.index('-o') + 1]) / (info['id'] + '_' + info['version'] + '_all.ipk')
                package.write_bytes(b'isolated package fixture')
                return subprocess.CompletedProcess(args, 0)

            with (patch.dict(os.environ, ARES_PACKAGE='fixture-ares-package'),
                  patch('subprocess.run', package_or_run), patch.object(sys, 'path', sys.path.copy()),
                  patch.dict(sys.modules)):
                for name in ('scripts', 'scripts.no_root_assets', 'scripts.theme_receiver'):
                    sys.modules.pop(name, None)
                runpy.run_path(str(source / 'scripts/build-update-lab.py'))
                self.assertEqual(Path(sys.modules['scripts.no_root_assets'].__file__).resolve(),
                                 (source / 'scripts/no_root_assets.py').resolve())
            stage = source / 'build/update-lab'
            renewal = stage / 'renewal/service.js'
            updater = stage / 'service/service.js'
            for name in ('updater', 'home-1.2.0', 'home-1.2.1'):
                with self.subTest(app=name):
                    app = stage / name
                    assets = PageAssets()
                    assets.feed((app / 'index.html').read_text())
                    self.assertTrue(assets.local)
                    self.assertEqual([url for url in assets.local if not (app / url).is_file()], [])
                    self.assertNotIn('system-updates.js', assets.local)
            upstream_assets = PageAssets()
            upstream_assets.feed((ROOT / 'updater-app/index.html').read_text())
            self.assertEqual([url for url in upstream_assets.local
                              if not (stage / 'updater' / url).is_file()], [])
            recovery = run(['node', str(ROOT / 'tests/updates/recovery-ui.cjs'),
                            str(stage / 'updater/app.js'), 'com.cleanyourtv.updaterlab.service'],
                           capture_output=True, text=True)
            self.assertEqual(recovery.returncode, 0, recovery.stdout + recovery.stderr)
            for name, exported in (('renewal/theme-receiver.js', 'activityHold'),
                                   ('renewal/state-permissions.js', 'atomicRecord'),
                                   ('service/user-data.js', 'validate')):
                with self.subTest(module=name):
                    result = run(['node', '-e', """
const assert = require('node:assert/strict');
assert.equal(typeof require(process.argv[1])[process.argv[2]], 'function');
""", str(stage / name), exported], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
            for name, expected in (('updater/appinfo.json', 'com.cleanyourtv.updaterlab'),
                                   ('service/services.json', 'com.cleanyourtv.updaterlab.service'),
                                   ('home-1.2.0/appinfo.json', 'com.cleanyourtv.updatetest'),
                                   ('home-1.2.1/appinfo.json', 'com.cleanyourtv.updatetest'),
                                   ('renewal/services.json', 'com.cleanyourtv.updatetest.renewal')):
                self.assertEqual(json.loads((stage / name).read_text())['id'], expected)
            for script in (renewal, updater):
                run(['node', '--check', str(script)], check=True, capture_output=True)
            self.assertNotIn('com.palm.activitymanager/', renewal.read_text())
            self.assertNotIn('return worker.run()', renewal.read_text())
            self.assertIn("helper:'0.6.13'", updater.read_text())
            self.assertIn("fs.readFileSync(__dirname+'/update.json','utf8')", updater.read_text())


if __name__ == '__main__':
    unittest.main()
