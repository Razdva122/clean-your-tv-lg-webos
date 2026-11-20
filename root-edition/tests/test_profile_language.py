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
        for locale in ('auto', 'pt-BR', 'cs', 'ro', 'zh-Hans', 'zh-Hant'):
            profile['settings']['tvhome.language'] = locale
            self.assertEqual(validate(profile)['settings']['tvhome.language'], locale)
        profile['settings']['tvhome.language'] = '<script>'
        with self.assertRaises(ValueError):
            validate(profile)
