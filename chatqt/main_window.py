"""Main window: sidebar of conversations, chat view, composer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from .api import ChatWorker, ModelsWorker, TitleWorker, build_messages
from .config import Settings
from .dialogs import ApiSettingsDialog, DataFolderDialog
from .storage import DEFAULT_TITLE, Conversation, Message, Store, now_ts
from .widgets import (
    IMAGE_EXTS,
    ChatScroll,
    Composer,
    ConversationRow,
    EmptyState,
    MessageWidget,
    PendingImage,
    fmt_time,
)

CONTENT_MAX_WIDTH = 780


def _icon_button(name: str, tip: str, color: str = theme.MUTED) -> QPushButton:
    b = QPushButton()
    b.setObjectName("IconButton")
    b.setIcon(icons.icon(name, color))
    b.setIconSize(icons.icon_size(18))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class Sidebar(QFrame):
    new_chat = Signal()
    selected = Signal(str)  # conv id
    api_settings = Signal()
    data_folder = Signal()
    context_menu = Signal(str, QPoint)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.rows: dict[str, tuple[QListWidgetItem, ConversationRow]] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(16, 18, 16, 12)
        hl.setSpacing(12)
        mark_row = QHBoxLayout()
        mark_row.setSpacing(8)
        mark = QLabel("ChatQT")
        mark.setObjectName("Wordmark")
        sub = QLabel("GPT CLIENT")
        sub.setObjectName("WordmarkSub")
        mark_row.addWidget(mark)
        mark_row.addWidget(sub)
        mark_row.addStretch(1)
        hl.addLayout(mark_row)

        self.new_btn = QPushButton("新对话")
        self.new_btn.setObjectName("Primary")
        self.new_btn.setIcon(icons.icon("plus", theme.ON_ACCENT))
        self.new_btn.setIconSize(icons.icon_size(16))
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setToolTip("新对话 (Ctrl+N)")
        self.new_btn.clicked.connect(self.new_chat.emit)
        hl.addWidget(self.new_btn)

        search_wrap = QWidget()
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("搜索对话  Ctrl+K")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)
        sw.addWidget(self.search)
        search_icon = QLabel(search_wrap)
        search_icon.setPixmap(icons.pixmap("search", theme.MUTED_2, 14))
        search_icon.setFixedSize(14, 14)
        search_icon.move(10, 9)
        search_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._search_icon = search_icon
        hl.addWidget(search_wrap)
        lay.addWidget(head)

        self.list = QListWidget()
        self.list.setObjectName("ConvList")
        self.list.setFrameShape(QFrame.Shape.NoFrame)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context)
        self.list.currentItemChanged.connect(self._on_current)
        self.list.setUniformItemSizes(True)
        lay.addWidget(self.list, 1)

        self.empty_hint = QLabel("还没有对话")
        self.empty_hint.setObjectName("ConvPreview")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setContentsMargins(0, 28, 0, 28)
        lay.addWidget(self.empty_hint)

        footer = QWidget()
        footer.setObjectName("SidebarFooter")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(0, 6, 0, 6)
        fl.setSpacing(0)
        self.api_btn = QPushButton("接口设置")
        self.api_btn.setObjectName("FooterButton")
        self.api_btn.setIcon(icons.icon("sliders", theme.FG_SOFT))
        self.api_btn.setIconSize(icons.icon_size(16))
        self.api_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.api_btn.setToolTip("自定义 Base URL、密钥与模型 (Ctrl+,)")
        self.api_btn.clicked.connect(self.api_settings.emit)
        self.data_btn = QPushButton("数据文件夹")
        self.data_btn.setObjectName("FooterButton")
        self.data_btn.setIcon(icons.icon("folder", theme.FG_SOFT))
        self.data_btn.setIconSize(icons.icon_size(16))
        self.data_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_btn.setToolTip("查看或更换会话与图片的存放位置")
        self.data_btn.clicked.connect(self.data_folder.emit)
        fl.addWidget(self.api_btn)
        fl.addWidget(self.data_btn)
        lay.addWidget(footer)

    # -- list management --------------------------------------------------
    def rebuild(self, convs: list[Conversation], current_id: str | None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        self.rows.clear()
        for c in convs:
            item = QListWidgetItem()
            row = ConversationRow(c)
            item.setSizeHint(row.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
            self.rows[c.id] = (item, row)
            if c.id == current_id:
                self.list.setCurrentItem(item)
                row.set_selected(True)
        self.list.blockSignals(False)
        self.apply_filter(self.search.text())
        self.empty_hint.setVisible(not convs)

    def refresh_row(self, conv: Conversation) -> None:
        pair = self.rows.get(conv.id)
        if pair:
            pair[1].refresh()

    def set_current(self, conv_id: str | None) -> None:
        self.list.blockSignals(True)
        for cid, (item, row) in self.rows.items():
            on = cid == conv_id
            row.set_selected(on)
            if on:
                self.list.setCurrentItem(item)
        if conv_id is None:
            self.list.clearSelection()
            self.list.setCurrentRow(-1)
        self.list.blockSignals(False)

    def apply_filter(self, text: str) -> None:
        q = text.strip().lower()
        for item, row in self.rows.values():
            c = row.conv
            hit = not q or q in c.title.lower() or any(q in m.content.lower() for m in c.messages)
            item.setHidden(not hit)

    def _on_current(self, cur: QListWidgetItem | None, _prev) -> None:
        if cur is None:
            return
        cid = cur.data(Qt.ItemDataRole.UserRole)
        for k, (_item, row) in self.rows.items():
            row.set_selected(k == cid)
        self.selected.emit(cid)

    def _on_context(self, pos: QPoint) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        self.context_menu.emit(item.data(Qt.ItemDataRole.UserRole), self.list.viewport().mapToGlobal(pos))


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.store = Store(settings.resolved_data_dir())
        self.convs: list[Conversation] = []
        self.current: Conversation | None = None
        self.widgets: dict[str, MessageWidget] = {}
        self.worker: ChatWorker | None = None
        self.title_workers: list[TitleWorker] = []
        self.models_worker: ModelsWorker | None = None
        self._streaming_widget: MessageWidget | None = None
        self._pending_delta: list[str] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_delta)

        self.setWindowTitle("ChatQT")
        self.setMinimumSize(920, 620)
        self.setWindowIcon(icons.icon("chat", theme.ACCENT, 32))
        self._build()
        self._shortcuts()
        self._restore_geometry()
        self.load_conversations()
        self._apply_settings_to_ui()

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setChildrenCollapsible(False)

        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(400)
        self.sidebar.new_chat.connect(self.new_conversation)
        self.sidebar.selected.connect(self.select_conversation)
        self.sidebar.api_settings.connect(self.open_api_settings)
        self.sidebar.data_folder.connect(self.open_data_folder)
        self.sidebar.context_menu.connect(self._conv_menu)
        self.splitter.addWidget(self.sidebar)

        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # header
        header = QFrame()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 10, 16, 10)
        hl.setSpacing(8)
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("HeaderTitle")
        self.title_edit.setPlaceholderText(DEFAULT_TITLE)
        self.title_edit.setToolTip("点击重命名，Enter 确认")
        self.title_edit.editingFinished.connect(self._title_edited)
        self.title_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hl.addWidget(self.title_edit, 1)
        self.header_meta = QLabel("")
        self.header_meta.setObjectName("HeaderMeta")
        hl.addWidget(self.header_meta)
        hl.addSpacing(8)
        self.model_combo = QComboBox()
        self.model_combo.setToolTip("当前对话使用的模型")
        self.model_combo.setMinimumWidth(170)
        self.model_combo.currentTextChanged.connect(self._model_changed)
        hl.addWidget(self.model_combo)
        self.refresh_models_btn = _icon_button("refresh", "从接口刷新模型列表")
        self.refresh_models_btn.clicked.connect(self.refresh_models)
        hl.addWidget(self.refresh_models_btn)
        self.pin_btn = _icon_button("pin", "置顶对话")
        self.pin_btn.clicked.connect(self.toggle_pin)
        self.export_btn = _icon_button("export", "导出为 Markdown")
        self.export_btn.clicked.connect(self.export_markdown)
        self.delete_btn = _icon_button("trash", "删除对话")
        self.delete_btn.clicked.connect(lambda: self.delete_conversation(self.current.id if self.current else None))
        hl.addWidget(self.pin_btn)
        hl.addWidget(self.export_btn)
        hl.addWidget(self.delete_btn)
        ml.addWidget(header)

        # chat / empty stack
        self.stack = QStackedWidget()
        self.chat_scroll = ChatScroll()
        self.msg_host = QWidget()
        host_l = QHBoxLayout(self.msg_host)
        host_l.setContentsMargins(24, 24, 24, 24)
        self.msg_col = QWidget()
        self.msg_col.setMaximumWidth(CONTENT_MAX_WIDTH)
        self.msg_layout = QVBoxLayout(self.msg_col)
        self.msg_layout.setContentsMargins(0, 0, 0, 0)
        self.msg_layout.setSpacing(28)
        self.msg_layout.addStretch(1)
        host_l.addStretch(1)
        host_l.addWidget(self.msg_col, 10)
        host_l.addStretch(1)
        self.chat_scroll.setWidget(self.msg_host)
        self.stack.addWidget(self.chat_scroll)

        empty_host = QWidget()
        el = QHBoxLayout(empty_host)
        el.setContentsMargins(24, 24, 24, 24)
        self.empty = EmptyState()
        self.empty.prompt_chosen.connect(self._use_suggestion)
        el.addStretch(1)
        el.addWidget(self.empty, 10)
        el.addStretch(1)
        self.stack.addWidget(empty_host)
        ml.addWidget(self.stack, 1)

        # composer
        comp_host = QWidget()
        cl = QHBoxLayout(comp_host)
        cl.setContentsMargins(24, 0, 24, 16)
        self.composer = Composer()
        self.composer.setMaximumWidth(CONTENT_MAX_WIDTH)
        self.composer.submitted.connect(self.send)
        self.composer.stop_requested.connect(self.stop)
        self.composer.attach_btn.clicked.connect(self.pick_images)
        cl.addStretch(1)
        cl.addWidget(self.composer, 10)
        cl.addStretch(1)
        ml.addWidget(comp_host)

        # status bar
        status = QFrame()
        status.setObjectName("StatusBar")
        sl = QHBoxLayout(status)
        sl.setContentsMargins(20, 5, 20, 5)
        self.status_left = QLabel("")
        self.status_right = QLabel("")
        sl.addWidget(self.status_left)
        sl.addStretch(1)
        sl.addWidget(self.status_right)
        ml.addWidget(status)

        self.splitter.addWidget(main)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([self.settings.sidebar_width, 900])
        self.setCentralWidget(self.splitter)

    def _shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_conversation)
        QShortcut(
            QKeySequence("Ctrl+K"),
            self,
            activated=lambda: (self.sidebar.search.setFocus(), self.sidebar.search.selectAll()),
        )
        QShortcut(QKeySequence("Ctrl+U"), self, activated=self.pick_images)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_api_settings)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, activated=self.export_markdown)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: self.composer.input.setFocus())
        QShortcut(QKeySequence("Escape"), self, activated=self.stop)
        del_act = QAction(self)
        del_act.setShortcut(QKeySequence.StandardKey.Delete)
        del_act.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        del_act.triggered.connect(lambda: self.delete_conversation(self.current.id if self.current else None))
        self.sidebar.list.addAction(del_act)

    def _restore_geometry(self) -> None:
        if self.settings.window_geometry:
            self.restoreGeometry(QByteArray.fromBase64(self.settings.window_geometry.encode()))
        else:
            self.resize(1240, 800)
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(screen.center() - self.rect().center())

    def _apply_settings_to_ui(self) -> None:
        self.composer.set_send_on_enter(self.settings.send_on_enter)
        self._fill_models()
        self._update_status()

    def _fill_models(self) -> None:
        ids = list(self.settings.known_models)
        if self.settings.model and self.settings.model not in ids:
            ids.insert(0, self.settings.model)
        want = (self.current.model if self.current and self.current.model else None) or self.settings.model
        if want and want not in ids:
            ids.insert(0, want)
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(ids)
        self.model_combo.setCurrentText(want)
        self.model_combo.blockSignals(False)

    def _update_status(self, extra: str = "") -> None:
        host = self.settings.base_url.replace("https://", "").replace("http://", "")
        key_state = "" if self.settings.api_key else " · 未设置密钥"
        self.status_left.setText(f"{host}{key_state}")
        if self.current:
            n = len([m for m in self.current.messages if m.role in ("user", "assistant")])
            parts = [f"{n} 条消息"]
            if extra:
                parts.append(extra)
            self.status_right.setText(" · ".join(parts))
        else:
            self.status_right.setText(extra)

    # -------------------------------------------------------- conversations
    def load_conversations(self) -> None:
        self.convs = self.store.load_all()
        self.sidebar.rebuild(self.convs, None)
        if self.convs:
            self.select_conversation(self.convs[0].id)
        else:
            self.new_conversation()

    def _find(self, conv_id: str | None) -> Conversation | None:
        return next((c for c in self.convs if c.id == conv_id), None)

    def _sort(self) -> None:
        self.convs.sort(key=lambda c: (not c.pinned, -c.updated_at))

    def new_conversation(self) -> None:
        if self.current and not self.current.messages:
            self.composer.input.setFocus()
            return
        self.current = Conversation(model=self.settings.model)
        self.widgets.clear()
        self.sidebar.set_current(None)
        self._render_current()
        self.composer.clear()
        self.composer.input.setFocus()

    def select_conversation(self, conv_id: str) -> None:
        if self.worker and self.worker.isRunning() and self.current and self.current.id != conv_id:
            self.stop()
        conv = self._find(conv_id)
        if conv is None:
            return
        self.current = conv
        self.sidebar.set_current(conv.id)
        self._render_current()
        self.composer.input.setFocus()

    def _render_current(self) -> None:
        conv = self.current
        # clear message column
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()
        self.widgets.clear()
        if conv is None:
            return
        self.title_edit.blockSignals(True)
        self.title_edit.setText("" if conv.title == DEFAULT_TITLE and not conv.messages else conv.title)
        self.title_edit.blockSignals(False)
        self._fill_models()
        self.pin_btn.setIcon(icons.icon("pin", theme.ACCENT if conv.pinned else theme.MUTED))
        self.pin_btn.setToolTip("取消置顶" if conv.pinned else "置顶对话")
        persisted = conv in self.convs
        self.export_btn.setEnabled(bool(conv.messages))
        self.delete_btn.setEnabled(persisted)
        self.pin_btn.setEnabled(persisted)
        if conv.messages:
            for m in conv.messages:
                self._add_message_widget(m)
            self.stack.setCurrentWidget(self.chat_scroll)
            QTimer.singleShot(0, self.chat_scroll.scroll_to_bottom)
            self.header_meta.setText(self._conv_meta(conv))
        else:
            self.stack.setCurrentIndex(1)
            self.header_meta.setText("")
        self._update_status()

    def _conv_meta(self, conv: Conversation) -> str:
        return f"创建于 {fmt_time(conv.created_at)}"

    def _add_message_widget(self, m: Message) -> MessageWidget:
        paths = [self.store.abs_path(rel) for rel in m.images]
        w = MessageWidget(m, [p for p in paths if p.exists()])
        w.copy_requested.connect(self._copy)
        w.retry_requested.connect(self.retry)
        w.delete_requested.connect(self.delete_message)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, w)
        self.widgets[m.id] = w
        return w

    def _persist(self, conv: Conversation) -> None:
        conv.updated_at = now_ts()
        self.store.save(conv)
        if conv not in self.convs:
            self.convs.insert(0, conv)
            self._sort()
            self.sidebar.rebuild(self.convs, conv.id)
        else:
            self._sort()
            order = [c.id for c in self.convs]
            listed = list(self.sidebar.rows.keys())
            if order != listed:
                self.sidebar.rebuild(self.convs, conv.id)
            else:
                self.sidebar.refresh_row(conv)
        if conv is self.current:
            self.export_btn.setEnabled(bool(conv.messages))
            self.delete_btn.setEnabled(True)
            self.pin_btn.setEnabled(True)

    def delete_conversation(self, conv_id: str | None) -> None:
        conv = self._find(conv_id)
        if conv is None:
            return
        box = QMessageBox(self)
        box.setWindowTitle("删除对话")
        box.setText(f"删除「{conv.title}」？")
        box.setInformativeText(f"{len(conv.messages)} 条消息和相关图片会从数据文件夹中移除，且无法恢复。")
        yes = box.addButton("删除", QMessageBox.ButtonRole.DestructiveRole)
        yes.setObjectName("Danger")
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not yes:
            return
        if self.current is conv and self.worker and self.worker.isRunning():
            self.stop()
        self.store.delete(conv)
        self.convs.remove(conv)
        if self.current is conv:
            self.current = None
        self.sidebar.rebuild(self.convs, None)
        if self.current is None:
            if self.convs:
                self.select_conversation(self.convs[0].id)
            else:
                self.new_conversation()

    def rename_conversation(self, conv_id: str) -> None:
        conv = self._find(conv_id)
        if conv is None:
            return
        if conv is not self.current:
            self.select_conversation(conv_id)
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def _title_edited(self) -> None:
        conv = self.current
        if conv is None:
            return
        text = self.title_edit.text().strip()
        if not text or text == conv.title:
            return
        conv.title = text
        conv.title_is_auto = False
        if conv in self.convs:
            self._persist(conv)
        self.title_edit.clearFocus()

    def toggle_pin(self, conv_id: str | None = None) -> None:
        conv = self._find(conv_id) if isinstance(conv_id, str) else self.current
        if conv is None or conv not in self.convs:
            return
        conv.pinned = not conv.pinned
        self.store.save(conv)
        self._sort()
        self.sidebar.rebuild(self.convs, self.current.id if self.current else None)
        if conv is self.current:
            self.pin_btn.setIcon(icons.icon("pin", theme.ACCENT if conv.pinned else theme.MUTED))
            self.pin_btn.setToolTip("取消置顶" if conv.pinned else "置顶对话")

    def export_markdown(self, conv_id: str | None = None) -> None:
        conv = self._find(conv_id) if isinstance(conv_id, str) else self.current
        if conv is None or not conv.messages:
            return
        safe = "".join(ch for ch in conv.title if ch not in '\\/:*?"<>|').strip() or "conversation"
        path, _ = QFileDialog.getSaveFileName(self, "导出 Markdown", str(Path.home() / f"{safe}.md"), "Markdown (*.md)")
        if not path:
            return
        try:
            Path(path).write_text(conv.to_markdown(), encoding="utf-8")
            self._update_status(f"已导出到 {Path(path).name}")
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))

    def _conv_menu(self, conv_id: str, global_pos: QPoint) -> None:
        conv = self._find(conv_id)
        if conv is None:
            return
        menu = QMenu(self)
        menu.addAction(icons.icon("pencil"), "重命名", lambda: self.rename_conversation(conv_id))
        menu.addAction(icons.icon("pin"), "取消置顶" if conv.pinned else "置顶", lambda: self.toggle_pin(conv_id))
        menu.addAction(icons.icon("export"), "导出 Markdown…", lambda: self.export_markdown(conv_id))
        menu.addSeparator()
        menu.addAction(icons.icon("trash", theme.ERROR), "删除", lambda: self.delete_conversation(conv_id))
        menu.exec(global_pos)

    # -------------------------------------------------------------- chat
    def _use_suggestion(self, text: str) -> None:
        self.composer.set_text(text)

    def pick_images(self) -> None:
        pattern = " ".join(f"*{e}" for e in sorted(IMAGE_EXTS))
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", str(Path.home()), f"图片 ({pattern})")
        if files:
            n = self.composer.add_files([Path(f) for f in files])
            if n < len(files):
                self._update_status(f"{len(files) - n} 个文件不是可用的图片，已跳过")

    def _model_changed(self, model: str) -> None:
        if not model or self.current is None:
            return
        self.current.model = model
        if self.current in self.convs:
            self.store.save(self.current)

    def send(self, text: str, images: list[PendingImage]) -> None:
        if self.worker and self.worker.isRunning():
            return
        if not self.settings.api_key:
            self.open_api_settings()
            if not self.settings.api_key:
                return
        conv = self.current or Conversation(model=self.settings.model)
        self.current = conv
        rels = [self.store.store_image_bytes(img.data, img.ext) for img in images]
        user_msg = Message(role="user", content=text, images=rels)
        conv.messages.append(user_msg)
        if conv.title == DEFAULT_TITLE and conv.title_is_auto and text:
            conv.title = " ".join(text.split())[:24]
        self.composer.clear()
        self._persist(conv)
        if self.stack.currentWidget() is not self.chat_scroll:
            self._render_current()
        else:
            self._add_message_widget(user_msg)
            self.sidebar.refresh_row(conv)
        self._start_generation(conv)

    def _start_generation(self, conv: Conversation) -> None:
        model = conv.model or self.settings.model
        history = [m for m in conv.messages if m.role in ("user", "assistant")]
        payload = build_messages(history, self.settings.system_prompt, self.store.root)
        assistant = Message(role="assistant", model=model)
        conv.messages.append(assistant)
        w = self._add_message_widget(assistant)
        w.set_streaming(True)
        self._streaming_widget = w
        self._pending_delta.clear()
        self.composer.set_busy(True)
        self.chat_scroll.scroll_to_bottom()
        self._update_status("生成中…")

        self.worker = ChatWorker(self.settings, model, payload, self)
        self.worker.delta.connect(self._on_delta)
        self.worker.finished_ok.connect(lambda text, usage, c=conv, m=assistant: self._on_done(c, m, text, usage))
        self.worker.failed.connect(lambda err, c=conv, m=assistant: self._on_failed(c, m, err))
        self.worker.start()
        self._flush_timer.start()

    def _on_delta(self, piece: str) -> None:
        self._pending_delta.append(piece)

    def _flush_delta(self) -> None:
        if not self._pending_delta or self._streaming_widget is None:
            return
        chunk = "".join(self._pending_delta)
        self._pending_delta.clear()
        self._streaming_widget.append_delta(chunk)

    def _finish_stream(self) -> None:
        self._flush_timer.stop()
        self._flush_delta()
        if self._streaming_widget:
            self._streaming_widget.set_streaming(False)
        self._streaming_widget = None
        self.composer.set_busy(False)

    def _on_done(self, conv: Conversation, msg: Message, text: str, usage: dict) -> None:
        self._finish_stream()
        msg.content = text
        msg.error = ""
        w = self.widgets.get(msg.id)
        if w:
            w.refresh()
        self._persist(conv)
        extra = ""
        if usage:
            total = usage.get("total_tokens")
            if total:
                extra = f"本轮 {total} tokens"
        self._update_status(extra)
        user_turns = [m for m in conv.messages if m.role == "user"]
        if self.settings.auto_title and conv.title_is_auto and len(user_turns) == 1 and text:
            self._auto_title(conv, user_turns[0].content or "（图片）", text)

    def _on_failed(self, conv: Conversation, msg: Message, err: str) -> None:
        self._finish_stream()
        msg.error = err
        w = self.widgets.get(msg.id)
        if w:
            w.refresh()
        self._persist(conv)
        self._update_status("请求失败")

    def stop(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2000)
            self._finish_stream()
            conv = self.current
            if conv and conv.messages and conv.messages[-1].role == "assistant":
                last = conv.messages[-1]
                if not last.content:
                    last.error = "已停止生成"
                w = self.widgets.get(last.id)
                if w:
                    w.refresh()
                self._persist(conv)
            self._update_status("已停止")

    def retry(self, msg_id: str) -> None:
        conv = self.current
        if conv is None or (self.worker and self.worker.isRunning()):
            return
        idx = next((i for i, m in enumerate(conv.messages) if m.id == msg_id), None)
        if idx is None:
            return
        for m in conv.messages[idx:]:
            w = self.widgets.pop(m.id, None)
            if w:
                w.setParent(None)
                w.deleteLater()
        del conv.messages[idx:]
        self._start_generation(conv)

    def delete_message(self, msg_id: str) -> None:
        conv = self.current
        if conv is None or (self.worker and self.worker.isRunning()):
            return
        msg = next((m for m in conv.messages if m.id == msg_id), None)
        if msg is None:
            return
        for rel in msg.images:
            try:
                self.store.abs_path(rel).unlink(missing_ok=True)
            except OSError:
                pass
        conv.messages.remove(msg)
        w = self.widgets.pop(msg_id, None)
        if w:
            w.setParent(None)
            w.deleteLater()
        if conv in self.convs:
            if conv.messages:
                self._persist(conv)
            else:
                self.store.delete(conv)
                self.convs.remove(conv)
                self.sidebar.rebuild(self.convs, None)
                self.current = Conversation(model=conv.model)
        self._render_current()

    def _auto_title(self, conv: Conversation, user_text: str, assistant_text: str) -> None:
        tw = TitleWorker(self.settings, conv.model or self.settings.model, conv.id, user_text, assistant_text, self)
        tw.done.connect(self._title_ready)
        tw.finished.connect(lambda: self.title_workers.remove(tw) if tw in self.title_workers else None)
        self.title_workers.append(tw)
        tw.start()

    def _title_ready(self, conv_id: str, title: str) -> None:
        conv = self._find(conv_id)
        if conv is None or not conv.title_is_auto:
            return
        conv.title = title
        self.store.save(conv)
        self.sidebar.refresh_row(conv)
        if conv is self.current:
            self.title_edit.blockSignals(True)
            self.title_edit.setText(title)
            self.title_edit.blockSignals(False)

    def _copy(self, text: str) -> None:
        QApplication.clipboard().setText(text)
        self._update_status("已复制到剪贴板")

    # ----------------------------------------------------------- settings
    def open_api_settings(self) -> None:
        dlg = ApiSettingsDialog(self.settings, self)
        if dlg.exec() == ApiSettingsDialog.DialogCode.Accepted:
            self.settings.save()
            self._apply_settings_to_ui()

    def refresh_models(self) -> None:
        if self.models_worker and self.models_worker.isRunning():
            return
        self.refresh_models_btn.setEnabled(False)
        self._update_status("拉取模型列表…")
        self.models_worker = ModelsWorker(self.settings, self)
        self.models_worker.done.connect(self._models_ready)
        self.models_worker.failed.connect(lambda e: self._update_status(f"模型列表拉取失败：{e}"))
        self.models_worker.finished.connect(lambda: self.refresh_models_btn.setEnabled(True))
        self.models_worker.start()

    def _models_ready(self, ids: list) -> None:
        self.settings.known_models = ids
        self.settings.save()
        self._fill_models()
        self._update_status(f"已加载 {len(ids)} 个模型")

    def open_data_folder(self) -> None:
        dlg = DataFolderDialog(self.settings, self.store, self)
        if dlg.exec() != DataFolderDialog.DialogCode.Accepted or dlg.result_path is None:
            return
        if self.worker and self.worker.isRunning():
            self.stop()
        new_root = dlg.result_path
        try:
            self.store = self.store.migrate_to(new_root) if dlg.migrate else Store(new_root)
        except OSError as exc:
            QMessageBox.warning(self, "更换失败", str(exc))
            return
        self.settings.data_dir = str(new_root)
        self.settings.save()
        self.current = None
        self.load_conversations()
        self._update_status(f"数据文件夹已切换到 {new_root}")

    # -------------------------------------------------------------- close
    def closeEvent(self, e: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1500)
        for tw in list(self.title_workers):
            tw.wait(500)
        self.settings.window_geometry = bytes(self.saveGeometry().toBase64().data()).decode()
        sizes = self.splitter.sizes()
        if sizes:
            self.settings.sidebar_width = sizes[0]
        self.settings.save()
        super().closeEvent(e)
