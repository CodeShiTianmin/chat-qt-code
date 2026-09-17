"""Reusable widgets: message rows, composer, attachment strip, sidebar rows."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from .markdown_render import document_css, render
from .storage import Conversation, Message

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_IMAGE_EDGE = 1600


def fmt_time(ts: float) -> str:
    dt = datetime.fromtimestamp(ts)
    now = datetime.now()
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    if dt.year == now.year:
        return dt.strftime("%m-%d %H:%M")
    return dt.strftime("%Y-%m-%d")


def fmt_relative(ts: float) -> str:
    delta = time.time() - ts
    if delta < 60:
        return "刚刚"
    if delta < 3600:
        return f"{int(delta // 60)} 分钟前"
    if delta < 86400:
        return f"{int(delta // 3600)} 小时前"
    dt = datetime.fromtimestamp(ts)
    if delta < 86400 * 7:
        return f"{int(delta // 86400)} 天前"
    return dt.strftime("%m-%d")


def set_prop(w: QWidget, name: str, value) -> None:
    """Set a dynamic property and force a stylesheet re-evaluation."""
    w.setProperty(name, value)
    st = w.style()
    st.unpolish(w)
    st.polish(w)
    w.update()


# --------------------------------------------------------------------------
# pending images (composer)
# --------------------------------------------------------------------------


@dataclass
class PendingImage:
    data: bytes
    ext: str
    pixmap: QPixmap
    name: str = ""


def _downscale(img: QImage) -> QImage:
    if max(img.width(), img.height()) <= MAX_IMAGE_EDGE:
        return img
    return img.scaled(
        MAX_IMAGE_EDGE, MAX_IMAGE_EDGE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )


def pending_from_image(img: QImage, name: str = "剪贴板图片") -> PendingImage | None:
    if img.isNull():
        return None
    img = _downscale(img)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    data = bytes(buf.data().data())
    return PendingImage(data=data, ext="png", pixmap=QPixmap.fromImage(img), name=name)


def pending_from_file(path: Path) -> PendingImage | None:
    if path.suffix.lower() not in IMAGE_EXTS:
        return None
    img = QImage(str(path))
    if img.isNull():
        return None
    if max(img.width(), img.height()) > MAX_IMAGE_EDGE or path.suffix.lower() in {".bmp"}:
        return pending_from_image(img, path.name)
    try:
        data = path.read_bytes()
    except OSError:
        return None
    ext = path.suffix.lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    return PendingImage(data=data, ext=ext, pixmap=QPixmap.fromImage(img), name=path.name)


# --------------------------------------------------------------------------
# image thumbnails + preview
# --------------------------------------------------------------------------


class ImagePreview(QDialog):
    def __init__(self, pixmap: QPixmap, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        maxw, maxh = int(screen.width() * 0.85), int(screen.height() * 0.85)
        if pixmap.width() > maxw or pixmap.height() > maxh:
            pixmap = pixmap.scaled(
                maxw, maxh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lab = QLabel()
        lab.setPixmap(pixmap)
        lay.addWidget(lab)
        self.setFixedSize(pixmap.size())

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.close()
        super().keyPressEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.close()


class ImageThumb(QLabel):
    def __init__(self, pixmap: QPixmap, size: int = 120, title: str = "图片", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ImageThumb")
        self._full = pixmap
        self._title = title
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        scaled = pixmap.scaled(
            size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
        self.setFixedSize(scaled.size() + QSize(2, 2))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip(f"{title} · {pixmap.width()}×{pixmap.height()} · 点击放大")

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            ImagePreview(self._full, self._title, self.window()).exec()


# --------------------------------------------------------------------------
# message body (auto-height rich text)
# --------------------------------------------------------------------------


class MessageBody(QTextBrowser):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        doc = self.document()
        doc.setDefaultStyleSheet(document_css())
        doc.setDocumentMargin(0)
        doc.documentLayout().documentSizeChanged.connect(self._sync_height)
        self.viewport().setAutoFillBackground(False)
        self.setMinimumHeight(1)
        self._height = 1

    def set_markdown(self, text: str, keep_newlines: bool = False) -> None:
        self.setHtml(render(text, keep_newlines=keep_newlines))

    def _sync_height(self, size) -> None:
        h = int(math.ceil(size.height())) + 4
        if h != self._height:
            self._height = h
            self.setFixedHeight(h)
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        return QSize(super().sizeHint().width(), self._height)

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)
        self._sync_height(self.document().documentLayout().documentSize())


# --------------------------------------------------------------------------
# message row
# --------------------------------------------------------------------------


class MessageWidget(QFrame):
    copy_requested = Signal(str)
    retry_requested = Signal(str)  # message id
    delete_requested = Signal(str)

    def __init__(self, message: Message, image_paths: list[Path], parent: QWidget | None = None):
        super().__init__(parent)
        self.message = message
        self.setObjectName("MessageRow")
        is_user = message.role == "user"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(10)
        self.role_label = QLabel("你" if is_user else (message.model or "助手").upper())
        self.role_label.setObjectName("RoleLabel")
        self.role_label.setProperty("role", "user" if is_user else "assistant")
        self.time_label = QLabel(fmt_time(message.created_at))
        self.time_label.setObjectName("MsgTime")
        head.addWidget(self.role_label)
        head.addWidget(self.time_label)
        head.addStretch(1)

        self.action_bar = QWidget()
        act = QHBoxLayout(self.action_bar)
        act.setContentsMargins(0, 0, 0, 0)
        act.setSpacing(2)
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setObjectName("MsgAction")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.message.content))
        act.addWidget(self.copy_btn)
        if not is_user:
            self.retry_btn = QPushButton("重新生成")
            self.retry_btn.setObjectName("MsgAction")
            self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.retry_btn.clicked.connect(lambda: self.retry_requested.emit(self.message.id))
            act.addWidget(self.retry_btn)
        self.del_btn = QPushButton("删除")
        self.del_btn.setObjectName("MsgAction")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.message.id))
        act.addWidget(self.del_btn)
        self.action_bar.setVisible(False)
        head.addWidget(self.action_bar)
        outer.addLayout(head)

        if image_paths:
            strip = QHBoxLayout()
            strip.setSpacing(8)
            for p in image_paths:
                pm = QPixmap(str(p))
                if pm.isNull():
                    continue
                strip.addWidget(ImageThumb(pm, 140, p.name))
            strip.addStretch(1)
            outer.addLayout(strip)

        self.body = MessageBody()
        if is_user:
            self.body.setObjectName("UserBody")
            bubble = QFrame()
            bubble.setObjectName("UserBubble")
            bl = QVBoxLayout(bubble)
            bl.setContentsMargins(14, 10, 14, 10)
            bl.addWidget(self.body)
            outer.addWidget(bubble)
        else:
            self.body.setObjectName("AssistantBody")
            outer.addWidget(self.body)

        self.typing = QLabel("● ● ●")
        self.typing.setObjectName("Typing")
        self.typing.setVisible(False)
        outer.addWidget(self.typing)
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(380)
        self._typing_timer.timeout.connect(self._tick)
        self._tick_n = 0

        self.error_box = QLabel()
        self.error_box.setObjectName("ErrorBox")
        self.error_box.setWordWrap(True)
        self.error_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.error_box.setVisible(False)
        outer.addWidget(self.error_box)

        self.refresh()

    # -- state ------------------------------------------------------------
    def refresh(self) -> None:
        m = self.message
        is_user = m.role == "user"
        if m.content:
            self.body.set_markdown(m.content, keep_newlines=is_user)
            self.body.setVisible(True)
        else:
            self.body.setVisible(is_user)
        if m.error:
            self.error_box.setText(m.error)
            self.error_box.setVisible(True)
        else:
            self.error_box.setVisible(False)
        if not is_user and m.model:
            self.role_label.setText(m.model.upper())
        self.copy_btn.setEnabled(bool(m.content))

    def set_streaming(self, on: bool) -> None:
        self.typing.setVisible(on and not self.message.content)
        if on:
            self._typing_timer.start()
        else:
            self._typing_timer.stop()
        self.action_bar.setEnabled(not on)

    def append_delta(self, text: str) -> None:
        self.message.content += text
        self.typing.setVisible(False)
        self.body.setVisible(True)
        self.body.set_markdown(self.message.content)

    def _tick(self) -> None:
        self._tick_n = (self._tick_n + 1) % 3
        dots = ["● ○ ○", "○ ● ○", "○ ○ ●"][self._tick_n]
        self.typing.setText(dots)

    def enterEvent(self, e) -> None:
        self.action_bar.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self.action_bar.setVisible(False)
        super().leaveEvent(e)


# --------------------------------------------------------------------------
# empty state
# --------------------------------------------------------------------------

SUGGESTIONS = [
    "用一张表格对比 Python 的 asyncio 与线程池的适用场景",
    "把这段需求整理成带优先级的开发任务清单",
    "解释一下 Transformer 里的注意力机制，配一个小例子",
    "帮我写一封简洁的英文邮件，向同事催一份评审意见",
]


class EmptyState(QWidget):
    prompt_chosen = Signal(str)
    attach_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(2)

        title = QLabel("开始一段新的对话")
        title.setObjectName("EmptyTitle")
        body = QLabel("输入问题、粘贴一张截图，或者从下面挑一个开始。回复会以 Markdown 排版展示，代码块自带高亮。")
        body.setObjectName("EmptyBody")
        body.setWordWrap(True)
        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(body)
        lay.addSpacing(24)

        for s in SUGGESTIONS:
            b = QPushButton(s)
            b.setObjectName("EmptyChip")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=s: self.prompt_chosen.emit(t))
            lay.addWidget(b)
            lay.addSpacing(6)

        lay.addStretch(3)
        self.setMaximumWidth(640)


# --------------------------------------------------------------------------
# attachment strip
# --------------------------------------------------------------------------


class AttachmentTile(QWidget):
    removed = Signal(object)

    def __init__(self, item: PendingImage, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        self.setFixedSize(72, 72)
        thumb = QLabel(self)
        thumb.setObjectName("AttachmentThumb")
        thumb.setGeometry(0, 4, 66, 66)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setPixmap(
            item.pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        thumb.setToolTip(f"{item.name} · {item.pixmap.width()}×{item.pixmap.height()}")
        x = QPushButton("×", self)
        x.setObjectName("AttachmentRemove")
        x.setCursor(Qt.CursorShape.PointingHandCursor)
        x.setToolTip("移除这张图片")
        x.setGeometry(56, 0, 16, 16)
        x.clicked.connect(lambda: self.removed.emit(self))


class AttachmentStrip(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(12, 10, 12, 0)
        self._lay.setSpacing(8)
        self._lay.addStretch(1)
        self.tiles: list[AttachmentTile] = []
        self.setVisible(False)

    def add(self, item: PendingImage) -> None:
        tile = AttachmentTile(item)
        tile.removed.connect(self._remove)
        self._lay.insertWidget(len(self.tiles), tile)
        self.tiles.append(tile)
        self.setVisible(True)
        self.changed.emit()

    def _remove(self, tile: AttachmentTile) -> None:
        self.tiles.remove(tile)
        tile.setParent(None)
        tile.deleteLater()
        self.setVisible(bool(self.tiles))
        self.changed.emit()

    def items(self) -> list[PendingImage]:
        return [t.item for t in self.tiles]

    def clear(self) -> None:
        for t in self.tiles:
            t.setParent(None)
            t.deleteLater()
        self.tiles.clear()
        self.setVisible(False)
        self.changed.emit()


# --------------------------------------------------------------------------
# composer
# --------------------------------------------------------------------------


class ComposerInput(QPlainTextEdit):
    submit = Signal()
    image_pasted = Signal(object)  # QImage
    files_pasted = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ComposerInput")
        self.send_on_enter = True
        self.setTabChangesFocus(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            mods = e.modifiers()
            shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
            ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
            if (self.send_on_enter and not shift) or (not self.send_on_enter and ctrl):
                self.submit.emit()
                return
            if self.send_on_enter and shift:
                self.insertPlainText("\n")
                return
        super().keyPressEvent(e)

    def canInsertFromMimeData(self, source) -> bool:
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source) -> None:
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and not img.isNull():
                self.image_pasted.emit(img)
                return
        if source.hasUrls():
            paths = [Path(u.toLocalFile()) for u in source.urls() if u.isLocalFile()]
            imgs = [p for p in paths if p.suffix.lower() in IMAGE_EXTS]
            if imgs:
                self.files_pasted.emit(imgs)
                return
        super().insertFromMimeData(source)


class Composer(QFrame):
    submitted = Signal(str, list)  # text, list[PendingImage]
    stop_requested = Signal()

    MIN_LINES = 2
    MAX_LINES = 10

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ComposerFrame")
        self.setAcceptDrops(True)
        self._busy = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.strip = AttachmentStrip()
        lay.addWidget(self.strip)

        self.input = ComposerInput()
        self.input.setPlaceholderText("输入消息… 支持 Markdown，粘贴或拖入图片")
        self.input.submit.connect(self._on_submit)
        self.input.image_pasted.connect(self._on_image)
        self.input.files_pasted.connect(self.add_files)
        self.input.textChanged.connect(self._grow)
        self.input.installEventFilter(self)
        lay.addWidget(self.input)

        bar = QHBoxLayout()
        bar.setContentsMargins(8, 4, 8, 8)
        bar.setSpacing(6)
        self.attach_btn = QPushButton()
        self.attach_btn.setObjectName("IconButton")
        self.attach_btn.setIcon(icons.icon("image", theme.MUTED))
        self.attach_btn.setIconSize(icons.icon_size(18))
        self.attach_btn.setToolTip("添加图片 (Ctrl+U)")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bar.addWidget(self.attach_btn)

        self.hint = QLabel()
        self.hint.setObjectName("ComposerHint")
        bar.addWidget(self.hint)
        bar.addStretch(1)

        self.counter = QLabel("")
        self.counter.setObjectName("ComposerHint")
        bar.addWidget(self.counter)

        self.send_btn = QPushButton()
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setIconSize(icons.icon_size(18))
        self.send_btn.clicked.connect(self._on_send_clicked)
        bar.addWidget(self.send_btn)
        lay.addLayout(bar)

        self.set_send_on_enter(True)
        self.set_busy(False)
        self._grow()

    # -- public -------------------------------------------------------------
    def set_send_on_enter(self, on: bool) -> None:
        self.input.send_on_enter = on
        self.hint.setText("Enter 发送 · Shift+Enter 换行" if on else "Ctrl+Enter 发送 · Enter 换行")

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        set_prop(self.send_btn, "stopping", busy)
        if busy:
            self.send_btn.setIcon(icons.icon("stop", theme.ON_ACCENT))
            self.send_btn.setToolTip("停止生成 (Esc)")
        else:
            self.send_btn.setIcon(icons.icon("send", theme.ON_ACCENT, disabled_color=theme.MUTED_2))
            self.send_btn.setToolTip("发送")
        self._update_send_enabled()

    def add_files(self, paths: list[Path]) -> int:
        n = 0
        for p in paths:
            item = pending_from_file(p)
            if item:
                self.strip.add(item)
                n += 1
        self._update_send_enabled()
        return n

    def add_image(self, img: QImage, name: str = "剪贴板图片") -> None:
        item = pending_from_image(img, name)
        if item:
            self.strip.add(item)
            self._update_send_enabled()

    def set_text(self, text: str) -> None:
        self.input.setPlainText(text)
        self.input.moveCursor(self.input.textCursor().MoveOperation.End)
        self.input.setFocus()

    def clear(self) -> None:
        self.input.clear()
        self.strip.clear()

    # -- internals ----------------------------------------------------------
    def _on_image(self, img: QImage) -> None:
        self.add_image(img)

    def _on_submit(self) -> None:
        if self._busy:
            return
        text = self.input.toPlainText().strip()
        items = self.strip.items()
        if not text and not items:
            return
        self.submitted.emit(text, items)

    def _on_send_clicked(self) -> None:
        if self._busy:
            self.stop_requested.emit()
        else:
            self._on_submit()

    def _update_send_enabled(self) -> None:
        if self._busy:
            self.send_btn.setEnabled(True)
            return
        has = bool(self.input.toPlainText().strip()) or bool(self.strip.items())
        self.send_btn.setEnabled(has)
        n = len(self.input.toPlainText())
        self.counter.setText(f"{n} 字" if n > 200 else "")

    def _grow(self) -> None:
        fm = self.input.fontMetrics()
        line_h = fm.lineSpacing()
        doc_h = self.input.document().size().height()
        lines = max(self.MIN_LINES, min(self.MAX_LINES, int(math.ceil(doc_h))))
        margins = self.input.contentsMargins()
        h = int(lines * line_h + margins.top() + margins.bottom() + 16)
        self.input.setFixedHeight(h)
        self._update_send_enabled()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.input:
            if event.type() == event.Type.FocusIn:
                set_prop(self, "focused", True)
            elif event.type() == event.Type.FocusOut:
                set_prop(self, "focused", False)
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        md = e.mimeData()
        if md.hasUrls() and any(Path(u.toLocalFile()).suffix.lower() in IMAGE_EXTS for u in md.urls()):
            e.acceptProposedAction()
            set_prop(self, "dragging", True)
        elif md.hasImage():
            e.acceptProposedAction()
            set_prop(self, "dragging", True)

    def dragLeaveEvent(self, e) -> None:
        set_prop(self, "dragging", False)

    def dropEvent(self, e: QDropEvent) -> None:
        set_prop(self, "dragging", False)
        md = e.mimeData()
        if md.hasUrls():
            self.add_files([Path(u.toLocalFile()) for u in md.urls() if u.isLocalFile()])
        elif md.hasImage():
            img = md.imageData()
            if isinstance(img, QImage):
                self.add_image(img, "拖入图片")
        e.acceptProposedAction()


# --------------------------------------------------------------------------
# sidebar conversation row
# --------------------------------------------------------------------------


class ConversationRow(QFrame):
    def __init__(self, conv: Conversation, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ConvRow")
        self.conv = conv
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.title = QLabel()
        self.title.setObjectName("ConvTitle")
        self.pin = QLabel()
        self.pin.setPixmap(icons.pixmap("pin", theme.MUTED, 12))
        self.pin.setFixedSize(12, 12)
        self.meta = QLabel()
        self.meta.setObjectName("ConvMeta")
        top.addWidget(self.title, 1)
        top.addWidget(self.pin)
        top.addWidget(self.meta)
        lay.addLayout(top)

        self.preview = QLabel()
        self.preview.setObjectName("ConvPreview")
        lay.addWidget(self.preview)
        self.refresh()

    def refresh(self) -> None:
        c = self.conv
        fm = self.title.fontMetrics()
        self.title.setText(fm.elidedText(c.title, Qt.TextElideMode.ElideRight, 170))
        self.title.setToolTip(c.title)
        self.pin.setVisible(c.pinned)
        self.meta.setText(fmt_relative(c.updated_at))
        pfm = self.preview.fontMetrics()
        self.preview.setText(pfm.elidedText(c.preview, Qt.TextElideMode.ElideRight, 220))

    def set_selected(self, on: bool) -> None:
        set_prop(self, "selected", on)


class ChatScroll(QScrollArea):
    """Scroll area that tracks the bottom while streaming unless the user scrolled up."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ChatScroll")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._stick = True
        bar = self.verticalScrollBar()
        bar.valueChanged.connect(self._on_value)
        bar.rangeChanged.connect(self._on_range)

    def _on_value(self, v: int) -> None:
        bar = self.verticalScrollBar()
        self._stick = v >= bar.maximum() - 8

    def _on_range(self, _min: int, _max: int) -> None:
        if self._stick:
            self.verticalScrollBar().setValue(_max)

    def scroll_to_bottom(self) -> None:
        self._stick = True
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
