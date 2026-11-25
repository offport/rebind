"""The panel that edits one shortcut: "when I press X, do Y"."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QStackedWidget, QVBoxLayout, QWidget)

from ..keys import KEYS, MEDIA_KEYS, MOD_LABEL, MODS, PICKER_GROUPS
from ..model import Action, Binding, Trigger, reserved
from .app_picker import AppPicker
from .widgets import Pills, button

_TABS = [("keys", "Shortcut"), ("launch", "Open app"), ("text", "Type text"), ("media", "Media key"),
         ("none", "Disable")]
_TYPING_GROUPS = {"letter", "digit", "symbol"}
_TYPING_KEYS = {"Space", "Enter", "Backspace", "Tab"}


class Editor(QFrame):
    saved = Signal(object)            # Binding
    removed = Signal(object)          # Trigger
    recordRequested = Signal()        # "record the shortcut to send"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._trigger: Trigger | None = None
        self._existing: Binding | None = None
        self._label = ""              # friendly name of the chosen app
        self._loading = False

        self.stack = QStackedWidget()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.addWidget(self.stack)
        self.stack.addWidget(self._build_empty())
        self.stack.addWidget(self._build_form())

    # ---- construction -----------------------------------------------------

    def _build_empty(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        head = QLabel("Pick a key to remap")
        head.setObjectName("heading")
        head.setAlignment(Qt.AlignCenter)
        body = QLabel("Click Ctrl, Alt, Shift or Win on the keyboard to choose what is held,\n"
                      "then click the key. Or press Record and type the combination.")
        body.setObjectName("dim")
        body.setAlignment(Qt.AlignCenter)
        lay.addWidget(head)
        lay.addSpacing(6)
        lay.addWidget(body)
        lay.addStretch(1)
        return w

    def _build_form(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)
        when = QLabel("WHEN I PRESS")
        when.setObjectName("section")
        self.trigger_pills = Pills()
        top.addWidget(when)
        top.addWidget(self.trigger_pills)
        top.addStretch(1)
        lay.addLayout(top)

        seg = QHBoxLayout()
        seg.setSpacing(4)
        self.tabs = QButtonGroup(self)
        self.pages = QStackedWidget()
        for i, (_, title) in enumerate(_TABS):
            b = button(title, "seg")
            b.setCheckable(True)
            self.tabs.addButton(b, i)
            seg.addWidget(b)
        seg.addStretch(1)
        self.tabs.idClicked.connect(self._tab_changed)
        lay.addLayout(seg)

        for build in (self._page_keys, self._page_launch, self._page_text, self._page_media, self._page_none):
            self.pages.addWidget(build())
        lay.addWidget(self.pages, 1)

        self.note = QLabel()
        self.note.setObjectName("note")
        self.note.setWordWrap(True)
        self.note.hide()
        lay.addWidget(self.note)

        foot = QHBoxLayout()
        self.remove_btn = button("Remove", "danger")
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self._trigger))
        self.save_btn = button("Save shortcut", "primary")
        self.save_btn.clicked.connect(self._save)
        foot.addWidget(self.remove_btn)
        foot.addStretch(1)
        foot.addWidget(self.save_btn)
        lay.addLayout(foot)
        return w

    @staticmethod
    def _page(*rows, hint: str = "") -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(10)
        for r in rows:
            lay.addLayout(r) if isinstance(r, QHBoxLayout) else lay.addWidget(r)
        if hint:
            label = QLabel(hint)
            label.setObjectName("dim")
            label.setWordWrap(True)
            lay.addWidget(label)
        lay.addStretch(1)
        return w

    def _page_keys(self) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(6)
        self.mod_chips = {}
        for m in MODS:
            chip = button(MOD_LABEL[m], "chip")
            chip.setCheckable(True)
            chip.toggled.connect(self._changed)
            self.mod_chips[m] = chip
            row.addWidget(chip)
        plus = QLabel("+")
        plus.setObjectName("dim")
        row.addWidget(plus)
        self.key_box = QComboBox()
        self.key_box.setMaxVisibleItems(16)
        self.key_box.setMinimumWidth(150)
        self.key_box.addItem("Choose a key…", "")
        for group in PICKER_GROUPS:
            self.key_box.insertSeparator(self.key_box.count())
            for k in KEYS.values():
                if k.group == group:
                    self.key_box.addItem(k.label, k.id)
        self.key_box.currentIndexChanged.connect(self._changed)
        row.addWidget(self.key_box)
        row.addStretch(1)
        self.record_btn = button("Record", tip="Press the shortcut you want to send")
        self.record_btn.clicked.connect(self.recordRequested)
        row.addWidget(self.record_btn)
        return self._page(row, hint="Windows receives this shortcut instead of the keys you pressed.")

    def _page_launch(self) -> QWidget:
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("App, file, folder or web address")
        self.target_edit.textEdited.connect(self._target_typed)
        choose = button("Choose app…")
        choose.clicked.connect(self._choose_app)
        browse = button("Browse…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self.target_edit, 1)
        row.addWidget(choose)
        row.addWidget(browse)
        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("Arguments (optional)")
        self.args_edit.textEdited.connect(self._changed)
        return self._page(row, self.args_edit)

    def _page_text(self) -> QWidget:
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Text to type, for example an email address or a signature")
        self.text_edit.setFixedHeight(72)
        self.text_edit.textChanged.connect(self._changed)
        return self._page(self.text_edit)

    def _page_media(self) -> QWidget:
        self.media_box = QComboBox()
        for kid in MEDIA_KEYS:
            self.media_box.addItem(KEYS[kid].label, kid)
        self.media_box.currentIndexChanged.connect(self._changed)
        row = QHBoxLayout()
        row.addWidget(self.media_box)
        row.addStretch(1)
        return self._page(row, hint="Works like the media keys on a multimedia keyboard.")

    def _page_none(self) -> QWidget:
        return self._page(hint="The key combination does nothing while Rebind is active. "
                               "Handy for keys you keep hitting by accident.")

    # ---- loading ----------------------------------------------------------

    def clear(self) -> None:
        self._trigger = self._existing = None
        self.stack.setCurrentIndex(0)

    def trigger(self) -> Trigger | None:
        return self._trigger

    def load(self, trigger: Trigger, existing: Binding | None) -> None:
        self._loading = True
        self._trigger, self._existing = trigger, existing
        self.trigger_pills.setParts(trigger.parts())
        a = existing.action if existing else Action("keys")
        tab = "media" if a.type == "keys" and a.key in MEDIA_KEYS and not a.mods else a.type
        for m, chip in self.mod_chips.items():
            chip.setChecked(tab == "keys" and m in a.mods)
        self.key_box.setCurrentIndex(max(0, self.key_box.findData(a.key)) if tab == "keys" else 0)
        self.media_box.setCurrentIndex(max(0, self.media_box.findData(a.key)) if tab == "media" else 0)
        self.target_edit.setText(a.target)
        self.args_edit.setText(a.args)
        self._label = a.label
        self.text_edit.setPlainText(a.text)
        self._show_tab([t for t, _ in _TABS].index(tab))
        self.stack.setCurrentIndex(1)
        self._loading = False
        self._refresh()

    def set_action_keys(self, mods, key: str) -> None:
        """Result of Record."""
        for m, chip in self.mod_chips.items():
            chip.setChecked(m in mods)
        self.key_box.setCurrentIndex(max(0, self.key_box.findData(key)))

    def set_recording(self, on: bool) -> None:
        self.record_btn.setText("Press keys…" if on else "Record")
        self.record_btn.setProperty("recording", on)
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)

    # ---- behaviour --------------------------------------------------------

    def _show_tab(self, index: int) -> None:
        self.tabs.button(index).setChecked(True)
        self.pages.setCurrentIndex(index)

    def _tab_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self._refresh()

    def _changed(self, *_):
        if not self._loading:
            self._refresh()

    def _target_typed(self, *_):
        self._label = ""              # the user is typing a path of their own
        self._refresh()

    def _choose_app(self):
        dialog = AppPicker(self.window())
        if dialog.exec() and dialog.choice:
            self._label, target = dialog.choice
            self.target_edit.setText(target)
            self.args_edit.clear()
            self._refresh()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self.window(), "Choose what to open", "",
                                              "Apps and shortcuts (*.exe *.lnk *.bat *.cmd);;All files (*)")
        if path:
            self._label = ""
            self.target_edit.setText(path.replace("/", "\\"))
            self._refresh()

    def _action(self) -> Action:
        tab = _TABS[self.pages.currentIndex()][0]
        if tab == "keys":
            mods = frozenset(m for m, chip in self.mod_chips.items() if chip.isChecked())
            return Action("keys", mods, self.key_box.currentData() or "")
        if tab == "media":
            return Action("keys", frozenset(), self.media_box.currentData())
        if tab == "launch":
            return Action("launch", target=self.target_edit.text().strip(), args=self.args_edit.text().strip(),
                          label=self._label)
        if tab == "text":
            return Action("text", text=self.text_edit.toPlainText())
        return Action("none")

    def _refresh(self) -> None:
        if self._trigger is None:
            return
        action = self._action()
        same = action.type == "keys" and action.mods == self._trigger.mods and action.key == self._trigger.key
        blocked = reserved(self._trigger)
        key = KEYS[self._trigger.key]
        note = blocked or ""
        if not note and same:
            note = "That is the same shortcut you are pressing. Choose something different to send."
        elif not note and not self._trigger.mods and (key.group in _TYPING_GROUPS or key.id in _TYPING_KEYS):
            note = f"Heads up: with nothing held, this replaces the {key.label} key everywhere, including while typing."
        self.note.setText(note)
        self.note.setVisible(bool(note))
        unchanged = self._existing is not None and self._existing.action == action
        self.save_btn.setEnabled(action.valid() and not same and not blocked and not unchanged)
        self.save_btn.setText("Saved" if unchanged else "Save shortcut")
        self.remove_btn.setVisible(self._existing is not None)

    def _save(self) -> None:
        enabled = self._existing.enabled if self._existing else True
        self.saved.emit(Binding(self._trigger, self._action(), enabled))
