"""Release APK checks without an installed Android SDK."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cytv import package

spec = importlib.util.spec_from_file_location('android_verify_release', ROOT / 'android/verify_release.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

VERSIONS = {'android': '0.1.3-preview', 'android_version_code': 4,
            'home': '1.3.4', 'helper': '0.6.16', 'root': '0.1.8'}
CERT = 'ab' * 32
BADGING = """package: name='com.cleanyourtv.android' versionCode='4' versionName='0.1.3-preview' platformBuildVersionName='15'
sdkVersion:'24'
targetSdkVersion:'35'
application-label:'Clean Your TV'
native-code: 'arm64-v8a'
"""


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / 'android').mkdir()
        (self.root / 'scripts').mkdir()
        # Reuse the production embedded verifier, including actual IPK appinfo checks.
        for name in ('assemble-release.py', 'release-inputs.py'):
            (self.root / 'scripts' / name).write_text((ROOT / 'scripts' / name).read_text())
        (self.root / 'release-versions.json').write_text(json.dumps(VERSIONS))
        (self.root / 'android/preview-certificate.sha256').write_text(CERT + '\n')
        self.apk = self.root / 'preview.apk'
        self.files = {'root/release.json': json.dumps({'version': '0.1.8'}).encode(),
                      'root/bundle.json': b'{"package":"root.ipk"}'}
        for filename, app, version in [('launcher.ipk', 'com.gathin.tvhome', '1.3.4'),
                                       ('helper.ipk', 'com.local.nativehome', '0.6.16'),
                                       ('root/root.ipk', package.ROOT_APP, '0.1.8')]:
            self.files[filename] = package.ipk(app, version, {
                'usr/palm/applications/' + app + '/appinfo.json':
                    json.dumps({'id': app, 'version': version}).encode()})
        self.badging = BADGING
        self.cert_output = 'Signer #1 certificate SHA-256 digest: ' + ':'.join(['AB'] * 32) + '\n'
        self.signing_error = False
        self.build_info = {'schema': 1, 'source_commit': 'a' * 40, 'versions': VERSIONS}
        self.graphics = None
        self.write_apk()

    def write_apk(self, corrupt=None, empty=False):
        manifest = {'files': {n: hashlib.sha256(b).hexdigest() for n, b in self.files.items()},
                    'home_version': '1.3.4', 'helper_version': '0.6.16'}
        if self.graphics is not None:manifest['graphics']=self.graphics
        with zipfile.ZipFile(self.apk, 'w') as archive:
            if self.build_info is not None:
                archive.writestr('assets/cytv-build.json', json.dumps(self.build_info))
            archive.writestr('assets/payload/payload.json', b'' if empty else json.dumps(manifest))
            for name, data in self.files.items():
                archive.writestr('assets/payload/' + name, b'corrupt' if name == corrupt else data)

    def run_binary(self, command, **kwargs):
        self.assertIsInstance(command, list)
        self.assertNotIn('shell', kwargs)
        if Path(command[0]).name == 'aapt':
            self.assertEqual(command[1:], ['dump', 'badging', str(self.apk)])
            return self.badging
        if Path(command[0]).name == 'apksigner':
            self.assertEqual(command[1:], ['verify', '--print-certs', str(self.apk)])
            if self.signing_error:
                raise subprocess.CalledProcessError(1, command)
            return self.cert_output
        self.assertEqual(command, ['git', 'rev-parse', 'HEAD'])
        return 'a' * 40 + '\n'

    def verify(self, allow_legacy=True):
        with patch.dict('os.environ', {'ANDROID_HOME': '/fake/android-sdk'}), \
                patch.object(verifier.subprocess, 'check_output', side_effect=self.run_binary):
            return verifier.verify_apk(self.apk, root=self.root, allow_legacy=allow_legacy)

    def test_current_apk_rejects_fhd_only_payload_with_valid_hashes(self):
        with self.assertRaisesRegex(ValueError,'graphics'):
            self.verify(allow_legacy=False)

    def test_current_dual_graphics_apk_passes_strict_verification(self):
        self.graphics={'1920x1080':{'launcher':'launcher.ipk','root':'root'},'1280x720':{'launcher':'launcher-720p.ipk','root':'root-720p'}}
        for graphics,paths in self.graphics.items():
            for kind,app,key in [('launcher','com.gathin.tvhome','home'),('root',package.ROOT_APP,'root')]:
                name=paths[kind]+('/root.ipk' if kind=='root' else '')
                self.files[name]=package.ipk(app,VERSIONS[key],{'usr/palm/applications/'+app+'/appinfo.json':json.dumps({'id':app,'version':VERSIONS[key],'resolution':graphics}).encode()})
                if kind=='root':
                    self.files[paths[kind]+'/bundle.json']=b'{"package":"root.ipk"}'
                    self.files[paths[kind]+'/release.json']=json.dumps({'version':VERSIONS['root']}).encode()
        self.write_apk();self.verify(allow_legacy=False)
        del self.files['launcher-720p.ipk'];self.write_apk()
        with self.assertRaisesRegex(ValueError,'Unhashed'):
            self.verify(allow_legacy=False)

    def test_valid_apk_report_binds_versions_signer_and_bytes(self):
        report = self.verify()
        self.assertEqual(report, {'schema': 1, 'source_commit': 'a' * 40, 'versions': VERSIONS,
                                 'android_version_name': '0.1.3-preview', 'android_version_code': 4,
                                 'package': 'com.cleanyourtv.android', 'abi': 'arm64-v8a',
                                 'min_sdk': 24, 'target_sdk': 35, 'debuggable': False, 'signer_sha256': CERT,
                                 'sha256': hashlib.sha256(self.apk.read_bytes()).hexdigest()})

    def test_rejects_debuggable_apk_even_with_trusted_signer_and_payload(self):
        self.badging = BADGING + 'application-debuggable\n'
        with self.assertRaisesRegex(ValueError, 'debuggable'):
            self.verify()

    def test_rejects_wrong_package_versions_sdk_and_abi(self):
        for before, after in [('com.cleanyourtv.android', 'example.other'),
                              ("versionName='0.1.3-preview'", "versionName='0.1.2-preview'"),
                              ("versionCode='4'", "versionCode='3'"),
                              ("sdkVersion:'24'", "sdkVersion:'23'"),
                              ("targetSdkVersion:'35'", "targetSdkVersion:'34'"),
                              ("native-code: 'arm64-v8a'", "native-code: 'arm64-v8a' 'x86_64'")]:
            with self.subTest(after=after):
                self.badging = BADGING.replace(before, after)
                with self.assertRaises(ValueError): self.verify()

    def test_rejects_wrong_or_missing_certificate_and_failed_signature(self):
        for output in ['Signer #1 certificate SHA-256 digest: ' + 'cd' * 32, '',
                       self.cert_output + 'Signer #2 certificate SHA-256 digest: ' + 'cd' * 32]:
            with self.subTest(output=output):
                self.cert_output = output
                with self.assertRaises(ValueError): self.verify()
        self.signing_error = True
        with self.assertRaises(subprocess.CalledProcessError): self.verify()

    def test_rejects_payload_hash_corruption(self):
        self.write_apk(corrupt='helper.ipk')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): self.verify()

    def test_rejects_actual_embedded_component_version_despite_valid_hashes(self):
        app = 'com.gathin.tvhome'
        self.files['launcher.ipk'] = package.ipk(app, '1.0.0', {
            'usr/palm/applications/' + app + '/appinfo.json':
                json.dumps({'id': app, 'version': '1.0.0'}).encode()})
        self.write_apk()
        with self.assertRaisesRegex(ValueError, 'application version mismatch'): self.verify()

    def test_rejects_stale_or_missing_embedded_provenance(self):
        for info in [None, {'schema': 1, 'source_commit': 'b' * 40, 'versions': VERSIONS},
                     {'schema': 1, 'source_commit': 'a' * 40,
                      'versions': {**VERSIONS, 'helper': '0.6.15'}},
                     {'schema': 2, 'source_commit': 'a' * 40, 'versions': VERSIONS}]:
            with self.subTest(info=info):
                self.build_info = info
                self.write_apk()
                with self.assertRaisesRegex(ValueError, 'provenance'): self.verify()

    def test_rejects_empty_payload_manifest(self):
        self.write_apk(empty=True)
        with self.assertRaises(ValueError): self.verify()


if __name__ == '__main__':
    unittest.main()
