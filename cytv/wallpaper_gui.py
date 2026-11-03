"""Independent photo-to-wallpaper flow; no installer, SSH or pairing state."""
import threading

from PySide6.QtCore import QObject, Signal, QRect, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                              QLineEdit, QProgressBar, QPushButton, QSlider, QVBoxLayout)
from cytv import wallpaper
from cytv.i18n import translate as tr
from cytv.gui_style import STYLE


class WorkerEvents(QObject):
    progress = Signal(str)
    finished = Signal(str)


class WallpaperDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Wallpapers'))
        self.setStyleSheet(parent.styleSheet() if parent is not None else STYLE)
        self.setStyleSheet(self.styleSheet() + '\nQSlider::groove:horizontal { height: 4px; background: #51483e; border-radius: 2px; }'
                           'QSlider::sub-page:horizontal { background: #b49c7e; border-radius: 2px; }'
                           'QSlider::handle:horizontal { width: 16px; margin: -6px 0; background: #e0d4c4; border: 1px solid #8e7b68; border-radius: 8px; }'
                           'QSlider::handle:horizontal:focus { border: 2px solid #fff8eb; }')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(740,740)
        self.busy = False
        self.path = None
        self.image = None
        self.worker = None
        self.close_when_done = False
        self.events = WorkerEvents(self)
        self.events.progress.connect(lambda text: self.status.setText(tr(text)))
        self.events.finished.connect(self.finished_work)
        layout = QVBoxLayout(self)
        title = QLabel(tr('Your photo on your TV')); title.setObjectName('title'); layout.addWidget(title)
        instructions = QLabel(tr('On your TV, open Settings → Wallpapers → Receive from CYTV. Keep that screen open, then enter its private IPv4 address and six-digit PIN below.'))
        instructions.setWordWrap(True); layout.addWidget(instructions)
        self.choose = QPushButton(tr('Choose JPG or PNG')); self.choose.clicked.connect(self.choose_file); layout.addWidget(self.choose)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setFixedHeight(170); layout.addWidget(self.preview)
        self.source_info = QLabel(tr('Choose an image to preview the 16:9 crop.')); self.source_info.setWordWrap(True); layout.addWidget(self.source_info)
        form = QFormLayout(); layout.addLayout(form)
        self.zoom = QSlider(Qt.Orientation.Horizontal); self.zoom.setRange(100,400); self.zoom.setValue(100)
        self.horizontal = QSlider(Qt.Orientation.Horizontal); self.horizontal.setRange(0,100); self.horizontal.setValue(50)
        self.vertical = QSlider(Qt.Orientation.Horizontal); self.vertical.setRange(0,100); self.vertical.setValue(50)
        for key,widget in [('Zoom',self.zoom),('Horizontal position',self.horizontal),('Vertical position',self.vertical)]:
            widget.setAccessibleName(tr(key)); widget.valueChanged.connect(self.update_preview); form.addRow(tr(key),widget)
        self.address = QLineEdit(); self.address.setPlaceholderText('192.168.1.2'); self.address.setMaxLength(15)
        self.pin = QLineEdit(); self.pin.setMaxLength(6); self.pin.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr('TV private IPv4 address'),self.address); form.addRow(tr('TV receiving PIN'),self.pin)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.progress = QProgressBar(); self.progress.setRange(0,0); self.progress.setTextVisible(False); self.progress.hide(); layout.addWidget(self.progress)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        self.send_button = QPushButton(tr('Prepare and send wallpaper')); self.send_button.setEnabled(False); self.send_button.setProperty('primary',True); self.send_button.clicked.connect(self.send); buttons.addWidget(self.send_button)
        self.cancel_button = QPushButton(tr('Close')); self.cancel_button.clicked.connect(self.cancel_or_close); buttons.addWidget(self.cancel_button)

    def choose_file(self):
        path,_ = QFileDialog.getOpenFileName(self,tr('Choose JPG or PNG'),'','Images (*.jpg *.jpeg *.png)')
        if path:
            try: self.load_file(path)
            except (ValueError,OSError) as error: self.status.setText(tr(str(error)))

    def load_file(self,path):
        image = wallpaper.load_image(path)
        self.path,self.image = path,image
        self.zoom.setValue(100); self.horizontal.setValue(50); self.vertical.setValue(50)
        self.update_preview(); self.send_button.setEnabled(True); self.status.clear()

    def crop(self):
        return wallpaper.crop_rect(self.image.width(),self.image.height(),self.zoom.value()/100,self.horizontal.value()/100,self.vertical.value()/100)

    def update_preview(self):
        if self.image is None: return
        crop = self.crop()
        preview = self.image.copy(QRect(*crop)).scaled(560,170,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        self.preview.setPixmap(QPixmap.fromImage(preview))
        quality = '4K + 1080p video' if crop[2] >= 3840 else '1080p video' if crop[2] >= 1920 else 'Image only; source is below 1080p'
        self.source_info.setText(tr('Original') + f': {self.image.width()} × {self.image.height()} · ' + tr('Crop') + f': {crop[2]} × {crop[3]}\n' + tr(quality))

    def send(self):
        if self.busy or self.path is None: return
        try: wallpaper.destination(self.address.text().strip(),self.pin.text())
        except ValueError as error: self.status.setText(tr(str(error))); return
        path,crop,host,pin = self.path,self.crop(),self.address.text().strip(),self.pin.text()
        self.cancel_event = threading.Event()
        self.busy = True
        self.close_when_done = False
        self.set_controls(False); self.progress.show(); self.cancel_button.setText(tr('Cancel'))
        self.status.setText(tr('Preparing wallpaper…'))
        def work():
            try:
                envelope = wallpaper.prepare(path,crop=crop,cancel=self.cancel_event,progress=self.events.progress.emit)
                wallpaper.upload(host,pin,envelope,cancel=self.cancel_event,progress=self.events.progress.emit)
                message = 'Received by TV. Choose Apply on the TV to use this wallpaper.'
            except wallpaper.Cancelled: message = 'Cancelled. Your current TV wallpaper is unchanged.'
            except (ValueError,OSError) as error: message = str(error)
            except Exception: message = 'Wallpaper preparation failed. Choose another image and try again.'
            self.events.finished.emit(message)
        self.worker = threading.Thread(target=work,daemon=True); self.worker.start()

    def set_controls(self,enabled):
        for widget in (self.choose,self.zoom,self.horizontal,self.vertical,self.address,self.pin,self.send_button): widget.setEnabled(enabled)

    def finished_work(self,message):
        self.busy = False
        self.pin.clear()
        self.set_controls(True); self.cancel_button.setEnabled(True); self.progress.hide(); self.cancel_button.setText(tr('Close')); self.status.setText(tr(message))
        if self.close_when_done: self.close()

    def cancel_work(self):
        if self.busy:
            self.cancel_event.set(); self.status.setText(tr('Cancelling…')); self.cancel_button.setEnabled(False)

    def cancel_or_close(self):
        if self.busy: self.cancel_work()
        else: self.close()

    def reject(self):
        self.close()

    def closeEvent(self,event):
        if self.busy:
            self.close_when_done = True; self.cancel_work(); event.ignore()
        else:
            self.pin.clear(); self.image = None; self.path = None; self.preview.clear(); event.accept()
