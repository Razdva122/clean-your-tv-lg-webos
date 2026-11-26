"""Offline Homebrew review and first-install source selection."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'root-edition'))
import deploy
from install_driver import reviewed_candidate


class HomebrewMigrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.home = self.root / 'usr/palm/applications/com.gathin.tvhome'
        self.profile = self.root / 'usr/palm/services/com.cleanyourtv.updater.service/state/profile.json'
        installed = patch.object(deploy, 'INSTALLED', self.root)
        installed.start()
        self.addCleanup(installed.stop)

    def packaged(self):
        self.home.mkdir(parents=True)
        (self.home / 'appinfo.json').write_text('{"id":"com.gathin.tvhome"}')
        (self.home / 'apps.js').write_text('window.TV_APPS = {apps:[],inputs:[]};')
        (self.home / 'config.js').write_text("window.CONFIG={columns:4,hiddenApps:['tile']};")

    def test_true_absence_is_distinct_from_incomplete_or_indirect_source(self):
        self.assertEqual(deploy.homebrew_migration(), (None, 'absent'))
        self.home.mkdir(parents=True)
        with self.assertRaises((OSError, ValueError)):
            deploy.homebrew_migration()
        self.home.rmdir()
        self.home.symlink_to(self.root / 'missing')
        with self.assertRaises((OSError, ValueError)):
            deploy.homebrew_migration()

    def test_packaged_prefs_are_data_and_receipt_follows_actual_bytes(self):
        self.packaged()
        prepared, before = deploy.homebrew_migration()
        self.assertIn(b'"tile"', prepared[0]['config.js'])
        (self.home / 'config.js').write_text('window.CONFIG={columns:3};')
        _, after = deploy.homebrew_migration()
        self.assertNotEqual(after, before)
        self.assertNotEqual(reviewed_candidate(self.root, {}, before), reviewed_candidate(self.root, {}, after))
        self.assertNotEqual(reviewed_candidate(self.root, {}), reviewed_candidate(self.root, {}, 'absent'))
        with self.assertRaises(ValueError):
            deploy.homebrew_migration(expected=before)
        (self.home / 'config.js').write_text('window.CONFIG={columns:3};run();')
        with self.assertRaises(ValueError):
            deploy.homebrew_migration()

    def test_valid_profile_has_priority_and_corruption_never_falls_back(self):
        self.packaged()
        self.profile.parent.mkdir(parents=True)
        data = dict(schema=1, inventory=dict(apps=[], inputs=[]), config=dict(columns=7, dockApps=[], hiddenApps=[]))
        self.profile.write_text(json.dumps(data))
        prepared, binding = deploy.homebrew_migration()
        self.assertIn('updater profile', prepared[1])
        self.assertEqual(len(binding), 64)
        self.profile.write_text('bad')
        with self.assertRaises(ValueError):
            deploy.homebrew_migration()
        self.profile.unlink()
        with self.assertRaises(ValueError):
            deploy.homebrew_migration(expected=binding)

    def inspect(self, state='fresh', *, homebrew=True):
        import install_driver
        import install_device
        from installation import Ownership
        args = ['driver', 'inspect', '--payload', str(self.root)]
        if homebrew:
            args.append('--homebrew-setup')
        stream = io.StringIO()
        with patch.object(sys, 'argv', args), patch.object(Ownership, 'status', return_value=None), \
                patch.object(install_driver.Coordinator, 'inspect', return_value={'state': state}), \
                patch.object(install_driver, '_verified_payload', return_value={}) as bundles, \
                patch.object(install_device.LocalDevice, 'log'), redirect_stdout(stream):
            install_driver.main()
        return json.loads(stream.getvalue()), bundles

    def test_fresh_inspection_selects_supervisor_and_reviewed_settings_only_for_homebrew(self):
        empty, bundles = self.inspect()
        self.assertIs(empty['installation']['migrate_available'], False)
        self.assertIs(bundles.call_args.args[1], True)
        self.packaged()
        found, bundles = self.inspect()
        self.assertIs(found['installation']['migrate_available'], True)
        self.assertNotEqual(empty['candidate_sha256'], found['candidate_sha256'])
        for state, homebrew in [('fresh',False), ('installed',True), ('recovery_required',True)]:
            result, bundles = self.inspect(state, homebrew=homebrew)
            self.assertNotIn('migrate_available', result['installation'])
            self.assertIs(bundles.call_args.args[1], False)

    def test_corrupt_fresh_source_disables_homebrew_setup_without_enumerating_files(self):
        self.packaged()
        (self.home / 'config.js').unlink()
        result, bundles = self.inspect()
        self.assertEqual(result['state'], 'recovery_required')
        self.assertNotIn('candidate_sha256', result)
        self.assertNotIn(str(self.root), json.dumps(result))
        bundles.assert_not_called()

    def test_foreign_app_metadata_at_fixed_home_path_is_rejected(self):
        self.packaged()
        (self.home / 'appinfo.json').write_text('{"id":"another.app"}')
        with self.assertRaises(ValueError):
            deploy.homebrew_migration()


if __name__ == '__main__':
    unittest.main()
