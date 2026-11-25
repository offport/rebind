import json

from rebind.engine import Engine
from rebind.keys import KEYS, LAYOUT, MASK_VK, from_vk
from rebind.model import Action, Binding, Config, Trigger, mac_preset

MASK = [(MASK_VK, False, True), (MASK_VK, False, False)]


def ev(kid, down):
    return (KEYS[kid].vk, KEYS[kid].ext, down)


def bind(mods, key, action):
    return Binding(Trigger(frozenset(mods), key), action)


def keys_action(mods, key):
    return Action("keys", frozenset(mods), key)


class Rig:
    def __init__(self, *bindings):
        self.sent, self.launched = [], []
        self.engine = Engine(send=lambda e: self.sent.extend(e), launch=lambda t, a: self.launched.append((t, a)),
                             sync=True)
        self.engine.set_bindings(bindings)

    def down(self, kid):
        return self.engine.handle(KEYS[kid].vk, KEYS[kid].ext, False)

    def up(self, kid):
        return self.engine.handle(KEYS[kid].vk, KEYS[kid].ext, True)


def test_layout_only_uses_known_keys_and_has_no_duplicates():
    ids = [item[0] for item in LAYOUT]
    assert all(i in KEYS for i in ids)
    assert len(ids) == len(set(ids)) == 104


def test_numpad_keys_are_told_apart_from_their_twins():
    assert from_vk(0x0D, True) == "NumpadEnter" and from_vk(0x0D, False) == "Enter"
    assert from_vk(0x24, False) == "Numpad7" and from_vk(0x24, True) == "Home"
    assert from_vk(0xFF, False) is None


def test_win_c_becomes_ctrl_c_and_win_is_put_back():
    rig = Rig(bind(["win"], "C", keys_action(["ctrl"], "C")))
    assert rig.down("LWin") is False            # the modifier itself still reaches Windows
    assert rig.down("C") is True                # the C is hidden
    assert rig.sent == MASK + [ev("LCtrl", True), ev("LWin", False), ev("C", True), ev("C", False),
                               ev("LWin", True)] + MASK + [ev("LCtrl", False)]
    assert rig.up("C") is True
    assert rig.up("LWin") is False


def test_shared_modifier_is_left_alone():
    rig = Rig(bind(["ctrl"], "J", keys_action(["ctrl"], "Down")))
    rig.down("LCtrl")
    rig.down("J")
    assert rig.sent == [ev("Down", True), ev("Down", False)]


def test_unbound_disabled_and_inexact_combinations_pass_through():
    rig = Rig(bind(["ctrl"], "C", keys_action([], "F5")))
    assert rig.down("C") is False and rig.up("C") is False
    rig.down("LCtrl"); rig.down("LShift")
    assert rig.down("C") is False               # Ctrl+Shift+C is not Ctrl+C
    rig.up("C"); rig.up("LShift")
    rig.engine.enabled = False
    assert rig.down("C") is False
    assert rig.sent == []


def test_single_key_opens_an_app_once_even_when_held():
    rig = Rig(bind([], "ScrollLock", Action("launch", target="notepad.exe")))
    assert rig.down("ScrollLock") and rig.down("ScrollLock") and rig.up("ScrollLock")
    assert rig.launched == [("notepad.exe", "")]


def test_held_shortcut_repeats():
    rig = Rig(bind(["alt"], "H", keys_action([], "Left")))
    rig.down("LAlt"); rig.down("H"); rig.down("H")
    assert rig.sent.count(ev("Left", True)) == 2


def test_remapped_modifier_stops_being_a_modifier():
    rig = Rig(bind([], "RCtrl", Action("none")), bind(["ctrl"], "C", keys_action([], "F5")))
    assert rig.down("RCtrl") is True
    assert rig.down("C") is False
    assert rig.sent == []


def test_key_stays_hidden_until_released_after_modifier_is_let_go():
    rig = Rig(bind(["win"], "C", keys_action(["ctrl"], "C")))
    rig.down("LWin"); rig.down("C"); rig.up("LWin")
    assert rig.down("C") is True                # auto-repeat must not start typing "c"
    assert rig.up("C") is True
    assert rig.down("C") is False


def test_type_text_releases_held_modifiers_first():
    rig = Rig(bind(["shift"], "F9", Action("text", text="a\n")))
    rig.down("LShift"); rig.down("F9")
    assert rig.sent == [ev("LShift", False), (None, ord("a"), True), (None, ord("a"), False),
                        ev("Enter", True), ev("Enter", False), ev("LShift", True)]


def test_capture_swallows_and_reports_the_combination():
    rig = Rig(bind(["ctrl"], "K", keys_action([], "F5")))
    got = []
    rig.engine.capture(got.append)
    assert rig.down("LCtrl") and rig.down("K")
    assert got == [(frozenset({"ctrl"}), "K")] and rig.sent == []
    assert rig.up("K") and rig.up("LCtrl")
    rig.engine.capture(got.append)
    rig.down("Esc")
    assert got[-1] is None


def test_config_round_trip_and_replace(tmp_path):
    cfg = Config(path=tmp_path / "c.json")
    cfg.upsert(bind(["win"], "C", keys_action(["ctrl"], "C")))
    cfg.upsert(bind([], "Pause", Action("launch", target="calc.exe", label="Calculator")))
    cfg.upsert(bind(["win"], "C", keys_action(["ctrl"], "Insert")))
    cfg.enabled = False
    cfg.save()
    again = Config.load(cfg.path)
    assert [b.to_dict() for b in again.bindings] == [b.to_dict() for b in cfg.bindings]
    assert len(again.bindings) == 2 and again.enabled is False
    assert again.bindings[0].action.describe() == "Ctrl + Insert"
    assert again.bindings[1].action.describe() == "Open Calculator"


def test_broken_entries_are_skipped(tmp_path):
    good = bind(["alt"], "V", keys_action(["ctrl"], "V")).to_dict()
    bad = {"trigger": {"mods": [], "key": "Nope"}, "action": {"type": "none"}}
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"bindings": [bad, good, {"junk": 1}]}), encoding="utf-8")
    assert [b.trigger.text() for b in Config.load(path).bindings] == ["Alt + V"]


def test_mac_preset_has_copy_and_paste():
    found = {b.trigger.text(): b.action.describe() for b in mac_preset("win")}
    assert found["Win + C"] == "Ctrl + C" and found["Win + V"] == "Ctrl + V"
    assert found["Win + Shift + Z"] == "Ctrl + Y"
