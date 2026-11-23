"""Root cleanup discovers private disk staging without widening its path boundary."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install_device


class SupportStaging(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.temp = self.base / 'tmp'; self.temp.mkdir()
        self.private = self.base / 'private'; self.private.mkdir(mode=0o700)
        self.addCleanup(patch.stopall)
        patch.object(install_device, 'TEMP', self.temp).start()
        patch.object(install_device, 'PRIVATE_TEMP', self.private, create=True).start()
        self.device = install_device.LocalDevice()
        self.device.payload = None
        self.device.ownership = SimpleNamespace(store=SimpleNamespace(uid=os.getuid()))

    def test_interrupted_private_stage_is_outstanding_cleanup(self):
        stage = self.private / ('cytv-c1-root-' + 'a'*32)
        stage.mkdir(mode=0o700)
        self.assertTrue(self.device.has_untracked_support({}))
        self.assertFalse(self.device.has_untracked_support({'support_stages':[{'path':str(stage)}]}))

    def test_unknown_private_entry_refuses_cleanup(self):
        (self.private / 'foreign').write_text('keep')
        with self.assertRaises(ValueError): self.device.has_untracked_support({})
        self.assertEqual((self.private / 'foreign').read_text(), 'keep')

    def test_private_parent_must_remain_private_and_not_a_symlink(self):
        self.private.chmod(0o755)
        with self.assertRaises(ValueError): self.device.has_untracked_support({})
        self.private.rmdir(); self.private.symlink_to(self.temp, target_is_directory=True)
        with self.assertRaises(ValueError): self.device.has_untracked_support({})

    def test_legacy_shared_temporary_files_are_ignored(self):
        (self.temp / 'foreign').touch()
        stage = self.temp / ('cytv-product-'+'b'*32); stage.mkdir()
        self.assertTrue(self.device.has_untracked_support({}))
        stage.rmdir()
        self.assertFalse(self.device.has_untracked_support({}))

    def test_retired_product_paths_remain_confined_to_exact_support_roots(self):
        for root in (self.temp,self.private):
            self.assertTrue(install_device.support_stage_path(root/('cytv-product-'+'c'*32),'product'))
            self.assertFalse(install_device.support_stage_path(root/('cytv-coordinator-'+'c'*32),'product'))
            self.assertFalse(install_device.support_stage_path(root/'nested'/('cytv-product-'+'c'*32),'product'))
        self.assertFalse(install_device.support_stage_path(self.base/('cytv-product-'+'c'*32),'product'))
