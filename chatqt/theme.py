"""Design tokens and the global Qt stylesheet. Square corners everywhere, one accent."""

from __future__ import annotations

# Stone neutral family (warm tint) + terracotta accent. See DESIGN.md.
BG = "#FAFAF9"
SURFACE = "#F5F5F4"
SURFACE_2 = "#EDEBE8"
FG = "#1C1917"
FG_SOFT = "#44403C"
MUTED = "#78716C"
MUTED_2 = "#A8A29E"
BORDER = "#E7E5E4"
BORDER_STRONG = "#D6D3D1"
ACCENT = "#C45A3A"
ACCENT_HOVER = "#A84A2F"
ACCENT_PRESSED = "#8F3F28"
ACCENT_SOFT = "#F6E7E0"
ERROR = "#BE3554"
ERROR_SOFT = "#F8E4E9"
SUCCESS = "#059669"
SUCCESS_SOFT = "#DDF3EA"
ON_ACCENT = "#FCF7F4"

UI_FONT = "Geist"
CJK_FONTS = [
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "PingFang SC",
    "Microsoft YaHei",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
]
MONO_FONT = "Geist Mono"
MONO_FALLBACK = ["JetBrains Mono", "SF Mono", "Consolas", "DejaVu Sans Mono", "monospace"]

FONT_FAMILIES = [UI_FONT, *CJK_FONTS, "sans-serif"]
MONO_FAMILIES = [MONO_FONT, *MONO_FALLBACK]


def css_font_stack(families: list[str]) -> str:
    return ", ".join(f"'{f}'" if " " in f else f for f in families)


