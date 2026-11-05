"""The existing Home package remains one opaque CARD at both resolutions."""
import json
import runpy
import unittest
from pathlib import Path
from cytv import package

ROOT = Path(__file__).resolve().parents[2]


class NoRootCardPackageTests(unittest.TestCase):
    def test_real_home_packages_keep_identity_and_persistent_card_runtime(self):
        builder = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))
        home = builder['tracked_files']('launcher')
        renewal = builder['tracked_files']('renewal-service')
        for resolution in ('1920x1080', '1280x720'):
            with self.subTest(resolution=resolution):
                app = dict(home)
                info = json.loads(app['appinfo.json'])
                info['resolution'] = resolution
                app['appinfo.json'] = json.dumps(info).encode()
                files = package.data_files(builder['pack_app'](app, renewal))
                prefix = 'usr/palm/applications/com.gathin.tvhome/'
                installed = json.loads(files[prefix + 'appinfo.json'])
                self.assertEqual(installed['id'], 'com.gathin.tvhome')
                self.assertEqual(installed['resolution'], resolution)
                self.assertEqual(installed['defaultWindowType'], 'card')
                self.assertIs(installed['transparent'], False)
                self.assertNotIn('handlesRelaunch', installed)
                self.assertIs(installed['noSplashOnLaunch'], True)
                self.assertIs(installed['spinnerOnLaunch'], False)
                self.assertEqual(installed['requiredACG'], ['application.launcher', 'network.query'])
                self.assertEqual(installed['systemUpdateProtocol'], 1)
                self.assertNotIn(b'presentationContext', files[prefix + 'app.js'])
                self.assertNotIn(b'home-presentation.js', files[prefix + 'index.html'])
                envelope = json.loads(files['usr/palm/packages/com.gathin.tvhome/packageinfo.json'])
                self.assertEqual(envelope['app'], 'com.gathin.tvhome')
                self.assertEqual(envelope['services'], ['com.gathin.tvhome.renewal'])
                self.assertEqual(envelope['version'], installed['version'])
