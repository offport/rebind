"""Write the icon files from the icon the app draws for itself:
assets/rebind.ico (all sizes, for the exe) and assets/icon.png (for the README)."""
import struct
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from PySide6.QtCore import QBuffer, QIODevice      # noqa: E402
from PySide6.QtGui import QGuiApplication          # noqa: E402

from rebind.ui.widgets import app_pixmap           # noqa: E402

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def png(size: int) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    app_pixmap(size).save(buf, "PNG")
    return bytes(buf.data())


app = QGuiApplication(sys.argv)
assets = root / "assets"
assets.mkdir(exist_ok=True)
images = [png(s) for s in SIZES]
# An .ico is a small directory followed by one PNG per size.
out = struct.pack("<HHH", 0, 1, len(SIZES))
offset = 6 + 16 * len(SIZES)
for size, data in zip(SIZES, images):
    out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
    offset += len(data)
(assets / "rebind.ico").write_bytes(out + b"".join(images))
(assets / "icon.png").write_bytes(png(256))
print("icons written")
