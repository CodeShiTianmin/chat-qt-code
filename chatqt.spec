# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: `pyinstaller chatqt.spec` -> dist/ChatQT(.exe), single file, no console.
import sys
from pathlib import Path

ROOT = Path(SPECPATH)
ASSETS = ROOT / "chatqt" / "assets"

# Qt modules the app never touches; dropping them keeps the exe small.
EXCLUDED_QT = [
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtGraphs", "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtSerialBus", "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech", "PySide6.QtSpatialAudio", "PySide6.QtDesigner", "PySide6.QtUiTools",
    "PySide6.QtHelp", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtConcurrent", "PySide6.QtDBus", "PySide6.QtHttpServer",
    "PySide6.QtNetworkAuth", "PySide6.QtPrintSupport", "PySide6.QtAsyncio",
    "tkinter", "unittest", "pydoc", "doctest", "xmlrpc",
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ASSETS), "chatqt/assets")],
    hiddenimports=["markdown.extensions.fenced_code", "markdown.extensions.tables", "markdown.extensions.sane_lists",
                   "markdown.extensions.nl2br", "markdown.extensions.codehilite", "pygments.lexers", "pygments.formatters.html"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDED_QT,
    noarchive=False,
)
pyz = PYZ(a.pure)

icon = str(ASSETS / ("icon.ico" if sys.platform == "win32" else "icon.png"))

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ChatQT",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon,
)

if sys.platform == "darwin":
    app = BUNDLE(exe, name="ChatQT.app", icon=icon, bundle_identifier="dev.chatqt.app",
                 info_plist={"NSHighResolutionCapable": True})
