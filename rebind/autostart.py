"""Start Rebind (hidden in the tray) when the user signs in to Windows."""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "Rebind"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    script = Path(__file__).resolve().parent.parent / "run.py"
    return f'"{pythonw}" "{script}" --tray'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN) as key:
            winreg.QueryValueEx(key, _NAME)
            return True
    except OSError:
        return False


def set_enabled(on: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, _NAME)
            except OSError:
                pass
