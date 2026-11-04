import importlib.util
from pathlib import Path
import sys
import os
import subprocess
import runpy
import tempfile
import unittest
from unittest.mock import patch
HAS_BUILD_DEPS = importlib.util.find_spec('PySide6') is not None and importlib.util.find_spec('imageio_ffmpeg') is not None
if HAS_BUILD_DEPS:
    from cytv import wallpaper

@unittest.skipUnless(HAS_BUILD_DEPS, 'Optional desktop build dependencies are not installed')
class WallpaperPackageTests(unittest.TestCase):
    def test_binary_packaging_ignores_runtime_override_and_preserves_license(self):
        spec=importlib.util.spec_from_file_location('desktop_packaging',Path(__file__).resolve().parents[2]/'scripts/desktop_packaging.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            with patch.dict('os.environ',{'IMAGEIO_FFMPEG_EXE':'/untrusted/ffmpeg'}):
                args=module.ffmpeg_bundle_args(directory)
            self.assertIn('--add-binary',args); self.assertTrue(any('ffmpeg' in arg for arg in args)); self.assertIn('--add-data',args)
            staged = Path(args[args.index('--add-binary')+1].split(os.pathsep)[0])
            self.assertIn('ffmpeg version',subprocess.check_output([str(staged),'-version'],text=True))
            self.assertIn('GNU GENERAL PUBLIC LICENSE',staged.with_name('LICENSE.txt').read_text())
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS','/application/runtime',create=True),patch('sys.platform','win32'):
            self.assertEqual(wallpaper.ffmpeg_executable(),str(Path('/application/runtime')/'ffmpeg'/'ffmpeg.exe'))
        self.assertIn('imageio-ffmpeg==0.6.0',(Path(__file__).resolve().parents[2]/'cytv/build-requirements.txt').read_text())

    def test_desktop_frozen_runtime_probe_executes_actual_bundled_ffmpeg(self):
        from cytv.runtime_check import check_ffmpeg_runtime
        spec=importlib.util.spec_from_file_location('desktop_packaging',Path(__file__).resolve().parents[2]/'scripts/desktop_packaging.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.ffmpeg_bundle_args(Path(tmp))
            runtime=Path(tmp)/'build/cytv'
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',str(runtime),create=True),patch.dict(os.environ,{'IMAGEIO_FFMPEG_EXE':'/untrusted/ffmpeg'}):
                check_ffmpeg_runtime()
                binary=runtime/'ffmpeg'/('ffmpeg.exe' if sys.platform=='win32' else 'ffmpeg')
                binary.unlink()
                with self.assertRaises(OSError): check_ffmpeg_runtime()
                binary.write_bytes(b'not an executable encoder'); binary.chmod(0o755)
                with self.assertRaises(OSError): check_ffmpeg_runtime()
                with patch.object(sys,'argv',['cytv-desktop','--check-runtime']),patch.object(sys,'stderr',None):
                    with self.assertRaises(SystemExit) as stopped: runpy.run_module('cytv.desktop_entry',run_name='__main__')
                    self.assertEqual(stopped.exception.code,1)

    def test_only_gui_frozen_check_runtime_runs_bundled_ffmpeg_probe(self):
        from cytv import runtime_check
        for frozen,flag,expected in [(True,'--check-runtime',True),(False,'--check-runtime',False),(True,'--version',False)]:
            with self.subTest(frozen=frozen,flag=flag),patch.object(sys,'frozen',frozen,create=True),patch.object(sys,'argv',['cytv-desktop',flag]),patch('cytv.cli.main',return_value=0),patch.object(runtime_check,'check_ffmpeg_runtime') as probe:
                with self.assertRaises(SystemExit): runpy.run_module('cytv.desktop_entry',run_name='__main__')
                self.assertEqual(probe.called,expected)

    def test_runtime_workflow_runs_wallpaper_tests_and_uses_release_binary_arguments(self):
        root=Path(__file__).resolve().parents[2]
        workflow=(root/'.github/workflows/cytv-runtime.yml').read_text()
        for text in ('cytv/wallpaper*.py','cytv/licenses/**','tests/cytv/test_wallpaper*.py','test_wallpaper*.py','actions/setup-node@v4','ffmpeg_bundle_args(root)'):
            self.assertIn(text,workflow)
        spec=importlib.util.spec_from_file_location('desktop_packaging',root/'scripts/desktop_packaging.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            args=module.ffmpeg_bundle_args(Path(tmp))
            self.assertIn('--exclude-module',args)
            self.assertEqual(args[args.index('--exclude-module')+1],'imageio_ffmpeg')

    def test_windowed_missing_or_tampered_encoder_exits_without_uncaught_exception(self):
        from cytv import runtime_check
        for error in (OSError('missing binary'),RuntimeError('invalid FFmpeg version'),subprocess.CalledProcessError(1,['ffmpeg']),subprocess.TimeoutExpired(['ffmpeg'],10)):
            with self.subTest(error=type(error).__name__),patch.object(sys,'frozen',True,create=True),patch.object(sys,'argv',['cytv-desktop','--check-runtime']),patch.object(sys,'stderr',None),patch.object(runtime_check,'check_ffmpeg_runtime',side_effect=error),patch('cytv.cli.main') as main:
                with self.assertRaises(SystemExit) as stopped: runpy.run_module('cytv.desktop_entry',run_name='__main__')
                self.assertEqual(stopped.exception.code,1); main.assert_not_called()
