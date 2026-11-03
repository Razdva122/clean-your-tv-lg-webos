"""Author media guardrails; encoding/decode is exercised with the real themes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prepare_theme_wallpaper', ROOT / 'scripts/prepare-theme-wallpaper.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

@unittest.skipUnless(importlib.util.find_spec('imageio_ffmpeg'), 'author encoder is optional outside media preparation')
class PreparationTests(unittest.TestCase):
    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'existing'
            out.mkdir()
            (out / 'keep').write_text('accepted media')
            with self.assertRaisesRegex(ValueError, 'existing media'):
                MODULE.prepare(ROOT / 'themes/ribbon/assets/preview.jpg', out)
            self.assertEqual((out / 'keep').read_text(), 'accepted media')

    def test_thumbnail_cannot_be_upscaled_to_uhd(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'rejected'
            with self.assertRaisesRegex(ValueError, 'real pixels'):
                MODULE.prepare(ROOT / 'themes/ribbon/assets/preview.jpg', out)
            self.assertFalse(out.exists())

if __name__ == '__main__':
    unittest.main()
