"""Example notes extension."""

from __future__ import annotations


def register(context):
    storage = context.storage()
    storage.write_text("README.txt", "Notes helper storage area.")

    def match_query(query: str) -> bool:
        return "plugin notes" in query.lower()

    def execute_query(query: str) -> tuple[bool, str]:
        return True, (
            "Notes helper is active. Ask about your indexed notes through Zoe's normal notes route."
        )

    context.register_tool(
        name="Plugin Notes",
        route_id="ext_plugin_notes",
        match_query=match_query,
        execute_query=execute_query,
        priority=30,
    )

    def on_conversation_finished(data: dict) -> None:
        context.logger().debug("Conversation finished (notes plugin observer)")

    context.register_event("conversation_finished", on_conversation_finished)
