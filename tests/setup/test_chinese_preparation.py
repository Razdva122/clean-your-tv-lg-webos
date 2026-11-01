"""Automatic font preparation follows runtime translations, never edits sources."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import chinese_fonts as fonts

ROOT = Path(__file__).resolve().parents[2]

class PreparationTests(unittest.TestCase):
    def test_collector_decodes_scripts_and_ignores_other_locales(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'launcher').mkdir()
            (root/'launcher/theme-locales.js').write_text('HomeI18n.add({"zh-Hans":{"x":`\\u5f62力`},"zh-Hant":{"x":"氣"},"en":{"x":"龘"}});')
            chars=fonts.required_characters(root)
            self.assertTrue({ord(c) for c in '形力'} <= chars['SC'])
            self.assertIn(ord('氣'), chars['TC'])
            self.assertNotIn(ord('龘'), chars['SC'])
            self.assertNotIn(ord('氣'), chars['SC'])

    def test_current_catalogs_prepare_small_static_fonts_without_source_changes(self):
        before={s: (ROOT/f'launcher/fonts/NotoSans{s}.ttf').read_bytes() for s in fonts.SCRIPTS}
        prepared=fonts.prepare_fonts()
        required=fonts.required_characters()
        for s in fonts.SCRIPTS:
            raw=prepared[f'fonts/NotoSans{s}.ttf']
            self.assertLess(len(raw), 1024*1024)
            self.assertTrue(required[s] <= fonts.coverage(raw))
            self.assertTrue(fonts.static_regular(raw))
            self.assertEqual((ROOT/f'launcher/fonts/NotoSans{s}.ttf').read_bytes(),before[s])

    def test_new_glyph_offline_determinism_and_corrupt_cache_refusal(self):
        # Seed verified source bytes through the normal content-pinned source path once.
        originals={s:fonts.source_font(s,fonts.default_cache()) for s in fonts.SCRIPTS}
        required={s:fonts.required_characters()[s] | {ord(c) for c in '形力'} for s in fonts.SCRIPTS}
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)
            for s,raw in originals.items():
                target=cache/'sources'/fonts.SOURCES[s]['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            with patch.object(fonts,'required_characters',return_value=required),patch.object(fonts.urllib.request,'urlopen',side_effect=AssertionError('offline')):
                first=fonts.prepare_fonts(cache=cache)
                for record in (cache/'subsets').glob('*.json'):record.unlink()
                second=fonts.prepare_fonts(cache=cache)
                self.assertEqual(first,second)
                for s in fonts.SCRIPTS:self.assertTrue(required[s] <= fonts.coverage(first[f'fonts/NotoSans{s}.ttf']))
                records=list((cache/'subsets').glob('*.json'));self.assertTrue(records)
                record=json.loads(records[0].read_text());record['sha256']='0'*64;records[0].write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'cache'):fonts.prepare_fonts(cache=cache)
            source=cache/'sources'/fonts.SOURCES['SC']['sha256'];source.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'source'):fonts.source_font('SC',cache)

    def test_covered_retained_fonts_need_no_source_download(self):
        required={s:{ord('中')} for s in fonts.SCRIPTS}
        with patch.object(fonts,'required_characters',return_value=required),patch.object(fonts,'source_font',side_effect=AssertionError('retained coverage')):
            for name,raw in fonts.prepare_fonts().items():self.assertEqual(raw,(ROOT/'launcher'/name).read_bytes())

    def test_runtime_catalog_new_glyph_is_prepared_without_editing_font(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'launcher/fonts').mkdir(parents=True)
            for script in fonts.SCRIPTS:
                source=ROOT/f'launcher/fonts/NotoSans{script}.ttf'
                (root/f'launcher/fonts/NotoSans{script}.ttf').write_bytes(source.read_bytes())
            (root/'launcher/catalogs.js').write_text('HomeI18n.add({"zh-Hans":{"x":"形力"},"zh-Hant":{"x":"形力"}});')
            self.assertTrue(any(not {ord(c) for c in '形力'} <= fonts.coverage((root/f'launcher/fonts/NotoSans{s}.ttf').read_bytes()) for s in fonts.SCRIPTS),'fixture must reproduce missing retained glyphs')
            prepared=fonts.prepare_fonts(root=root,cache=fonts.default_cache())
            for s in fonts.SCRIPTS:
                self.assertTrue({ord(c) for c in '形力'} <= fonts.coverage(prepared[f'fonts/NotoSans{s}.ttf']))
                self.assertEqual((root/f'launcher/fonts/NotoSans{s}.ttf').read_bytes(),(ROOT/f'launcher/fonts/NotoSans{s}.ttf').read_bytes())

    def test_unsupported_source_glyph_fails_instead_of_silent_subsetting(self):
        required=fonts.required_characters();required['SC'].add(0x323AF)
        with patch.object(fonts,'required_characters',return_value=required),self.assertRaisesRegex(ValueError,'source font lacks.*U\\+323AF'):
            fonts.prepare_fonts()

    def test_compiler_collects_new_locale_module_without_source_list_changes(self):
        from fontTools.ttLib import TTFont
        from scripts.tv_web_build import compile_web
        import io
        full=[set(TTFont(io.BytesIO(fonts.source_font(s,fonts.default_cache()))).getBestCmap()) for s in fonts.SCRIPTS]
        known=set.union(*fonts.required_characters().values())
        retained=set.union(*(fonts.coverage((ROOT/f'launcher/fonts/NotoSans{s}.ttf').read_bytes()) for s in fonts.SCRIPTS))
        code=min(c for c in (full[0]&full[1])-known-retained if 0x4E00 <= c <= 0x9FFF)
        files={f'fonts/NotoSans{s}.ttf':(ROOT/f'launcher/fonts/NotoSans{s}.ttf').read_bytes() for s in fonts.SCRIPTS}
        self.assertTrue(any(code not in fonts.coverage(raw) for raw in files.values()))
        files['new-runtime-module.js']=('HomeI18n.add('+json.dumps({locale:{'new':chr(code)} for locale in fonts.SCRIPTS.values()})+');').encode()
        prepared=compile_web(files)
        for s in fonts.SCRIPTS:self.assertIn(code,fonts.coverage(prepared[f'fonts/NotoSans{s}.ttf']))
