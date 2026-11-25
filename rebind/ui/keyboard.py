"""The drawn keyboard. Shows which keys are remapped in the current modifier layer and what they do."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from ..keys import KEYS, LAYOUT, LAYOUT_H, LAYOUT_W
from . import theme


_ARROWS = {"Left": (-1, 0), "Right": (1, 0), "Up": (0, -1), "Down": (0, 1)}


class KeyboardWidget(QWidget):
    keyClicked = Signal(str)        # a normal key
    modToggled = Signal(str)        # "ctrl" / "alt" / "shift" / "win"
    loneModClicked = Signal(str)    # right-click on a modifier: remap that key by itself

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layer: frozenset = frozenset()
        self._selected: str | None = None
        self._bound: dict[str, str] = {}     # key id -> caption
        self._tips: dict[str, str] = {}
        self._pressed: set[str] = set()
        self._flash: set[str] = set()
        self._hover: str | None = None
        self.setMouseTracking(True)
        self.setMinimumWidth(900)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # ---- state ------------------------------------------------------------

    def set_state(self, layer, selected, bound: dict, tips: dict) -> None:
        self._layer, self._selected, self._bound, self._tips = frozenset(layer), selected, bound, tips
        self.update()

    def set_pressed(self, kid: str, down: bool) -> None:
        (self._pressed.add if down else self._pressed.discard)(kid)
        self.update()

    def clear_pressed(self) -> None:
        self._pressed.clear()
        self.update()

    def flash(self, kid: str) -> None:
        self._flash.add(kid)
        self.update()
        QTimer.singleShot(260, lambda: (self._flash.discard(kid), self.update()))

    # ---- geometry ---------------------------------------------------------

    MAX_UNIT = 56

    def heightForWidth(self, w: int) -> int:
        return int(min(w / LAYOUT_W, self.MAX_UNIT) * LAYOUT_H)

    def sizeHint(self) -> QSize:
        return QSize(1100, self.heightForWidth(1100))

    def resizeEvent(self, e):
        # Layouts honour height-for-width only loosely; pinning the height keeps the keys square.
        self.setFixedHeight(self.heightForWidth(self.width()))
        super().resizeEvent(e)

    def _unit(self):
        u = min(self.width() / LAYOUT_W, self.height() / LAYOUT_H)
        return u, (self.width() - u * LAYOUT_W) / 2, (self.height() - u * LAYOUT_H) / 2

    def _rect(self, item, u, ox, oy) -> QRectF:
        _, x, y, w, h = item
        gap = u * 0.05
        return QRectF(ox + x * u + gap, oy + y * u + gap, w * u - 2 * gap, h * u - 2 * gap)

    def _key_at(self, pos) -> str | None:
        u, ox, oy = self._unit()
        for item in LAYOUT:
            if self._rect(item, u, ox, oy).contains(QPointF(pos)):
                return item[0]
        return None

    # ---- mouse ------------------------------------------------------------

    def mouseMoveEvent(self, e):
        kid = self._key_at(e.position())
        if kid != self._hover:
            self._hover = kid
            self.setCursor(Qt.PointingHandCursor if kid else Qt.ArrowCursor)
            self.update()
            if kid and kid in self._tips:
                QToolTip.showText(e.globalPosition().toPoint(), self._tips[kid], self)
            else:
                QToolTip.hideText()

    def leaveEvent(self, _):
        self._hover = None
        self.update()

    def mousePressEvent(self, e):
        kid = self._key_at(e.position())
        if not kid:
            return
        mod = KEYS[kid].mod
        if e.button() == Qt.LeftButton:
            self.modToggled.emit(mod) if mod else self.keyClicked.emit(kid)
        elif e.button() == Qt.RightButton and mod:
            self.loneModClicked.emit(kid)

    # ---- paint ------------------------------------------------------------

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        u, ox, oy = self._unit()
        label_font = QFont(theme.FONT)
        label_font.setPixelSize(max(9, int(u * 0.255)))
        label_font.setWeight(QFont.DemiBold)
        cap_font = QFont(theme.FONT)
        cap_font.setPixelSize(max(8, int(u * 0.2)))
        cap_font.setWeight(QFont.DemiBold)
        cap_fm = QFontMetricsF(cap_font)
        label_fm = QFontMetricsF(label_font)
        radius = u * 0.16
        pad = u * 0.11

        for item in LAYOUT:
            kid = item[0]
            key = KEYS[kid]
            r = self._rect(item, u, ox, oy)
            selected = kid == self._selected
            held = key.mod is not None and key.mod in self._layer and not selected
            bound = kid in self._bound
            pressed = kid in self._pressed
            flash = kid in self._flash

            # the edge the keycap sits on
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.KEY_EDGE))
            p.drawRoundedRect(r.translated(0, u * 0.05), radius, radius)
            if pressed:
                r = r.translated(0, u * 0.035)

            grad = QLinearGradient(r.topLeft(), r.bottomLeft())
            if selected or flash:
                grad.setColorAt(0, QColor("#86f1e0")); grad.setColorAt(1, QColor("#4fdcc5"))
                border, ink, sub = QColor("#b4f7ec"), QColor(theme.ACCENT_INK), QColor("#0d4a40")
            elif held:
                grad.setColorAt(0, QColor("#4a3d1c")); grad.setColorAt(1, QColor("#3a3018"))
                border, ink, sub = QColor(theme.AMBER), QColor(theme.AMBER), QColor(theme.AMBER)
            elif bound:
                grad.setColorAt(0, QColor("#1f3d3b")); grad.setColorAt(1, QColor("#193230"))
                border, ink, sub = QColor(94, 234, 212, 150), QColor(theme.TEXT), QColor(theme.ACCENT)
            else:
                grad.setColorAt(0, QColor(theme.KEY_TOP)); grad.setColorAt(1, QColor(theme.KEY_BOTTOM))
                border, ink, sub = QColor("#333a4b"), QColor("#c9cedb"), QColor(theme.DIM)
            if kid == self._hover and not selected:
                border = QColor(theme.ACCENT) if not held else border.lighter(120)
            p.setBrush(grad)
            p.setPen(QPen(border, 1.2 if (selected or held or bound or kid == self._hover) else 1))
            p.drawRoundedRect(r, radius, radius)
            if pressed and not (selected or flash):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 34))
                p.drawRoundedRect(r, radius, radius)

            inner = r.adjusted(pad, pad, -pad * 0.6, -pad)
            p.setPen(ink)
            fits = label_fm.horizontalAdvance(key.cap) <= inner.width()
            if kid in _ARROWS:       # drawn by hand: arrow glyphs fall back to a coloured emoji font
                dx, dy = _ARROWS[kid]
                c, a = QPointF(inner.left() + u * 0.14, inner.top() + u * 0.16), u * 0.12
                tip = QPointF(c.x() + dx * a, c.y() + dy * a)
                p.setPen(QPen(ink, max(1.4, u * 0.035), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawLine(QPointF(c.x() - dx * a, c.y() - dy * a), tip)
                for s in (-1, 1):
                    p.drawLine(tip, QPointF(tip.x() - dx * a * 0.8 + s * dy * a * 0.8,
                                            tip.y() - dy * a * 0.8 + s * dx * a * 0.8))
            else:
                p.setFont(label_font if fits else cap_font)
                p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, key.cap)
            if bound:
                p.setPen(sub)
                p.setFont(cap_font)
                text = self._bound[kid]
                if cap_fm.horizontalAdvance(text) > inner.width():
                    text = cap_fm.elidedText(text.replace("+", " "), Qt.ElideRight, inner.width())
                p.drawText(inner, Qt.AlignLeft | Qt.AlignBottom, text)
