"""C1 experiment admission, native proof and profile isolation contracts."""
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
sys.path.insert(0, str(ROOT))


class BackendTests(unittest.TestCase):
    def setUp(self):
        try:
            self.gate = importlib.import_module('c1_gate')
        except ModuleNotFoundError:
            self.fail('The explicit experimental C1 backend is not implemented')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.uid = os.getuid()

    def descriptor(self):
        return {'schema': 1, 'backend': 'c1-native-gate', 'experimental': True,
                'native_sha256': 'a' * 64,
                'admission': {'model': 'OLED65C14LB', 'firmware': '03.51.15',
                              'webos': '6.5.0', 'target_sha256': 'b' * 64,
                              'target': {'dev': 1, 'ino': 2, 'size': 50684, 'mtime_ns': 1737433159000000000}}}

    def write_descriptor(self, value=None):
        path = self.root / 'home-backend.json'
        path.write_text(json.dumps(self.descriptor() if value is None else value))
        path.chmod(0o600)
        return path

    def test_default_has_no_experiment_or_filesystem_effect(self):
        self.assertIsNone(self.gate.selection(self.root, self.uid))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_only_exact_experiment_descriptor_selects_backend(self):
        self.write_descriptor()
        self.assertEqual(self.gate.selection(self.root, self.uid), self.descriptor())
        for update in ({'experimental': False}, {'backend': 'profile'}, {'schema': True}, {'extra': 1}):
            with self.subTest(update=update):
                self.write_descriptor(dict(self.descriptor(), **update))
                with self.assertRaises(ValueError):
                    self.gate.selection(self.root, self.uid)

    def test_untrusted_or_malformed_marker_never_falls_back_to_profiles(self):
        path = self.write_descriptor()
        path.chmod(0o666)
        with self.assertRaises(ValueError):
            self.gate.selection(self.root, self.uid)
        path.chmod(0o600)
        path.write_text('{broken')
        with self.assertRaises(ValueError):
            self.gate.selection(self.root, self.uid)
        path.unlink()
        path.symlink_to(self.root / 'missing')
        with self.assertRaises((OSError, ValueError)):
            self.gate.selection(self.root, self.uid)

    def test_admission_is_actual_c1_webos6_arm32_native_not_error_fallback(self):
        elf = b'\x7fELF\x01\x01\x01' + b'\0' * 11 + b'\x28\x00' + b'\0' * 32
        valid = {'returnValue': True, 'modelName': 'OLED65C14LB',
                 'firmwareVersion': '03.51.15', 'sdkVersion': '6.5.0'}
        self.assertEqual(self.gate.admit(valid, elf, pointer_bits=32)['model'], 'OLED65C14LB')
        for info, data, bits in ((dict(valid, modelName='OLED55C3RLA'), elf, 32),
                                 (dict(valid, sdkVersion='11.2.0'), elf, 32),
                                 (dict(valid, returnValue=False), elf, 32),
                                 (valid, elf, 64), (valid, b'#!/bin/sh\n', 32),
                                 (dict(valid, firmwareVersion=''), elf, 32)):
            with self.subTest(info=info, bits=bits), self.assertRaises(ValueError):
                self.gate.admit(info, data, pointer_bits=bits)

    def checkpoint(self):
        shared = self.root / 'cmn_data'
        target = shared / 'checkpoint/com.webos.app.home'
        target.mkdir(parents=True, mode=0o755)
        (target / 'snapshot').write_bytes(b'original checkpoint')
        return shared, target

    def test_checkpoint_preflight_rejects_nonsticky_shared_parent_read_only(self):
        shared, target = self.checkpoint()
        shared.chmod(0o777)
        with patch.object(self.gate, 'CHECKPOINTS', (target,)):
            with self.assertRaisesRegex(ValueError, 'checkpoint'):
                self.gate.checkpoint_preflight(self.uid)
        self.assertEqual(shared.stat().st_mode & 0o7777, 0o777)
        self.assertEqual((target / 'snapshot').read_bytes(), b'original checkpoint')

    def test_checkpoint_preflight_keeps_native_leaf_and_sticky_ancestor_rules(self):
        shared, target = self.checkpoint()
        shared.chmod(0o1777)
        with patch.object(self.gate, 'CHECKPOINTS', (target,)):
            self.gate.checkpoint_preflight(self.uid)
            target.parent.chmod(0o1777)
            self.gate.checkpoint_preflight(self.uid)
            for mode in (0o777, 0o1777):
                target.chmod(mode)
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    self.gate.checkpoint_preflight(self.uid)
            target.chmod(0o755)
            target.rename(target.with_name('retained'))
            target.symlink_to(target.with_name('retained'))
            with self.assertRaises(ValueError):
                self.gate.checkpoint_preflight(self.uid)
        self.assertEqual((target / 'snapshot').read_bytes(), b'original checkpoint')

    def test_absent_optional_checkpoint_is_not_created_by_preflight(self):
        target = self.root / 'absent/checkpoint/home'
        with patch.object(self.gate, 'CHECKPOINTS', (target,)):
            self.gate.checkpoint_preflight(self.uid)
        self.assertFalse(target.parent.exists())

    def test_probe_rejects_checkpoints_before_home_read_or_luna(self):
        with patch.object(self.gate.os, 'geteuid', return_value=0), \
                patch.object(self.gate.sys, 'platform', 'linux'), \
                patch.object(self.gate, 'checkpoint_preflight', side_effect=ValueError('checkpoint refused')), \
                patch.object(self.gate, 'secure') as read, patch.object(self.gate, 'luna') as rpc:
            with self.assertRaisesRegex(ValueError, 'checkpoint'):
                self.gate.probe()
        read.assert_not_called()
        rpc.assert_not_called()

    def test_checkpoint_refusal_precedes_durable_install_reservation_and_effects(self):
        from installation import Ownership, device_operation
        from updater.store import Store
        shared, target = self.checkpoint()
        shared.chmod(0o777)
        store = Store(self.root / 'ownership', uid=self.uid)
        owner = Ownership(store)
        with patch.object(self.gate, 'CHECKPOINTS', (target,)):
            with self.assertRaisesRegex(ValueError, 'checkpoint'):
                with device_operation('deploy', ownership=owner, read=lambda path: None,
                        check=lambda: self.gate.checkpoint_preflight(self.uid)):
                    self.fail('Unsafe checkpoint admitted installation effects')
        self.assertIsNone(owner.status())
        self.assertIsNone(store.read('operation'))
        self.assertEqual((target / 'snapshot').read_bytes(), b'original checkpoint')

    def test_status_requires_real_native_stock_proof_without_fake_profiles(self):
        self.write_descriptor()
        native = {'returnValue': True, 'backend': 'c1-native-gate', 'state': 'stock',
                  'mounted': False, 'healthy': False, 'token': 'c' * 32,
                  'stock_verified': True, 'profiles': None, 'stopped': True,
                  'reason': 'explicit-stop', 'guardian_pid': 0}
        with patch.object(self.gate, 'native', return_value=native), \
                patch.object(self.gate, 'read_intent', return_value=None):
            result = self.gate.status(self.root, self.uid)
        self.assertIsNone(result['effective']['profiles'])
        self.assertTrue(result['effective']['stock_verified'])
        self.assertFalse(result['update_home_resume_available'])
        self.assertEqual(result['intent']['phase'], 'disabled')
        for changed in ({'profiles': {}}, {'stock_verified': 'true'}, {'mounted': True}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.gate.validate_native(dict(native, **changed))

    def test_selected_runtime_dispatch_never_reads_profile_adapter(self):
        spec = importlib.util.spec_from_file_location('c1_runtime_cli', ROOT / 'runtime/cli.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch.object(self.gate, 'selection', return_value=self.descriptor()), \
                patch.object(self.gate, 'execute', return_value={'backend': 'c1-native-gate'}) as run, \
                patch.object(cli.d, 'main', side_effect=AssertionError('profile adapter must not run')):
            self.assertEqual(cli.execute('status'), {'backend': 'c1-native-gate'})
            run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
