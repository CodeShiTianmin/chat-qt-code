"""Line icons (24px grid, 1.5 stroke) rendered from inline SVG with any tint."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, QStandardPaths, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

_ICONS: dict[str, str] = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "sliders": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    "folder": '<path d="M3.5 7.5v10a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1h-8.2l-2-2.5H4.5a1 1 0 0 0-1 1Z"/>',
    "image": '<rect x="3.5" y="5.5" width="17" height="13"/><path d="m3.5 15.5 4.6-4.6a1 1 0 0 1 1.4 0l6.5 6.5"/><path d="m14 14 2.3-2.3a1 1 0 0 1 1.4 0l2.8 2.8"/><circle cx="15.5" cy="9.5" r="1.2"/>',
    "send": '<path d="M12 19V5"/><path d="m6 11 6-6 6 6"/>',
    "stop": '<rect x="7" y="7" width="10" height="10"/>',
    "trash": '<path d="M5 7h14M9 7V4.5h6V7M7 7l.8 12h8.4L17 7"/><path d="M10 10.5v6M14 10.5v6"/>',
    "pencil": '<path d="m4 20 4.2-.9L19.5 7.8a1 1 0 0 0 0-1.4l-1.9-1.9a1 1 0 0 0-1.4 0L4.9 15.8 4 20Z"/><path d="m14.5 6.2 3.3 3.3"/>',
    "copy": '<rect x="8.5" y="8.5" width="11" height="11"/><path d="M15.5 8.5v-4h-11v11h4"/>',
    "refresh": '<path d="M19 12a7 7 0 1 1-2.05-4.95"/><path d="M19 4v4.5h-4.5"/>',
    "x": '<path d="m6 6 12 12M18 6 6 18"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "chat": '<path d="M4 5.5h16v10.5H9.5L5 20v-4H4V5.5Z"/>',
    "sparkle": '<path d="M12 3.5 14 9.8l6.3 2.2-6.3 2.2L12 20.5l-2-6.3-6.3-2.2L10 9.8 12 3.5Z"/>',
    "export": '<path d="M13 5h6v6M19 5l-8.5 8.5"/><path d="M17 14v5H5V7h5"/>',
    "pin": '<path d="M15 3.5 20.5 9l-4.2 1.4-3.2 3.2.4 4.4-3-3L5 20l4.9-5.5-3-3 4.4.4 3.2-3.2L15 3.5Z"/>',
    "dots": '<circle cx="6" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="18" cy="12" r="1.4"/>',
    "open": '<path d="M3.5 7.5v10a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1h-8.2l-2-2.5H4.5a1 1 0 0 0-1 1Z"/><path d="M8 14h8"/>',
    "broom": '<path d="m14 4 6 6-7.5 7.5a3 3 0 0 1-4.2 0L5.5 14.7a3 3 0 0 1 0-4.2L14 4Z"/><path d="M4 20h8"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/>',
    "database": '<ellipse cx="12" cy="6" rx="7" ry="2.5"/><path d="M5 6v12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6"/><path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
    "plug": '<path d="M9 3.5v4M15 3.5v4M6.5 7.5h11v4a5.5 5.5 0 0 1-11 0v-4Z"/><path d="M12 17v3.5"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
}


def svg_markup(name: str, color: str, size: int = 24) -> str:
    body = _ICONS[name]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )


def pixmap(name: str, color: str = theme.FG, size: int = 18, dpr: float = 1.0) -> QPixmap:
    px = int(size * dpr)
    image = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg_markup(name, color).encode("utf-8")))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    pm = QPixmap.fromImage(image)
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str = theme.FG, size: int = 18, disabled_color: str | None = None) -> QIcon:
    ic = QIcon()
    for dpr in (1.0, 2.0):
        ic.addPixmap(pixmap(name, color, size, dpr), QIcon.Mode.Normal)
        ic.addPixmap(pixmap(name, disabled_color or theme.MUTED_2, size, dpr), QIcon.Mode.Disabled)
    return ic


def icon_size(size: int = 18) -> QSize:
    return QSize(size, size)


_cache_dir: Path | None = None


def svg_file(name: str, color: str = theme.FG) -> str:
    """Write the SVG to a cache file for use in stylesheet url() references."""
    global _cache_dir
    if _cache_dir is None:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) or "/tmp"
        _cache_dir = Path(base) / "icons"
        _cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5(f"{name}{color}".encode()).hexdigest()[:8]
    path = _cache_dir / f"{name}-{digest}.svg"
    if not path.exists():
        path.write_text(svg_markup(name, color), encoding="utf-8")
    return path.as_posix()
