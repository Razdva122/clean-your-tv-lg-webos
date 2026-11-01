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
        with self.assertRaisesRegex(ValueError,'source font lacks.*U\\+323AF'):
            fonts.prepare_fonts(files={'literal.js':('window.label='+json.dumps(chr(0x323AF))+';').encode()})

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

    def test_unscoped_static_compiler_inputs_are_decoded(self):
        inputs={
            'widget.js':b'window.title="\\u9f98"; window.hint=`\\u529b`;',
            'widget.json':b'{"title":"\\u5f62","id":"\\u9f98","en":{"foreign":"\\u9fa0"}}',
            'widget.html':b'<div title="&#x9f98;">&#x5f62;</div><script>window.caption="\\u529b";</script>',
            'widget.css':b'.label::before{content:"\\9f98 ";}',
        }
        for name,raw in inputs.items():
            with self.subTest(name=name):
                chars=fonts.required_characters(files={name:raw})
                wanted={'widget.js':'龘力','widget.json':'形龘','widget.html':'形龘力','widget.css':'龘'}[name]
                for script in fonts.SCRIPTS:self.assertTrue({ord(c) for c in wanted} <= chars[script])
        scoped=fonts.required_characters(files={'widget.js':b'const choices=[{code:"zh-Hans",name:"\\u7b80"}];const messages={en:{title:"\\u9fa0"}};'})
        self.assertNotIn(ord('简'),scoped['TC'])
        for script in fonts.SCRIPTS:self.assertNotIn(ord('龠'),scoped[script])

    def test_mixed_script_titles_and_scoped_brands_use_declared_cascade(self):
        from scripts.tv_web_build import compile_web
        files={f'fonts/NotoSans{s}.ttf':(ROOT/f'launcher/fonts/NotoSans{s}.ttf').read_bytes() for s in fonts.SCRIPTS}
        files.update({'community.json':json.dumps({'title':'简约'}).encode(),
                      'brand.js':b'HomeI18n.add({"zh-Hant":{"brand":"\\u7b80\\u4e66"}});'})
        prepared=compile_web(files)
        combined=set.union(*(fonts.coverage(prepared[f'fonts/NotoSans{s}.ttf']) for s in fonts.SCRIPTS))
        self.assertTrue({ord(c) for c in '简约书'} <= combined)
        self.assertIn(ord('简'),fonts.coverage(prepared['fonts/NotoSansSC.ttf']))
        # Every locale can display a shared community title; Hant retains priority.
        css=(ROOT/'launcher/i18n.css').read_text()
        self.assertIn('Outfit,"CYTV NotoSansTC","CYTV NotoSansSC"',css)
        self.assertIn('"CYTV NotoSansDevanagari","CYTV NotoSansSC","CYTV NotoSansTC","CYTV NotoSansKR"',css)
        homebrew=(ROOT/'homebrew/app/style.css').read_text()
        self.assertIn('font-family:CYTVChineseTC,CYTVChineseSC,CYTV',homebrew)
        self.assertIn('font-family:CYTV,CYTVChineseSC,CYTVChineseTC',homebrew)

    def test_foreign_markup_and_css_are_excluded_but_nested_chinese_survives(self):
        inputs={'foreign.html':b'<html lang="en"><span lang="ko-KR">&#x3409;</span><script>HomeI18n.add({"zh-Hans":{"x":"\\u529b"}});</script></html>',
                'foreign.css':b'html[lang = "ko"]::after{content:"\\340a ";}html:lang(zh-Hant)::after{content:"\\529b ";}'}
        chars=fonts.required_characters(files=inputs)
        self.assertIn(ord('力'),chars['SC']);self.assertIn(ord('力'),chars['TC'])
        for script in fonts.SCRIPTS:
            self.assertNotIn(0x3409,chars[script]);self.assertNotIn(0x340A,chars[script])

    @unittest.skipUnless(hasattr(__import__('os'),'mkfifo'),'FIFO fixtures require POSIX')
    def test_nonregular_source_and_subset_cache_entries_are_refused(self):
        import base64,os,shutil
        prepared=fonts.prepare_fonts()
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)/'cache';shutil.copytree(fonts.default_cache(),cache)
            match=next(p for p in (cache/'subsets').glob('*.json') if base64.b64decode(json.loads(p.read_text())['data'])==prepared['fonts/NotoSansSC.ttf'])
            match.unlink();os.mkfifo(match)
            with self.assertRaisesRegex(ValueError,'cache'):fonts.prepare_fonts(cache=cache)
            path=cache/'sources'/fonts.SOURCES['SC']['sha256'];path.unlink();os.mkfifo(path)
            with self.assertRaisesRegex(ValueError,'source'):fonts.source_font('SC',cache)

    def test_document_language_does_not_hide_shared_inline_runtime_code(self):
        chars=fonts.required_characters(files={'index.html':b'<html lang="en"><script>window.title="\\u3400";</script><script type="application/json">{"title":"\\u3402"}</script><style>.theme{content:"\\3401 "}</style></html>'})
        for script in fonts.SCRIPTS:self.assertTrue({0x3400,0x3401,0x3402} <= chars[script])

    def test_negated_and_shared_css_selectors_cannot_hide_chinese_content(self):
        chars=fonts.required_characters(files={'widget.css':b'html:not(:lang(en))::before{content:"\\3400 ";}.shared,html:lang(ko){content:"\\3401 ";}'})
        for script in fonts.SCRIPTS:self.assertTrue({0x3400,0x3401} <= chars[script])

    def test_invalid_unicode_css_escape_uses_replacement_without_breaking_collection(self):
        chars=fonts.required_characters(files={'widget.css':b'.label{content:"\\110000 \\d800 \\0 ";}'})
        for script in fonts.SCRIPTS:self.assertNotIn(0x110000,chars[script])

    def test_currency_and_formatting_are_not_chinese_font_requirements(self):
        baseline=fonts.prepare_fonts()
        for source in (b'window.price="\\u20b910 \\u20b4 \\u20bd\\u200d";',
                       b'HomeI18n.add({"zh-Hans":{"price":"\\u20b910"},"zh-Hant":{"price":"\\u20b4 \\u20bd"}});'):
            with self.subTest(source=source):
                chars=fonts.required_characters(files={'price.js':source})
                for codes in chars.values():self.assertFalse({0x20B9,0x20B4,0x20BD,0x200D} & codes)
                self.assertEqual(fonts.prepare_fonts(files={'price.js':source}),baseline)

    def test_unsupported_optional_symbol_does_not_replace_cjk_validation(self):
        chars=fonts.required_characters(files={'widget.js':b'window.symbol="\\u2800";'})
        for codes in chars.values():self.assertNotIn(0x2800,codes)
        self.assertIn(ord('✓'),set.union(*chars.values()))
        self.assertIn(ord('›'),set.union(*chars.values()))