def build_qss() -> str:
    mono = css_font_stack(MONO_FAMILIES)
    return f"""
* {{
    outline: none;
}}
QWidget {{
    background: {BG};
    color: {FG};
    font-size: 14px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {FG};
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QToolTip {{
    background: {FG};
    color: {BG};
    border: 1px solid {FG};
    padding: 5px 8px;
    font-size: 12px;
}}

/* ---- sidebar ------------------------------------------------------ */
#Sidebar {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
#Sidebar QWidget {{
    background: transparent;
}}
#Wordmark {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.3px;
    color: {FG};
}}
#WordmarkSub {{
    font-size: 11px;
    color: {MUTED};
    font-family: {mono};
    letter-spacing: 0.4px;
}}
#SearchField {{
    background: {BG};
    border: 1px solid {BORDER};
    padding: 7px 10px 7px 30px;
    color: {FG};
    font-size: 13px;
}}
#SearchField:focus {{
    border: 1px solid {ACCENT};
}}
#ConvList {{
    background: transparent;
    border: none;
    padding: 0;
}}
#ConvList::item {{
    padding: 0;
    border: none;
}}
#ConvList::item:selected, #ConvList::item:hover {{
    background: transparent;
}}
#ConvRow {{
    border-left: 2px solid transparent;
}}
#ConvRow[selected="true"] {{
    background: {BG};
    border-left: 2px solid {ACCENT};
}}
#ConvRow:hover {{
    background: {SURFACE_2};
}}
#ConvRow[selected="true"]:hover {{
    background: {BG};
}}
#ConvTitle {{
    font-size: 13px;
    font-weight: 500;
    color: {FG};
}}
#ConvPreview {{
    font-size: 12px;
    color: {MUTED};
}}
#ConvMeta {{
    font-size: 11px;
    color: {MUTED_2};
    font-family: {mono};
}}
#GroupLabel {{
    font-size: 11px;
    color: {MUTED};
    font-family: {mono};
    letter-spacing: 1px;
    padding: 14px 16px 4px 16px;
}}
#SidebarFooter {{
    border-top: 1px solid {BORDER};
}}
#FooterButton {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    background: transparent;
    color: {FG_SOFT};
    font-size: 13px;
}}
#FooterButton:hover {{
    background: {SURFACE_2};
    color: {FG};
}}
#FooterButton:pressed {{
    background: {BORDER};
}}
#FooterButton:focus {{
    border: 1px solid {ACCENT};
}}

/* ---- buttons ------------------------------------------------------ */
QPushButton {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
    padding: 7px 14px;
    color: {FG};
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {SURFACE};
    border-color: {MUTED_2};
}}
QPushButton:pressed {{
    background: {SURFACE_2};
}}
QPushButton:disabled {{
    color: {MUTED_2};
    border-color: {BORDER};
    background: {SURFACE};
}}
QPushButton:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton#Primary {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: {ON_ACCENT};
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#Primary:pressed {{
    background: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
QPushButton#Primary:disabled {{
    background: {SURFACE_2};
    border-color: {SURFACE_2};
    color: {MUTED_2};
}}
QPushButton#Primary:focus {{
    border: 1px solid {FG};
}}
QPushButton#Danger {{
    color: {ERROR};
    border-color: {ERROR};
    background: {BG};
}}
QPushButton#Danger:hover {{
    background: {ERROR_SOFT};
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {MUTED};
    padding: 4px 8px;
}}
QPushButton#Ghost:hover {{
    background: {SURFACE};
    color: {FG};
    border-color: {BORDER};
}}
QPushButton#IconButton {{
    background: transparent;
    border: 1px solid transparent;
    padding: 6px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}
QPushButton#IconButton:hover {{
    background: {SURFACE};
    border-color: {BORDER};
}}
QPushButton#IconButton:pressed {{
    background: {SURFACE_2};
}}
QPushButton#IconButton:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton#SendButton {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    padding: 0;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}
QPushButton#SendButton:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#SendButton:disabled {{
    background: {SURFACE_2};
    border-color: {SURFACE_2};
}}
QPushButton#SendButton[stopping="true"] {{
    background: {FG};
    border-color: {FG};
}}
QPushButton#SendButton:focus {{
    border: 1px solid {FG};
}}

/* ---- header ------------------------------------------------------- */
#Header {{
    border-bottom: 1px solid {BORDER};
    background: {BG};
}}
#HeaderTitle {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.2px;
    border: 1px solid transparent;
    padding: 4px 6px;
    background: transparent;
}}
#HeaderTitle:hover {{
    border: 1px solid {BORDER};
}}
#HeaderTitle:focus {{
    border: 1px solid {ACCENT};
    background: {BG};
}}
#HeaderMeta {{
    color: {MUTED};
    font-size: 12px;
    font-family: {mono};
}}

/* ---- combo -------------------------------------------------------- */
QComboBox {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
    padding: 5px 30px 5px 10px;
    font-size: 13px;
    color: {FG};
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {MUTED_2};
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
QComboBox::down-arrow {{
    image: url(:/icons/chevron-down.svg);
    width: 14px;
    height: 14px;
}}
QComboBox QAbstractItemView {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 0;
    outline: none;
    selection-background-color: {SURFACE_2};
    selection-color: {FG};
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 24px;
}}

/* ---- inputs ------------------------------------------------------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
    padding: 7px 10px;
    color: {FG};
    font-size: 13px;
    selection-background-color: {ACCENT_SOFT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled {{
    color: {MUTED_2};
    background: {SURFACE};
}}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0;
    border: none;
}}
QCheckBox {{
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_STRONG};
    background: {BG};
}}
QCheckBox::indicator:hover {{
    border-color: {MUTED};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url(:/icons/check.svg);
}}
QCheckBox:focus {{
    color: {ACCENT};
}}
QSlider::groove:horizontal {{
    height: 2px;
    background: {BORDER_STRONG};
}}
QSlider::handle:horizontal {{
    width: 12px;
    height: 12px;
    margin: -5px 0;
    background: {FG};
    border: 1px solid {FG};
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QSlider::sub-page:horizontal {{
    background: {FG};
}}

/* ---- composer ----------------------------------------------------- */
#ComposerFrame {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
}}
#ComposerFrame[focused="true"] {{
    border: 1px solid {FG};
}}
#ComposerFrame[dragging="true"] {{
    border: 1px dashed {ACCENT};
    background: {ACCENT_SOFT};
}}
#ComposerInput {{
    border: none;
    padding: 10px 12px 4px 12px;
    font-size: 14px;
    background: transparent;
}}
#ComposerHint {{
    color: {MUTED_2};
    font-size: 11px;
    font-family: {mono};
}}
#AttachmentThumb {{
    border: 1px solid {BORDER_STRONG};
    background: {SURFACE};
}}
#AttachmentRemove {{
    background: {FG};
    border: none;
    color: {BG};
    font-size: 11px;
    font-weight: 700;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
    padding: 0;
}}
#AttachmentRemove:hover {{
    background: {ERROR};
}}

/* ---- chat area ---------------------------------------------------- */
#ChatScroll {{
    border: none;
    background: {BG};
}}
#ChatScroll > QWidget > QWidget {{
    background: {BG};
}}
#RoleLabel {{
    font-family: {mono};
    font-size: 11px;
    letter-spacing: 1px;
    color: {MUTED};
}}
#RoleLabel[role="user"] {{
    color: {ACCENT};
}}
#MsgTime {{
    font-family: {mono};
    font-size: 11px;
    color: {MUTED_2};
}}
#UserBubble {{
    background: {SURFACE};
    border: 1px solid {BORDER};
}}
#UserBody, #AssistantBody {{
    border: none;
    background: transparent;
    padding: 0;
}}
#UserBody:focus, #AssistantBody:focus {{
    border: none;
}}
#ErrorBox {{
    background: {ERROR_SOFT};
    border: 1px solid {ERROR};
    color: {ERROR};
    padding: 8px 12px;
    font-size: 13px;
}}
#EmptyTitle {{
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.8px;
    color: {FG};
}}
#EmptyBody {{
    font-size: 14px;
    color: {MUTED};
    line-height: 1.6;
}}
#EmptyChip {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
    padding: 10px 14px;
    text-align: left;
    color: {FG_SOFT};
    font-weight: 400;
}}
#EmptyChip:hover {{
    border-color: {FG};
    color: {FG};
}}
#Typing {{
    color: {MUTED_2};
    font-family: {mono};
    font-size: 13px;
    letter-spacing: 2px;
}}
#MsgAction {{
    background: transparent;
    border: 1px solid transparent;
    color: {MUTED};
    padding: 2px 6px;
    font-size: 11px;
    font-family: {mono};
}}
#MsgAction:hover {{
    color: {FG};
    border-color: {BORDER};
    background: {SURFACE};
}}
#ImageThumb {{
    border: 1px solid {BORDER_STRONG};
}}
#ImageThumb:hover {{
    border-color: {FG};
}}
#StatusBar {{
    border-top: 1px solid {BORDER};
    color: {MUTED};
    font-family: {mono};
    font-size: 11px;
}}
#StatusBar QLabel {{
    color: {MUTED};
    font-family: {mono};
    font-size: 11px;
}}

/* ---- dialogs ------------------------------------------------------ */
#DialogTitle {{
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.4px;
}}
#DialogSub {{
    color: {MUTED};
    font-size: 13px;
}}
#FieldLabel {{
    font-size: 12px;
    color: {FG_SOFT};
    font-weight: 500;
}}
#FieldHelp {{
    font-size: 12px;
    color: {MUTED};
}}
#ResultOk {{
    color: {SUCCESS};
    font-size: 12px;
    font-family: {mono};
}}
#ResultErr {{
    color: {ERROR};
    font-size: 12px;
}}
#PathBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    padding: 10px 12px;
    font-family: {mono};
    font-size: 12px;
    color: {FG_SOFT};
}}
#StatValue {{
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.6px;
    font-family: {mono};
}}
#StatLabel {{
    font-size: 11px;
    color: {MUTED};
    font-family: {mono};
    letter-spacing: 1px;
}}
#Divider {{
    background: {BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* ---- scrollbars --------------------------------------------------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    min-height: 32px;
    margin: 0 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {MUTED_2};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    min-width: 32px;
    margin: 3px 0;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

/* ---- menus -------------------------------------------------------- */
QMenu {{
    background: {BG};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 7px 28px 7px 14px;
    font-size: 13px;
}}
QMenu::item:selected {{
    background: {SURFACE_2};
}}
QMenu::item:disabled {{
    color: {MUTED_2};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 0;
}}
QMessageBox {{
    background: {BG};
}}
QMessageBox QLabel {{
    font-size: 13px;
}}
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
}}
QSplitter::handle:hover {{
    background: {ACCENT};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    top: -1px;
}}
QTabBar::tab {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    padding: 7px 14px;
    color: {MUTED};
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {BG};
    color: {FG};
    border-bottom-color: {BG};
}}
"""
