"""Self-test of the real keyboard hook, using only keys nothing listens to (F21 to F24).

Installs the hook, pretends the user pressed F23 and Shift+F21, and checks that Windows
received F24 and F22 instead. Prints PASS or FAIL.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rebind import winapi                                   # noqa: E402
from rebind.engine import Engine                            # noqa: E402
from rebind.keys import KEYS                                # noqa: E402
from rebind.model import Action, Binding, Trigger           # noqa: E402


def main():
    seen = []           # key presses Rebind itself sent, as the hook saw them arrive
    physical = []
    engine = Engine()
    engine.set_bindings([
        Binding(Trigger(frozenset(), "F23"), Action("keys", frozenset(), "F24")),
        Binding(Trigger(frozenset({"shift"}), "F21"), Action("keys", frozenset(), "F22")),
    ])
    engine.on_key = lambda kid, down: physical.append((kid, down))
    if not engine.start(tap=lambda vk, up: seen.append((vk, up))):
        print("FAIL: the hook did not install")
        return 1

    def press(*kids):   # extra=0 makes these look like the user's own key presses
        winapi.send_input([(KEYS[k].vk, KEYS[k].ext, True) for k in kids], extra=0)
        time.sleep(0.15)
        winapi.send_input([(KEYS[k].vk, KEYS[k].ext, False) for k in reversed(kids)], extra=0)
        time.sleep(0.15)

    press("F23")
    press("LShift", "F21")
    press("F20")        # not remapped: must pass through untouched
    engine.stop()

    f = lambda k: KEYS[k].vk
    expect = [(f("F24"), False), (f("F24"), True),
              (f("LShift"), True), (f("F22"), False), (f("F22"), True), (f("LShift"), False)]
    ok = seen == expect and ("F23", True) in physical and ("F20", True) in physical
    print("PASS" if ok else "FAIL")
    if not ok:
        print(" sent by Rebind:", seen, "\n expected:", expect, "\n physical:", physical)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
