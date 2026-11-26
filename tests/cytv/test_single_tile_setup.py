"""Consent and readback boundaries of the A to B clean-install alternative."""
import unittest
from unittest.mock import Mock, patch

from cytv import single_tile_setup
from cytv.errors import UserError


class SingleTileSetup(unittest.TestCase):
    def setUp(self):
        self.installer = Mock()
        self.source = {'com.local.nativehome': '0.11.0', 'com.gathin.tvhome': '1.22.0'}
        self.installer.single_tile_source.return_value = self.source
        self.installer.uninstall_project.return_value = {'removed': True, 'verified_clean': True}
        self.output = []
        self.ask = Mock()

    def select(self, *, unattended=False):
        return single_tile_setup.select_source(self.installer, self.output.append,
                                               self.ask, non_interactive=unattended)

    def test_declining_keeps_existing_installation(self):
        with patch.object(single_tile_setup.prompts, 'confirm', return_value=False) as confirm:
            self.assertFalse(self.select())
        self.assertIn('personal wallpapers', self.output[0])
        self.assertIs(confirm.call_args.kwargs['default'], False)
        self.installer.uninstall_project.assert_not_called()

    def test_unattended_install_never_confirms_erasure(self):
        self.assertFalse(self.select(unattended=True))
        self.ask.assert_not_called()
        self.installer.uninstall_project.assert_not_called()

    def test_changed_source_stops_before_clean_removal(self):
        self.installer.single_tile_source.side_effect = (self.source, {})
        with patch.object(single_tile_setup.prompts, 'confirm', return_value=True):
            with self.assertRaises(UserError):
                self.select()
        self.installer.uninstall_project.assert_not_called()

    def test_verified_removal_is_separate_from_new_installation(self):
        with patch.object(single_tile_setup.prompts, 'confirm', side_effect=[True, False]) as confirm:
            self.assertFalse(self.select())
        self.assertEqual(confirm.call_count, 2)
        self.installer.uninstall_project.assert_called_once_with()
        self.installer.require_fresh_single_tile.assert_called_once_with()

    def test_unfinished_removal_stops_before_fresh_confirmation(self):
        self.installer.uninstall_project.return_value = {'restart_required': True}
        with patch.object(single_tile_setup.prompts, 'confirm', return_value=True) as confirm:
            with self.assertRaises(UserError):
                self.select()
        self.assertEqual(confirm.call_count, 1)
        self.installer.require_fresh_single_tile.assert_not_called()
