"""Settings dialogs: API endpoint and data folder."""

from __future__ import annotations

import subprocess
import sys
import time
from copy import copy
from pathlib import Path

import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from .api import ApiError, ModelsWorker, complete_once
from .config import DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT, Settings
from .storage import Store, human_size


def _title(text: str, sub: str = "") -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    t = QLabel(text)
    t.setObjectName("DialogTitle")
    lay.addWidget(t)
    if sub:
        s = QLabel(sub)
        s.setObjectName("DialogSub")
        s.setWordWrap(True)
        lay.addWidget(s)
    return w


def _field_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("FieldLabel")
    return lab


def _help(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("FieldHelp")
    lab.setWordWrap(True)
    return lab


def _divider() -> QFrame:
    f = QFrame()
    f.setObjectName("Divider")
    f.setFixedHeight(1)
    return f


class PingWorker(QThread):
    done = Signal(float, str)
    failed = Signal(str)

    def __init__(self, settings: Settings, model: str, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.model = model

    def run(self) -> None:
        t0 = time.perf_counter()
        try:
            reply = complete_once(
                self.settings,
                self.model,
                [{"role": "user", "content": "只回复两个字：收到"}],
                max_tokens=20,
                timeout=45,
            )
        except (ApiError, requests.RequestException, ValueError) as exc:
            self.failed.emit(str(exc))
            return
        self.done.emit(time.perf_counter() - t0, reply)


# --------------------------------------------------------------------------
# API settings
# --------------------------------------------------------------------------


class ApiSettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("接口设置")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.settings = settings
        self._models_worker: ModelsWorker | None = None
        self._ping_worker: PingWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)
        root.addWidget(_title("接口设置", "任何 OpenAI 兼容的 /v1 接口都可以。密钥只保存在本机配置文件里。"))
        root.addWidget(_divider())

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.base_url = QLineEdit(settings.base_url)
        self.base_url.setPlaceholderText(DEFAULT_BASE_URL)
        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        url_row.addWidget(self.base_url, 1)
        reset_btn = QPushButton("恢复默认")
        reset_btn.setObjectName("Ghost")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(lambda: self.base_url.setText(DEFAULT_BASE_URL))
        url_row.addWidget(reset_btn)
        form.addRow(_field_label("Base URL"), url_row)

        self.api_key = QLineEdit(settings.api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-…")
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.addWidget(self.api_key, 1)
        self.show_key = QPushButton("显示")
        self.show_key.setObjectName("Ghost")
        self.show_key.setCheckable(True)
        self.show_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_key.toggled.connect(self._toggle_key)
        key_row.addWidget(self.show_key)
        form.addRow(_field_label("API Key"), key_row)

        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        known = list(settings.known_models) or [DEFAULT_MODEL]
        if settings.model and settings.model not in known:
            known.insert(0, settings.model)
        self.model.addItems(known)
        self.model.setCurrentText(settings.model or DEFAULT_MODEL)
        model_row = QHBoxLayout()
        model_row.setSpacing(6)
        model_row.addWidget(self.model, 1)
        self.fetch_btn = QPushButton("拉取模型列表")
        self.fetch_btn.setObjectName("Ghost")
        self.fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fetch_btn.clicked.connect(self._fetch_models)
        model_row.addWidget(self.fetch_btn)
        form.addRow(_field_label("默认模型"), model_row)

        self.system_prompt = QPlainTextEdit(settings.system_prompt)
        self.system_prompt.setPlaceholderText(DEFAULT_SYSTEM_PROMPT)
        self.system_prompt.setFixedHeight(84)
        form.addRow(_field_label("系统提示词"), self.system_prompt)

        gen_row = QHBoxLayout()
        gen_row.setSpacing(14)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(1)
        self.temperature.setValue(settings.temperature)
        self.temperature.setFixedWidth(84)
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(0, 200000)
        self.max_tokens.setSingleStep(256)
        self.max_tokens.setSpecialValueText("由服务端决定")
        self.max_tokens.setValue(settings.max_tokens)
        self.max_tokens.setFixedWidth(140)
        gen_row.addWidget(QLabel("Temperature"))
        gen_row.addWidget(self.temperature)
        gen_row.addSpacing(8)
        gen_row.addWidget(QLabel("Max tokens"))
        gen_row.addWidget(self.max_tokens)
        gen_row.addStretch(1)
        form.addRow(_field_label("生成参数"), gen_row)

        opts = QVBoxLayout()
        opts.setSpacing(6)
        self.stream = QCheckBox("流式输出（逐字显示）")
        self.stream.setChecked(settings.stream)
        self.auto_title = QCheckBox("首轮回复后自动为会话命名")
        self.auto_title.setChecked(settings.auto_title)
        self.send_on_enter = QCheckBox("Enter 发送，Shift+Enter 换行")
        self.send_on_enter.setChecked(settings.send_on_enter)
        opts.addWidget(self.stream)
        opts.addWidget(self.auto_title)
        opts.addWidget(self.send_on_enter)
        form.addRow(_field_label("行为"), opts)
        root.addLayout(form)

        root.addWidget(_divider())

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setVisible(False)
        root.addWidget(self.result_label)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setIcon(icons.icon("plug", theme.FG))
        self.test_btn.setIconSize(icons.icon_size(16))
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self._ping)
        btns.addWidget(self.test_btn)
        btns.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("保存")
        save.setObjectName("Primary")
        save.setDefault(True)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._accept)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

        if not settings.api_key:
            self.api_key.setFocus()

    # -- helpers ------------------------------------------------------------
    def _toggle_key(self, on: bool) -> None:
        self.api_key.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
        self.show_key.setText("隐藏" if on else "显示")

    def _draft(self) -> Settings:
        s = copy(self.settings)
        s.base_url = self.base_url.text().strip().rstrip("/") or DEFAULT_BASE_URL
        s.api_key = self.api_key.text().strip()
        s.model = self.model.currentText().strip() or DEFAULT_MODEL
        s.system_prompt = self.system_prompt.toPlainText().strip()
        s.temperature = round(self.temperature.value(), 2)
        s.max_tokens = int(self.max_tokens.value())
        s.stream = self.stream.isChecked()
        s.auto_title = self.auto_title.isChecked()
        s.send_on_enter = self.send_on_enter.isChecked()
        s.known_models = [self.model.itemText(i) for i in range(self.model.count())]
        return s

    def _show_result(self, text: str, ok: bool) -> None:
        self.result_label.setObjectName("ResultOk" if ok else "ResultErr")
        self.result_label.style().unpolish(self.result_label)
        self.result_label.style().polish(self.result_label)
        self.result_label.setText(text)
        self.result_label.setVisible(True)

    def _fetch_models(self) -> None:
        if self._models_worker and self._models_worker.isRunning():
            return
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("拉取中…")
        self._models_worker = ModelsWorker(self._draft(), self)
        self._models_worker.done.connect(self._models_ok)
        self._models_worker.failed.connect(self._models_fail)
        self._models_worker.finished.connect(
            lambda: (self.fetch_btn.setEnabled(True), self.fetch_btn.setText("拉取模型列表"))
        )
        self._models_worker.start()

    def _models_ok(self, ids: list) -> None:
        current = self.model.currentText()
        self.model.clear()
        self.model.addItems(ids)
        if current in ids:
            self.model.setCurrentText(current)
        elif ids:
            self.model.setCurrentIndex(0)
        gpt = [i for i in ids if i.startswith("gpt")]
        self._show_result(f"拉到 {len(ids)} 个模型，其中 GPT 系列 {len(gpt)} 个。", True)

    def _models_fail(self, err: str) -> None:
        self._show_result(f"拉取失败：{err}", False)

    def _ping(self) -> None:
        if self._ping_worker and self._ping_worker.isRunning():
            return
        draft = self._draft()
        if not draft.api_key:
            self._show_result("请先填写 API Key。", False)
            self.api_key.setFocus()
            return
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中…")
        self._ping_worker = PingWorker(draft, draft.model, self)
        self._ping_worker.done.connect(self._ping_ok)
        self._ping_worker.failed.connect(self._ping_fail)
        self._ping_worker.finished.connect(lambda: (self.test_btn.setEnabled(True), self.test_btn.setText("测试连接")))
        self._ping_worker.start()

    def _ping_ok(self, seconds: float, reply: str) -> None:
        self._show_result(f"{self.model.currentText()} 可用 · 往返 {seconds:.1f}s · 回复「{reply[:40]}」", True)

    def _ping_fail(self, err: str) -> None:
        self._show_result(f"连接失败：{err}", False)

    def _accept(self) -> None:
        draft = self._draft()
        if not draft.api_key:
            self._show_result("API Key 不能为空。", False)
            self.api_key.setFocus()
            return
        self.settings.__dict__.update(draft.__dict__)
        self.accept()


