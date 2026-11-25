"""Small painted pieces: the on/off switch, the keycap "pills" that spell a shortcut, and the app icon."""
from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QPushButton, QWidget

from . import theme


def button(text: str, kind: str = "", tip: str = "") -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    return b


class Switch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(130)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 22)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, on: bool, animate: bool = False) -> None:
        if on == self._checked:
            return
        self._checked = on
        self._anim.stop()
        if animate:
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(1.0 if on else 0.0)
            self._anim.start()
        else:
            self._pos = 1.0 if on else 0.0
            self.update()

    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, v: float) -> None:
        self._pos = v
        self.update()

    pos = Property(float, _get_pos, _set_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.setChecked(not self._checked, animate=True)
            self.toggled.emit(self._checked)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        off, on = QColor("#2a3040"), QColor(theme.ACCENT)
        t = self._pos
        track = QColor(int(off.red() + (on.red() - off.red()) * t), int(off.green() + (on.green() - off.green()) * t),
                       int(off.blue() + (on.blue() - off.blue()) * t))
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, 38, 22), 11, 11)
        p.setBrush(QColor(theme.ACCENT_INK) if t > 0.5 else QColor("#aab1c3"))
        p.drawEllipse(QRectF(3 + 16 * t, 3, 16, 16))


class Pills(QWidget):
    """A shortcut drawn as keycaps: [Win] + [C]."""
    H, PAD, GAP = 26, 9, 16

    def __init__(self, parts=(), accent: bool = False, parent=None):
        super().__init__(parent)
        self._parts = list(parts)
        self._accent = accent
        self._font = QFont(theme.FONT)
        self._font.setPixelSize(12)
        self._font.setWeight(QFont.DemiBold)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setParts(self, parts) -> None:
        self._parts = list(parts)
        self.updateGeometry()
        self.update()

    def _widths(self):
        fm = QFontMetricsF(self._font)
        return [max(self.H, fm.horizontalAdvance(s) + 2 * self.PAD) for s in self._parts]

    def sizeHint(self) -> QSize:
        w = self._widths()
        return QSize(int(sum(w) + self.GAP * max(0, len(w) - 1)) + 2, self.H + 2)

    minimumSizeHint = sizeHint

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self._font)
        x, y = 1.0, (self.height() - self.H) / 2
        for i, (text, w) in enumerate(zip(self._parts, self._widths())):
            if i:
                p.setPen(QColor(theme.FAINT))
                p.drawText(QRectF(x - self.GAP, y, self.GAP, self.H), Qt.AlignCenter, "+")
            r = QRectF(x, y, w, self.H)
            if self._accent:
                p.setPen(QPen(QColor(94, 234, 212, 130), 1))
                p.setBrush(QColor(94, 234, 212, 26))
            else:
                p.setPen(QPen(QColor(theme.BORDER_HI), 1))
                p.setBrush(QColor(theme.KEY_TOP))
            p.drawRoundedRect(r, 6, 6)
            p.setPen(QColor(theme.ACCENT if self._accent else theme.TEXT))
            p.drawText(r, Qt.AlignCenter, text)
            x += w + self.GAP


def app_pixmap(size: int, paused: bool = False) -> QPixmap:
    """The icon: a single mint keycap, seen slightly from above, with two arrows swapping places."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 64.0
    if paused:
        side, rim0, rim1, top0, top1, ink = "#3d4454", "#8a92a6", "#646c80", "#a4abbb", "#7c8498", "#1b1f29"
    else:
        side, rim0, rim1, top0, top1, ink = "#0f6b5d", "#7cf0de", "#2fbfa8", "#b6faee", "#5eead4", theme.ACCENT_INK
    p.setPen(Qt.NoPen)
    # the side of the keycap, then its body, then the dished top face
    p.setBrush(QColor(side))
    p.drawRoundedRect(QRectF(3 * s, 9 * s, 58 * s, 53 * s), 14 * s, 14 * s)
    body = QRectF(3 * s, 2 * s, 58 * s, 53 * s)
    g = QLinearGradient(body.topLeft(), body.bottomLeft())
    g.setColorAt(0, QColor(rim0)); g.setColorAt(1, QColor(rim1))
    p.setBrush(g)
    p.drawRoundedRect(body, 14 * s, 14 * s)
    if size >= 32:
        face = QRectF(8 * s, 5.5 * s, 48 * s, 43 * s)
        g = QLinearGradient(face.topLeft(), face.bottomLeft())
        g.setColorAt(0, QColor(top0)); g.setColorAt(1, QColor(top1))
        p.setBrush(g)
        p.drawRoundedRect(face, 10 * s, 10 * s)
    # two arrows pointing opposite ways; bolder at small sizes so they survive in the tray
    small = size < 32
    w, x0, x1, head = (7.0, 15, 49, 8.0) if small else (5.2, 18, 46, 7.0)
    p.setPen(QPen(QColor(ink), w * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    for y, d in (((19, 1), (37, -1)) if small else ((19.5, 1), (34.5, -1))):
        a, b = (x0, x1) if d > 0 else (x1, x0)
        tip = QPointF(b * s, y * s)
        p.drawLine(QPointF(a * s, y * s), tip)
        p.drawPolyline([QPointF((b - head * d) * s, (y - head) * s), tip, QPointF((b - head * d) * s, (y + head) * s)])
    p.end()
    return pm


def app_icon(paused: bool = False) -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_pixmap(size, paused))
    return icon
