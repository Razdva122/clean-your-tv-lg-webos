import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import importlib.util
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
HAS_QT = importlib.util.find_spec('PySide6') is not None
if HAS_QT:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage, QColor
    from cytv.wallpaper_gui import WallpaperDialog
    from cytv.gui import Wizard

@unittest.skipUnless(HAS_QT, 'Optional desktop Qt dependency is not installed')
class WallpaperGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def test_storage_estimates_remain_visible_after_transfer_status_changes(self):
        dialog=WallpaperDialog(); self.addCleanup(dialog.close)
        message='Storage estimate (Video cache): required 12.0 MiB; available 8.0 MiB; shortfall 4.0 MiB.'
        dialog.show_progress(message)
        dialog.show_progress('Sending wallpaper…')
        self.assertIn('shortfall 4.0 MiB',dialog.storage_info.text())
        self.assertEqual(dialog.status.text(),'Sending wallpaper…')

    def test_crop_quality_and_independent_home_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'source.png'; image=QImage(3840,2160,QImage.Format.Format_RGB32); image.fill(QColor('blue')); image.save(str(file))
            dialog=WallpaperDialog(); self.addCleanup(dialog.close); dialog.load_file(str(file))
            self.assertIn('3840 × 2160',dialog.source_info.text()); self.assertIn('4K',dialog.source_info.text())
            dialog.zoom.setValue(200); self.assertEqual(dialog.crop(),(960,540,1920,1080)); self.assertNotIn('4K',dialog.source_info.text())
            dialog.horizontal.setValue(0); self.assertEqual(dialog.crop()[0],0)
        with patch('cytv.i18n.configure'):
            wizard=Wizard(); self.addCleanup(wizard.close)
            self.assertEqual(wizard.wallpapers_button.text(),'Wallpapers')
            wizard.running=True; wizard.open_wallpapers(); self.assertFalse(hasattr(wizard,'wallpaper_dialog'))
            wizard.running=False; wizard.open_wallpapers(); self.assertTrue(wizard.wallpaper_dialog.isVisible()); wizard.wallpaper_dialog.close()

    def test_video_selection_uses_worker_and_disables_photo_crop(self):
        dialog=WallpaperDialog(); self.addCleanup(dialog.close)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'clip.mp4'; source.write_bytes(b'video')
            with patch('cytv.wallpaper_gui.wallpaper.load_image',side_effect=AssertionError('video must not enter photo decoder')):
                dialog.load_file(str(source))
            self.assertTrue(dialog.send_button.isEnabled())
            self.assertFalse(dialog.zoom.isEnabled())
            self.assertIn('clip.mp4',dialog.source_info.text())
            dialog.address.setText('192.168.1.2'); dialog.pin.setText('123456')
            with patch('cytv.wallpaper_gui.wallpaper.prepare_video',return_value={}) as prepare,patch('cytv.wallpaper_gui.wallpaper.upload',return_value='received'):
                dialog.send(); end=time.monotonic()+3
                while dialog.busy and time.monotonic()<end: self.app.processEvents(); time.sleep(.01)
                self.assertFalse(dialog.busy); prepare.assert_called_once()
                self.assertIn('Apply',dialog.status.text()); self.assertFalse(dialog.zoom.isEnabled())
            image=QImage(640,360,QImage.Format.Format_RGB32); image.fill(QColor('blue')); photo=Path(tmp)/'photo.png'; image.save(str(photo))
            dialog.load_file(str(photo)); self.assertTrue(dialog.zoom.isEnabled())

    def test_background_cancel_and_received_requires_tv_apply(self):
        started=threading.Event()
        def preparation(path,crop,cancel,progress):
            started.set()
            while not cancel.wait(.01): pass
            from cytv.wallpaper import Cancelled
            raise Cancelled()
        dialog=WallpaperDialog(); self.addCleanup(dialog.close)
        dialog.path='unused.png'; dialog.image=QImage(640,360,QImage.Format.Format_RGB32)
        dialog.address.setText('192.168.1.2'); dialog.pin.setText('123456')
        with patch('cytv.wallpaper_gui.wallpaper.prepare',side_effect=preparation):
            dialog.send(); self.assertTrue(started.wait(1)); self.assertTrue(dialog.busy); dialog.cancel_work()
            end=time.monotonic()+3
            while dialog.busy and time.monotonic()<end: self.app.processEvents(); time.sleep(.01)
            self.assertFalse(dialog.busy); self.assertIn('Cancelled',dialog.status.text()); self.assertTrue(dialog.cancel_button.isEnabled())
        dialog.pin.setText('123456')
        with patch('cytv.wallpaper_gui.wallpaper.prepare',return_value={}),patch('cytv.wallpaper_gui.wallpaper.upload',return_value='received'):
            dialog.send(); end=time.monotonic()+3
            while dialog.busy and time.monotonic()<end: self.app.processEvents(); time.sleep(.01)
            self.assertIn('Apply',dialog.status.text()); self.assertIn('Received',dialog.status.text())

    def test_closing_main_window_cancels_active_wallpaper_worker(self):
        started=threading.Event()
        def preparation(path,crop,cancel,progress):
            started.set(); cancel.wait(3)
            from cytv.wallpaper import Cancelled
            raise Cancelled()
        with patch('cytv.i18n.configure'):
            wizard=Wizard(); wizard.show(); self.addCleanup(wizard.close); wizard.open_wallpapers()
        dialog=wizard.wallpaper_dialog; dialog.path='unused.png'; dialog.image=QImage(640,360,QImage.Format.Format_RGB32)
        dialog.address.setText('192.168.1.2'); dialog.pin.setText('123456')
        with patch('cytv.wallpaper_gui.wallpaper.prepare',side_effect=preparation):
            dialog.send(); self.assertTrue(started.wait(1)); wizard.close()
            deadline=time.monotonic()+3
            while dialog.busy and time.monotonic()<deadline: self.app.processEvents(); time.sleep(.01)
            self.assertFalse(dialog.busy); self.assertTrue(dialog.cancel_event.is_set())
            self.assertFalse(wizard.isVisible())

    def test_localized_wallpaper_strings_cover_all_desktop_locales(self):
        from cytv import translations
        rows=Path(__file__).resolve().parents[2]/'cytv/wallpaper_gui.py'
        import ast
        keys={'Zoom','Horizontal position','Vertical position','4K + 1080p video','1080p video','Image only; source is below 1080p', 'Received by TV. Choose Apply on the TV to use this wallpaper.'}
        for node in ast.walk(ast.parse(rows.read_text(encoding='utf-8'))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tr' and node.args and isinstance(node.args[0],ast.Constant): keys.add(node.args[0].value)
        for key in keys:
            for code in translations.LANGS:
                with self.subTest(key=key,language=code): self.assertTrue(translations.MESSAGES[key][code])

    def test_escape_cancels_worker_before_closing_dialog(self):
        started=threading.Event()
        def preparation(path,crop,cancel,progress):
            started.set(); cancel.wait(3)
            from cytv.wallpaper import Cancelled
            raise Cancelled()
        dialog=WallpaperDialog(); dialog.show(); self.addCleanup(dialog.close)
        dialog.path='unused.png'; dialog.image=QImage(640,360,QImage.Format.Format_RGB32)
        dialog.address.setText('192.168.1.2'); dialog.pin.setText('123456')
        with patch('cytv.wallpaper_gui.wallpaper.prepare',side_effect=preparation):
            dialog.send(); self.assertTrue(started.wait(1)); dialog.reject()
            self.assertTrue(dialog.cancel_event.is_set())
            deadline=time.monotonic()+3
            while dialog.busy and time.monotonic()<deadline: self.app.processEvents(); time.sleep(.01)
            self.assertFalse(dialog.busy); self.assertFalse(dialog.isVisible())

    def test_catalog_source_scan_uses_utf8_under_legacy_windows_text_default(self):
        original_read=Path.read_text
        def legacy_read(path,*args,**kwargs):
            if not args and not kwargs.get('encoding'): kwargs['encoding']='cp1252'
            return original_read(path,*args,**kwargs)
        with patch.object(Path,'read_text',autospec=True,side_effect=legacy_read):
            self.test_localized_wallpaper_strings_cover_all_desktop_locales()
