"""TV naming is data-only personalization; no TV connection is required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv import cli, install_settings, package, prompts


class TVNameTests(unittest.TestCase):
    def test_unicode_names_defaults_and_invalid_input(self):
        for value,wanted in [('', 'Home'),('   ','Home'),(' Aashiyaan ','Aashiyaan'),('आशियाना','आशियाना'),('Cafe\u0301','Café')]:
            self.assertEqual(package.normalize_tv_name(value),wanted)
        self.assertEqual(package.normalize_tv_name('x'*48),'x'*48)
        for value in (None,42,'x'*49,'bad\nname','bad\x00name','bad\u202ename','a\u061cb','\ud800'):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):package.normalize_tv_name(value)

    def test_prompt_retries_invalid_name_and_blank_preserves_name(self):
        answers=iter(['x'*49,''])
        self.assertEqual(prompts.tv_name(lambda _:next(answers),lambda _:None),None)
        self.assertEqual(prompts.tv_name(lambda _:'Aashiyaan',lambda _:None),'Aashiyaan')

    def test_name_requires_root_edition_even_over_root_ssh(self):
        for profile in ({'edition': 'no-root'}, {'edition': 'no-root', 'connection': 'root-ssh'}):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                install_settings.validate({'tv_name': 'Living Room'}, profile)

    def test_cli_flag_validation_and_default(self):
        self.assertEqual(cli.parser().parse_args(['install','--tv-name',' Aashiyaan ']).tv_name,'Aashiyaan')
        self.assertIsNone(cli.parser().parse_args(['install','--non-interactive']).tv_name)
        with patch('cytv.cli.choose_profile') as choose:
            self.assertEqual(cli.main(['status','--tv-name','Aashiyaan'],write=lambda _:None),2)
            choose.assert_not_called()

    def test_noninteractive_cli_rejects_name_for_no_root(self):
        from tests.cytv.test_cli import CLITests
        from tests.cytv.test_operations import Remote
        for flag in ([], ['--tv-name','Aashiyaan']):
            with (
                self.subTest(flag=flag),
                tempfile.TemporaryDirectory() as temp,
                patch('cytv.cli.Installer') as cls,
                patch('cytv.cli.package.verify_payload', return_value={}),
                patch('cytv.cli.payload_dir', return_value=Path(temp)),
                patch('cytv.tv.SSAP') as ssap,
                patch('cytv.install_settings.apply_services') as apply,
            ):
                (Path(temp) / 'fallback.png').write_bytes(b'test-fallback')
                ssap.return_value.__enter__.return_value.inventory.return_value={'apps':[{'id':'example.app'}],'inputs':[]}
                cls.return_value.version_summary.return_value=[]
                cls.return_value.install.return_value={}
                remote=Remote();remote.close=lambda:None
                code,output,_=CLITests().run_cli(['install','--host','192.0.2.10','--edition','no-root','--data-dir',temp,'--yes','--non-interactive']+flag,remote=remote)
                self.assertEqual(code, 2 if flag else 0, output)
                self.assertNotIn('tv_name', cls.return_value.__dict__)
                apply.assert_not_called()
                self.assertEqual(cls.return_value.install.call_count, 0 if flag else 1)
