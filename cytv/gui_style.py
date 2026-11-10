"""Desktop presentation only; installation stays in the semantic CLI bridge."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPalette, QPen, QPixmap, QPainterPath
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QComboBox, QRadioButton, QCheckBox, QLabel, QSizePolicy

# Approved B1 marks retain their original colours. The working UI uses quiet
# warm charcoal surfaces and restrained controls rather than bright brand fills.
STYLE = '''
QMainWindow, QMessageBox, QDialog { background: #1d1c1a; }
QWidget { font-family: "Segoe UI", "Noto Sans", "Noto Sans SC", "Noto Sans TC", "Helvetica Neue"; font-size: 16px; color: #f3ede3; }
QWidget#sidebar { background: #171614; }
QLabel { background: transparent; }
QLabel#railTitle { color: #e0d4c4; font-size: 14px; font-weight: 600; }
QLabel#railNote, QLabel#version { color: #c0b5a5; font-size: 14px; }
QLabel#version { font-size: 13px; }
QFrame#step { border: none; border-radius: 10px; background: transparent; }
QFrame#step[state="current"] { background: #302c27; }
QLabel#stepNumber { color: #c0b5a5; border: 1px solid #8e7b68; border-radius: 15px; font-weight: 600; }
QLabel#stepName { color: #c0b5a5; font-size: 14px; }
QFrame#step[state="current"] QLabel { color: #fff8eb; }
QFrame#step[state="current"] QLabel#stepNumber { background: #51483e; border-color: #b49c7e; }
QFrame#step[state="complete"] QLabel { color: #b9d4c5; }
QFrame#step[state="complete"] QLabel#stepNumber { border-color: #94b8a5; }
QFrame#step[state="error"] QLabel { color: #ff6b6b; }
QFrame#step[state="error"] QLabel#stepNumber { border-color: #ff6b6b; }
QLabel#badge { color: #d6c5ae; font-size: 14px; background: #302c27; border-radius: 11px; padding: 5px 12px; }
QLabel#title { font-size: 30px; font-weight: 700; color: #f3ede3; }
QLabel#title[state="error"], QLabel#badge[state="error"] { color: #ff6b6b; }
QLabel#subtitle { color: #c0b5a5; font-size: 15px; }
QTextBrowser { background: transparent; color: #c0b5a5; border: none; padding: 0; selection-background-color: #51483e; }
QWidget#form { background: #272521; border-radius: 12px; }
QFrame#runtimeChoice { background: #24221e; border: 1px solid #51483e; border-radius: 10px; }
QScrollArea#runtimeChoices { background: transparent; border: none; }
QScrollArea#installationSettings, QWidget#installationSettingsFields { background: #272521; border: none; }
QLabel#settingTitle { font-weight: 600; }
QLabel#settingHint { color: #c0b5a5; font-size: 14px; }
QFrame#settingsDivider { background: #51483e; border: none; }
QWidget#runtimeChoiceList { background: #2a2722; }
QLabel#choiceDetail { color: #c0b5a5; font-size: 15px; }
QLabel#promptTitle { font-size: 16px; font-weight: 600; }
QPushButton { background: #302d28; border: 1px solid #796956; border-radius: 8px; padding: 10px 16px; font-weight: 500; min-height: 22px; }
QPushButton:hover { background: #3a342d; border-color: #a28c73; }
QPushButton:pressed { background: #443b32; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border: 2px solid #d6c5ae; }
QPushButton[primary="true"] { background: #51483e; color: #fff8eb; border: 2px solid #8e7b68; font-weight: 600; }
QPushButton[primary="true"]:hover { background: #605447; border-color: #b49c7e; }
QPushButton[primary="true"]:pressed { background: #443b32; }
QPushButton[primary="true"]:focus { border-color: #fff8eb; }
QPushButton:disabled { background: #272521; color: #a79a88; border-color: #51483e; }
QPushButton#setupTV { background: #e0d4c4; color: #1d1c1a; border: 2px solid #e0d4c4; font-size: 18px; font-weight: 600; min-height: 32px; padding: 12px 16px; }
QPushButton#setupTV:hover { background: #f3ede3; border-color: #f3ede3; }
QPushButton#setupTV:pressed { background: #c9b89f; border-color: #c9b89f; }
QPushButton#setupTV:focus { border-color: #796956; }
QPushButton#setupTV:disabled { background: #272521; color: #a79a88; border-color: #51483e; }
QWidget#homeSecondaryActions QPushButton { min-height: 30px; }
QPushButton#maintenanceToggle:checked { background: #443b32; border-color: #d6c5ae; }
QWidget#maintenanceActions { background: #211f1b; border: 1px solid #51483e; border-radius: 8px; }
QPushButton#detailsToggle { background: transparent; border: none; text-align: left; padding: 4px 0; font-size: 14px; color: #d6c5ae; }
QPushButton#detailsToggle:focus { border: 2px solid #d6c5ae; padding: 2px; }
QPushButton#close { background: transparent; padding: 6px 16px; }
QLineEdit, QComboBox { background: #24221e; color: #f3ede3; border: 1px solid #8e7b68; border-radius: 7px; padding: 10px 12px; min-height: 22px; selection-background-color: #51483e; }
QComboBox { padding-right: 30px; }
QComboBox::down-arrow { image: none; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { color: #f3ede3; background: #24221e; selection-background-color: #51483e; selection-color: #fff8eb; padding: 6px; }
QComboBox:disabled { background: #272521; color: #a79a88; }
QComboBox#language { font-size: 14px; min-height: 18px; padding: 6px 30px 6px 10px; }
QProgressBar { background: #302c27; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #b49c7e; border-radius: 3px; }
QScrollBar:vertical { background: #272521; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #8e7b68; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
'''


class BrandSignature(QWidget):
    """Render the approved outlined lockup, without recreating its lettering."""
    def __init__(self, source):
        super().__init__()
        source = Path(source)
        if not source.is_file():
            source = Path(__file__).resolve().parents[1] / 'assets/brand/logo-stacked-dark.svg'
        self.renderer = QSvgRenderer(str(source))
        self.setFixedHeight(126)
        self.setAccessibleName('Clean Your TV / FOR LG webOS')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = min(self.width(), self.height() * 760 / 580)
        self.renderer.render(painter, QRectF((self.width() - width) / 2, 0, width, self.height()))
        painter.end()


class TVPreview(QWidget):
    """Resolution-independent illustration, with no network or image dependencies."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(206)
        self.setAccessibleName('Clean Your TV')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = min(self.width() / 560, self.height() / 206)
        p.translate((self.width() - 560 * scale) / 2, 0)
        p.scale(scale, scale)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#292622'))
        p.drawRoundedRect(QRectF(0, 8, 560, 190), 16, 16)
        # Quiet signal arcs connect the installer to the TV.
        p.setPen(QPen(QColor('#66594b'), 2))
        for size in (46, 72, 98):
            p.drawArc(QRectF(440-size/2, 104-size/2, size, size), -65*16, 130*16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#51483e'))
        p.drawRoundedRect(QRectF(118, 22, 326, 154), 9, 9)
        gradient = QLinearGradient(125, 30, 432, 168)
        gradient.setColorAt(0, QColor('#22201c'))
        gradient.setColorAt(1, QColor('#494238'))
        p.setBrush(gradient)
        p.drawRoundedRect(QRectF(125, 29, 312, 138), 4, 4)
        p.setPen(QColor('#fff8eb'))
        p.setFont(QFont('Noto Sans', 15, QFont.Weight.DemiBold))
        p.drawText(QRectF(146, 48, 270, 32), Qt.AlignmentFlag.AlignLeft, 'Clean Your TV')
        p.setPen(Qt.PenStyle.NoPen)
        for x, color in ((146, '#b4977d'), (214, '#dbb7a0'), (282, '#d6c5ab'), (350, '#a7d7c5')):
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(x, 98, 56, 43), 6, 6)
            p.setBrush(QColor('#292622'))
            p.drawRoundedRect(QRectF(x+13, 110, 30, 3), 1, 1)
            p.drawRoundedRect(QRectF(x+13, 119, 20, 3), 1, 1)
        p.setBrush(QColor('#51483e'))
        p.drawRoundedRect(QRectF(273, 176, 16, 9), 2, 2)
        p.drawRoundedRect(QRectF(244, 184, 74, 4), 2, 2)
        p.end()


