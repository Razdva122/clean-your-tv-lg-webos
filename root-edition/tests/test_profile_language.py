"""Language preferences survive strict Root update profile validation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from updater.profile import validate

class ProfileLanguageTests(unittest.TestCase):
    def test_language_is_validated_and_retained(self):
        profile = {'schema': 1, 'inventory': {'apps': [], 'inputs': []},
                   'config': {'columns': 5, 'dockApps': [], 'hiddenApps': []},
                   'settings': {'tvhome.language': 'cs'}}
        for locale in ('pt-BR', 'cs'):
            profile['settings']['tvhome.language'] = locale
            self.assertEqual(validate(profile)['settings']['tvhome.language'], locale)
        profile['settings']['tvhome.language'] = 'auto'
        self.assertEqual(validate(profile)['settings']['tvhome.language'], 'auto')
        profile['settings']['tvhome.language'] = '<script>'
        with self.assertRaises(ValueError):
            validate(profile)


class ProfileNameTests(unittest.TestCase):
    def test_optional_name_survives_and_old_profile_remains_valid(self):
        profile = {'schema': 1, 'inventory': {'apps': [], 'inputs': []},
                   'config': {'columns': 5, 'dockApps': [], 'hiddenApps': []},
                   'settings': {}}
        self.assertNotIn('tvhome.name', validate(profile)['settings'])
        for name in ('Aashiyaan', 'आशियाना', '🏠' * 48):
            profile['settings']['tvhome.name'] = name
            self.assertEqual(validate(profile)['settings']['tvhome.name'], name)
        for name in ('x' * 49, 'bad\nname', ''):
            profile['settings']['tvhome.name'] = name
            with self.assertRaises(ValueError):
                validate(profile)
