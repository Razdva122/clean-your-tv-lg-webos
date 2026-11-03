import importlib.util
from pathlib import Path
import sys
import os
import subprocess
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
            self.assertEqual(wallpaper.ffmpeg_executable(),'/application/runtime/ffmpeg/ffmpeg.exe')
        self.assertIn('imageio-ffmpeg==0.6.0',(Path(__file__).resolve().parents[2]/'cytv/build-requirements.txt').read_text())
