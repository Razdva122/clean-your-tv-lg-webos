import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from test_core import Store
from test_device import tar

class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.store = Store(self.root / 'bootstrap', uid=os.getuid())
        self.mod = importlib.import_module('system_updater.activation')
        self.catalog = {'engine': {'version': '1.2.11'}}
        files = {'engine-entry.py': b'print("ready")\n', 'system_updater/cli.py': b'# cli\n'}
        manifest = {'schema': 1, 'version': '1.2.11', 'files': {n: hashlib.sha256(v).hexdigest() for n,v in files.items()}}
        self.raw = tar(dict(files, **{'engine.json': json.dumps(manifest).encode()}))
        self.catalog['engine'].update(sha256=hashlib.sha256(self.raw).hexdigest(), size=len(self.raw))
        self.slots = self.mod.Slots(self.store, self.root / 'code', lambda proof: self.catalog)
    def tearDown(self):
        self.tmp.cleanup()
    def test_staging_does_not_activate_and_trial_requires_exact_confirmation(self):
        slot = self.slots.stage({'signature': 'test'}, self.raw)
        self.assertEqual(self.slots.active(), self.root / 'code')
        self.slots.begin('a'*32, slot)
        self.assertEqual(self.slots.active(), self.root / 'code')
        with self.assertRaises(ValueError): self.slots.confirm('b'*32)
        self.slots.confirm('a'*32)
        self.assertEqual(self.slots.active(), slot)
    def test_corrupt_or_indirect_engine_is_never_selected(self):
        slot = self.slots.stage({}, self.raw)
        self.slots.begin('a'*32, slot); self.slots.confirm('a'*32)
        (slot / 'engine-entry.py').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.slots.active()
    def test_interrupted_trial_retains_previous_engine(self):
        slot = self.slots.stage({}, self.raw)
        self.slots.begin('a'*32, slot)
        recreated = self.mod.Slots(self.store, self.root / 'code', lambda proof: self.catalog)
        self.assertEqual(recreated.active(), self.root / 'code')
        recreated.cancel('a'*32)
        self.assertEqual(recreated.active(), self.root / 'code')
    def test_recycled_slot_resumes_after_partial_new_write(self):
        from unittest.mock import patch
        for identifier in ('a'*32, 'b'*32):
            slot = self.slots.stage({}, self.raw)
            self.slots.begin(identifier, slot); self.slots.confirm(identifier)
        original = self.mod.atomic
        calls = []
        def power_loss(path, raw):
            original(path, raw); calls.append(path)
            if len(calls) == 1: raise KeyboardInterrupt('power loss')
        with patch.object(self.mod, 'atomic', side_effect=power_loss):
            with self.assertRaises(KeyboardInterrupt): self.slots.stage({}, self.raw)
        # A new process can finish the same authenticated slot, without selecting
        # the partial generation or needing a computer to clear old receipts.
        slot = self.slots.stage({}, self.raw)
        self.assertEqual(slot.name, 'a')
        self.assertEqual(self.slots.active().name, 'b')

    def test_wrong_package_hash_is_refused_before_staging(self):
        with self.assertRaises(ValueError): self.slots.stage({}, self.raw + b'broken')
        self.assertFalse((self.root/'bootstrap/slots').exists())

    def test_new_offer_can_replace_partial_inactive_slot(self):
        from unittest.mock import patch
        def interrupt(path, raw):
            atomic(path, raw)
            raise KeyboardInterrupt('power loss')

        original = {'signature': 'original'}
        slot = self.slots.stage(original, self.raw)
        self.slots.begin('a'*32, slot)
        self.slots.confirm('a'*32)
        atomic = self.mod.atomic
        with patch.object(self.mod, 'atomic', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.slots.stage({'signature': 'cancelled'}, self.raw)
        # The outer lease admits a different proof only after the pending
        # operation is cancelled. A newer catalog must not strand this slot.
        self.assertEqual(self.slots.stage({'signature': 'new'}, self.raw).name, 'b')
        self.assertEqual(self.slots.active(), slot)

if __name__ == '__main__': unittest.main()
