"""Recovery verification uses the selected backend's actual packaged files."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'runtime'), str(ROOT)]
import device_adapter as d


class RecoveryManifestTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('compositor_recovery_manifest', ROOT/'runtime/provision.py')
        self.verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.verifier)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name).resolve()
        self.runtime = self.state/'runtime'
        self.runtime.mkdir(mode=0o700)
        self.module = self.write(self.runtime/'provision.py', b'# verifier fixture')
        self.callback = self.write(self.state/'boot.sh', (str(self.runtime/'cli.py')+' boot').encode())
        self.files = [self.module, self.callback]
        for context in (patch.object(d, 'STATE', self.state), patch.object(d, 'EXPECTED_UID', os.getuid()),
                        patch.object(d, 'trusted_dir'), patch.object(d.python_binding, 'verify_binding'),
                        patch.object(self.verifier, '__file__', str(self.module))):
            context.start()
            self.addCleanup(context.stop)

    def write(self, path, data):
        path.write_bytes(data)
        path.chmod(0o600)
        return path

    def save(self):
        self.proof = dict(version=1, mode='recovery-only', boot_callback=str(self.callback),
                          files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.files})
        self.persist()

    def persist(self):
        self.write(self.state/'recovery-provision.json', json.dumps(self.proof).encode())

    def backend(self, schema):
        name = 'c1-home-gate' if schema == 1 else 'c1-keyfilter-guard'
        guard = self.write(self.runtime/name, b'native guard')
        admission = dict(model='55NANO77SRA' if schema == 3 else 'OLED65C14LB',
                         firmware='03.51.15', webos='9.2.2' if schema == 3 else '6.5.0',
                         target_sha256='a'*64, target=dict(dev=1, ino=1, size=52, mtime_ns=1))
        marker = dict(schema=schema, backend='c1-native-gate', experimental=True,
                      native_sha256=hashlib.sha256(guard.read_bytes()).hexdigest(), admission=admission)
        if schema != 1:
            marker['routing'] = 'compositor-keyfilter-v1'
            self.files.append(self.write(self.runtime/'c1-home-filter.js', b'private filter'))
        self.files.extend([guard, self.write(self.state/'home-backend.json', json.dumps(marker).encode())])
        return guard

    def test_schema3_selected_guard_and_filter_are_required_and_hash_bound(self):
        guard = self.backend(3)
        self.save()
        self.assertTrue(self.verifier.verify()['integrity_verified'])
        for path in (guard, self.runtime/'c1-home-filter.js'):
            with self.subTest(path=path.name):
                digest = self.proof['files'].pop(str(path))
                self.persist()
                with self.assertRaisesRegex(ValueError, 'Incomplete'):
                    self.verifier.verify()
                self.proof['files'][str(path)] = digest
                self.persist()
                original = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    self.verifier.verify()
                path.write_bytes(original)

    def test_schema2_uses_compositor_files(self):
        self.backend(2)
        self.save()
        self.assertTrue(self.verifier.verify()['integrity_verified'])

    def test_schema1_retains_native_gate_requirement(self):
        guard = self.backend(1)
        self.save()
        self.assertTrue(self.verifier.verify()['integrity_verified'])
        guard.unlink()
        with self.assertRaises(OSError):
            self.verifier.verify()

    def test_ordinary_recovery_still_checks_all_runtime_files(self):
        entry = self.write(self.runtime/'cli.py', b'# cli fixture')
        self.files.append(entry)
        self.save()
        self.assertTrue(self.verifier.verify()['integrity_verified'])
        self.proof['files'].pop(str(entry))
        self.persist()
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.verifier.verify()


if __name__ == '__main__':
    unittest.main()
