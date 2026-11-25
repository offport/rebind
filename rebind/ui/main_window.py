"""The window: header, keyboard, list of shortcuts, editor, and the tray icon."""
from __future__ import annotations

import os

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox,
                               QScrollArea, QSizePolicy, QSystemTrayIcon, QVBoxLayout, QWidget)

from .. import APP_NAME, autostart
from ..keys import KEYS, MOD_LABEL, MODS
from ..model import Binding, Config, Trigger, mac_preset
from .editor import Editor
from .keyboard import KeyboardWidget
from .widgets import Pills, Switch, app_icon, app_pixmap, button


class Bridge(QObject):
    """Carries engine callbacks (hook / worker threads) over to the UI thread."""
    key = Signal(str, bool)
    fired = Signal(object)
    captured = Signal(object)
    error = Signal(str)


class Row(QFrame):
    clicked = Signal()
    toggled = Signal(bool)
    removed = Signal()

    def __init__(self, binding: Binding, selected: bool):
        super().__init__()
        self.setObjectName("row")
        self.setProperty("selected", selected)
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 8, 6)
        lay.setSpacing(10)
        trigger = Pills(binding.trigger.parts())
        trigger.setMinimumWidth(176)
        lay.addWidget(trigger)
        arrow = QLabel("→")
        arrow.setObjectName("arrow")
        lay.addWidget(arrow)
        a = binding.action
        if a.type == "keys":
            lay.addWidget(Pills(a.parts(), accent=True))
            lay.addStretch(1)
        else:
            text = QLabel(a.describe())
            text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            text.setToolTip(a.target if a.type == "launch" else a.text)
            lay.addWidget(text, 1)
        switch = Switch(binding.enabled)
        switch.setToolTip("Turn this shortcut on or off")
        switch.toggled.connect(self.toggled)
        lay.addWidget(switch)
        remove = button("✕", "quiet", "Remove")
        remove.clicked.connect(self.removed)
        lay.addWidget(remove)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, engine, hook_ok: bool = True):
        super().__init__()
        self.cfg, self.engine, self.hook_ok = cfg, engine, hook_ok
        self.layer: set[str] = set()
        self.selected: str | None = None
        self._capturing: str | None = None     # "trigger" | "action"
        self._really_quit = False
        self._dark_done = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1200, 880)
        self.setMinimumSize(1040, 800)

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(22, 18, 22, 22)
        lay.setSpacing(16)
        lay.addLayout(self._build_header())
        lay.addWidget(self._build_keyboard_card())
        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        bottom.addWidget(self._build_list_card(), 5)
        self.editor = Editor()
        self.editor.setMinimumWidth(480)
        self.editor.saved.connect(self._save)
        self.editor.removed.connect(self._remove)
        self.editor.recordRequested.connect(lambda: self._toggle_capture("action"))
        bottom.addWidget(self.editor, 5)
        lay.addLayout(bottom, 1)

        self.bridge = Bridge()
        self.bridge.key.connect(self._on_key)
        self.bridge.fired.connect(lambda b: self.isVisible() and self.keyboard.flash(b.trigger.key))
        self.bridge.captured.connect(self._on_captured)
        self.bridge.error.connect(self._on_error)
        engine.on_fired = self.bridge.fired.emit
        engine.on_error = self.bridge.error.emit

        self._build_tray()
        self._rehook = QTimer(self)
        self._rehook.timeout.connect(engine.refresh_hook)
        self._rehook.start(120_000)
        self._apply_enabled()
        self._refresh()

    # ---- construction -----------------------------------------------------

    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(app_pixmap(72))
        logo.setScaledContents(True)
        logo.setFixedSize(36, 36)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        sub = QLabel("Make any key do what you want")
        sub.setObjectName("dim")
        titles.addWidget(title)
        titles.addWidget(sub)
        row.addWidget(logo)
        row.addLayout(titles)
        row.addStretch(1)

        self.record_btn = button("●  Record a shortcut", tip="Press the keys you want to remap instead of clicking them")
        self.record_btn.clicked.connect(lambda: self._toggle_capture("trigger"))
        self.record_btn.setEnabled(self.hook_ok)
        row.addWidget(self.record_btn)

        presets = button("Presets  ▾")
        menu = QMenu(presets)
        menu.addAction("Mac-style shortcuts, Win key as Command", lambda: self._apply_preset("win"))
        menu.addAction("Mac-style shortcuts, Alt key as Command", lambda: self._apply_preset("alt"))
        menu.addSeparator()
        menu.addAction("Remove all shortcuts…", self._remove_all)
        presets.setMenu(menu)
        row.addWidget(presets)

        more = button("•••", tip="More")
        more_menu = QMenu(more)
        self.autostart_action = QAction("Start with Windows", more_menu, checkable=True)
        self.autostart_action.setChecked(autostart.is_enabled())
        self.autostart_action.toggled.connect(self._set_autostart)
        more_menu.addAction(self.autostart_action)
        more_menu.addAction("Open settings folder", self._open_folder)
        more_menu.addSeparator()
        more_menu.addAction("Quit Rebind", self.quit)
        more.setMenu(more_menu)
        row.addWidget(more)

        row.addSpacing(8)
        self.status = QLabel()
        self.status.setMinimumWidth(52)
        self.status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.master = Switch(self.cfg.enabled)
        self.master.setToolTip("Turn all remapping on or off")
        self.master.toggled.connect(self._set_enabled)
        self.master.setEnabled(self.hook_ok)
        row.addWidget(self.status)
        row.addWidget(self.master)
        return row

    def _build_keyboard_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(14)
        top = QHBoxLayout()
        top.setSpacing(8)
        label = QLabel("WHILE HOLDING")
        label.setObjectName("section")
        top.addWidget(label)
        top.addSpacing(4)
        self.layer_chips = {}
        for m in MODS:
            chip = button(MOD_LABEL[m], "chip")
            chip.setCheckable(True)
            chip.clicked.connect(lambda _=False, m=m: self._toggle_mod(m))
            self.layer_chips[m] = chip
            top.addWidget(chip)
        top.addStretch(1)
        self.hint = QLabel()
        self.hint.setObjectName("dim")
        top.addWidget(self.hint)
        lay.addLayout(top)
        self.keyboard = KeyboardWidget()
        self.keyboard.keyClicked.connect(lambda k: self._select(self.layer, k))
        self.keyboard.modToggled.connect(self._toggle_mod)
        self.keyboard.loneModClicked.connect(lambda k: self._select((), k))
        lay.addWidget(self.keyboard)
        return card

    def _build_list_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 16, 8, 12)
        lay.setSpacing(8)
        top = QHBoxLayout()
        top.setContentsMargins(8, 0, 8, 0)
        label = QLabel("YOUR SHORTCUTS")
        label.setObjectName("section")
        self.count = QLabel("0")
        self.count.setObjectName("badge")
        top.addWidget(label)
        top.addWidget(self.count)
        top.addStretch(1)
        lay.addLayout(top)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lay.addWidget(self.scroll, 1)
        return card

    def _build_tray(self):
        self.tray = QSystemTrayIcon(app_icon(), self)
        menu = QMenu()
        menu.addAction("Open Rebind", self.reveal)
        self.tray_toggle = menu.addAction("Pause remapping", lambda: self._set_enabled(not self.cfg.enabled))
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        self._tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda why: why in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) and self.reveal())
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    # ---- selection --------------------------------------------------------

    def _trigger(self) -> Trigger | None:
        return Trigger(frozenset(self.layer), self.selected) if self.selected else None

    def _select(self, mods, key: str) -> None:
        self.layer, self.selected = set(mods), key
        trigger = self._trigger()
        self.editor.load(trigger, self.cfg.find(trigger))
        self._refresh()

    def _toggle_mod(self, mod: str) -> None:
        self.layer ^= {mod}
        if self.selected and KEYS[self.selected].mod:     # a modifier remapped on its own has no layer
            self.selected = None
        if self.selected:
            self._select(self.layer, self.selected)
        else:
            self.editor.clear()
            self._refresh()

    def _refresh(self) -> None:
        layer = frozenset(self.layer)
        here = [b for b in self.cfg.bindings if b.trigger.mods == layer]
        self.keyboard.set_state(layer, self.selected,
                                {b.trigger.key: b.action.short() for b in here},
                                {b.trigger.key: f"{b.trigger.text()}  →  {b.action.describe()}" for b in here})
        for m, chip in self.layer_chips.items():
            chip.setChecked(m in layer)
        if layer:
            held = " + ".join(MOD_LABEL[m] for m in MODS if m in layer)
            self.hint.setText(f"Showing what each key does while you hold {held}")
        else:
            self.hint.setText("Click a modifier to hold it, then click a key   ·   right-click a modifier to remap it alone")
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(2)
        current = self._trigger()
        if not self.cfg.bindings:
            empty = QLabel("Nothing remapped yet.\nPick a key on the keyboard, or start from Presets.")
            empty.setObjectName("dim")
            empty.setAlignment(Qt.AlignCenter)
            lay.addStretch(1)
            lay.addWidget(empty)
            lay.addStretch(1)
        for b in self.cfg.bindings:
            row = Row(b, b.trigger == current)
            row.clicked.connect(lambda b=b: self._select(b.trigger.mods, b.trigger.key))
            row.toggled.connect(lambda on, b=b: self._set_binding_enabled(b, on))
            row.removed.connect(lambda b=b: self._remove(b.trigger))
            lay.addWidget(row)
            if b.trigger == current:
                QTimer.singleShot(0, lambda row=row: self.scroll.widget() is holder
                                  and self.scroll.ensureWidgetVisible(row, 0, 8))
        if self.cfg.bindings:
            lay.addStretch(1)
        position = self.scroll.verticalScrollBar().value()
        self.scroll.setWidget(holder)
        self.scroll.verticalScrollBar().setValue(position)
        self.count.setText(str(len(self.cfg.bindings)))

    # ---- changes ----------------------------------------------------------

    def _commit(self) -> None:
        self.cfg.save()
        self.engine.set_bindings(self.cfg.bindings)

    def _save(self, binding: Binding) -> None:
        self.cfg.upsert(binding)
        self._commit()
        self._select(binding.trigger.mods, binding.trigger.key)

    def _remove(self, trigger: Trigger) -> None:
        self.cfg.remove(trigger)
        self._commit()
        if trigger == self._trigger():
            self.editor.load(trigger, None)
        self._refresh()

    def _set_binding_enabled(self, binding: Binding, on: bool) -> None:
        binding.enabled = on
        self._commit()

    def _apply_preset(self, command: str) -> None:
        for b in mac_preset(command):
            self.cfg.upsert(b)
        self._commit()
        self.layer, self.selected = {command}, None
        self.editor.clear()
        self._refresh()

    def _remove_all(self) -> None:
        if not self.cfg.bindings:
            return
        answer = QMessageBox.question(self, APP_NAME, f"Remove all {len(self.cfg.bindings)} shortcuts?",
                                      QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer == QMessageBox.Yes:
            self.cfg.bindings = []
            self._commit()
            self.selected = None
            self.editor.clear()
            self._refresh()

    def _set_enabled(self, on: bool) -> None:
        self.cfg.enabled = on
        self.cfg.save()
        self._apply_enabled()

    def _apply_enabled(self) -> None:
        on = self.cfg.enabled and self.hook_ok
        self.engine.enabled = on
        self.master.setChecked(on)
        self.status.setText("Active" if on else ("Paused" if self.hook_ok else "Unavailable"))
        self.status.setStyleSheet(f"color: {'#5eead4' if on else '#8a92a6'}; font-weight: 600;")
        self.tray.setIcon(app_icon(paused=not on))
        self.tray.setToolTip(f"Rebind: {'active' if on else 'paused'}")
        self.tray_toggle.setText("Pause remapping" if on else "Resume remapping")

    def _set_autostart(self, on: bool) -> None:
        try:
            autostart.set_enabled(on)
        except OSError as exc:
            self._on_error(f"Could not change the startup setting: {exc}")

    def _open_folder(self) -> None:
        if self.cfg.path:
            self.cfg.path.parent.mkdir(parents=True, exist_ok=True)
            os.startfile(self.cfg.path.parent)

    # ---- recording --------------------------------------------------------

    def _toggle_capture(self, purpose: str) -> None:
        if self._capturing:
            self._end_capture()
            return
        self._capturing = purpose
        self.engine.capture(self.bridge.captured.emit)
        if purpose == "trigger":
            self.record_btn.setText("Press the keys…  (Esc cancels)")
            self._mark(self.record_btn, True)
        else:
            self.editor.set_recording(True)

    def _end_capture(self) -> None:
        self.engine.cancel_capture()
        self._capturing = None
        self.record_btn.setText("●  Record a shortcut")
        self._mark(self.record_btn, False)
        self.editor.set_recording(False)

    @staticmethod
    def _mark(widget, on: bool) -> None:
        widget.setProperty("recording", on)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _on_captured(self, result) -> None:
        purpose = self._capturing
        self._end_capture()
        if not result or not purpose:
            return
        mods, key = result
        if purpose == "trigger":
            self._select(mods, key)
        else:
            self.editor.set_action_keys(mods, key)

    # ---- engine events ----------------------------------------------------

    def _on_key(self, kid: str, down: bool) -> None:
        if self.isVisible():
            self.keyboard.set_pressed(kid, down)

    def _on_error(self, message: str) -> None:
        if self.tray.isVisible():
            self.tray.showMessage(APP_NAME, message, QSystemTrayIcon.Warning, 5000)

    # ---- window -----------------------------------------------------------

    def reveal(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit(self) -> None:
        self._really_quit = True
        self.tray.hide()
        QApplication.quit()

    def showEvent(self, e):
        super().showEvent(e)
        self.engine.on_key = self.bridge.key.emit
        if not self._dark_done:
            self._dark_done = True
            from .. import winapi
            winapi.set_dark_titlebar(int(self.winId()))

    def hideEvent(self, e):
        super().hideEvent(e)
        self.engine.on_key = None
        self.keyboard.clear_pressed()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == e.Type.ActivationChange and not self.isActiveWindow() and self._capturing:
            self._end_capture()

    def closeEvent(self, e):
        if self._really_quit or not self.tray.isVisible():
            e.accept()
            QApplication.quit()
            return
        e.ignore()
        self.hide()
        if not self.cfg.tray_hint_shown:
            self.cfg.tray_hint_shown = True
            self.cfg.save()
            self.tray.showMessage(APP_NAME, "Still running here in the tray, so your shortcuts keep working. "
                                            "Right-click the icon to quit.", QSystemTrayIcon.Information, 6000)