class WrappedLabel(QLabel):
    """Reserve the actual wrapped height instead of clipping in a nested form."""
    def __init__(self, text):
        super().__init__(text)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMinimumHeight(self.heightForWidth(self.width()))


class Select(QComboBox):
    """A visible disclosure indicator on both native and Fusion styles."""
    def showPopup(self):
        # Qt paints the popup margins using the container's Base palette role.
        popup = self.view().window()
        palette = popup.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor('#24221e'))
        popup.setPalette(palette)
        super().showPopup()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#c0b5a5'), 1.5))
        x, y = self.width() - 18, self.height() // 2
        p.drawLine(x - 4, y - 2, x, y + 2)
        p.drawLine(x, y + 2, x + 4, y - 2)
        p.end()


class EditionOption(QRadioButton):
    """A keyboard-accessible radio option with a wrapping description."""
    def __init__(self, title, detail, key):
        super().__init__(title + ('\n' + detail if detail else ''))
        self.title, self.detail, self.key = title, detail, key
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(144)

    def sizeHint(self):
        return QSize(260, 144)

    def hitButton(self, position):
        return self.rect().contains(position)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isChecked()
        p.setBrush(QColor('#332d27' if selected else '#302c27' if self.underMouse() else '#292622'))
        p.setPen(QPen(QColor('#b49c7e' if selected or self.hasFocus() else '#796956'), 2 if selected or self.hasFocus() else 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 9, 9)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#f3ede3'), 1, Qt.PenStyle.DotLine))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(6, 6, -6, -6), 6, 6)
        p.setPen(QPen(QColor('#b49c7e' if selected else '#796956'), 1.5))
        p.setBrush(QColor('#b49c7e' if selected else '#292622'))
        p.drawEllipse(QRectF(16, 19, 16, 16))
        if selected:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#292622'))
            p.drawEllipse(QRectF(21, 24, 6, 6))
        p.setPen(QColor('#f3ede3'))
        font = self.font()
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(44, 16, self.width()-60, 36), Qt.TextFlag.TextWordWrap, self.title)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor('#c0b5a5'))
        p.drawText(QRectF(16, 52, self.width()-32, self.height()-60), Qt.TextFlag.TextWordWrap, self.detail)
        p.end()


