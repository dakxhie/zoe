"""Example local plugin template — copy to plugins/local/."""

from plugins.permissions import Permission
from plugins.plugin import Plugin, ToolCategory
from plugins.sandbox import wrap_execute


def _match(query: str) -> bool:
    return "hello plugin" in query.lower()


def _execute(query: str) -> tuple[bool, str]:
    return True, "Hello from your local plugin!"


PLUGIN = Plugin(
    id="local.hello",
    name="Hello Plugin",
    version="0.1.0",
    author="Community",
    description="Example drop-in plugin",
    category=ToolCategory.EXPERIMENTAL,
    permissions=frozenset({Permission.MEMORY.value}),
    priority=10,
    route_id="experimental_hello",
    examples=("hello plugin",),
    match_query=_match,
    execute_query=wrap_execute("local.hello", frozenset({Permission.MEMORY.value}), _execute),
)
