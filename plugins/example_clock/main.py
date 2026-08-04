"""Example clock extension — uses PluginContext only (stdlib + plugin API)."""

from __future__ import annotations

from datetime import datetime, timezone


def register(context):
    def match_query(query: str) -> bool:
        text = query.lower().strip()
        return text.startswith("clock") or text in {"what time is it", "current time"}

    def execute_query(query: str) -> tuple[bool, str]:
        now = datetime.now(timezone.utc).astimezone()
        return True, f"The current local time is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}."

    context.register_tool(
        name="Clock",
        route_id="ext_clock",
        match_query=match_query,
        execute_query=execute_query,
        priority=85,
        description="Returns the current date and time",
    )
