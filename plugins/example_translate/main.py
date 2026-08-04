"""Example translate extension (local stub, no network calls)."""

from __future__ import annotations


def register(context):
    def match_query(query: str) -> bool:
        text = query.lower()
        return text.startswith("translate ") or text.startswith("plugin translate ")

    def execute_query(query: str) -> tuple[bool, str]:
        parts = query.split(maxsplit=2)
        if len(parts) < 2:
            return True, "Usage: translate <text>"
        phrase = query.split("translate", 1)[-1].strip()
        if not phrase:
            return True, "Usage: translate <text>"
        return True, f"[translate stub] Received: {phrase}"

    context.register_tool(
        name="Translate",
        route_id="ext_translate",
        match_query=match_query,
        execute_query=execute_query,
        priority=35,
    )

    def chat_hook(data: dict):
        if "translate" in data.get("user_message", "").lower():
            return {"append": ""}

    context.register_chat_hook(chat_hook)
