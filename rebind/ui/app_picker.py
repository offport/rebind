"""Pick an installed app (desktop or Store) by name. The list is what the Start menu shows."""
from __future__ import annotations

import json
import subprocess

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from .widgets import button

_cache: list[tuple[str, str]] | None = None


class _Loader(QThread):
    loaded = Signal(list)

    def run(self):
        apps = []
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-StartApps | Select-Object Name,AppID | "
                 "ConvertTo-Json -Compress"],
                capture_output=True, timeout=30, creationflags=0x08000000).stdout.decode("utf-8", "replace")
            data = json.loads(out) if out.strip() else []
            for item in data if isinstance(data, list) else [data]:
                if item.get("Name") and item.get("AppID"):
                    apps.append((item["Name"], item["AppID"]))
        except Exception:
            pass
        self.loaded.emit(sorted(set(apps), key=lambda a: a[0].lower()))


class AppPicker(QDialog):
    """exec() then read .choice -> (name, target) or None."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose an app")
        self.resize(440, 520)
        self.choice = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search your apps")
        self.search.textChanged.connect(self._filter)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self._accept())
        self.list.currentItemChanged.connect(lambda *_: self.ok.setEnabled(self.list.currentItem() is not None))
        self.status = QLabel("Loading your apps…")
        self.status.setObjectName("dim")
        self.ok = button("Choose", "primary")
        self.ok.setEnabled(False)
        self.ok.clicked.connect(self._accept)
        cancel = button("Cancel")
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(self.status, 1)
        row.addWidget(cancel)
        row.addWidget(self.ok)
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addLayout(row)
        self.search.setFocus()
        if _cache is not None:
            self._fill(_cache)
        else:
            self._loader = _Loader(self)
            self._loader.loaded.connect(self._fill)
            self._loader.start()

    def _fill(self, apps):
        global _cache
        _cache = apps
        for name, app_id in apps:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, app_id)
            self.list.addItem(item)
        self.status.setText(f"{len(apps)} apps" if apps else "Could not read the app list. Use Browse instead.")
        self._filter(self.search.text())

    def _filter(self, text):
        needle = text.strip().lower()
        first = None
        for i in range(self.list.count()):
            item = self.list.item(i)
            hide = needle not in item.text().lower()
            item.setHidden(hide)
            if not hide and first is None:
                first = item
        self.list.setCurrentItem(first)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Down, Qt.Key_Up) and self.search.hasFocus():
            self.list.setFocus()
            self.list.keyPressEvent(e)
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._accept()
        else:
            super().keyPressEvent(e)

    def _accept(self):
        item = self.list.currentItem()
        if item and not item.isHidden():
            self.choice = (item.text(), "shell:AppsFolder\\" + item.data(Qt.UserRole))
            self.accept()
