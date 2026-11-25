"""One palette for the whole app. Mint = "this key is remapped"; amber = "this modifier is held"."""

BG = "#0d0f13"
SURFACE = "#14171e"
SURFACE_2 = "#1b1f29"
FIELD = "#0f1217"
BORDER = "#252a37"
BORDER_HI = "#3b4357"
TEXT = "#e7eaf1"
DIM = "#8a92a6"
FAINT = "#5a6174"
ACCENT = "#5eead4"
ACCENT_INK = "#06241e"
AMBER = "#fbbf24"
DANGER = "#f87171"
KEY_TOP = "#262b38"
KEY_BOTTOM = "#1d212c"
KEY_EDGE = "#0a0c10"

FONT = "Segoe UI Variable Text"

QSS = f"""
QWidget {{ color: {TEXT}; font-size: 13px; }}
QMainWindow, QDialog {{ background: {BG}; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px; }}
QLabel {{ background: transparent; }}
QLabel#appTitle {{ font-size: 19px; font-weight: 600; }}
QLabel#heading {{ font-size: 15px; font-weight: 600; }}
QLabel#section {{ color: {DIM}; font-size: 11px; font-weight: 600; letter-spacing: 1.2px; }}
QLabel#dim {{ color: {DIM}; }}
QLabel#note {{ color: {AMBER}; }}
QLabel#badge {{ color: {DIM}; background: {SURFACE_2}; border-radius: 9px; padding: 1px 8px; font-size: 11px; }}
QLabel#arrow {{ color: {FAINT}; font-size: 15px; }}

QPushButton {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background: #232836; border-color: {BORDER_HI}; }}
QPushButton:pressed {{ background: #181c25; }}
QPushButton:disabled {{ color: {FAINT}; background: #171a22; border-color: {BORDER}; }}
QPushButton::menu-indicator {{ image: none; width: 0; }}
QPushButton[kind="primary"] {{ background: {ACCENT}; color: {ACCENT_INK}; border: none; font-weight: 600;
    padding: 8px 18px; }}
QPushButton[kind="primary"]:hover {{ background: #86f1e0; }}
QPushButton[kind="primary"]:disabled {{ background: #1d3a36; color: #5c8e85; }}
QPushButton[kind="danger"] {{ background: transparent; color: {DANGER}; border-color: #47272c; }}
QPushButton[kind="danger"]:hover {{ background: #2a171a; border-color: {DANGER}; }}
QPushButton[kind="quiet"] {{ background: transparent; border: none; color: {DIM}; padding: 4px 8px; }}
QPushButton[kind="quiet"]:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QPushButton[kind="chip"] {{ border-radius: 14px; padding: 5px 16px; color: {DIM}; }}
QPushButton[kind="chip"]:checked {{ background: rgba(251,191,36,0.14); border-color: {AMBER}; color: {AMBER}; }}
QPushButton[kind="seg"] {{ background: transparent; border: 1px solid transparent; color: {DIM}; padding: 6px 12px; }}
QPushButton[kind="seg"]:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QPushButton[kind="seg"]:checked {{ background: rgba(94,234,212,0.10); border-color: rgba(94,234,212,0.55);
    color: {ACCENT}; }}
QPushButton[recording="true"] {{ border-color: {AMBER}; color: {AMBER}; background: rgba(251,191,36,0.10); }}

QLineEdit, QPlainTextEdit, QComboBox {{ background: {FIELD}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 7px 10px; selection-background-color: #2b6b60; selection-color: {TEXT}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QComboBox:on {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: none; width: 0; height: 0; border-left: 4px solid {FIELD};
    border-right: 4px solid {FIELD}; border-top: 5px solid {DIM}; margin-right: 10px; }}
QComboBox QAbstractItemView {{ background: {SURFACE_2}; border: 1px solid {BORDER_HI}; outline: none;
    padding: 4px; selection-background-color: #2a3142; selection-color: {ACCENT}; }}

QMenu {{ background: {SURFACE_2}; border: 1px solid {BORDER_HI}; padding: 6px; }}
QMenu::item {{ padding: 7px 26px 7px 26px; border-radius: 6px; }}
QMenu::item:selected {{ background: #2a3142; }}
QMenu::item:disabled {{ color: {FAINT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}

QListWidget {{ background: {FIELD}; border: 1px solid {BORDER}; border-radius: 8px; outline: none; padding: 4px; }}
QListWidget::item {{ padding: 8px 10px; border-radius: 6px; }}
QListWidget::item:hover {{ background: {SURFACE_2}; }}
QListWidget::item:selected {{ background: #2a3142; color: {ACCENT}; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_HI}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QFrame#row {{ border: 1px solid transparent; border-radius: 10px; background: transparent; }}
QFrame#row:hover {{ background: {SURFACE_2}; }}
QFrame#row[selected="true"] {{ background: rgba(94,234,212,0.07); border-color: rgba(94,234,212,0.40); }}

QToolTip {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER_HI}; padding: 5px 8px; }}
"""
