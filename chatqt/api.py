"""OpenAI-compatible chat client (streaming, vision) running on worker threads."""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

import requests
from PySide6.QtCore import QThread, Signal

from .config import Settings
from .storage import Message


class ApiError(Exception):
    pass


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.api_key.strip()}",
        "Content-Type": "application/json",
    }


def _endpoint(base_url: str, path: str) -> str:
    return base_url.strip().rstrip("/") + path


def _extract_error(resp: requests.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error")
        if isinstance(err, dict):
            return err.get("message") or json.dumps(err, ensure_ascii=False)
        if isinstance(err, str):
            return err
        return json.dumps(data, ensure_ascii=False)[:400]
    except ValueError:
        return resp.text[:400] or f"HTTP {resp.status_code}"


def image_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def build_messages(history: list[Message], system_prompt: str, data_root: Path) -> list[dict]:
    out: list[dict] = []
    if system_prompt.strip():
        out.append({"role": "system", "content": system_prompt.strip()})
    for m in history:
        if m.role not in ("user", "assistant"):
            continue
        if m.error and not m.content:
            continue
        if m.images:
            parts: list[dict] = []
            if m.content:
                parts.append({"type": "text", "text": m.content})
            for rel in m.images:
                p = data_root / rel
                if p.exists():
                    parts.append({"type": "image_url", "image_url": {"url": image_to_data_url(p)}})
            out.append({"role": m.role, "content": parts})
        else:
            out.append({"role": m.role, "content": m.content})
    return out


def list_models(settings: Settings, timeout: float = 20) -> list[str]:
    resp = requests.get(_endpoint(settings.base_url, "/models"), headers=_headers(settings), timeout=timeout)
    if resp.status_code >= 400:
        raise ApiError(_extract_error(resp))
    data = resp.json()
    ids = [str(m["id"]) for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
    return sorted(set(ids))


def complete_once(
    settings: Settings, model: str, messages: list[dict], max_tokens: int = 200, timeout: float = 60
) -> str:
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    resp = requests.post(
        _endpoint(settings.base_url, "/chat/completions"),
        headers=_headers(settings),
        json=payload,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise ApiError(_extract_error(resp))
    data = resp.json()
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ApiError(f"响应格式无法解析: {exc}") from exc


class ChatWorker(QThread):
    """Streams one chat completion. Emits deltas, then finished(full_text, usage)."""

    delta = Signal(str)
    finished_ok = Signal(str, dict)
    failed = Signal(str)

    def __init__(self, settings: Settings, model: str, messages: list[dict], parent=None):
        super().__init__(parent)
        self.settings = settings
        self.model = model
        self.messages = messages
        self._cancel = False
        self._resp: requests.Response | None = None

    def cancel(self) -> None:
        self._cancel = True
        resp = self._resp
        if resp is not None:
            try:
                resp.close()
            except Exception:  # noqa: BLE001 - closing a socket must never raise into the UI
                pass

    def run(self) -> None:
        payload: dict = {
            "model": self.model,
            "messages": self.messages,
            "stream": self.settings.stream,
            "temperature": self.settings.temperature,
        }
        if self.settings.max_tokens > 0:
            payload["max_tokens"] = self.settings.max_tokens
        try:
            self._resp = requests.post(
                _endpoint(self.settings.base_url, "/chat/completions"),
                headers=_headers(self.settings),
                json=payload,
                stream=self.settings.stream,
                timeout=(20, 300),
            )
        except requests.RequestException as exc:
            self.failed.emit(f"无法连接接口: {exc}")
            return

        resp = self._resp
        if resp.status_code >= 400:
            self.failed.emit(f"HTTP {resp.status_code}: {_extract_error(resp)}")
            return
        # text/event-stream rarely declares a charset; requests would fall back to latin-1.
        resp.encoding = "utf-8"

        full: list[str] = []
        usage: dict = {}
        try:
            if not self.settings.stream:
                data = resp.json()
                text = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage") or {}
                self.delta.emit(text)
                full.append(text)
            else:
                for raw in resp.iter_lines(decode_unicode=True):
                    if self._cancel:
                        break
                    if not raw or not raw.startswith("data:"):
                        continue
                    chunk = raw[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("usage"):
                        usage = obj["usage"]
                    for choice in obj.get("choices", []):
                        piece = (choice.get("delta") or {}).get("content")
                        if piece:
                            full.append(piece)
                            self.delta.emit(piece)
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            if not self._cancel:
                self.failed.emit(f"读取响应失败: {exc}")
                return
        finally:
            try:
                resp.close()
            except Exception:  # noqa: BLE001
                pass
        self.finished_ok.emit("".join(full), usage)


class TitleWorker(QThread):
    """Asks the model for a short conversation title."""

    done = Signal(str, str)  # conv_id, title
    failed = Signal(str, str)

    def __init__(self, settings: Settings, model: str, conv_id: str, user_text: str, assistant_text: str, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.model = model
        self.conv_id = conv_id
        self.user_text = user_text[:1500]
        self.assistant_text = assistant_text[:1500]

    def run(self) -> None:
        prompt = (
            "根据下面的对话，为它取一个简短的标题：不超过 12 个汉字或 6 个英文单词，"
            "不要标点、引号或前缀，直接输出标题本身。\n\n"
            f"用户：{self.user_text}\n\n助手：{self.assistant_text}"
        )
        try:
            title = complete_once(self.settings, self.model, [{"role": "user", "content": prompt}], max_tokens=40)
        except (ApiError, requests.RequestException) as exc:
            self.failed.emit(self.conv_id, str(exc))
            return
        title = title.strip().strip("\"“”'「」《》").splitlines()[0] if title else ""
        title = title.rstrip("。.!！?？,，")
        if len(title) > 30:
            title = title[:30]
        if not title:
            self.failed.emit(self.conv_id, "空标题")
            return
        self.done.emit(self.conv_id, title)


class ModelsWorker(QThread):
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings

    def run(self) -> None:
        try:
            self.done.emit(list_models(self.settings))
        except (ApiError, requests.RequestException, ValueError) as exc:
            self.failed.emit(str(exc))
