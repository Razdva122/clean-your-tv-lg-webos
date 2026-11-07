"""Offline acceptance fixtures must exercise real packages without production IDs."""
import base64
import hashlib
import io
import json
import re
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/build-root-update-lab.py'
APP = 'com.cleanyourtv.root.updatetest'
UPDATER = 'com.cleanyourtv.root.updaterlab'


def payload(path):
    raw = path.read_bytes()
    parts, offset = {}, 8
    assert raw[:8] == b'!<arch>\n'
    while offset < len(raw):
        header = raw[offset:offset + 60]
        size = int(header[48:58])
        parts[header[:16].decode().strip().rstrip('/')] = raw[offset + 60:offset + 60 + size]
        offset += 60 + size + size % 2
    files, directories, seen = {}, set(), set()
    roots = {'usr/palm/'+kind+'/'+owner+suffix
             for owner in (APP, UPDATER)
             for kind, suffix in (('applications',''), ('services','.service'), ('packages',''))}
    with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz'])) as archive:
        for member in archive:
            name = member.name
            relative = PurePosixPath(name)
            if (not name or relative.is_absolute() or str(relative) != name
                    or '..' in relative.parts or '\\' in name or '\x00' in name
                    or name in seen
                    or not any(name == root or name.startswith(root+'/') for root in roots)):
                raise ValueError('Unsafe isolated lab package path')
            seen.add(name)
            if member.isdir():
                if member.size or member.mode != 0o755 or member.uid != 0 or member.gid != 0:
                    raise ValueError('Unsafe isolated lab package directory')
                directories.add(name)
            elif member.isfile():
                files[name] = archive.extractfile(member).read()
            else:
                raise ValueError('Special isolated lab package entry')
    ancestors = {str(parent) for name in files for parent in PurePosixPath(name).parents}
    if directories - ancestors:
        raise ValueError('Unowned isolated lab package directory')
    return files


