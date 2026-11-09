import io
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class PackageTests(unittest.TestCase):
    def stage_home_service(self, root):
        # The source build packages the paired Home service from tracked sources.
        names = subprocess.run(['git', 'ls-files', '--', 'renewal-service'],
                               cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
        for name in names:
            target = root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT/name, target)
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        subprocess.run(['git', 'add', 'renewal-service'], cwd=root, check=True)

    def test_source_build_reuses_published_helper_without_compiling_it(self):
        with tempfile.TemporaryDirectory(prefix='pinned helper ') as tmp:
            root = Path(tmp)
            self.stage_home_service(root)
            for directory in ('scripts', 'native/app', 'native/published', 'launcher'):
                (root/directory).mkdir(parents=True)
            for name in ('build.sh', 'build-cytv.py', 'fix-package-data.py', 'tv_web_build.py', 'compile-tv-web.cjs', 'helper_build.py', 'compile-helper.cjs'):
                shutil.copy(ROOT/'scripts'/name, root/'scripts'/name)
            shutil.copy(ROOT/'package.json', root/'package.json')
            helper = 'com.local.nativehome_0.6.17_arm.ipk'
            shutil.copy(ROOT/'native/published'/helper, root/'native/published'/helper)
            (root/'native/app/appinfo.json').write_text(json.dumps({'id':'com.local.nativehome','version':'0.6.17'}))
            (root/'launcher/appinfo.json').write_text(json.dumps({'id':'com.gathin.tvhome','version':'9.8.7','type':'web'}))
            (root/'renewal-service/services.json').write_text('{}')
            (root/'launcher/index.html').write_text('<html><head></head><body></body></html>')
            zig = root/'zig'
            zig.write_text('#!/bin/sh\nexit 99\n')
            zig.chmod(0o755)
            packager = root/'packager'
            packager.write_text('#!' + sys.executable + "\n" + '''
from pathlib import Path
from cytv.package import ipk
assert Path('build/home-service/state/home-control/.keep').is_file()
assert Path('build/home-service/theme-receiver/core.js').is_file()
assert Path('build/home-service/theme-receiver/register.js').is_file()
assert Path('build/home-service/weather.js').is_file()
files={'usr/palm/services/com.gathin.tvhome.renewal/state/home-control/.keep':b''}
Path('dist/com.gathin.tvhome_9.8.7_all.ipk').write_bytes(ipk('com.gathin.tvhome','9.8.7',files))
''')
            packager.chmod(0o755)
            env = dict(os.environ, ZIG=str(zig), ARES_PACKAGE=str(packager),
                       PYTHONPATH=str(ROOT), NODE_PATH=str(ROOT/'node_modules'))
            result = subprocess.run(['bash', 'scripts/build.sh'], cwd=root, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual((root/'dist'/helper).read_bytes(), (ROOT/'native/published'/helper).read_bytes())

    def test_build_repairs_current_metadata_package_and_preserves_stale_package(self):
        with tempfile.TemporaryDirectory(prefix='helper build ') as tmp:
            root = Path(tmp)
            self.stage_home_service(root)
            (root/'scripts').mkdir()
            for name in ('build.sh', 'build-cytv.py', 'fix-package-data.py', 'tv_web_build.py', 'compile-tv-web.cjs', 'helper_build.py', 'compile-helper.cjs'):
                shutil.copy(ROOT/'scripts'/name, root/'scripts'/name)
            shutil.copy(ROOT/'package.json', root/'package.json')
            for directory in ('native/app', 'native/service', 'launcher', 'renewal-service'):
                path = root/directory
                path.mkdir(parents=True, exist_ok=True)
                (path/'example.js').write_text('// fixture')
                (path/'icon.png').write_bytes(b'fixture')
                (path/'appinfo.json').write_text(json.dumps({
                    'id': 'com.local.nativehome' if directory == 'native/app' else 'com.gathin.tvhome',
                    'version': '9.8.7'}))
            (root/'renewal-service/state').mkdir()
            (root/'renewal-service/state/settings.json').write_text('PRIVATE')
            shutil.copy(ROOT/'native/app/state-permissions.js', root/'native/app/state-permissions.js')
            shutil.copy(ROOT/'native/service/app-inventory.js', root/'native/service/app-inventory.js')
            (root/'native/app/vendor').mkdir()
            (root/'bin').mkdir()
            zig = root/'bin/zig'
            zig.write_text('#!/bin/sh\nfor arg do target="$arg"; done\n: > "$target"\n')
            zig.chmod(0o755)
            packager = root/'bin/ares-package'
            packager.write_text('#!' + sys.executable + "\n" + '''
import json, sys
from pathlib import Path
from cytv.package import ipk
app = json.loads((Path(sys.argv[1])/'appinfo.json').read_text())
helper = app['id'] == 'com.local.nativehome'
files = {'usr/palm/applications/'+app['id']+'/state/.keep': b''}
if helper:
    assert (Path(sys.argv[2])/'state-permissions.js').read_bytes() == (Path(sys.argv[1])/'state-permissions.js').read_bytes()
    assert (Path(sys.argv[2])/'app-inventory.js').read_bytes() == (Path(sys.argv[1])/'app-inventory.js').read_bytes()
    files['usr/palm/services/com.local.nativehome.service/state/.keep'] = b''
else:
    assert (Path(sys.argv[2])/'state/home-control/.keep').is_file()
    assert not (Path(sys.argv[2])/'state/settings.json').exists()
    files['usr/palm/services/com.gathin.tvhome.renewal/state/home-control/.keep'] = b''
arch = 'arm' if helper else 'all'
(Path('dist')/(app['id']+'_'+app['version']+'_'+arch+'.ipk')).write_bytes(
    ipk(app['id'], app['version'], files, architecture=arch))
''')
            packager.chmod(0o755)
            (root/'dist').mkdir()
            stale = root/'dist/com.local.nativehome_0.6.14_arm.ipk'
            stale.write_bytes(b'old package must stay untouched')
            env = dict(os.environ, NODE_PATH=str(ROOT/'node_modules'), PATH=str(root/'bin')+os.pathsep+os.environ['PATH'],
                       ZIG=str(zig), ARES_PACKAGE=str(packager), PYTHONPATH=str(ROOT))
            result = subprocess.run(['bash', 'scripts/build.sh'], cwd=root, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual(stale.read_bytes(), b'old package must stay untouched')
            sys.path.insert(0, str(ROOT))
            from cytv.package import read_ar
            data = read_ar((root/'dist/com.local.nativehome_9.8.7_arm.ipk').read_bytes())['data.tar.gz']
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
                for name in ('usr/palm/applications/com.local.nativehome/state',
                             'usr/palm/services/com.local.nativehome.service/state'):
                    entry = archive.getmember(name)
                    self.assertEqual((entry.uid, entry.gid, entry.mode), (5999, 5000, 0o770))

    def test_home_and_updater_payloads_include_compiled_service_runtime(self):
        import runpy
        from cytv.package import data_files
        build = runpy.run_path(str(ROOT/'scripts/build-cytv.py'))
        for folder, app_id, service_id in (
                ('renewal-service', 'com.gathin.tvhome', 'com.gathin.tvhome.renewal'),
                ('updater-service', 'com.cleanyourtv.updater', 'com.cleanyourtv.updater.service')):
            with self.subTest(service=service_id):
                app = {'appinfo.json': json.dumps({'id':app_id,'version':'9.8.7'}).encode()}
                service = build['tracked_files'](folder)
                if folder == 'updater-service':
                    service['user-data.js'] = (ROOT/'launcher/user-data.js').read_bytes()
                files = data_files(build['pack_app'](app, service))
                prefix = 'usr/palm/services/'+service_id+'/'
                for name in ('compat-runtime.js', 'compat-polyfills.js', 'compat-buffer.js', 'compat-LICENSE.txt'):
                    self.assertIn(prefix+name, files)
                self.assertIn(b"require('./compat-runtime')", files[prefix+'service.js'])
                if folder == 'renewal-service':
                    self.assertIn(prefix+'theme-receiver/core.js', files)
                    self.assertIn(prefix+'weather.js', files)
                    self.assertEqual(files[prefix+'ca-bundle.crt'], (ROOT/'renewal-service/ca-bundle.crt').read_bytes())
                    self.assertEqual(files[prefix+'ca-LICENSE.txt'], (ROOT/'renewal-service/ca-LICENSE.txt').read_bytes())
                    self.assertEqual(files[prefix+'state/home-control/.keep'], b'')

    def test_home_archive_sets_only_the_two_owned_state_directories(self):
        from cytv.package import ipk, read_ar
        prefix = 'usr/palm/services/com.gathin.tvhome.renewal/'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'home.ipk'
            path.write_bytes(ipk('com.gathin.tvhome', '1.0.0', {prefix+'state/home-control/.keep':b''}))
            subprocess.run([sys.executable, str(ROOT/'scripts/fix-package-data.py'), str(path), '--home-control'], check=True, capture_output=True)
            with tarfile.open(fileobj=io.BytesIO(read_ar(path.read_bytes())['data.tar.gz']), mode='r:gz') as archive:
                for name in ('state','state/home-control'):
                    entry = archive.getmember(prefix+name)
                    self.assertEqual((entry.uid,entry.gid,entry.mode), (5999,5000,0o2770))
                self.assertEqual(archive.getmember(prefix.rstrip('/')).mode, 0o755)

    def test_archive_members_and_state_permissions(self):
        payload = io.BytesIO()
        names = ['./usr/palm/applications/com.local.nativehome/state',
                 './usr/palm/services/com.local.nativehome.service/state']
        with tarfile.open(fileobj=payload, mode='w:gz') as archive:
            for name in names:
                entry = tarfile.TarInfo(name); entry.type = tarfile.DIRTYPE
                entry.mode = 0o775; archive.addfile(entry)
            entry = tarfile.TarInfo('usr/palm/example.txt'); entry.size = 5
            archive.addfile(entry, io.BytesIO(b'hello'))
        members = [('debian-binary', b'2.0\n'), ('control.tar.gz', b'odd'), ('data.tar.gz', payload.getvalue())]
        raw = bytearray(b'!<arch>\n')
        for name, data in members:
            header = f'{name+"/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode()
            raw += header + data + (b'\n' if len(data)%2 else b'')
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)/'test.ipk'; package.write_bytes(raw)
            subprocess.run([sys.executable, str(ROOT/'scripts/fix-package-data.py'), str(package)], check=True, capture_output=True)
            data = package.read_bytes(); self.assertEqual(data[:8], b'!<arch>\n')
            offset=8; found={}
            while offset < len(data):
                header=data[offset:offset+60]; self.assertEqual(header[58:], b'`\n')
                size=int(header[48:58]); name=header[:16].decode().strip().rstrip('/')
                found[name]=data[offset+60:offset+60+size]
                self.assertEqual(len(found[name]), size)
                offset += 60+size+(size%2)
            self.assertEqual(offset, len(data))
            self.assertEqual(list(found), [name for name,_ in members])
            self.assertEqual(found['debian-binary'], b'2.0\n')
            self.assertEqual(found['control.tar.gz'], b'odd')
            with tarfile.open(fileobj=io.BytesIO(found['data.tar.gz']), mode='r:gz') as archive:
                for name in names:
                    entry=archive.getmember(name)
                    self.assertEqual((entry.uid,entry.gid,entry.mode), (5999,5000,0o770))
                    self.assertEqual((entry.uname,entry.gname), ('prisoner','jailer'))
                self.assertEqual(archive.extractfile('usr/palm/example.txt').read(), b'hello')

if __name__ == '__main__': unittest.main()
