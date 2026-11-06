"""Build real static ARM installer support without changing Helper package bytes."""
import hashlib
import os
from pathlib import Path
import runpy
import struct
import tempfile
import unittest


class InstallerSupportBuild(unittest.TestCase):
    def test_native_support_is_independent_static_arm_payload(self):
        repo = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(repo / 'scripts/build-cytv.py'))
        self.assertIn('stage_installer_support', build, 'standalone installer support is not staged')
        with tempfile.TemporaryDirectory(prefix='cytv-support-') as directory:
            work = Path(directory); payload = work / 'payload'; payload.mkdir()
            helper = payload / 'helper.ipk'; helper.write_bytes(b'pinned Helper baseline bytes')
            digest = hashlib.sha256(helper.read_bytes()).hexdigest()
            build['stage_installer_support'](payload, work)
            for name in ('lifecycle-gate', 'cleanup-noop'):
                raw = (payload / 'installer-support' / name).read_bytes()
                self.assertEqual(raw[:7], b'\x7fELF\x01\x01\x01')
                self.assertEqual(struct.unpack_from('<H', raw, 18)[0], 40)  # EM_ARM
                offset, entry_size, count = struct.unpack_from('<I', raw, 28)[0], struct.unpack_from('<H', raw, 42)[0], struct.unpack_from('<H', raw, 44)[0]
                self.assertNotIn(3, [struct.unpack_from('<I', raw, offset + i * entry_size)[0] for i in range(count)])  # no PT_INTERP
            self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), digest)
