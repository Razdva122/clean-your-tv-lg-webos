"""Actual isolated native child, with only TV boundaries adapted."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from install_device import LocalDevice
from install_driver import failure_summary
from installation import Ownership
from updater.store import Store


class NativeFailureTests(unittest.TestCase):
    def test_actual_child_preserves_admission_cause_without_commands_or_prose(self):
        import deploy
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve();bundle=base/'root';bundle.mkdir()
            names=set(deploy.SUPPORT_FILES)|{'runtime/c1_gate.py','runtime/c1_keyfilter.py'}
            for name in names:
                target=bundle/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,target)
            (bundle/'release.json').write_text(json.dumps({'routing':'compositor-keyfilter-v1'}))
            # Exercise real deploy.experimental_admission and its packaged import
            # closure. Only the device snapshot and hardware probe are adapters.
            with (bundle/'deploy.py').open('a') as out:
                out.write("\nimport installation\ninstallation.device_snapshot=lambda **kw: dict(supported=True,packages_match=False,receipts_match=False,pending=False,retained=False,complete=False,migration_supported=False)\n")
                out.write("from runtime import c1_keyfilter\ndef denied():\n    raise PermissionError(13,'PRIVATE password/address/path')\nc1_keyfilter.probe=denied\n")
            device=LocalDevice();device.ownership=Ownership(Store(base/'state',uid=os.getuid()))
            with device.ownership.operation('product','product-'+'a'*32+'.json') as lease:
                device.operation=lease
                with self.assertRaises(subprocess.CalledProcessError) as caught:
                    device.native_deploy(base)
            detail=failure_summary(caught.exception).get('root_driver')
            self.assertIsNotNone(detail,'The isolated child cause was lost')
            self.assertEqual(detail['exception_type'],'PermissionError')
            self.assertEqual(detail['errno'],13)
            self.assertTrue(any(f['file']=='deploy.py' for f in detail['frames']))
            self.assertNotIn('PRIVATE',json.dumps(detail))
            self.assertNotIn(str(base),json.dumps(detail))
            self.assertNotIn('attempt',detail)
            self.assertLess(len(json.dumps(detail)),4096)
            self.assertFalse((base/'state'/('request-'+'a'*32)).exists())

            from install_driver import Coordinator
            owner=Ownership(Store(base/'coordinator',uid=os.getuid()))
            device.preflight=lambda *args,**kwargs:None
            device.log=lambda error:None
            driver=Coordinator(device,owner,read=lambda _:None)
            result=driver.native_install('c'*32,base)
            self.assertEqual(result['state'],'recovery_required')
            self.assertEqual(result['stage'],'root-deploy')
            self.assertEqual(result['failure']['root_driver']['exception_type'],'PermissionError')
            saved=owner.store.read('request-'+'c'*32)
            device.native_deploy=lambda *_:self.fail('retained install replayed')
            self.assertEqual(driver.native_install('c'*32,base),result)
            self.assertEqual(owner.store.read('request-'+'c'*32),saved)

    def test_unbound_or_oversized_child_output_never_becomes_diagnostic_evidence(self):
        from types import SimpleNamespace
        device=LocalDevice();device.ownership=SimpleNamespace(fd=0);device.operation={'id':'a'*32}
        for raw in (b'PRIVATE',b'x'*4097,json.dumps({'returnValue':False,'root_install_failure':{
                'schema':1,'attempt':'b'*32,'exception_type':'PermissionError','errno':13,'frames':[]}}).encode()):
            error=subprocess.CalledProcessError(1,['PRIVATE'],output=raw,stderr=b'PRIVATE')
            with self.subTest(size=len(raw)),patch('install_device.subprocess.run',side_effect=error):
                with self.assertRaises(subprocess.CalledProcessError) as caught:device.native_deploy(Path('/fixture'))
                self.assertNotIn('root_driver',failure_summary(caught.exception))

    def test_worker_revalidates_child_metadata_before_retaining(self):
        error=subprocess.CalledProcessError(1,['PRIVATE'])
        error.root_driver={'exception_type':'PermissionError','errno':13,'frames':[
            {'file':'deploy.py','line':351},{'file':'/PRIVATE','line':1}], 'message':'PRIVATE'}
        expected={'exception_type':'PermissionError','errno':13,'frames':[{'file':'deploy.py','line':351}]}
        self.assertEqual(failure_summary(error).get('root_driver'),expected)
        error.root_driver={'exception_type':'PRIVATE','frames':[]}
        self.assertNotIn('root_driver',failure_summary(error))