# --------------------------------------------------------------------------
# Data folder
# --------------------------------------------------------------------------


def reveal_in_file_manager(path: Path) -> None:
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class DataFolderDialog(QDialog):
    """Returns (new_path, migrate) through .result_path / .migrate after accept()."""

    def __init__(self, settings: Settings, store: Store, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("数据文件夹")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.settings = settings
        self.store = store
        self.result_path: Path | None = None
        self.migrate = True

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)
        root.addWidget(_title("数据文件夹", "所有会话（JSON）和图片都存放在这里。启动时会自动加载其中全部对话。"))
        root.addWidget(_divider())

        count, size = store.stats()
        stats = QHBoxLayout()
        stats.setSpacing(32)
        for value, label in (
            (str(count), "个会话"),
            (human_size(size), "占用空间"),
            (str(len(list(store.img_dir.glob("*")))), "张图片"),
        ):
            col = QVBoxLayout()
            col.setSpacing(2)
            v = QLabel(value)
            v.setObjectName("StatValue")
            lab = QLabel(label)
            lab.setObjectName("StatLabel")
            col.addWidget(v)
            col.addWidget(lab)
            stats.addLayout(col)
        stats.addStretch(1)
        root.addLayout(stats)

        root.addWidget(_field_label("当前位置"))
        self.path_box = QLabel(str(store.root))
        self.path_box.setObjectName("PathBox")
        self.path_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_box.setWordWrap(True)
        root.addWidget(self.path_box)

        row = QHBoxLayout()
        row.setSpacing(8)
        open_btn = QPushButton("在文件管理器中打开")
        open_btn.setIcon(icons.icon("open", theme.FG))
        open_btn.setIconSize(icons.icon_size(16))
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: reveal_in_file_manager(store.root))
        choose_btn = QPushButton("更换文件夹…")
        choose_btn.setIcon(icons.icon("folder", theme.FG))
        choose_btn.setIconSize(icons.icon_size(16))
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.clicked.connect(self._choose)
        row.addWidget(open_btn)
        row.addWidget(choose_btn)
        row.addStretch(1)
        root.addLayout(row)

        self.migrate_box = QCheckBox("更换时把现有会话和图片复制到新文件夹")
        self.migrate_box.setChecked(True)
        root.addWidget(self.migrate_box)
        root.addWidget(_help("更换后旧文件夹不会被删除。若新文件夹里已有会话，会一起加载。"))

        root.addWidget(_divider())
        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("关闭")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.reject)
        btns.addWidget(close)
        root.addLayout(btns)

    def _choose(self) -> None:
        picked = QFileDialog.getExistingDirectory(self, "选择数据文件夹", str(self.store.root))
        if not picked:
            return
        new_root = Path(picked)
        if new_root.resolve() == self.store.root.resolve():
            return
        ok = QMessageBox.question(
            self,
            "更换数据文件夹",
            f"将数据文件夹切换到：\n{new_root}\n\n{'现有会话会被复制过去。' if self.migrate_box.isChecked() else '不复制现有会话，只加载新文件夹里的内容。'}",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if ok != QMessageBox.StandardButton.Ok:
            return
        self.result_path = new_root
        self.migrate = self.migrate_box.isChecked()
        self.accept()
