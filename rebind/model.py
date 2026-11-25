"""Shortcuts (trigger -> action), the saved settings, and the presets."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .keys import KEYS, MOD_LABEL, MODS


def _mod_parts(mods) -> list[str]:
    return [MOD_LABEL[m] for m in MODS if m in mods]


@dataclass(frozen=True)
class Trigger:
    mods: frozenset
    key: str

    def parts(self) -> list[str]:
        return _mod_parts(self.mods) + [KEYS[self.key].label]

    def text(self) -> str:
        return " + ".join(self.parts())


@dataclass(frozen=True)
class Action:
    """type: keys (send a shortcut) | launch (open something) | text (type it) | none (disable the key)."""
    type: str = "keys"
    mods: frozenset = frozenset()
    key: str = ""
    target: str = ""
    args: str = ""
    label: str = ""
    text: str = ""

    def parts(self) -> list[str]:
        return _mod_parts(self.mods) + [KEYS[self.key].label]

    def launch_name(self) -> str:
        if self.label:
            return self.label
        name = os.path.basename(self.target.rstrip("\\/")) or self.target
        return os.path.splitext(name)[0] if name.lower().endswith((".exe", ".lnk", ".bat", ".cmd")) else name

    def describe(self) -> str:
        if self.type == "keys":
            return " + ".join(self.parts())
        if self.type == "launch":
            return f"Open {self.launch_name()}"
        if self.type == "text":
            flat = " ".join(self.text.split())
            return f"Type “{flat[:28]}{'…' if len(flat) > 28 else ''}”"
        return "Do nothing"

    def short(self) -> str:
        """A few characters for the caption on a keycap."""
        if self.type == "keys":
            return "+".join(_mod_parts(self.mods) + [KEYS[self.key].cap or KEYS[self.key].label])
        if self.type == "launch":
            return self.launch_name()
        if self.type == "text":
            return "Text"
        return "Off"

    def valid(self) -> bool:
        if self.type == "keys":
            return self.key in KEYS
        if self.type == "launch":
            return bool(self.target.strip())
        if self.type == "text":
            return bool(self.text)
        return self.type == "none"


@dataclass
class Binding:
    trigger: Trigger
    action: Action
    enabled: bool = True

    def to_dict(self) -> dict:
        a = self.action
        act = {"type": a.type}
        if a.type == "keys":
            act.update(mods=_sorted(a.mods), key=a.key)
        elif a.type == "launch":
            act.update(target=a.target, args=a.args, label=a.label)
        elif a.type == "text":
            act.update(text=a.text)
        return {"trigger": {"mods": _sorted(self.trigger.mods), "key": self.trigger.key},
                "action": act, "enabled": self.enabled}

    @staticmethod
    def from_dict(d: dict) -> "Binding":
        t, a = d["trigger"], d["action"]
        trigger = Trigger(_mods(t.get("mods")), t["key"])
        action = Action(type=a["type"], mods=_mods(a.get("mods")), key=a.get("key", ""),
                        target=a.get("target", ""), args=a.get("args", ""), label=a.get("label", ""),
                        text=a.get("text", ""))
        if trigger.key not in KEYS or not action.valid():
            raise ValueError("unknown key or incomplete action")
        return Binding(trigger, action, bool(d.get("enabled", True)))


def _sorted(mods) -> list[str]:
    return [m for m in MODS if m in mods]


def _mods(value) -> frozenset:
    return frozenset(m for m in (value or []) if m in MODS)


def default_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "Rebind" / "config.json"


@dataclass
class Config:
    path: Path | None = None
    enabled: bool = True
    tray_hint_shown: bool = False
    bindings: list[Binding] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or default_path()
        cfg = cls(path=path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cfg
        cfg.enabled = bool(data.get("enabled", True))
        cfg.tray_hint_shown = bool(data.get("tray_hint_shown", False))
        for item in data.get("bindings", []):
            try:
                cfg.upsert(Binding.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue  # a hand-edited entry that no longer makes sense is skipped, not fatal
        return cfg

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "enabled": self.enabled, "tray_hint_shown": self.tray_hint_shown,
                "bindings": [b.to_dict() for b in self.bindings]}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def find(self, trigger: Trigger) -> Binding | None:
        return next((b for b in self.bindings if b.trigger == trigger), None)

    def upsert(self, binding: Binding) -> None:
        for i, b in enumerate(self.bindings):
            if b.trigger == binding.trigger:
                self.bindings[i] = binding
                return
        self.bindings.append(binding)

    def remove(self, trigger: Trigger) -> None:
        self.bindings = [b for b in self.bindings if b.trigger != trigger]


# ---- presets ---------------------------------------------------------------

_MAC = [  # (extra trigger mods, key, action mods, action key)
    ((), "C", ("ctrl",), "C"), ((), "V", ("ctrl",), "V"), ((), "X", ("ctrl",), "X"),
    ((), "Z", ("ctrl",), "Z"), (("shift",), "Z", ("ctrl",), "Y"), ((), "A", ("ctrl",), "A"),
    ((), "S", ("ctrl",), "S"), ((), "F", ("ctrl",), "F"), ((), "N", ("ctrl",), "N"),
    ((), "O", ("ctrl",), "O"), ((), "P", ("ctrl",), "P"), ((), "T", ("ctrl",), "T"),
    (("shift",), "T", ("ctrl", "shift"), "T"), ((), "W", ("ctrl",), "W"), ((), "R", ("ctrl",), "R"),
    ((), "B", ("ctrl",), "B"), ((), "I", ("ctrl",), "I"), ((), "Q", ("alt",), "F4"),
]


def mac_preset(command: str) -> list[Binding]:
    """Mac-style shortcuts with `command` ("win" or "alt") standing in for the Command key."""
    return [Binding(Trigger(frozenset((command, *extra)), key), Action("keys", frozenset(amods), akey))
            for extra, key, amods, akey in _MAC]


def reserved(trigger: Trigger) -> str | None:
    """Why Windows will not let this combination be remapped, if it won't."""
    if trigger.key == "L" and trigger.mods == {"win"}:
        return "Windows keeps Win + L for locking the PC. It cannot be remapped."
    if trigger.key == "Delete" and trigger.mods == {"ctrl", "alt"}:
        return "Windows keeps Ctrl + Alt + Delete for itself. It cannot be remapped."
    return None
