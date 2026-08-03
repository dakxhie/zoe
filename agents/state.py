"""Agent execution state for Zoe AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    """High-level intent categories."""

    CONVERSATION = "conversation"
    MEMORY_RETRIEVAL = "memory_retrieval"
    MEMORY_WRITE = "memory_write"
    NOTES = "notes"
    PDF = "pdf"
    CODE = "code"
    VISION = "vision"
    WEB = "web"
    CALCULATOR = "calculator"
    DATETIME = "datetime"
    FILESYSTEM = "filesystem"
    PROJECT_ANALYSIS = "project_analysis"
    MULTI_TOOL = "multi_tool"
    COMPLEX_REASONING = "complex_reasoning"
    COMPARISON = "comparison"
    SUMMARIZATION = "summarization"
    STEP_BY_STEP = "step_by_step"
    REPORT_GENERATION = "report_generation"


class Complexity(str, Enum):
    """Request complexity estimate."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Intent:
    """Classified user intent with tool hints."""

    type: IntentType
    confidence: float
    required_tools: tuple[str, ...]
    complexity: Complexity
    primary_route: str = "chat"


@dataclass(frozen=True)
class PlanStep:
    """One internal execution step (never shown to the user)."""

    order: int
    action: str
    tool: str
    detail: str = ""


@dataclass
class ToolOutput:
    """Structured output from one tool invocation."""

    tool: str
    content: str
    confidence: float
    execution_time_ms: float
    source: str
    success: bool = True
    error: str = ""


@dataclass
class ExecutionResult:
    """Aggregate result from executing a plan."""

    success: bool
    steps: list[PlanStep] = field(default_factory=list)
    outputs: list[ToolOutput] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class TimingMetrics:
    """Per-request timing breakdown (DEBUG only)."""

    planner_ms: float = 0.0
    tool_ms: float = 0.0
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class AgentState:
    """Mutable state for one request lifecycle."""

    conversation_id: str
    goal: str
    intent: Intent | None = None
    plan: list[PlanStep] = field(default_factory=list)
    completed_steps: list[PlanStep] = field(default_factory=list)
    failed_steps: list[PlanStep] = field(default_factory=list)
    tool_outputs: list[ToolOutput] = field(default_factory=list)
    execution: ExecutionResult | None = None
    timings: TimingMetrics = field(default_factory=TimingMetrics)
    analysis_context: str = ""
    fused_context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
