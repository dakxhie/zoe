"""Pytest-only defaults for the Zoe test suite (Phase E harness).

Loaded only by pytest through ``pytest.ini`` (``addopts = -p zoe_test_defaults``).
No production module imports it, so it cannot change runtime behavior.

Phase E flipped the ``ZOE_TOOL_LOOP`` default to ON. Most of the existing
suite exercises the legacy pipeline, so under pytest the variable defaults to
``0`` (legacy) unless the shell already set it. ``os.environ.setdefault`` never
overrides an explicit value. The Phase D/E tests remove the variable and reset
the flag cache themselves to test the real (default-on) semantics.
"""

from __future__ import annotations

import os

TEST_DEFAULT_FLAG = ("ZOE_TOOL_LOOP", "0")


def _apply_test_defaults() -> None:
    name, value = TEST_DEFAULT_FLAG
    os.environ.setdefault(name, value)


_apply_test_defaults()  # at plugin import: before any test module or conftest runs


def pytest_configure(config) -> None:  # pragma: no cover - trivial
    _apply_test_defaults()
