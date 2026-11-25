"""The key table: every key Rebind knows, its Windows virtual-key code, and where it sits on the drawn keyboard."""
from __future__ import annotations

from dataclasses import dataclass

MODS = ("win", "ctrl", "alt", "shift")   # the order Windows writes them: Win + Ctrl + Alt + Shift + key
MOD_LABEL = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
# The key pressed when a shortcut needs a modifier the user is not holding.
MOD_KEY = {"ctrl": "LCtrl", "alt": "LAlt", "shift": "LShift", "win": "LWin"}

# An unassigned virtual key. Tapping it while Win or Alt is down stops Windows from
# opening the Start menu / activating the menu bar when that modifier is released.
MASK_VK = 0xE8


@dataclass(frozen=True)
class Key:
    id: str
    label: str          # full name, used in lists and descriptions
    cap: str            # short name, drawn on the keycap
    vk: int
    ext: bool = False   # needs the "extended key" flag when sent
    mod: str | None = None
    group: str = "other"


KEYS: dict[str, Key] = {}


def _add(id, label, vk, cap=None, ext=False, mod=None, group="other"):
    KEYS[id] = Key(id, label, cap or label, vk, ext, mod, group)


for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _add(_c, _c, ord(_c), group="letter")
for _d in "1234567890":
    _add(_d, _d, ord(_d), group="digit")
for _i in range(1, 25):
    _add(f"F{_i}", f"F{_i}", 0x6F + _i, group="function")

_add("Esc", "Esc", 0x1B, group="edit")
_add("Tab", "Tab", 0x09, group="edit")
_add("CapsLock", "Caps Lock", 0x14, cap="Caps", group="edit")
_add("Space", "Space", 0x20, cap="", group="edit")
_add("Enter", "Enter", 0x0D, group="edit")
_add("Backspace", "Backspace", 0x08, group="edit")
_add("Insert", "Insert", 0x2D, cap="Ins", ext=True, group="nav")
_add("Delete", "Delete", 0x2E, cap="Del", ext=True, group="nav")
_add("Home", "Home", 0x24, ext=True, group="nav")
_add("End", "End", 0x23, ext=True, group="nav")
_add("PageUp", "Page Up", 0x21, cap="PgUp", ext=True, group="nav")
_add("PageDown", "Page Down", 0x22, cap="PgDn", ext=True, group="nav")
_add("Up", "Up", 0x26, cap="↑", ext=True, group="nav")
_add("Down", "Down", 0x28, cap="↓", ext=True, group="nav")
_add("Left", "Left", 0x25, cap="←", ext=True, group="nav")
_add("Right", "Right", 0x27, cap="→", ext=True, group="nav")

_add("Backquote", "`", 0xC0, group="symbol")
_add("Minus", "-", 0xBD, group="symbol")
_add("Equal", "=", 0xBB, group="symbol")
_add("BracketLeft", "[", 0xDB, group="symbol")
_add("BracketRight", "]", 0xDD, group="symbol")
_add("Backslash", "\\", 0xDC, group="symbol")
_add("Semicolon", ";", 0xBA, group="symbol")
_add("Quote", "'", 0xDE, group="symbol")
_add("Comma", ",", 0xBC, group="symbol")
_add("Period", ".", 0xBE, group="symbol")
_add("Slash", "/", 0xBF, group="symbol")

_add("PrintScreen", "Print Screen", 0x2C, cap="PrtSc", ext=True, group="system")
_add("ScrollLock", "Scroll Lock", 0x91, cap="ScrLk", group="system")
_add("Pause", "Pause", 0x13, group="system")
_add("Menu", "Menu", 0x5D, ext=True, group="system")

_add("NumLock", "Num Lock", 0x90, cap="Num", ext=True, group="numpad")
for _i in range(10):
    _add(f"Numpad{_i}", f"Numpad {_i}", 0x60 + _i, cap=str(_i), group="numpad")
_add("NumpadDivide", "Numpad /", 0x6F, cap="/", ext=True, group="numpad")
_add("NumpadMultiply", "Numpad *", 0x6A, cap="*", group="numpad")
_add("NumpadSubtract", "Numpad -", 0x6D, cap="-", group="numpad")
_add("NumpadAdd", "Numpad +", 0x6B, cap="+", group="numpad")
_add("NumpadDecimal", "Numpad .", 0x6E, cap=".", group="numpad")
_add("NumpadEnter", "Numpad Enter", 0x0D, cap="Enter", ext=True, group="numpad")

_add("LShift", "Left Shift", 0xA0, cap="Shift", mod="shift", group="modifier")
_add("RShift", "Right Shift", 0xA1, cap="Shift", mod="shift", group="modifier")
_add("LCtrl", "Left Ctrl", 0xA2, cap="Ctrl", mod="ctrl", group="modifier")
_add("RCtrl", "Right Ctrl", 0xA3, cap="Ctrl", ext=True, mod="ctrl", group="modifier")
_add("LAlt", "Left Alt", 0xA4, cap="Alt", mod="alt", group="modifier")
_add("RAlt", "Right Alt", 0xA5, cap="Alt", ext=True, mod="alt", group="modifier")
_add("LWin", "Left Win", 0x5B, cap="Win", ext=True, mod="win", group="modifier")
_add("RWin", "Right Win", 0x5C, cap="Win", ext=True, mod="win", group="modifier")