class ThemeCard(QRadioButton):
    """Native exclusive selection with a packaged, offline theme screenshot."""
    def __init__(self, title, key, preview):
        super().__init__(title)
        self.key = key
        self.preview = QPixmap(str(preview))
        self.setAccessibleName(title)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setFixedHeight(166)

    def sizeHint(self):
        return QSize(220, 166)

    def minimumSizeHint(self):
        return QSize(110, 166)

    def hitButton(self, position):
        return self.rect().contains(position)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        selected = self.isChecked()
        p.setBrush(QColor('#332d27' if selected else '#302c27' if self.underMouse() else '#24221e'))
        p.setPen(QPen(QColor('#d6c5ae' if selected or self.hasFocus() else '#796956'), 2 if selected or self.hasFocus() else 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 10, 10)
        image = QRectF(10, 10, self.width()-20, self.height()-58)
        clip = QPainterPath()
        clip.addRoundedRect(image, 5, 5)
        p.save()
        p.setClipPath(clip)
        p.fillRect(image, QColor('#171614'))
        if not self.preview.isNull():
            size = self.preview.size().scaled(image.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
            target = QRectF(image.center().x()-size.width()/2, image.center().y()-size.height()/2, size.width(), size.height())
            p.drawPixmap(target, self.preview, QRectF(self.preview.rect()))
        p.restore()
        p.setPen(QColor('#f3ede3'))
        font = self.font();font.setBold(True);p.setFont(font)
        p.drawText(QRectF(14, self.height()-42, self.width()-48, 28), Qt.AlignmentFlag.AlignVCenter, self.text())
        circle = QRectF(self.width()-31, self.height()-34, 14, 14)
        p.setPen(QPen(QColor('#d6c5ae' if selected else '#8e7b68'), 1.5))
        p.setBrush(QColor('#d6c5ae' if selected else '#24221e'))
        p.drawEllipse(circle)
        if selected:
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#292622'))
            p.drawEllipse(circle.adjusted(4, 4, -4, -4))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#f3ede3'), 1, Qt.PenStyle.DotLine))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(6, 6, -6, -6), 7, 7)
        p.end()


class ToggleSwitch(QCheckBox):
    """Two-state switch retaining native checked state, focus and Space behavior."""
    def __init__(self, title, on_text, off_text):
        super().__init__(title)
        self.on_text, self.off_text = on_text, off_text
        self.setAccessibleName(title)
        self.setTristate(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggled.connect(lambda enabled:self.setAccessibleDescription(on_text if enabled else off_text))
        self.setAccessibleDescription(off_text)

    def state_font(self):
        font = QFont(self.font())
        font.setPixelSize(14)
        return font

    def sizeHint(self):
        metrics = QFontMetrics(self.state_font())
        return QSize(max(metrics.horizontalAdvance(self.on_text), metrics.horizontalAdvance(self.off_text))+76, 44)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, position):
        return self.rect().contains(position)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled, checked = self.isEnabled(), self.isChecked()
        if not enabled: p.setOpacity(.45)
        p.setFont(self.state_font())
        p.setPen(QColor('#f3ede3' if checked else '#c0b5a5'))
        p.drawText(QRectF(0, 0, self.width()-64, 44), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self.on_text if checked else self.off_text)
        track = QRectF(self.width()-54, 8, 50, 28)
        p.setPen(QPen(QColor('#b9d4c5' if checked else '#8e7b68'), 1))
        p.setBrush(QColor('#b9d4c5' if checked else '#302c27'))
        p.drawRoundedRect(track, 14, 14)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#1d1c1a' if checked else '#e0d4c4'))
        p.drawEllipse(QRectF(track.left()+(25 if checked else 4), 12, 20, 20))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#f3ede3'), 1, Qt.PenStyle.DotLine))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 6, 6)
        p.end()
