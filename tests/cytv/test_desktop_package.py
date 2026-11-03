import os
import runpy
import shutil
import tempfile
import unittest
import zipfile
import json
from pathlib import Path
from unittest.mock import patch


class WindowsDesktopPackageTests(unittest.TestCase):
    def test_windows_build_is_windowed_and_archive_keeps_runtime(self):
        root = Path(__file__).resolve().parents[2]
        packaging = runpy.run_path(str(root / 'scripts/desktop_packaging.py'))
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            def ffmpeg_args(root):
                directory = root / 'build/cytv/ffmpeg'
                directory.mkdir(parents=True)
                binary = directory / 'ffmpeg.exe'
                binary.write_bytes(b'FFmpeg package fixture')
                notice = directory / 'LICENSE.txt'
                notice.write_text('GNU GENERAL PUBLIC LICENSE fixture')
                return ['--add-binary', str(binary) + os.pathsep + 'ffmpeg', '--add-data', str(notice) + os.pathsep + 'ffmpeg']
            def run(command, **kwargs):
                if 'PyInstaller' in command:
                    self.assertIn('--windowed', command)
                    self.assertIn('--onedir', command)
                    self.assertIn('--icon', command)
                    self.assertIn('--add-binary', command)
                    frozen = project / 'dist/desktop/cytv-desktop'
                    (frozen / '_internal/payload').mkdir(parents=True)
                    (frozen / 'cytv-desktop.exe').write_bytes(b'MZ-test-GUI')
                    (frozen / '_internal/Qt6Widgets.dll').write_bytes(b'qt-runtime')
                    ffmpeg = command[command.index('--add-binary') + 1].split(os.pathsep)[0]
                    (frozen / '_internal/ffmpeg').mkdir()
                    shutil.copyfile(ffmpeg, frozen / '_internal/ffmpeg/ffmpeg.exe')
                    shutil.copyfile(Path(ffmpeg).with_name('LICENSE.txt'), frozen / '_internal/ffmpeg/LICENSE.txt')
                    (frozen / '_internal/payload/payload.json').write_text('{}')
            with patch('sys.platform', 'win32'), patch('platform.machine', return_value='AMD64'), patch('subprocess.run', side_effect=run) as invoke, patch.dict(packaging['build_desktop'].__globals__, {'ffmpeg_bundle_args': ffmpeg_args}):
                packaging['build_desktop'](project, project / 'payload', {}, '0.2.11')
            archive = project / 'dist/cytv-windows-x64-desktop.zip'
            self.assertTrue(archive.is_file(), 'Windows GUI packaging was skipped')
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(bundle.read('cytv-desktop/_internal/Qt6Widgets.dll'), b'qt-runtime')
                self.assertIn('cytv-desktop/cytv-desktop.exe', bundle.namelist())
                self.assertIn('cytv-desktop/_internal/ffmpeg/ffmpeg.exe', bundle.namelist())
                self.assertIn(b'GNU GENERAL PUBLIC LICENSE', bundle.read('cytv-desktop/_internal/ffmpeg/LICENSE.txt'))
                self.assertEqual(json.loads(bundle.read('cytv-desktop/version.json'))['cytv'], '0.2.11')
            self.assertTrue(any('--smoke-test' in c.args[0] for c in invoke.call_args_list))


@unittest.skipIf(os.name == 'nt', 'Debian package tree requires POSIX symlinks and permissions')
class DesktopPackageTests(unittest.TestCase):
    def test_frozen_cli_adapter_preserves_terminal_error_color(self):
        from cytv.terminal import Console
        with patch('sys.argv', ['cytv-desktop', '--check-payload']), \
             patch('cytv.terminal.supports_ansi', return_value=True), \
             patch.dict(os.environ, {}, clear=True), patch('cytv.cli.main', return_value=0) as main, \
             self.assertRaises(SystemExit):
            runpy.run_module('cytv.desktop_entry', run_name='__main__')
        console = main.call_args.kwargs['write']
        self.assertIsInstance(console, Console)
        self.assertTrue(console.color)

    def test_installed_launcher_uses_packaged_executable_without_terminal(self):
        root = Path(__file__).resolve().parents[2]
        packaging = runpy.run_path(str(root / 'scripts/desktop_packaging.py'))
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            frozen = directory / 'frozen'
            frozen.mkdir()
            (frozen / 'cytv-desktop').write_bytes(b'fake executable')
            (frozen / 'libQt.so').write_bytes(b'fake library')
            (frozen / 'libQt.so.6').symlink_to('libQt.so')
            tree = packaging['deb_tree'](root, frozen, '0.2.0', directory / 'deb')
            desktop = (tree / 'usr/share/applications/cytv.desktop').read_text()
            self.assertIn('Terminal=false\n', desktop)
            command = next(line[5:] for line in desktop.splitlines() if line.startswith('Exec='))
            executable = tree / command.lstrip('/')
            self.assertTrue(executable.is_file())
            self.assertTrue(executable.stat().st_mode & 0o111)
            self.assertTrue((tree / 'opt/clean-your-tv/libQt.so.6').is_symlink())
            control = (tree / 'DEBIAN/control').read_text()
            self.assertIn('Architecture: amd64', control)
            self.assertIn('libxcb-cursor0', control)
            self.assertFalse((tree / 'DEBIAN/postinst').exists())
            self.assertEqual((tree / 'usr/share/icons/hicolor/256x256/apps/cytv.png').read_bytes(),
                             (root / 'assets/icons/installer-256.png').read_bytes())
