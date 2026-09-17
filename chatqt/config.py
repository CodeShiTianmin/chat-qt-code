"""Application settings persisted as JSON in the user's config directory."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "chatqt"

DEFAULT_BASE_URL = "https://rkapi.com/v1"
# Never ship a key in source: first run asks for it (or reads CHATQT_API_KEY).
DEFAULT_API_KEY = os.environ.get("CHATQT_API_KEY", "")
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_SYSTEM_PROMPT = "你是一个乐于助人的助手。回答使用 Markdown 排版，代码放在带语言标注的代码块中。"


def config_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    if not base:
        base = os.path.join(Path.home(), ".config", APP_NAME)
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base:
        base = os.path.join(Path.home(), ".local", "share", APP_NAME)
    return Path(base) / "data"


@dataclass
class Settings:
    base_url: str = DEFAULT_BASE_URL
    api_key: str = DEFAULT_API_KEY
    model: str = DEFAULT_MODEL
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.7
    max_tokens: int = 0  # 0 = let the server decide
    stream: bool = True
    auto_title: bool = True
    send_on_enter: bool = True
    data_dir: str = ""
    known_models: list[str] = field(default_factory=list)
    window_geometry: str = ""
    sidebar_width: int = 272

    def resolved_data_dir(self) -> Path:
        return Path(self.data_dir).expanduser() if self.data_dir else default_data_dir()

    @classmethod
    def load(cls) -> Settings:
        path = config_dir() / "settings.json"
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        allowed = {f.name for f in fields(cls)}
        clean = {k: v for k, v in raw.items() if k in allowed}
        return cls(**clean)

    def save(self) -> None:
        path = config_dir() / "settings.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
