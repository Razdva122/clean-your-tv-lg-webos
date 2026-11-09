"""Common installer payload keeps normal bundles and embeds explicit C1 variants."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]

class RootC1PayloadTests(unittest.TestCase):
    def test_current_compositor_bundles_keep_authenticated_schema_one_removal_support(self):
        spec=importlib.util.spec_from_file_location('c1_payload_builder',ROOT/'scripts/build-cytv.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        ident=b'\x7fELF\x01\x01\x01'+b'\0'*9
        binary=struct.pack('<16sHHIIIIIHHHHHH',ident,2,40,1,0x10054,52,0,0x05000200,52,32,1,0,0,0)+struct.pack('<IIIIIIII',1,0,0x10000,0x10000,88,88,5,4096)+b'\0'*4
        calls=[]
        def run(argv,**kwargs):
            calls.append(argv)
            if '-target' in argv:
                Path(argv[argv.index('-o')+1]).write_bytes(binary)
                return subprocess.CompletedProcess(argv,0)
            return subprocess.run(argv,**kwargs)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();payload=root/'payload';payload.mkdir()
            builder.stage_c1_root(payload,root,'0.8.4',run=run)
            self.assertEqual(sum('-target' in argv for argv in calls),2)
            compile_call=calls[0]
            self.assertIn('arm-linux-musleabi',compile_call);self.assertIn('-static',compile_call)
            for graphics,path in builder.C1_GRAPHICS.items():
                bundle=payload/path
                manifest=json.loads((bundle/'bundle.json').read_text())
                release=json.loads((bundle/'release.json').read_text())
                self.assertEqual(release['home_backend'],'c1-native-gate')
                self.assertTrue(release['experimental']);self.assertFalse(release['hardware_validated'])
                self.assertIn('runtime/c1-keyfilter-guard',manifest['files'])
                self.assertIn('runtime/c1-home-filter.js',manifest['files'])
                self.assertIn('runtime/c1-home-gate',manifest['files'])
                self.assertEqual((bundle/'runtime/c1-home-gate').read_bytes(),binary)
                self.assertNotEqual(release['routing'],None)
                self.assertIn('runtime/c1_gate.py',manifest['files'])
                from cytv import package
                files=package.data_files((bundle/manifest['package']).read_bytes())
                app=json.loads(files['usr/palm/applications/com.cleanyourtv.root.preview/appinfo.json'])
                self.assertEqual(app['resolution'],graphics)
                # Exercise the real manifest verifier and recovery selector in
                # a fresh interpreter; only the device/native call is modeled.
                # Native recovery modules require POSIX; Windows still checks
                # both packaged ELF executables and the complete manifest above.
                if sys.platform != 'win32':
                    subprocess.run([sys.executable, '-c', r"""
import os,sys
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,'root-edition')
import clean_removal
bundle=Path(sys.argv[1]);native=bundle/'runtime/c1-home-gate'
backend=Mock();backend.STATE=Path('/retained-schema-one')
backend.selection.return_value={'schema':1,'native_sha256':'0'*64}
cli=Mock();cli.gate_backend.return_value=backend
sys.modules['cli']=cli
def restore(mode):
    assert mode=='restore'
    assert backend.binary(backend.STATE,os.getuid())==native
    return 'restored'
cli.main.side_effect=restore
assert clean_removal.runtime_restore(bundle,os.getuid())['result']=='restored'
assert native.stat().st_mode&0o777==0o700
import deploy
from runtime import c1_keyfilter
retained=bundle.parent/(bundle.name+'-fresh')
with patch.object(deploy,'STATE',retained),patch.object(deploy,'verify_payload'),patch.object(deploy,'install_launcher'),patch.object(c1_keyfilter,'prepare'),patch.object(c1_keyfilter,'native',return_value={'backend':'c1-native-gate','selfcheck':True}):
    deploy.install(bundle,run=lambda argv:None,observe=lambda *args,**kw:None,
        experimental_c1_gate=True,_experimental_admission={})
assert (retained/'runtime/c1-keyfilter-guard').is_file()
assert not (retained/'runtime/c1-home-gate').exists()
native.write_bytes(native.read_bytes()+b'changed')
try:clean_removal.runtime_restore(bundle,os.getuid())
except ValueError:pass
else:raise AssertionError('Changed recovery executable accepted')
assert cli.main.call_count==1
""", str(bundle)], cwd=ROOT, check=True)

            self.assertEqual(builder.GRAPHICS['1920x1080']['root'],'root')
            self.assertEqual(builder.GRAPHICS['1280x720']['root'],'root-720p')

    def test_beta_payload_advertises_the_same_backend_with_one_shared_native_build(self):
        spec=importlib.util.spec_from_file_location('shared_keyfilter_payload_builder',ROOT/'scripts/build-cytv.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        from tests.cytv.test_legacy_beta_build import load
        fixture=load('shared_keyfilter_fixture',ROOT/'root-edition/tests/test_c1_gate_bundle.py')
        calls=[]
        def run(argv,**kwargs):
            calls.append(argv)
            if '-target' in argv:
                Path(argv[argv.index('-o')+1]).write_bytes(fixture.static_arm())
                return subprocess.CompletedProcess(argv,0)
            return subprocess.run(argv,**kwargs)
        with tempfile.TemporaryDirectory() as folder:
            work=Path(folder).resolve();payload=work/'payload';payload.mkdir()
            (payload/'fallback.png').write_bytes(b'fixture')
            (payload/'installer-support').mkdir()
            helper=builder.stage_c1_root(payload,work,'0.0.1',run=run)
            builder.stage_legacy_root_beta(payload,'0.0.1',helper,run=run)
            nested=payload/'legacy-root-beta'
            manifest=json.loads((nested/'payload.json').read_bytes())
            self.assertEqual(manifest['root_backends'],builder.ROOT_BACKENDS)
            self.assertEqual(sum('-target' in argv for argv in calls),2)
            from cytv.root_runtime import select_payload
            outer=dict(legacy_root_beta='legacy-root-beta',files={
                'legacy-root-beta/'+name:digest for name,digest in manifest['files'].items()})
            selected,checked=select_payload(payload,outer)
            self.assertEqual(selected,nested)
            self.assertEqual(checked['root_backends'],builder.ROOT_BACKENDS)
            for path in builder.C1_GRAPHICS.values():
                release=json.loads((nested/path/'release.json').read_bytes())
                self.assertEqual(release['runtime_variant'],'node012-beta')
                self.assertEqual(release['routing'],'compositor-keyfilter-v1')
                self.assertEqual((nested/path/'runtime/c1-keyfilter-guard').read_bytes(),helper.read_bytes())
                for name in ('c1_keyfilter.py','c1-home-filter.js'):
                    self.assertEqual((nested/path/'runtime'/name).read_bytes(),(payload/path/'runtime'/name).read_bytes())

if __name__=='__main__':unittest.main()
