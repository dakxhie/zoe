"""Plugin event bus tests (create only)."""

from __future__ import annotations

from plugins.events import Event, clear_subscribers_for_tests, emit, subscribe


def test_emit_delivers_payload():
    clear_subscribers_for_tests()
    seen: list[str] = []

    def handler(payload: dict) -> None:
        seen.append(payload.get("value", ""))

    subscribe(Event.STARTUP, handler)
    emit(Event.STARTUP, {"value": "ok"})
    assert seen == ["ok"]
