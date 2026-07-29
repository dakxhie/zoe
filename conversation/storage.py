"""Persistent conversation history paths and JSONL storage for Zoe AI."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from core.config import ROOT

logger = logging.getLogger(__name__)

HISTORY_DIR = ROOT / "data" / "history"
CHAT_FILE = HISTORY_DIR / "chat.jsonl"
SUMMARY_FILE = HISTORY_DIR / "summary.json"
SESSION_FILE = HISTORY_DIR / "session.json"


@dataclass(frozen=True)
class StoredMessage:
    """One persisted conversation message."""

    session: str
    timestamp: str
    role: str
    content: str
    id: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert the message to a JSON-serializable dictionary."""
        payload = {
            "session": self.session,
            "timestamp": self.timestamp,
            "role": self.role,
            "content": self.content,
        }
        if self.id:
            payload["id"] = self.id
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> StoredMessage | None:
        """Parse one stored message, returning None when invalid."""
        session = str(payload.get("session", "")).strip()
        role = str(payload.get("role", "")).strip()
        content = str(payload.get("content", "")).strip()
        timestamp = str(payload.get("timestamp", "")).strip()
        if not session or not role or not content:
            return None
        return cls(
            session=session,
            timestamp=timestamp or utc_timestamp(),
            role=role,
            content=content,
            id=str(payload.get("id", "")).strip(),
        )


def utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_history_dir() -> Path:
    """Create the history directory when missing."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return HISTORY_DIR


def chat_file_exists() -> bool:
    """Return True when the chat history file exists and is non-empty."""
    return CHAT_FILE.exists() and CHAT_FILE.stat().st_size > 0


def append_jsonl(message: StoredMessage) -> None:
    """Append one message to the JSONL history file."""
    ensure_history_dir()
    with CHAT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")


def iter_messages() -> Iterator[StoredMessage]:
    """Yield all stored messages in file order."""
    if not CHAT_FILE.exists():
        return

    with CHAT_FILE.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping corrupt history line %s: %s", line_number, exc)
                continue
            if not isinstance(payload, dict):
                continue
            message = StoredMessage.from_dict(payload)
            if message is not None:
                yield message


def load_all_messages() -> list[StoredMessage]:
    """Load every stored message from disk."""
    return list(iter_messages())


def write_messages(messages: list[StoredMessage]) -> None:
    """Rewrite the entire chat history file."""
    ensure_history_dir()
    with CHAT_FILE.open("w", encoding="utf-8") as handle:
        for message in messages:
            handle.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")


def delete_history_files() -> None:
    """Remove persisted history and summary files."""
    for path in (CHAT_FILE, SUMMARY_FILE):
        if path.exists():
            path.unlink()


def read_json_file(path: Path) -> dict[str, object] | None:
    """Read one JSON file, returning None on corruption."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("Corrupt JSON file %s: %s", path, exc)
        return None
    return payload if isinstance(payload, dict) else None


def write_json_file(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON file."""
    ensure_history_dir()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_size_bytes(path: Path) -> int:
    """Return file size in bytes, or zero when missing."""
    if not path.exists():
        return 0
    return path.stat().st_size
