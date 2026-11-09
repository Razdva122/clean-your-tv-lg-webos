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
    def archive(self, app='com.gathin.tvhome'):
        prefix='usr/palm/applications/'+app+'/'
        files={prefix+'appinfo.json':json.dumps({'id':app,'title':'Home','version':'1.2.3'}).encode(),
               prefix+'index.html':b'<html><title>Home</title><body></body></html>',
               prefix+'apps.js':b'original inventory',prefix+'helper':b'unchanged executable'}
        return package.ipk(app,'1.2.3',files,executable={prefix+'helper'}),prefix

    def test_unicode_names_defaults_and_invalid_input(self):
        for value,wanted in [('', 'Home'),('   ','Home'),(' Aashiyaan ','Aashiyaan'),('आशियाना','आशियाना'),('Cafe\u0301','Café')]:
            self.assertEqual(package.normalize_tv_name(value),wanted)
        self.assertEqual(package.normalize_tv_name('x'*48),'x'*48)
        for value in (None,42,'x'*49,'bad\nname','bad\x00name','bad\u202ename'):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):package.normalize_tv_name(value)

    def test_name_changes_titles_without_changing_identity_or_executable(self):
        raw,prefix=self.archive()
        name='Aashiyaan <script>& "TV"'
        prepared,files=package.personalize(raw,'com.gathin.tvhome',{'apps':[{'id':'example.app'}]},tv_name=name)
        info=json.loads(files[prefix+'appinfo.json'])
        self.assertEqual((info['id'],info['version'],info['title']),('com.gathin.tvhome','1.2.3',name))
        seed=files[prefix+'tv-name-config.js'].decode()
        self.assertEqual(json.loads(seed.split('=',1)[1].strip().rstrip(';')),name)
        self.assertIn(b'&lt;script&gt;&amp;',files[prefix+'index.html'])
        self.assertNotIn(b'<script>',files[prefix+'index.html'])
        self.assertEqual(files[prefix+'helper'],b'unchanged executable')
        self.assertEqual(package.data_files(raw)[prefix+'apps.js'],b'original inventory')
        import io,tarfile
        with tarfile.open(fileobj=io.BytesIO(package.read_ar(prepared)['data.tar.gz']),mode='r:gz') as archive:
            self.assertTrue(archive.getmember(prefix+'helper').mode&0o111)

    def test_root_title_only_personalization_preserves_inventory_and_rehashes(self):
        raw,prefix=self.archive(package.ROOT_APP)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'home.ipk').write_bytes(raw)
            (root/'release.json').write_text(json.dumps({'files':{}}));(root/'SHA256SUMS').write_text('old')
            names=['home.ipk','release.json','SHA256SUMS']
            (root/'bundle.json').write_text(json.dumps({'package':'home.ipk','files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}}))
            package.personalize_root(root,None,tv_name='Aashiyaan')
            files=package.data_files((root/'home.ipk').read_bytes())
            self.assertEqual(files[prefix+'apps.js'],b'original inventory')
            self.assertEqual(json.loads(files[prefix+'appinfo.json'])['title'],'Aashiyaan')
            for name,digest in json.loads((root/'bundle.json').read_text())['files'].items():
                self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertEqual(json.loads((root/'release.json').read_text())['files'][prefix+'appinfo.json'],hashlib.sha256(files[prefix+'appinfo.json']).hexdigest())

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

    def test_noninteractive_cli_passes_name_to_installer(self):
        from tests.cytv.test_cli import CLITests
        from tests.cytv.test_operations import Remote
        for flag,expected in [([], 'Home'),(['--tv-name','Aashiyaan'],'Aashiyaan')]:
            with self.subTest(flag=flag),tempfile.TemporaryDirectory() as temp,patch('cytv.cli.Installer') as cls,patch('cytv.cli.package.verify_payload',return_value={}),patch('cytv.tv.SSAP') as ssap:
                ssap.return_value.__enter__.return_value.inventory.return_value={'apps':[{'id':'example.app'}],'inputs':[]}
                cls.return_value.version_summary.return_value=[]
                cls.return_value.install.return_value={}
                remote=Remote();remote.close=lambda:None
                code,output,_=CLITests().run_cli(['install','--host','192.0.2.10','--edition','no-root','--data-dir',temp,'--yes','--non-interactive']+flag,remote=remote)
                self.assertEqual(code,0,output)
                self.assertEqual(cls.return_value.tv_name,expected)
                cls.return_value.install.assert_called_once()

    def test_no_root_install_packages_the_selected_title_before_receipt(self):
        from tests.cytv.test_operations import OperationTests,Remote
        fixture=OperationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        remote=Remote();installer=fixture.installer(remote)
        installer.tv_name='bad\nname'
        with self.assertRaises(ValueError):installer.install(fixture.inventory,'test-key')
        self.assertFalse(remote.calls)
        self.assertIsNone(fixture.store.pending(installer.profile))
        installer.tv_name='Aashiyaan'
        installer.install(fixture.inventory,'test-key')
        raw=next(data for name,data in remote.uploads.items() if name.endswith('/launcher.ipk'))
        info=json.loads(package.data_files(raw)['usr/palm/applications/com.gathin.tvhome/appinfo.json'])
        self.assertEqual(info['title'],'Aashiyaan')
        self.assertIsNone(fixture.store.pending(installer.profile))

    def test_root_install_keeps_the_named_package_bound_to_its_manifest(self):
        from tests.cytv.test_operations import OperationTests,Remote
        fixture=OperationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.root_bundle()
        remote=Remote();installer=fixture.installer(remote,'root');installer.tv_name='Aashiyaan'
        installer.install(fixture.inventory)
        titles=[]
        for path,raw in remote.uploads.items():
            if path.endswith('.ipk'):
                files=package.data_files(raw)
                name='usr/palm/applications/'+package.ROOT_APP+'/appinfo.json'
                if name in files:titles.append(json.loads(files[name])['title'])
        self.assertEqual(titles,['Aashiyaan'])
        self.assertIsNone(fixture.store.pending(installer.profile))
