"""Conversation session management for Zoe AI."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from conversation.storage import SESSION_FILE, read_json_file, utc_timestamp, write_json_file


@dataclass(frozen=True)
class SessionInfo:
    """Persisted session metadata."""

    session_id: str
    created_at: str


_active_session_id: str | None = None


def create_session() -> str:
    """Create a new session id for the current chat launch."""
    global _active_session_id

    session_id = str(uuid.uuid4())
    _active_session_id = session_id
    write_json_file(
        SESSION_FILE,
        {
            "session_id": session_id,
            "created_at": utc_timestamp(),
        },
    )
    return session_id


def current_session() -> str:
    """Return the active session id, creating one when needed."""
    global _active_session_id

    if _active_session_id:
        return _active_session_id

    payload = read_json_file(SESSION_FILE)
    if payload and str(payload.get("session_id", "")).strip():
        _active_session_id = str(payload["session_id"])
        return _active_session_id

    return create_session()


def load_last_session() -> SessionInfo | None:
    """Load the most recently persisted session metadata."""
    payload = read_json_file(SESSION_FILE)
    if not payload:
        return None

    session_id = str(payload.get("session_id", "")).strip()
    if not session_id:
        return None

    return SessionInfo(
        session_id=session_id,
        created_at=str(payload.get("created_at", "")).strip(),
    )


def reset_active_session() -> None:
    """Clear the in-process active session cache."""
    global _active_session_id
    _active_session_id = None
