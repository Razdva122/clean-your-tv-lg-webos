"""Chinese UI must carry usable glyphs in the actual TV packages."""
import runpy
import struct
import json
import unittest
from pathlib import Path
from test_tv_fonts import tables
from cytv import package
from scripts.tv_web_build import compile_web

ROOT = Path(__file__).resolve().parents[2]


from scripts.chinese_fonts import coverage as cmap, required_characters


class ChineseFontTests(unittest.TestCase):
    def check_fonts(self, files):
        required_by_script = required_characters()
        for name in ('SC', 'TC'):
            required = required_by_script[name]
            data = files['fonts/NotoSans%s.ttf' % name]
            self.assertNotIn(b'fvar', tables(data), 'old TV engines need static fonts')
            self.assertEqual(struct.unpack_from('>H', tables(data)[b'OS/2'], 4)[0], 400)
            self.assertFalse(required - cmap(data), 'prepared Chinese font must cover all runtime translations')
            self.assertTrue({ord(c) for c in ('简体中文週' if name == 'SC' else '繁體中文週')} <= cmap(data), 'known runtime regression glyphs must survive independently of the collector')
            self.assertIn('fonts/NotoSans%s-OFL.txt' % name, files)

    def test_no_root_packaged_chinese_glyphs(self):
        builder = runpy.run_path(str(ROOT / 'scripts/build-cytv.py'))
        raw = builder['pack_app'](builder['tracked_files']('launcher'), builder['tracked_files']('renewal-service'))
        prefix = 'usr/palm/applications/com.gathin.tvhome/'
        self.check_fonts({name[len(prefix):]: data for name, data in package.data_files(raw).items() if name.startswith(prefix)})

    def test_root_packaged_chinese_glyphs(self):
        prepare = runpy.run_path(str(ROOT / 'root-edition/preview.py'))['prepare']
        self.check_fonts(compile_web(prepare()))
