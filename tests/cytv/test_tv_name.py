"""TV naming is data-only personalization; no TV connection is required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv import cli, package, prompts
from cytv.desktop import Prompt


class TVNameTests(unittest.TestCase):
    def test_unicode_names_defaults_and_invalid_input(self):
        for value,wanted in [('', 'Home'),('   ','Home'),(' Aashiyaan ','Aashiyaan'),('आशियाना','आशियाना'),('Cafe\u0301','Café')]:
            self.assertEqual(package.normalize_tv_name(value),wanted)
        self.assertEqual(package.normalize_tv_name('x'*48),'x'*48)
        for value in (None,42,'x'*49,'bad\nname','bad\x00name','bad\u202ename'):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):package.normalize_tv_name(value)

    def test_prompt_retries_invalid_name_and_blank_accepts_home(self):
        answers=iter(['x'*49,''])
        self.assertEqual(prompts.tv_name(lambda _:next(answers),lambda _:None),'Home')
        self.assertEqual(prompts.tv_name(lambda _:'Aashiyaan',lambda _:None),'Aashiyaan')
        self.assertEqual(Prompt('TV name [Home]: ').default,'Home')
        self.assertEqual(Prompt('TV name [Home]: ').kind,'text')

    def test_cli_flag_validation_and_default(self):
        self.assertEqual(cli.parser().parse_args(['install','--tv-name',' Aashiyaan ']).tv_name,'Aashiyaan')
        self.assertIsNone(cli.parser().parse_args(['install','--non-interactive']).tv_name)
        with patch('cytv.cli.choose_profile') as choose:
            self.assertEqual(cli.main(['status','--tv-name','Aashiyaan'],write=lambda _:None),2)
            choose.assert_not_called()

    def test_noninteractive_cli_applies_name_after_install_without_personalizing(self):
        from tests.cytv.test_cli import CLITests
        from tests.cytv.test_operations import Remote
        for flag,expected in [([], None),(['--tv-name','Aashiyaan'],'Aashiyaan')]:
            with self.subTest(flag=flag),tempfile.TemporaryDirectory() as temp,patch('cytv.cli.Installer') as cls,patch('cytv.cli.package.verify_payload',return_value={}),patch('cytv.tv.SSAP') as ssap,patch('cytv.install_settings.apply_services') as apply:
                ssap.return_value.__enter__.return_value.inventory.return_value={'apps':[{'id':'example.app'}],'inputs':[]}
                cls.return_value.version_summary.return_value=[]
                cls.return_value.install.return_value={}
                remote=Remote();remote.close=lambda:None
                code,output,_=CLITests().run_cli(['install','--host','192.0.2.10','--edition','no-root','--data-dir',temp,'--yes','--non-interactive']+flag,remote=remote)
                self.assertEqual(code,0,output)
                self.assertNotIn('tv_name', cls.return_value.__dict__)
                if expected is None:
                    apply.assert_not_called()
                else:
                    apply.assert_called_once()
                    self.assertEqual(apply.call_args.args[1], {'tv_name': expected})
                cls.return_value.install.assert_called_once()
