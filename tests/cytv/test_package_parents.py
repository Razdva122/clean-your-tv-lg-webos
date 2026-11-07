"""No-root IPKs must not depend on a recursively creating extractor."""
import io
import json
from pathlib import Path, PurePosixPath
import runpy
import tarfile
import unittest

from cytv import package


class PackageParentTests(unittest.TestCase):
    def assert_parent_entries(self, raw):
        with tarfile.open(fileobj=io.BytesIO(package.read_ar(raw)['data.tar.gz'])) as archive:
            seen = set()
            for entry in archive:
                for parent in PurePosixPath(entry.name).parents:
                    if str(parent) != '.':
                        self.assertIn(str(parent), seen, entry.name)
                seen.add(entry.name)
            for name in ('usr', 'usr/palm', 'usr/palm/applications', 'usr/palm/services', 'usr/palm/packages'):
                entry = archive.getmember(name)
                self.assertTrue(entry.isdir())
                self.assertEqual((entry.uid, entry.gid, entry.mode), (0, 0, 0o755))

    def test_no_root_builder_includes_parents_before_payload(self):
        builder = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/build-cytv.py'))
        app = {'appinfo.json': json.dumps({'id': 'com.local.nativehome', 'version': '0.6.22',
                                         'type': 'native', 'main': 'relay'}).encode(),
               'relay': b'fixture'}
        service = {'services.json': b'{"id":"com.local.nativehome.service","services":[{"name":"com.local.nativehome.service"}]}',
                   'package.json': b'{"name":"com.local.nativehome.service","main":"service.js"}',
                   'service.js': b'void 0;'}
        raw = builder['pack_app'](app, service, architecture='arm')
        self.assert_parent_entries(raw)
        self.assertEqual(package.data_files(raw)['usr/palm/services/com.local.nativehome.service/service.js'],
                         builder['compile_helper'](service)['service.js'])

    def test_home_personalization_keeps_parents_and_state_permissions(self):
        app = 'com.gathin.tvhome'
        files = {'usr/palm/applications/'+app+'/index.html': b'home',
                 'usr/palm/services/com.gathin.tvhome.renewal/state/home-control/.keep': b'',
                 'usr/palm/packages/'+app+'/packageinfo.json': b'{}'}
        original = package.ipk(app, '1.8.1', files)
        inventory = {'apps': [{'id': 'fixture.app'}]}
        first, _ = package.personalize(original, app, inventory)
        self.assert_parent_entries(first)
        self.assertEqual(first, package.personalize(original, app, inventory)[0])
        with tarfile.open(fileobj=io.BytesIO(package.read_ar(first)['data.tar.gz'])) as archive:
            entry = archive.getmember('usr/palm/services/com.gathin.tvhome.renewal/state/home-control')
            self.assertEqual((entry.uid, entry.gid, entry.mode), (5999, 5000, 0o2770))


if __name__ == '__main__':
    unittest.main()
