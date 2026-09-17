"""Render the app icon (square terracotta mark) to chatqt/assets/icon.png / icon.ico.

Run: QT_QPA_PLATFORM=offscreen python scripts/make_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chatqt import theme  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "chatqt" / "assets"


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # square plate, square inner rule: no rounded corners anywhere
    p.fillRect(0, 0, size, size, QColor(theme.ACCENT))
    inset = max(1, round(size * 0.09))
    pen = QPen(QColor(theme.ON_ACCENT))
    pen.setWidthF(max(1.0, size * 0.035))
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(inset, inset, size - 2 * inset, size - 2 * inset))

    # wordmark glyph
    f = QFont()
    f.setFamilies(theme.FONT_FAMILIES)
    f.setWeight(QFont.Weight.DemiBold)
    f.setPixelSize(round(size * 0.52))
    p.setFont(f)
    p.setPen(QColor(theme.ON_ACCENT))
    p.drawText(QRectF(0, -size * 0.02, size, size), Qt.AlignmentFlag.AlignCenter, "Q")
    p.end()
    return img


def main() -> None:
    QGuiApplication(sys.argv)
    from chatqt.app import _load_fonts

    _load_fonts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    big = render(256)
    big.save(str(OUT_DIR / "icon.png"))
    # Qt's ICO writer only stores one frame; the 256px frame downsamples cleanly on Windows.
    big.save(str(OUT_DIR / "icon.ico"))
    print(OUT_DIR / "icon.png", OUT_DIR / "icon.ico")


if __name__ == "__main__":
    main()
