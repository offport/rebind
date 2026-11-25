"""Start-up: one instance only, load the settings, start the engine, show the window (or just the tray)."""
from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from . import APP_NAME, keys
from .engine import Engine
from .model import Config
from .ui import theme
from .ui.main_window import MainWindow

_PIPE = "Rebind.single-instance"


def make_app(argv) -> QApplication:
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    font = QFont(theme.FONT)
    font.setPixelSize(13)
    app.setFont(font)
    app.setStyleSheet(theme.QSS)
    keys.localise()
    return app


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    app = make_app(argv)

    probe = QLocalSocket()
    probe.connectToServer(_PIPE)
    if probe.waitForConnected(300):          # already running: ask that one to show itself
        probe.write(b"show")
        probe.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(_PIPE)
    server = QLocalServer()
    server.listen(_PIPE)

    cfg = Config.load()
    engine = Engine()
    engine.set_bindings(cfg.bindings)
    engine.enabled = False
    hook_ok = engine.start()
    window = MainWindow(cfg, engine, hook_ok)

    def on_second_instance():
        while (conn := server.nextPendingConnection()) is not None:
            conn.close()
        window.reveal()

    server.newConnection.connect(on_second_instance)
    if "--tray" not in argv or not window.tray.isVisible():
        window.show()
    code = app.exec()
    engine.stop()
    return code
