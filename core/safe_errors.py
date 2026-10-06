"""Safe error rendering for user-facing boundaries (Phase B3, A.1 §8.5/§10.3/§10.5).

Every boundary that shows text to the user (``tools/executor.py``, the CLI chat
loop and command entry point, the desktop workers) turns unexpected exceptions
into a short, fixed message through this module. What reaches the user is
never a traceback, an exception ``repr``, or a raw exception message (which may
contain local paths, secrets or internal details).

Only exceptions that opt in by subclassing ``TypedSafeError`` contribute their
own ``error_type`` / ``safe_message``; those strings are authored in code and
never include user data or exception text. Everything else becomes
``internal_error`` with a generic message.

Logging is equally conservative: one WARNING line with the context, the
exception *type name* and the innermost frame as ``file basename:line in
function``. No message text, no full paths, no traceback.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from dataclasses import dataclass

INTERNAL_ERROR = "internal_error"
MODEL_UNAVAILABLE = "model_unavailable"

GENERIC_MESSAGE = "Sorry, something went wrong while handling that request. Please try again."
MODEL_UNAVAILABLE_MESSAGE = (
    "Sorry, I could not load the model. Run `python cli/main.py doctor` for details."
)
CANCELLED_MESSAGE = "Cancelled."


class TypedSafeError(Exception):
    """Mixin for exceptions whose ``error_type`` and ``safe_message`` are authored, safe text.

    Subclasses must only ever set ``safe_message`` to fixed strings written in
    code (no user input, no paths, no exception text).
    """

    error_type: str = INTERNAL_ERROR
    safe_message: str = GENERIC_MESSAGE


@dataclass(frozen=True)
class SafeError:
    """A user-presentable error: a stable code plus a fixed message."""

    code: str
    message: str


def to_safe_error(exc: BaseException) -> SafeError:
    """Map any exception to a ``SafeError`` without exposing its message or traceback."""
    if isinstance(exc, TypedSafeError):
        code = exc.error_type if isinstance(exc.error_type, str) and exc.error_type else INTERNAL_ERROR
        message = exc.safe_message if isinstance(exc.safe_message, str) and exc.safe_message else GENERIC_MESSAGE
        return SafeError(code, message)
    # Look the class up without importing the model stack: if brain.generation
    # was never imported, ``exc`` cannot be a ModelLoadError.
    generation = sys.modules.get("brain.generation")
    model_load_error = getattr(generation, "ModelLoadError", None)
    if isinstance(model_load_error, type) and isinstance(exc, model_load_error):
        # ModelLoadError text can embed local paths or wrapped library errors.
        return SafeError(MODEL_UNAVAILABLE, MODEL_UNAVAILABLE_MESSAGE)
    return SafeError(INTERNAL_ERROR, GENERIC_MESSAGE)


def safe_error_message(exc: BaseException) -> str:
    """The fixed user-facing message for ``exc``."""
    return to_safe_error(exc).message


def _location(exc: BaseException) -> str:
    try:
        frames = traceback.extract_tb(exc.__traceback__)
    except Exception:
        return "?"
    if not frames:
        return "?"
    last = frames[-1]
    return f"{os.path.basename(last.filename or '?')}:{last.lineno} in {last.name}"


def log_safe_exception(logger: logging.Logger, context: str, exc: BaseException) -> SafeError:
    """Log a safe one-line diagnostic for ``exc`` and return its ``SafeError``."""
    safe = to_safe_error(exc)
    logger.warning(
        "%s failed: %s (%s) at %s", context, safe.code, type(exc).__name__, _location(exc)
    )
    return safe
