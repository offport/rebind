"""Render the main window to PNG files without starting the keyboard hook (for checking the design).

    python tools/preview.py <output folder>
"""
import sys
from pathlib import Path

from PySide6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rebind.app import make_app                      # noqa: E402
from rebind.engine import Engine                     # noqa: E402
from rebind.model import Action, Binding, Config, Trigger, mac_preset   # noqa: E402
from rebind.ui.main_window import MainWindow         # noqa: E402


def settle(app, w):
    w.setAttribute(Qt.WA_DontShowOnScreen)
    w.resize(1200, 880)
    w.show()
    for _ in range(5):
        app.processEvents()


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = make_app(sys.argv)

    empty = MainWindow(Config(), Engine(), hook_ok=True)
    empty.tray.hide()
    settle(app, empty)
    empty.grab().save(str(out / "empty.png"))

    cfg = Config()
    for b in mac_preset("win")[:7]:
        cfg.upsert(b)
    cfg.upsert(Binding(Trigger(frozenset(), "ScrollLock"),
                       Action("launch", target="shell:AppsFolder\\Calc", label="Calculator")))
    cfg.upsert(Binding(Trigger(frozenset(), "Pause"), Action("keys", frozenset(), "MediaPlayPause")))
    cfg.upsert(Binding(Trigger(frozenset({"ctrl", "alt"}), "M"), Action("text", text="hello@example.com")))
    win = MainWindow(cfg, Engine(), hook_ok=True)
    win.tray.hide()
    settle(app, win)
    win._select({"win"}, "C")
    win.keyboard.set_pressed("LWin", True)
    app.processEvents()
    win.grab().save(str(out / "win_layer.png"))

    win._select((), "ScrollLock")
    win.keyboard.clear_pressed()
    app.processEvents()
    win.grab().save(str(out / "launch.png"))

    win._select((), "F9")
    win.editor._show_tab(0)
    win.grab().save(str(out / "new.png"))
    app.quit()


if __name__ == "__main__":
    main()
