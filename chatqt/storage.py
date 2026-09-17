"""Conversation persistence: one JSON file per conversation inside the data folder."""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONVERSATIONS_DIR = "conversations"
IMAGES_DIR = "images"
DEFAULT_TITLE = "新对话"


def now_ts() -> float:
    return time.time()


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str = ""
    images: list[str] = field(default_factory=list)  # relative paths under <data>/images
    created_at: float = field(default_factory=now_ts)
    model: str = ""
    error: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @classmethod
    def from_dict(cls, raw: dict) -> Message:
        return cls(
            role=raw.get("role", "user"),
            content=raw.get("content", ""),
            images=list(raw.get("images", [])),
            created_at=float(raw.get("created_at", now_ts())),
            model=raw.get("model", ""),
            error=raw.get("error", ""),
            id=raw.get("id") or uuid.uuid4().hex[:12],
        )


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = DEFAULT_TITLE
    model: str = ""
    created_at: float = field(default_factory=now_ts)
    updated_at: float = field(default_factory=now_ts)
    pinned: bool = False
    title_is_auto: bool = True
    messages: list[Message] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> Conversation:
        return cls(
            id=raw.get("id") or uuid.uuid4().hex,
            title=raw.get("title") or DEFAULT_TITLE,
            model=raw.get("model", ""),
            created_at=float(raw.get("created_at", now_ts())),
            updated_at=float(raw.get("updated_at", now_ts())),
            pinned=bool(raw.get("pinned", False)),
            title_is_auto=bool(raw.get("title_is_auto", True)),
            messages=[Message.from_dict(m) for m in raw.get("messages", [])],
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def preview(self) -> str:
        for m in reversed(self.messages):
            if m.content.strip():
                text = " ".join(m.content.split())
                return text[:80]
            if m.images:
                return f"[{len(m.images)} 张图片]"
        return "还没有消息"

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        for m in self.messages:
            who = {"user": "用户", "assistant": "助手", "system": "系统"}.get(m.role, m.role)
            lines.append(f"## {who}")
            lines.append("")
            if m.images:
                lines.extend(f"![image]({p})" for p in m.images)
                lines.append("")
            lines.append(m.content)
            lines.append("")
        return "\n".join(lines)


class Store:
    """Owns the data folder; loads and saves every conversation."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.conv_dir = self.root / CONVERSATIONS_DIR
        self.img_dir = self.root / IMAGES_DIR
        self.conv_dir.mkdir(parents=True, exist_ok=True)
        self.img_dir.mkdir(parents=True, exist_ok=True)

    # -- conversations -------------------------------------------------
    def _path(self, conv_id: str) -> Path:
        return self.conv_dir / f"{conv_id}.json"

    def load_all(self) -> list[Conversation]:
        convs: list[Conversation] = []
        for p in self.conv_dir.glob("*.json"):
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                convs.append(Conversation.from_dict(raw))
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                continue
        convs.sort(key=lambda c: (not c.pinned, -c.updated_at))
        return convs

    def save(self, conv: Conversation) -> None:
        path = self._path(conv.id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(conv.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def delete(self, conv: Conversation) -> None:
        for m in conv.messages:
            for rel in m.images:
                try:
                    (self.root / rel).unlink(missing_ok=True)
                except OSError:
                    pass
        try:
            self._path(conv.id).unlink(missing_ok=True)
        except OSError:
            pass

    # -- images --------------------------------------------------------
    def store_image_bytes(self, data: bytes, ext: str = "png") -> str:
        name = f"{uuid.uuid4().hex}.{ext.lower().lstrip('.') or 'png'}"
        (self.img_dir / name).write_bytes(data)
        return f"{IMAGES_DIR}/{name}"

    def store_image_file(self, src: Path) -> str:
        ext = src.suffix.lstrip(".").lower() or "png"
        name = f"{uuid.uuid4().hex}.{ext}"
        shutil.copyfile(src, self.img_dir / name)
        return f"{IMAGES_DIR}/{name}"

    def abs_path(self, rel: str) -> Path:
        return self.root / rel

    # -- stats ---------------------------------------------------------
    def stats(self) -> tuple[int, int]:
        count = len(list(self.conv_dir.glob("*.json")))
        size = 0
        for p in self.root.rglob("*"):
            if p.is_file():
                try:
                    size += p.stat().st_size
                except OSError:
                    pass
        return count, size

    # -- migration -----------------------------------------------------
    def migrate_to(self, new_root: Path) -> Store:
        new_root = Path(new_root)
        new_store = Store(new_root)
        for sub in (CONVERSATIONS_DIR, IMAGES_DIR):
            src = self.root / sub
            dst = new_root / sub
            if not src.exists():
                continue
            for p in src.iterdir():
                if p.is_file() and not (dst / p.name).exists():
                    shutil.copy2(p, dst / p.name)
        return new_store


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