_add("VolumeUp", "Volume up", 0xAF, ext=True, group="media")
_add("VolumeDown", "Volume down", 0xAE, ext=True, group="media")
_add("VolumeMute", "Mute", 0xAD, ext=True, group="media")
_add("MediaPlayPause", "Play / Pause", 0xB3, ext=True, group="media")
_add("MediaNext", "Next track", 0xB0, ext=True, group="media")
_add("MediaPrev", "Previous track", 0xB1, ext=True, group="media")
_add("MediaStop", "Stop playback", 0xB2, ext=True, group="media")
_add("BrowserBack", "Browser back", 0xA6, ext=True, group="media")
_add("BrowserForward", "Browser forward", 0xA7, ext=True, group="media")
_add("BrowserRefresh", "Browser refresh", 0xA8, ext=True, group="media")
_add("BrowserHome", "Browser home", 0xAC, ext=True, group="media")

MEDIA_KEYS = [k.id for k in KEYS.values() if k.group == "media"]
# Order of the "pick a key" list in the editor.
PICKER_GROUPS = ["letter", "digit", "function", "edit", "nav", "symbol", "system", "numpad"]

# ---- hook event -> key id -------------------------------------------------

_BY_VK = {k.vk: k.id for k in KEYS.values() if k.id != "NumpadEnter"}
_BY_VK.update({0x10: "LShift", 0x11: "LCtrl", 0x12: "LAlt"})
# With Num Lock off the number pad reports navigation codes *without* the extended flag.
_NUMPAD_NAV = {0x2D: "Numpad0", 0x23: "Numpad1", 0x28: "Numpad2", 0x22: "Numpad3", 0x25: "Numpad4",
               0x0C: "Numpad5", 0x27: "Numpad6", 0x24: "Numpad7", 0x26: "Numpad8", 0x21: "Numpad9",
               0x2E: "NumpadDecimal"}


def from_vk(vk: int, ext: bool) -> str | None:
    """Key id for a keyboard-hook event, or None for a key Rebind does not know."""
    if vk == 0x0D:
        return "NumpadEnter" if ext else "Enter"
    if not ext and vk in _NUMPAD_NAV:
        return _NUMPAD_NAV[vk]
    return _BY_VK.get(vk)


def localise() -> None:
    """Relabel the punctuation keys to match the active keyboard layout (Windows only)."""
    try:
        import ctypes
        user32 = ctypes.WinDLL("user32")
    except Exception:
        return
    for k in list(KEYS.values()):
        if k.group != "symbol":
            continue
        ch = user32.MapVirtualKeyW(k.vk, 2) & 0x7FFF
        if 0x20 < ch < 0xFFFF and chr(ch).isprintable():
            KEYS[k.id] = Key(k.id, chr(ch), chr(ch), k.vk, k.ext, k.mod, k.group)


# ---- drawn layout: (key id, x, y, width, height) in key units -------------

def _build_layout():
    out = []

    def row(y, x, items):
        for it in items:
            if isinstance(it, (int, float)):
                x += it
                continue
            kid, w = it if isinstance(it, tuple) else (it, 1)
            out.append((kid, x, y, w, 1))
            x += w

    row(0, 0, ["Esc", 1, "F1", "F2", "F3", "F4", .5, "F5", "F6", "F7", "F8", .5, "F9", "F10", "F11", "F12"])
    row(1.25, 0, ["Backquote", *"1234567890", "Minus", "Equal", ("Backspace", 2)])
    row(2.25, 0, [("Tab", 1.5), *"QWERTYUIOP", "BracketLeft", "BracketRight", ("Backslash", 1.5)])
    row(3.25, 0, [("CapsLock", 1.75), *"ASDFGHJKL", "Semicolon", "Quote", ("Enter", 2.25)])
    row(4.25, 0, [("LShift", 2.25), *"ZXCVBNM", "Comma", "Period", "Slash", ("RShift", 2.75)])
    row(5.25, 0, [("LCtrl", 1.25), ("LWin", 1.25), ("LAlt", 1.25), ("Space", 6.25),
                  ("RAlt", 1.25), ("RWin", 1.25), ("Menu", 1.25), ("RCtrl", 1.25)])
    nav = 15.25
    row(0, nav, ["PrintScreen", "ScrollLock", "Pause"])
    row(1.25, nav, ["Insert", "Home", "PageUp"])
    row(2.25, nav, ["Delete", "End", "PageDown"])
    row(4.25, nav + 1, ["Up"])
    row(5.25, nav, ["Left", "Down", "Right"])
    pad = 18.5
    row(1.25, pad, ["NumLock", "NumpadDivide", "NumpadMultiply", "NumpadSubtract"])
    row(2.25, pad, ["Numpad7", "Numpad8", "Numpad9"])
    row(3.25, pad, ["Numpad4", "Numpad5", "Numpad6"])
    row(4.25, pad, ["Numpad1", "Numpad2", "Numpad3"])
    row(5.25, pad, [("Numpad0", 2), "NumpadDecimal"])
    out.append(("NumpadAdd", pad + 3, 2.25, 1, 2))
    out.append(("NumpadEnter", pad + 3, 4.25, 1, 2))
    return out


LAYOUT = _build_layout()
LAYOUT_W = 22.5
LAYOUT_H = 6.25
