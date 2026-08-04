"""Plugin metadata schema for Zoe AI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PluginMetadata:
    """Descriptive metadata shipped with a plugin."""

    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    examples: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    minimum_zoe_version: str = "2.7"
    license: str = "Proprietary"
    route_id: str = ""

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category,
            "examples": list(self.examples),
            "dependencies": list(self.dependencies),
            "minimum_zoe_version": self.minimum_zoe_version,
            "license": self.license,
            "route_id": self.route_id,
        }
