"""The Windows calls Rebind needs: the low-level keyboard hook, synthetic key presses, and opening things."""
from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

ULONG_PTR = ctypes.c_size_t
LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

WH_KEYBOARD_LL = 13
WM_KEYUP, WM_SYSKEYUP, WM_QUIT = 0x0101, 0x0105, 0x0012
WM_REHOOK = 0x8000 + 1
LLKHF_EXTENDED, LLKHF_INJECTED = 0x01, 0x10
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x1, 0x2, 0x4
# Stamped on every key press Rebind sends, so the hook can tell them from the user's.
MAGIC = 0x52424E44


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT,
                                wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
shell32.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                  wintypes.LPCWSTR, ctypes.c_int]
shell32.ShellExecuteW.restype = ctypes.c_void_p


class HookThread(threading.Thread):
    """Owns the keyboard hook. Windows calls the hook on the thread that installed it, so that
    thread must do nothing but pump messages: a slow hook makes every key press on the PC lag."""

    def __init__(self, handler, tap=None):
        super().__init__(name="rebind-hook", daemon=True)
        self._handler = handler      # handler(vk, extended, is_up) -> True to hide the key from Windows
        self._tap = tap              # tap(vk, is_up) for Rebind's own key presses (used by the self-test)
        self._proc = HOOKPROC(self._callback)
        self._hook = None
        self.tid = 0
        self.ready = threading.Event()
        self.ok = False

    def _callback(self, code, wparam, lparam):
        if code == 0:
            k = KBDLLHOOKSTRUCT.from_address(lparam)
            up = wparam in (WM_KEYUP, WM_SYSKEYUP)
            if k.flags & LLKHF_INJECTED and k.dwExtraInfo == MAGIC:
                if self._tap:
                    self._tap(k.vkCode, up)
            else:
                try:
                    if self._handler(k.vkCode, bool(k.flags & LLKHF_EXTENDED), up):
                        return 1
                except Exception:   # never let a bug here take the keyboard down with it
                    pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def _install(self):
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        return bool(self._hook)

    def _remove(self):
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def run(self):
        self.tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)   # gives this thread a message queue
        self.ok = self._install()
        self.ready.set()
        while self.ok and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_REHOOK:
                self._remove()
                self._install()
        self._remove()

    def rehook(self):
        """Windows silently drops a hook that was ever too slow to answer; re-installing is cheap insurance."""
        if self.tid:
            user32.PostThreadMessageW(self.tid, WM_REHOOK, 0, 0)

    def stop(self):
        if self.tid:
            user32.PostThreadMessageW(self.tid, WM_QUIT, 0, 0)


def send_input(events, extra=MAGIC) -> None:
    """events: (vk, extended, down) for a key, or (None, utf16_unit, down) for a typed character."""
    if not events:
        return
    arr = (INPUT * len(events))()
    for i, (vk, x, down) in enumerate(events):
        arr[i].type = 1
        ki = arr[i].u.ki
        flags = 0 if down else KEYEVENTF_KEYUP
        if vk is None:
            ki.wScan, flags = x, flags | KEYEVENTF_UNICODE
        else:
            ki.wVk = vk
            ki.wScan = user32.MapVirtualKeyW(vk, 0)
            if x:
                flags |= KEYEVENTF_EXTENDEDKEY
        ki.dwFlags = flags
        ki.dwExtraInfo = extra
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def shell_open(target: str, args: str = "") -> None:
    """Open an app, file, folder or web address the way Explorer would."""
    target = os.path.expandvars(target.strip().strip('"'))
    cwd = os.path.dirname(target) if os.path.isfile(target) else None
    result = shell32.ShellExecuteW(None, "open", target, args or None, cwd, 1)
    if (result or 0) <= 32:
        raise OSError(f"Could not open {target}")


def set_dark_titlebar(hwnd: int) -> None:
    try:
        value = ctypes.c_int(1)
        ctypes.WinDLL("dwmapi").DwmSetWindowAttribute(wintypes.HWND(hwnd), 20, ctypes.byref(value), 4)
    except Exception:
        pass
