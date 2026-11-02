"""Graphics capability selection cannot replace a retained rollback descriptor."""
import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_core  # source package aliases used by the existing adapter tests
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'root-edition'))

class Graphics(unittest.TestCase):
    def test_same_strict_capability_in_all_python_paths(self):
        from cytv.graphics import resolution
        adapters=[importlib.import_module('system_updater.device'),importlib.import_module('updater.device')]
        for value,expected in [(True,'1920x1080'),('true','1920x1080'),(False,'1280x720'),('false','1280x720')]:
            response={'returnValue':True,'UHD':value}
            self.assertEqual(resolution(response),expected)
            for module in adapters:
                with patch.object(module,'call',return_value=response) as call:
                    self.assertEqual(module.Device.graphics_resolution(),expected)
                    call.assert_called_once_with('luna://com.webos.service.tv.systemproperty/getSystemInfo',{'keys':['UHD']})
        for response in [None,{},[],{'returnValue':False,'UHD':True}]+[{'returnValue':True,'UHD':v} for v in [None,0,1,'TRUE','False',{},[]]]:
            with self.assertRaises(ValueError):resolution(response)
            for module in adapters:
                with patch.object(module,'call',return_value=response),self.assertRaises(ValueError):module.Device.graphics_resolution()

    def test_offer_wrong_graphics_rejected_before_baseline_or_mutation(self):
        module=importlib.import_module('system_updater.device')
        d=module.Device.__new__(module.Device);d.graphics_resolution=lambda:'1280x720'
        d.require_components=lambda:None;d.integrity=lambda:None
        candidate={'edition':'no-root','release':'v2.0.0','components':[{'name':'home','application':'com.gathin.tvhome','version':'2.0.0','url':'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v2.0.0/com.gathin.tvhome_2.0.0_all.ipk'}]}
        d.fetch=lambda *args: {'candidate':candidate};d._verify_release=lambda c,e:c
        d._baseline=lambda e: self.fail('wrong channel must be rejected before baseline/install effects')
        with self.assertRaisesRegex(ValueError,'graphics'):d.offer('no-root')

    def test_unknown_capability_stops_before_integrity_mutations(self):
        module=importlib.import_module('system_updater.device');d=module.Device.__new__(module.Device)
        d.graphics_resolution=lambda:(_ for _ in ()).throw(ValueError('unknown graphics'))
        d.require_components=lambda:None;d.integrity=lambda:self.fail('unknown capability must precede integrity side effects')
        with self.assertRaises(ValueError):d.offer('root')

    def test_hd_bytes_required_and_original_fhd_rollback_unchanged(self):
        from test_device import ipk,digest
        from cytv import package
        module=importlib.import_module('system_updater.device');d=module.Device.__new__(module.Device)
        raw=ipk();descriptor={'name':'home','application':'com.gathin.tvhome','version':'1.0.0','sha256':digest(raw),'size':len(raw),'kind':'ipk','url':'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v2.0.0/com.gathin.tvhome_1.0.0_720p_all.ipk'}
        with self.assertRaisesRegex(ValueError,'graphics'):d.inspect(raw,descriptor)
        files=package.data_files(raw);name='usr/palm/applications/com.gathin.tvhome/appinfo.json'
        import json
        info=json.loads(files[name]);info['resolution']='1280x720';files[name]=json.dumps(info).encode()
        hd=package.ipk('com.gathin.tvhome','1.0.0',files);descriptor.update(sha256=digest(hd),size=len(hd))
        self.assertTrue(d.inspect(hd,descriptor))
        # Rollback is the retained baseline, not today's preferred variant.
        prior={k:v for k,v in descriptor.items() if k!='url'};prior.update(local=True,sha256=digest(raw),size=len(raw))
        self.assertTrue(d.inspect(raw,prior))
