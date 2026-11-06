"""Carrier archive behavior, with source-shaped service-inventory loss cases."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import unittest
from cytv import package


class CleanupCarrier(unittest.TestCase):
    def setUp(self):
        self.app = 'com.local.nativehome'
        self.service = 'com.local.nativehome.service'
        source = Path(__file__).resolve().parents[2] / 'cytv/no_root_carrier.py'
        self.assertTrue(source.exists(), 'inert cleanup carrier builder is not implemented')
        spec = importlib.util.spec_from_file_location('cytv.no_root_carrier', source)
        self.builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.builder)

    def original(self, services=None, version='0.7.4', app=None, architecture='arm'):
        app = app or self.app
        services = [self.service] if services is None else services
        files = {
            'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': version, 'type': 'native', 'main': 'detach'}).encode(),
            'usr/palm/applications/' + app + '/detach': b'ORIGINAL EXECUTABLE',
            'usr/palm/packages/' + app + '/packageinfo.json': json.dumps({'id': app, 'app': app, 'version': version, 'services': services}).encode(),
        }
        for service in services:
            files['usr/palm/services/' + service + '/services.json'] = json.dumps({'id': service, 'services': [{'name': service}], 'requiredACG': ['application.launcher']}).encode()
        return package.ipk(app, version, files, architecture=architecture)

    def test_inert_carrier_retains_original_service_cleanup_inventory(self):
        carrier = self.builder.build(self.app, [self.original()], noop=b'\x7fELFfixture', architecture='arm')
        files = package.data_files(carrier)
        metadata = json.loads(files['usr/palm/packages/' + self.app + '/packageinfo.json'])
        self.assertEqual(metadata['services'], [self.service])
        self.assertEqual(metadata['version'], '0.7.4')
        app = json.loads(files['usr/palm/applications/' + self.app + '/appinfo.json'])
        self.assertEqual(app['id'], self.app)
        self.assertEqual(app['requiredACG'], [])
        self.assertFalse(any('state/' in name or 'detach' in name or 'controller' in name for name in files))
        service = json.loads(files['usr/palm/services/' + self.service + '/services.json'])
        self.assertEqual(service['requiredACG'], [])
        self.assertEqual(service['services'], [{'name': self.service}])
        self.assertEqual(files['usr/palm/services/' + self.service + '/service.js'], b"'use strict';process.exit(0);\n")
        # OSE IpkRemoveStep/DataRemoveStep use NEW packageinfo, not old metadata.
        old_data = {self.service: 'private data'}
        for service in metadata['services']:
            old_data.pop(service, None)
        self.assertEqual(old_data, {})

    def test_service_free_current_metadata_does_not_forget_original_service(self):
        carrier = self.builder.build(self.app, [self.original(), self.original(services=[])], noop=b'\x7fELFfixture', architecture='arm')
        metadata = json.loads(package.data_files(carrier)['usr/palm/packages/' + self.app + '/packageinfo.json'])
        self.assertEqual(metadata['services'], [self.service])

    def test_mismatched_control_app_id_or_foreign_service_is_rejected(self):
        samples = [self.original(services=['com.foreign.service']), self.original(architecture='x86'), self.original(version='999\nDepends: foreign')]
        parts = package.read_ar(self.original())
        files = package.data_files(self.original())
        info = 'usr/palm/applications/' + self.app + '/appinfo.json'
        files[info] = json.dumps({'id': 'com.foreign', 'version': '0.7.4'}).encode()
        parts['data.tar.gz'] = package.tgz(files)
        samples.append(package.ar(parts))
        parts = package.read_ar(self.original())
        parts['control.tar.gz'] = package.tgz({'control': b'Package: com.foreign\nVersion: 0.7.4\nArchitecture: arm\n'})
        samples.append(package.ar(parts))
        for sample in samples:
            with self.subTest(sample=len(sample)), self.assertRaises(ValueError):
                self.builder.build(self.app, [sample], noop=b'\x7fELFfixture', architecture='arm')

    def test_control_scripts_and_broad_permissions_never_survive(self):
        parts = package.read_ar(self.original())
        control = package.read_ar(self.original())['control.tar.gz']
        with tarfile.open(fileobj=io.BytesIO(control)) as archive:
            raw = archive.extractfile('control').read()
        parts['control.tar.gz'] = package.tgz({'control': raw, 'postinst': b'echo unsafe'})
        with self.assertRaises(ValueError):
            self.builder.build(self.app, [package.ar(parts)], noop=b'\x7fELFfixture', architecture='arm')

    def test_noop_js_exits_on_every_configured_node_runtime(self):
        import os
        import shutil
        carrier = self.builder.build(self.app, [self.original()], noop=b'\x7fELFfixture', architecture='arm')
        source = package.data_files(carrier)['usr/palm/services/' + self.service + '/service.js']
        for node in [shutil.which('node')] + [os.environ[key] for key in ('NODE010', 'NODE01025', 'NODE012') if key in os.environ]:
            with self.subTest(node=node):
                result = subprocess.run([node, '-e', source], capture_output=True, timeout=5)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'', b''))
