"""Logging configuration for Zoe AI."""

from __future__ import annotations

import logging
import os


def configure_logging(level: int | None = None) -> None:
    """Configure application-wide logging once."""
    root_logger = logging.getLogger()

    if level is None:
        level = _resolve_level()

    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _resolve_level() -> int:
    env = os.environ.get("ZOE_LOG_LEVEL") or os.environ.get("LOG_LEVEL")
    if env:
        return getattr(logging, env.upper(), logging.INFO)
    try:
        from deployment.config import get_config

        return get_config().logging_level()
    except Exception:
        return logging.INFO
