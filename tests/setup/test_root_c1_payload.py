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
    def test_builds_static_gate_once_and_both_native_graphics_variants(self):
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
            self.assertEqual(sum('-target' in argv for argv in calls),1)
            compile_call=calls[0]
            self.assertIn('arm-linux-musleabi',compile_call);self.assertIn('-static',compile_call)
            for graphics,path in builder.C1_GRAPHICS.items():
                bundle=payload/path
                manifest=json.loads((bundle/'bundle.json').read_text())
                release=json.loads((bundle/'release.json').read_text())
                self.assertEqual(release['home_backend'],'c1-native-gate')
                self.assertTrue(release['experimental']);self.assertFalse(release['hardware_validated'])
                self.assertIn('runtime/c1-home-gate',manifest['files'])
                self.assertIn('runtime/c1_gate.py',manifest['files'])
                from cytv import package
                files=package.data_files((bundle/manifest['package']).read_bytes())
                app=json.loads(files['usr/palm/applications/com.cleanyourtv.root.preview/appinfo.json'])
                self.assertEqual(app['resolution'],graphics)
            self.assertEqual(builder.GRAPHICS['1920x1080']['root'],'root')
            self.assertEqual(builder.GRAPHICS['1280x720']['root'],'root-720p')

if __name__=='__main__':unittest.main()
