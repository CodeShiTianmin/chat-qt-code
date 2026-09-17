"""Offscreen smoke test: drives the real MainWindow against the configured API.

Usage: QT_QPA_PLATFORM=offscreen python scripts/smoke.py [out_dir]
Writes screenshots to out_dir (default /tmp/chatqt-smoke) and exits non-zero on failure.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatqt import app as boot  # noqa: E402
from chatqt.config import APP_NAME, Settings  # noqa: E402
from chatqt.main_window import MainWindow  # noqa: E402
from chatqt.widgets import pending_from_image  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/chatqt-smoke")
OUT.mkdir(parents=True, exist_ok=True)


def make_test_image() -> QImage:
    img = QImage(320, 200, QImage.Format.Format_RGB32)
    img.fill(QColor("#FAFAF9"))
    p = QPainter(img)
    p.setBrush(QColor("#C45A3A"))
    p.setPen(QColor("#1C1917"))
    p.drawRect(40, 40, 120, 120)
    p.setBrush(QColor("#059669"))
    p.drawEllipse(190, 50, 90, 90)
    p.end()
    return img


def main() -> int:
    QCoreApplication.setApplicationName(APP_NAME)
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    boot._load_fonts()
    app.setFont(boot._app_font())
    app.setPalette(boot._palette())
    app.setStyleSheet(boot._stylesheet())

    settings = Settings.load()
    settings.data_dir = tempfile.mkdtemp(prefix="chatqt-smoke-")
    if not settings.api_key:
        print("no api key configured; aborting", file=sys.stderr)
        return 2
    win = MainWindow(settings)
    win.resize(1240, 800)
    win.show()

    failures: list[str] = []

    def shot(name: str) -> None:
        win.grab().save(str(OUT / f"{name}.png"))

    def step_send_text() -> None:
        shot("01-empty")
        win.composer.set_text(
            "用 Markdown 简短介绍一下 Python 的列表推导式：给一个带表格的对比和一个代码示例，100 字以内。"
        )
        win.composer._on_submit()
        QTimer.singleShot(400, lambda: shot("02-streaming"))
        wait_idle(step_send_image)

    def step_send_image() -> None:
        shot("03-reply")
        conv = win.current
        assert conv is not None
        last = conv.messages[-1]
        if last.error or not last.content:
            failures.append(f"text reply failed: {last.error!r}")
        item = pending_from_image(make_test_image(), "shapes.png")
        win.composer.strip.add(item)
        win.composer.set_text("这张图里有哪些形状和颜色？一句话回答。")
        shot("04-attachment")
        win.composer._on_submit()
        wait_idle(step_verify)

    def step_verify() -> None:
        shot("05-vision-reply")
        conv = win.current
        assert conv is not None
        last = conv.messages[-1]
        if last.error or not last.content:
            failures.append(f"vision reply failed: {last.error!r}")
        else:
            print("vision reply:", last.content[:120])
        if not conv.messages[-2].images:
            failures.append("image not persisted on user message")
        # wait a little for the auto-title worker
        QTimer.singleShot(6000, step_reload)

    def step_reload() -> None:
        conv = win.current
        assert conv is not None
        print("title:", conv.title)
        if conv.title_is_auto and conv.title == conv.messages[0].content[:24]:
            failures.append("auto title did not run")
        win.current = None
        win.load_conversations()
        if not win.convs or len(win.convs[0].messages) != 4:
            failures.append(f"reload mismatch: {[len(c.messages) for c in win.convs]}")
        shot("06-reloaded")
        win.new_conversation()
        shot("07-new-empty")
        # delete without dialog
        c = win.convs[0]
        win.store.delete(c)
        win.convs.remove(c)
        win.sidebar.rebuild(win.convs, None)
        if win.store.load_all():
            failures.append("delete did not remove conversation file")
        finish()

    def wait_idle(next_step) -> None:
        def poll() -> None:
            if win.worker and win.worker.isRunning():
                QTimer.singleShot(200, poll)
            else:
                QTimer.singleShot(300, next_step)

        QTimer.singleShot(500, poll)

    def finish() -> None:
        for f in failures:
            print("FAIL:", f, file=sys.stderr)
        print("OK" if not failures else f"{len(failures)} failure(s)")
        app.exit(1 if failures else 0)

    QTimer.singleShot(800, step_send_text)
    QTimer.singleShot(180_000, lambda: (failures.append("timeout"), finish()))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
