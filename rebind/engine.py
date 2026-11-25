"""The remapper: decides, for each physical key event, whether to hide it and what to do instead.

Two threads. The hook thread only decides (a dictionary lookup) so typing never lags; a worker
thread carries out the action (sending keys, opening an app).
"""
from __future__ import annotations

import queue
import threading

from .keys import KEYS, MASK_VK, MOD_KEY, MODS, from_vk

_MASK_TAP = [(MASK_VK, False, True), (MASK_VK, False, False)]


def _ev(kid: str, down: bool):
    k = KEYS[kid]
    return (k.vk, k.ext, down)


def _needs_mask(kids) -> bool:
    return any(KEYS[k].mod in ("win", "alt") for k in kids)


def plan_keys(target_mods, key: str, held: list[str]):
    """Key events that make Windows see `target_mods + key` while the user is holding `held` modifiers.

    Returns (events, released, pressed): `released` are the user's modifiers lifted for the
    duration, `pressed` the ones added. The caller puts both back afterwards.
    """
    released = [k for k in held if KEYS[k].mod not in target_mods]
    have = {KEYS[k].mod for k in held}
    pressed = [MOD_KEY[m] for m in MODS if m in target_mods and m not in have]
    events = list(_MASK_TAP) if _needs_mask(released) else []
    events += [_ev(k, True) for k in pressed]
    events += [_ev(k, False) for k in released]
    events += [_ev(key, True), _ev(key, False)]
    return events, released, pressed


class Engine:
    def __init__(self, send=None, launch=None, sync=False):
        self._send = send
        self._launch = launch
        self._sync = sync              # tests: run actions inline instead of on the worker thread
        self._lock = threading.Lock()
        self._map: dict = {}
        self.enabled = True
        self._mods_down: set[str] = set()   # modifier keys the user is holding
        self._down: set[str] = set()        # every key the user is holding (to spot auto-repeat)
        self._hidden: set[str] = set()      # keys whose press was hidden from Windows
        self._capture = None
        self.on_key = None      # (key id, is_down)  every physical key, for the live keyboard
        self.on_fired = None    # (binding)
        self.on_error = None    # (message)
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._hook = None
        self._worker = None

    # ---- configuration ----------------------------------------------------

    def set_bindings(self, bindings) -> None:
        table = {(b.trigger.mods, b.trigger.key): b for b in bindings if b.enabled}
        with self._lock:
            self._map = table

    def capture(self, callback) -> None:
        """Hide the next key combination from Windows and hand it to callback((mods, key)),
        or callback(None) if the user pressed Esc on its own."""
        with self._lock:
            self._capture = callback

    def cancel_capture(self) -> None:
        with self._lock:
            self._capture = None

    # ---- lifecycle --------------------------------------------------------

    def start(self, tap=None) -> bool:
        from . import winapi
        self._send = self._send or winapi.send_input
        self._launch = self._launch or winapi.shell_open
        self._hook = winapi.HookThread(self.handle, tap)
        self._hook.start()
        self._hook.ready.wait(5)
        self._worker = threading.Thread(target=self._work, name="rebind-actions", daemon=True)
        self._worker.start()
        return self._hook.ok

    def stop(self) -> None:
        if self._hook:
            self._hook.stop()
            self._hook.join(2)
            self._hook = None
        self._queue.put(None)

    def refresh_hook(self) -> None:
        with self._lock:
            idle = not self._down
        if self._hook and idle:
            self._hook.rehook()

    # ---- the hook side ----------------------------------------------------

    def handle(self, vk: int, ext: bool, up: bool) -> bool:
        """Called for every physical key event. True hides the event from Windows."""
        kid = from_vk(vk, ext)
        if kid is None:
            return False
        with self._lock:
            hide, binding, captured = self._decide(kid, up)
        if self.on_key:
            self.on_key(kid, not up)
        if captured:
            captured[0](captured[1])
        if binding:
            if self.on_fired:
                self.on_fired(binding)
            if self._sync:
                self._run(binding)
            else:
                self._queue.put(binding)
        return hide

    def _decide(self, kid: str, up: bool):
        mod = KEYS[kid].mod
        if up:
            self._down.discard(kid)
            self._mods_down.discard(kid)
            if kid in self._hidden:
                self._hidden.discard(kid)
                return True, None, None
            return False, None, None

        repeat = kid in self._down
        self._down.add(kid)

        if self._capture:
            self._hidden.add(kid)
            if mod:
                self._mods_down.add(kid)
                return True, None, None
            mods = frozenset(KEYS[k].mod for k in self._mods_down)
            callback, self._capture = self._capture, None
            return True, None, (callback, None if kid == "Esc" and not mods else (mods, kid))

        # A modifier that was itself remapped (hidden) does not count as held.
        mods = frozenset(KEYS[k].mod for k in self._mods_down if k not in self._hidden)
        binding = self._map.get((mods, kid)) if self.enabled else None
        if binding is None:
            if kid in self._hidden:      # still held after its shortcut stopped matching: stay hidden until released
                return True, None, None
            if mod:
                self._mods_down.add(kid)
            return False, None, None
        self._hidden.add(kid)
        if repeat and binding.action.type != "keys":
            return True, None, None      # holding the key repeats a sent shortcut, but opens an app only once
        return True, binding, None

    # ---- the action side --------------------------------------------------

    def _work(self) -> None:
        while (binding := self._queue.get()) is not None:
            self._run(binding)

    def _run(self, binding) -> None:
        a = binding.action
        try:
            if a.type == "keys":
                events, released, pressed = plan_keys(a.mods, a.key, self._held())
                self._send(events)
                self._restore(released, pressed)
            elif a.type == "text":
                held = self._held()
                events = (list(_MASK_TAP) if _needs_mask(held) else []) + [_ev(k, False) for k in held]
                self._send(events + _text_events(a.text))
                self._restore(held, [])
            elif a.type == "launch":
                self._launch(a.target, a.args)
        except Exception as exc:
            if self.on_error:
                self.on_error(str(exc))

    def _held(self) -> list[str]:
        """Modifiers Windows currently believes the user is holding."""
        with self._lock:
            return sorted(k for k in self._mods_down if k not in self._hidden)

    def _restore(self, released, pressed) -> None:
        still = set(self._held())
        back = [k for k in released if k in still]
        events = [_ev(k, True) for k in back]
        if _needs_mask(back):
            events += _MASK_TAP
        events += [_ev(k, False) for k in reversed(pressed)]
        self._send(events)
        # The user may have let go in the instant between the check and the send.
        still = set(self._held())
        self._send([_ev(k, False) for k in back if k not in still])


def _text_events(text: str) -> list:
    events = []
    for ch in text.replace("\r\n", "\n"):
        if ch == "\n":
            events += [_ev("Enter", True), _ev("Enter", False)]
        elif ch == "\t":
            events += [_ev("Tab", True), _ev("Tab", False)]
        else:
            raw = ch.encode("utf-16-le")
            for i in range(0, len(raw), 2):
                unit = int.from_bytes(raw[i:i + 2], "little")
                events += [(None, unit, True), (None, unit, False)]
    return events
