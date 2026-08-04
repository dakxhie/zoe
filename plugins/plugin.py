"""Core plugin types for Zoe AI."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol

from plugins.metadata import PluginMetadata
from plugins.permissions import Permission, normalize_permissions

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    MEMORY = "memory"
    RESEARCH = "research"
    CODING = "coding"
    UTILITIES = "utilities"
    SYSTEM = "system"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    VISION = "vision"
    VOICE = "voice"
    EXPERIMENTAL = "experimental"


class PluginHealth(str, Enum):
    LOADED = "loaded"
    DISABLED = "disabled"
    FAILED = "failed"
    MISSING_DEPENDENCY = "missing_dependency"
    CRASHED = "crashed"
    NOT_LOADED = "not_loaded"


ExecuteFn = Callable[[str], tuple[bool, str]]
MatchFn = Callable[[str], bool]


@dataclass
class Plugin:
    """Runtime plugin registration."""

    id: str
    name: str
    version: str
    author: str
    description: str
    category: ToolCategory
    permissions: frozenset[str]
    enabled: bool = True
    priority: int = 50
    route_id: str = ""
    examples: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    minimum_zoe_version: str = "2.7"
    license: str = "Proprietary"
    match_query: MatchFn | None = None
    execute_query: ExecuteFn | None = None
    health: PluginHealth = PluginHealth.NOT_LOADED
    source_path: str = ""
    extension_id: str = ""
    metadata: PluginMetadata | None = None

    def __post_init__(self) -> None:
        if not self.route_id:
            self.route_id = self.id
        self.permissions = normalize_permissions(tuple(self.permissions))
        if self.metadata is None:
            self.metadata = PluginMetadata(
                plugin_id=self.id,
                name=self.name,
                version=self.version,
                author=self.author,
                description=self.description,
                category=self.category.value,
                examples=self.examples,
                dependencies=self.dependencies,
                minimum_zoe_version=self.minimum_zoe_version,
                license=self.license,
                route_id=self.route_id,
            )

    def matches(self, query: str) -> bool:
        if not self.enabled or self.health not in {
            PluginHealth.LOADED,
        }:
            return False
        if self.match_query is None:
            return False
        try:
            return bool(self.match_query(query))
        except Exception as exc:
            logger.warning("Plugin %s match failed: %s", self.id, exc)
            return False

    def run(self, query: str) -> tuple[bool, str]:
        if self.execute_query is None:
            return False, ""
        try:
            return self.execute_query(query)
        except Exception as exc:
            logger.warning("Plugin %s execution failed: %s", self.id, exc)
            self.health = PluginHealth.CRASHED
            raise


class PluginModule(Protocol):
    """Protocol for discoverable plugin modules."""

    PLUGIN: Plugin
