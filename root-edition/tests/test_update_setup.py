import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from updater.bootstrap import permission_plan, verify_bundle


class SetupTests(unittest.TestCase):
    def test_permissions_pin_service_methods_and_callers(self):
        files=permission_plan()
        text=json.dumps(files)
        self.assertNotIn('"all"',text);self.assertNotIn('"public"',text)
        client=files['client.json'];self.assertIn('com.cleanyourtv.root.preview',client)
        self.assertNotIn('org.other',client)
        role=files['role.json'];self.assertEqual(role['allowedNames'],['com.cleanyourtv.root.updater.service'])
        self.assertEqual(role['type'],'regular')

    def test_standalone_build_is_verified_and_private_files_excluded(self):
        source_fonts={name:(ROOT.parent/'launcher/fonts'/name).read_bytes() for name in ('NotoSansSC.ttf','NotoSansTC.ttf')}
        spec=importlib.util.spec_from_file_location('updater_build',ROOT/'build_updater.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp).resolve()/'bundle';module.build(out)
            manifest=verify_bundle(out)
            self.assertIn('updater/core.py',manifest['files'])
            self.assertIn('installation.py',manifest['files'])
            result=subprocess.run([sys.executable,'-I','-B','-c',
                'import sys;sys.path.insert(0,sys.argv[1]);import installation,install_driver,install_device,system_setup,root_package,package_data,startup_guard;'
                'assert installation.Store.__module__ == "updater.store"',str(out)],
                cwd=Path(temp),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('root-updater.ipk',manifest['files'])
            self.assertIn('updater/ca-bundle.crt',manifest['files'])
            self.assertIn('updater/ca-LICENSE.txt',manifest['files'])
            self.assertEqual((out/'updater/ca-bundle.crt').read_bytes(),
                             (ROOT.parent/'renewal-service/ca-bundle.crt').read_bytes())
            import io, tarfile
            sys.path.insert(0, str(ROOT.parent))
            from cytv.package import read_ar
            data = read_ar((out/'root-updater.ipk').read_bytes())['data.tar.gz']
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
                prefix = 'usr/palm/applications/com.cleanyourtv.root.updater/'
                version = json.loads((ROOT.parent/'release-versions.json').read_text())['updater']
                from scripts.chinese_fonts import prepare_fonts
                from fontTools.ttLib import TTFont
                prepared=prepare_fonts()
                for script,label in (('SC','简体中文'),('TC','繁體中文')):
                    name='NotoSans'+script+'.ttf';raw=archive.extractfile(prefix+'fonts/'+name).read()
                    self.assertEqual(raw,prepared['fonts/'+name])
                    face=TTFont(io.BytesIO(raw))
                    self.assertNotIn('fvar',face)
                    self.assertEqual(face['OS/2'].usWeightClass,400)
                    cmap=face.getBestCmap()
                    self.assertTrue(all(code in cmap and face.getGlyphID(cmap[code])>0 for code in map(ord,label+'年月日星期週')))
                    self.assertEqual((ROOT.parent/'launcher/fonts'/name).read_bytes(),source_fonts[name])
                for name in ('NotoSansSC-OFL.txt','NotoSansTC-OFL.txt'):
                    self.assertEqual(archive.extractfile(prefix+'fonts/'+name).read(),
                                     (ROOT.parent/'launcher/fonts'/name).read_bytes())
                import startup_hook
                self.assertEqual(archive.extractfile(prefix+'startup.sh').read(),startup_hook.packaged_content('com.cleanyourtv.root.updater'))
                self.assertEqual(archive.getmember(prefix+'startup.sh').mode,0o755)
                self.assertEqual(json.loads(archive.extractfile(prefix+'appinfo.json').read())['version'], version)
                self.assertEqual(json.loads(archive.extractfile('usr/palm/packages/com.cleanyourtv.root.updater/packageinfo.json').read())['version'], version)
                self.assertEqual(json.loads(archive.extractfile('usr/palm/services/com.cleanyourtv.root.updater.service/package.json').read())['version'], version)
                self.assertTrue(archive.extractfile(prefix+'system-updates.js').read())
                html = archive.extractfile(prefix+'index.html').read().decode()
                self.assertLess(html.index('system-updates.js'), html.index('root-updates.js'))
                self.assertLess(html.index('release-notes.js'), html.index('root-updates.js'))
                self.assertEqual(archive.extractfile(prefix+'release-notes.js').read(), (ROOT.parent/'launcher/release-notes.js').read_bytes())
            control = read_ar((out/'root-updater.ipk').read_bytes())['control.tar.gz']
            with tarfile.open(fileobj=io.BytesIO(control), mode='r:gz') as archive:
                self.assertIn('Version: '+version+'\n', archive.extractfile('control').read().decode())
            self.assertFalse(any('state/' in name for name in manifest['files']))
            # This fixed source file cleans private data; it contains no device data.
            self.assertEqual({name for name in manifest['files'] if 'private' in name},
                             {'cleanup_no_root_private.js'})
            from cytv.no_root_cleanup import PRIVATE_CLEANUP_PROGRAM
            self.assertEqual((out/'cleanup_no_root_private.js').read_bytes(),
                             PRIVATE_CLEANUP_PROGRAM.encode())
            (out/'updater/core.py').write_text('changed')
            with self.assertRaises(ValueError):verify_bundle(out)

    def test_distributed_setup_runs_readonly_plan_without_source_checkout(self):
        def load(name):
            spec=importlib.util.spec_from_file_location('bundle_test_'+name,ROOT/(name+'.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();updater=root/'updater';baseline=root/'baseline'
            load('build').build(baseline);load('build_updater').build(updater)
            result=subprocess.run([sys.executable,str(updater/'setup-updater.py'),'--bundle',str(updater),'--baseline',str(baseline)],cwd=root,capture_output=True,text=True)
            self.assertEqual(0,result.returncode,result.stderr)
            plan=json.loads(result.stdout)
            self.assertFalse(plan['replaces_root_runtime'])
            self.assertTrue(plan['requires_root_mode_disabled'])

    def test_fixed_cli_rejects_untrusted_fields(self):
        from updater.cli import validate_request
        for method,payload in (('shell',{}),('install',{'version':'0.2.0','profile':{},'url':'bad'}),('ready',{'transaction':'../escape','version':'0.2.0'}),('check',{'caller':'com.cleanyourtv.root.preview'})):
            with self.assertRaises(ValueError):validate_request(method,payload)


if __name__=='__main__':unittest.main()

class HostBoundaryTests(unittest.TestCase):
    def test_distributed_host_product_entrypoints_verify_without_posix_device_modules(self):
        def source(name):
            spec=importlib.util.spec_from_file_location('host_boundary_'+name,ROOT/(name+'.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();updater=root/'updater';baseline=root/'root'
            source('build').build(baseline);source('build_updater').build(updater)
            code='''import sys,builtins,subprocess,runpy
sys.path.insert(0,sys.argv[1])
original=builtins.__import__
def importing(name,*args,**kwargs):
 if name in ('fcntl','termios'):raise ImportError('device-only POSIX module on Windows-like host')
 return original(name,*args,**kwargs)
builtins.__import__=importing
calls=[]
def transport(args,**kwargs):calls.append(args)
subprocess.run=transport
from updater.bootstrap import verify_bundle
import setup
import updater.package as device_package
real_os=device_package.os
class NoDeviceFlags:
 def __getattr__(self,name):
  if name in ('O_NOFOLLOW','O_NONBLOCK'):raise AttributeError(name)
  return getattr(real_os,name)
device_package.os=NoDeviceFlags()
verify_bundle(sys.argv[1],reader=setup.bundle_bytes)
setup.execute('install','living-room',sys.argv[2],updater_bundle=sys.argv[1],operation='a'*32,run=transport)
assert 'install_driver.py install' in calls[-1][-1]
assert not any('deploy.py install' in str(call) for call in calls)
updater=sys.argv[1];baseline=sys.argv[2]
controller=runpy.run_path(updater+'/setup-updater.py')
sys.argv=['setup-updater','--bundle',updater,'--baseline',baseline,'--ssh','living-room','--apply','--operation','b'*32]
controller['main']()
assert '--operation '+('b'*32) in calls[-1][-1]
print('host setup product verification without fcntl/termios: OK')
'''
            result=subprocess.run([sys.executable,'-I','-B','-c',code,str(updater),str(baseline)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('without fcntl/termios: OK',result.stdout)