class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.output = Path(cls.tmp.name).resolve() / 'lab'
        cls.production_key = (ROOT / 'updater-service/release-public.pem').read_bytes()
        subprocess.run([sys.executable, str(SCRIPT), '--output', str(cls.output)], check=True, cwd=ROOT)

    def test_builds_real_isolated_root_and_updater_packages(self):
        for label, version in (('baseline', '0.1.0'), ('candidate', '0.1.1'), ('rollback-test', '0.1.2')):
            folder = self.output / 'packages' / label
            files = payload(folder / (APP + '_' + version + '_all.ipk'))
            prefix = 'usr/palm/applications/' + APP + '/'
            self.assertEqual(json.loads(files[prefix + 'appinfo.json'])['id'], APP)
            self.assertEqual(json.loads(files[prefix + 'appinfo.json'])['version'], version)
            self.assertEqual(files[prefix + 'apps.js'], b'window.TV_APPS = {apps: [], inputs: []};\n')
            self.assertIn(prefix + 'compat-polyfills.js', files)
            self.assertIn(b'compat-polyfills.js', files[prefix + 'index.html'])
            self.assertEqual(json.loads(files['usr/palm/packages/' + APP + '/packageinfo.json'])['services'], [APP + '.service'])
            for name, data in files.items():
                if name.endswith(('.js', '.json', '.html', '.css', '.sh')):
                    self.assertNotIn(b'com.cleanyourtv.root.preview', data)
                    self.assertNotIn(b'com.cleanyourtv.root.updater.service', data)
            service = files['usr/palm/services/' + APP + '.service/service.js']
            self.assertIn(b'/var/lib/clean-your-tv-root-updatetest/runtime/cli.py', service)
        updater = payload(self.output / 'updater-bundle/root-updater.ipk')
        self.assertEqual(json.loads(updater['usr/palm/applications/' + UPDATER + '/appinfo.json'])['id'], UPDATER)
        self.assertIn(b'/var/lib/clean-your-tv-root-updaterlab/code/service.js', updater['usr/palm/services/' + UPDATER + '.service/service.js'])

    def test_committed_source_is_isolated_and_original_key_is_unchanged(self):
        source = self.output / 'source'
        evidence = json.loads((self.output / 'lab-transform.json').read_text())
        self.assertEqual(evidence['source_commit'], subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
        self.assertEqual(evidence['paths']['root_state'], '/var/lib/clean-your-tv-root-updatetest')
        self.assertEqual(evidence['paths']['updater_state'], '/var/lib/clean-your-tv-root-updaterlab')
        self.assertFalse((source / '.git').exists())
        self.assertFalse((source / 'node_modules').exists())
        self.assertFalse(list(source.rglob('*.key')))
        self.assertEqual((ROOT / 'updater-service/release-public.pem').read_bytes(), self.production_key)
        self.assertNotEqual((source / 'updater-service/release-public.pem').read_bytes(), self.production_key)
        self.assertEqual((source / 'launcher/brand-v2-icon.png').read_bytes(), subprocess.check_output(['git', 'show', 'HEAD:launcher/brand-v2-icon.png'], cwd=ROOT))
        deploy = (source / 'root-edition/deploy.py').read_text()
        self.assertIn('usr/palm/services/com.cleanyourtv.updater.service/state/profile.json', deploy)
        self.assertIn('58-clean-your-tv-root-updatetest', (source / 'root-edition/startup_hook.py').read_text())
        bootstrap = (source / 'root-edition/updater/bootstrap.py').read_text()
        self.assertIn('59-clean-your-tv-root-updaterlab', bootstrap)
        self.assertIn("STATE=Path('/var/lib/clean-your-tv-root-updaterlab')", bootstrap)
        self.assertNotIn('updatetest-updater', bootstrap)
        self.assertIn('/var/webos-profile/override/clean-your-tv-root-updatetest.json', (source / 'root-edition/runtime/device_adapter.py').read_text())
        original = subprocess.check_output(['git', 'show', 'HEAD:root-edition/ui/root-settings.css'], cwd=ROOT)
        self.assertEqual((source / 'root-edition/ui/root-settings.css').read_bytes(), original)
        result = subprocess.run([sys.executable, str(SCRIPT), '--output', str(self.output)], cwd=ROOT, capture_output=True)
        self.assertNotEqual(result.returncode, 0, 'Existing output must never be replaced')

    def test_pinned_offers_verify_and_use_only_loopback_transport(self):
        source = self.output / 'source/root-edition'
        subprocess.run([sys.executable, '-c', 'from updater.bootstrap import verify_bundle; import sys; verify_bundle(sys.argv[1])', str(self.output / 'updater-bundle')], cwd=source, check=True)
        for version in ('0.1.1', '0.1.2'):
            offer = self.output / ('offer-' + version + '.json')
            envelope = json.loads(offer.read_text())
            manifest = json.loads(base64.b64decode(envelope['payload']))
            name = APP + '_' + version + '_all.ipk'
            package = self.output / ('http/releases/download/v' + version) / name
            self.assertEqual(manifest['sha256'], hashlib.sha256(package.read_bytes()).hexdigest())
            self.assertEqual(manifest['size'], package.stat().st_size)
            subprocess.run(['node', '-e', r'''
const fs=require('fs'),assert=require('assert'),f=require(process.argv[1]);
const offer=JSON.parse(fs.readFileSync(process.argv[2]));
const key=fs.readFileSync(process.argv[3]);assert.equal(f.verify(offer,key).application,'com.cleanyourtv.root.updatetest');
for(const u of ['https://github.com/x','http://localhost:18997/releases/x','http://127.0.0.1:18998/releases/x','http://127.0.0.1:18997/other','http://user@127.0.0.1:18997/releases/x'])assert.equal(f.allowed(u),false,u);
assert(f.allowed('http://127.0.0.1:18997/releases/latest/download/root-update.json'));
assert(f.allowed(f.verify(offer,key).url));
''', str(source / 'updater/fetch.js'), str(offer), str(self.output / 'updater-bundle/updater/release-public.pem')], check=True)
        for path in (self.output / 'updater-bundle').rglob('*'):
            if path.is_file() and path.suffix in {'.py', '.js', '.json', '.sh'}:
                raw = path.read_text()
                self.assertIsNone(re.search(r'com\.cleanyourtv\.root\.(?:preview|updater)(?!lab)', raw), str(path))
                self.assertIsNone(re.search(r'/var/lib/clean-your-tv-root(?!-updatetest|-updaterlab)', raw), str(path))
        self.assertEqual((self.output / 'http/releases/latest/download/root-update.json').read_bytes(), (self.output / 'offer-0.1.1.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
