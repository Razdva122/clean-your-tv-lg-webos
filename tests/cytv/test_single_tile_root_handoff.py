import unittest
from unittest.mock import Mock, patch

from cytv import package, single_tile_root
from cytv.errors import UserError


class RootHandoff(unittest.TestCase):
    def setUp(self):
        self.installer = Mock()
        self.installer.profile = {'edition': 'root'}
        self.installer.store.pending.return_value = None
        self.installer.installed_apps.return_value = [{'id': package.TILE_APP}]
        self.installer.remote.luna.return_value = {'returnValue': True}
        self.output = []
        self.ask = Mock(return_value='y')

    def handoff(self, non_interactive=False):
        return single_tile_root.handoff(self.installer, self.output.append, self.ask,
                                        non_interactive=non_interactive)

    def test_fresh_with_full_tile_continues_only_on_tv(self):
        with patch.object(single_tile_root, 'installed_role', return_value='homebrew') as role:
            self.assertEqual(self.handoff(), 0)
            role.assert_called_once_with(self.installer, require_tile_protocol=True)
            self.installer.remote.luna.assert_called_once_with(
                'com.webos.applicationManager/launch', {'id': package.TILE_APP})
            self.assertIn('Continue setup on the TV.', self.output)

    def test_missing_or_conflicting_install_never_launches(self):
        for apps in ([], [{'id': package.ROOT_APP}], [{'id': 'com.local.nativehome'}]):
            with self.subTest(apps=apps):
                self.installer.installed_apps.return_value = apps
                with self.assertRaises(UserError):
                    self.handoff()
                self.installer.remote.luna.assert_not_called()

    def test_light_tile_and_unattended_mode_do_not_launch(self):
        with patch.object(single_tile_root, 'installed_role', return_value='no-root') as role:
            with self.assertRaises(UserError):
                self.handoff()
            role.return_value = 'homebrew'
            self.assertEqual(self.handoff(non_interactive=True), 130)
            self.installer.remote.luna.assert_not_called()

    def test_legacy_root_erasure_and_handoff_have_separate_consent(self):
        self.installer.installed_apps.return_value += [
            {'id': package.ROOT_APP}, {'id': 'com.cleanyourtv.root.updater'}]
        self.installer.native_root_present.return_value = False
        self.installer.root_installation.return_value = {'state': 'installed', 'can_maintain': True}
        self.installer.uninstall_project.return_value = {'removed': True, 'verified_clean': True}
        with patch.object(single_tile_root, 'installed_role', return_value='homebrew'), \
                patch.object(single_tile_root.prompts, 'confirm', side_effect=[False, True, False]):
            self.assertEqual(self.handoff(), 130)
            self.installer.uninstall_project.assert_not_called()
            self.assertEqual(self.handoff(), 130)
            self.installer.uninstall_project.assert_called_once_with()
            self.installer.remote.luna.assert_not_called()
            self.assertIn('saved preferences will be removed', ' '.join(self.output))

    def test_legacy_with_incomplete_cleanup_cannot_launch_new_setup(self):
        self.installer.installed_apps.return_value += [
            {'id': package.ROOT_APP}, {'id': 'com.cleanyourtv.root.updater'}]
        self.installer.native_root_present.return_value = False
        self.installer.root_installation.return_value = {'state': 'installed', 'can_maintain': True}
        self.installer.uninstall_project.return_value = {'removed': True, 'verified_clean': False}
        with patch.object(single_tile_root, 'installed_role', return_value='homebrew'):
            with self.assertRaises(UserError):
                self.handoff()
            self.installer.remote.luna.assert_not_called()
