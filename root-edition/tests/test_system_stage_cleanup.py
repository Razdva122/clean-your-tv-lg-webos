"""Native-Python setup cache is discarded as data, never imported as recovery."""
import importlib.util
import os
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from install_device import LocalDevice
import install_device
from installation import Ownership
from updater.store import Store

REPO=Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location('stage_'+name,REPO/'system-updater'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class NativeSystemStage(unittest.TestCase):
    def test_known_cache_is_retired_and_unknown_temporary_files_are_retained(self):
        for extra in (None,'notes.txt','foreign.cpython-312.pyc'):
            with self.subTest(extra=extra),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();stage=root/('cytv-system-updater-'+'a'*32)
                load('build').build(stage)
                py_compile.compile(str(stage/'installation.py'),doraise=True)
                if extra:(stage/'__pycache__'/extra).write_bytes(b'private unknown data')
                device=LocalDevice.__new__(LocalDevice);device.payload=None
                device.ownership=Ownership(Store(root/'owner',uid=os.getuid()))
                device.system_setup=lambda:load('setup')
                with patch.object(install_device,'TEMP',root):
                    if extra:
                        record={'operation':'b'*32}
                        device.retire_temporary_support(record)
                        self.assertEqual(record['retained_temporary_stages'][0]['path'],str(stage))
                        self.assertTrue((stage/'bundle.json').exists())
                        self.assertTrue((stage/'__pycache__'/extra).exists())
                    else:
                        device.retire_temporary_support({'operation':'b'*32})
                        self.assertEqual(list(stage.iterdir()),[])
