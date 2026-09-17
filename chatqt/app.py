"""Application bootstrap: fonts, stylesheet, main window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from . import __version__, icons, theme
from .config import APP_NAME, Settings
from .main_window import MainWindow

ASSET_DIR = Path(__file__).parent / "assets"
FONT_DIR = ASSET_DIR / "fonts"


def _load_fonts() -> None:
    if not FONT_DIR.exists():
        return
    for p in sorted(FONT_DIR.glob("*.ttf")) + sorted(FONT_DIR.glob("*.otf")):
        QFontDatabase.addApplicationFont(str(p))


def _app_font() -> QFont:
    f = QFont()
    f.setFamilies(theme.FONT_FAMILIES)
    f.setPointSizeF(10.5)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def _palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(theme.BG))
    pal.setColor(QPalette.ColorRole.Base, QColor(theme.BG))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.SURFACE))
    pal.setColor(QPalette.ColorRole.Text, QColor(theme.FG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(theme.FG))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(theme.FG))
    pal.setColor(QPalette.ColorRole.Button, QColor(theme.BG))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(theme.ACCENT_SOFT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(theme.FG))
    pal.setColor(QPalette.ColorRole.Link, QColor(theme.ACCENT))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme.MUTED_2))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme.FG))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(theme.BG))
    return pal


def _stylesheet() -> str:
    qss = theme.build_qss()
    qss = qss.replace(":/icons/chevron-down.svg", icons.svg_file("chevron-down", theme.MUTED))
    qss = qss.replace(":/icons/check.svg", icons.svg_file("check", theme.ON_ACCENT))
    return qss


def main(argv: list[str] | None = None) -> int:
    # No organization name on purpose: keeps paths at ~/.config/chatqt instead of chatqt/chatqt.
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(__version__)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(argv if argv is not None else sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(ASSET_DIR / "icon.png")))
    _load_fonts()
    app.setFont(_app_font())
    app.setPalette(_palette())
    app.setStyleSheet(_stylesheet())

    settings = Settings.load()
    win = MainWindow(settings)
    win.show()
    if not settings.api_key:
        QTimer.singleShot(150, win.open_api_settings)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
