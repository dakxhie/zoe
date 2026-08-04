"""Lightweight plugin event bus."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], None]


class Event(str, Enum):
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_FINISHED = "conversation_finished"
    MEMORY_SAVED = "memory_saved"
    TOOL_CALLED = "tool_called"
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    VOICE_STARTED = "voice_started"
    VOICE_FINISHED = "voice_finished"
    TASK_STARTED = "task_started"
    TASK_FINISHED = "task_finished"


_subscribers: dict[str, list[EventHandler]] = {}


def subscribe(event: Event | str, handler: EventHandler) -> None:
    key = event.value if isinstance(event, Event) else str(event)
    _subscribers.setdefault(key, []).append(handler)


def on_event(event: Event | str) -> Callable[[EventHandler], EventHandler]:
    """Decorator for plugin event handlers."""

    def decorator(fn: EventHandler) -> EventHandler:
        subscribe(event, fn)
        return fn

    return decorator


def emit(event: Event | str, payload: dict[str, Any] | None = None) -> None:
    """Dispatch an event to subscribers; failures are isolated."""
    key = event.value if isinstance(event, Event) else str(event)
    data = payload or {}
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin event: %s", key)

    for handler in list(_subscribers.get(key, [])):
        try:
            handler(data)
        except Exception as exc:
            logger.warning("Plugin event handler failed for %s: %s", key, exc)


def clear_subscribers_for_tests() -> None:
    _subscribers.clear()
