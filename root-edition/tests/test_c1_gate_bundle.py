"""Experimental bundles never become normal Root/OTA candidates implicitly."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load(name):
    spec = importlib.util.spec_from_file_location('c1_test_' + name, ROOT / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def static_arm():
    ident = b'\x7fELF\x01\x01\x01' + b'\0' * 9
    header = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 40, 1, 0x10054,
                         52, 0, 0x05000200, 52, 32, 1, 0, 0, 0)
    program = struct.pack('<IIIIIIII', 1, 0, 0x10000, 0x10000, 88, 88, 5, 4096)
    return header + program + b'\0' * 4


class BundleTests(unittest.TestCase):
    def test_only_static_loadable_arm_executable_is_accepted(self):
        builder = load('build')
        builder.validate_native_gate(static_arm())
        for offset, value in ((16, b'\x03\0'), (52, b'\x03\0\0\0'),
                              (52, b'\x02\0\0\0'), (28, b'\xff' * 4)):
            invalid = bytearray(static_arm()); invalid[offset:offset+len(value)] = value
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                builder.validate_native_gate(bytes(invalid))
        with self.assertRaises(ValueError):
            builder.validate_native_gate(static_arm()[:52])

    def test_normal_bundle_excludes_experimental_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            load('build').build(root / 'normal')
            manifest = load('deploy').verify_bundle(root / 'normal')
            self.assertNotIn('runtime/c1_gate.py', manifest['files'])
            self.assertNotIn('runtime/c1-home-gate', manifest['files'])

    def test_experimental_native_bundle_requires_explicit_reader_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            helper = root / 'gate'
            helper.write_bytes(static_arm())
            builder = load('build')
            try:
                builder.build(root / 'bundle', experimental_c1_gate=helper)
            except TypeError:
                self.fail('The builder has no explicit C1 experiment option')
            deploy = load('deploy')
            with self.assertRaisesRegex(ValueError, '[Ee]xperimental'):
                deploy.verify_bundle(root / 'bundle')
            manifest = deploy.verify_bundle(root / 'bundle', allow_experimental=True)
            self.assertIn('runtime/c1-home-gate', manifest['files'])
            release = json.loads((root / 'bundle/release.json').read_text())
            self.assertEqual(release['home_backend'], 'c1-native-gate')
            self.assertIs(release['experimental'], True)
            self.assertIs(release['hardware_validated'], False)
            self.assertEqual(release['native_sha256'], hashlib.sha256(helper.read_bytes()).hexdigest())
            self.assertEqual((root / 'bundle/runtime/c1-home-gate').read_bytes(), helper.read_bytes())
            native = root / 'bundle/runtime/c1-home-gate'
            native.write_bytes(native.read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                deploy.verify_bundle(root / 'bundle', allow_experimental=True)

    def test_non_arm_native_helper_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            helper = root / 'gate'
            helper.write_bytes(b'#!/bin/sh\nexit 0\n')
            try:
                with self.assertRaises(ValueError):
                    load('build').build(root / 'bundle', experimental_c1_gate=helper)
            except TypeError:
                self.fail('The builder cannot validate an experimental native helper')
            self.assertFalse((root / 'bundle').exists())


if __name__ == '__main__':
    unittest.main()
