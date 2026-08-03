"""Pytest coverage for the Zoe agent orchestration layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.executor import execute_agent_plan
from agents.fusion import fuse_tool_outputs
from agents.intent import analyze_intent
from agents.orchestrator import orchestrate_chat_turn
from agents.planner import create_plan
from agents.project_report import build_project_report
from agents.recovery import retry_once, run_with_recovery
from agents.state import AgentState, ExecutionResult, IntentType, PlanStep, ToolOutput
from agents.verifier import verify_agent_state


def test_analyze_intent_detects_memory_and_web_routes() -> None:
    """Intent analyzer maps common queries to routes and tools."""
    memory_intent = analyze_intent("What do you know about me?")
    web_intent = analyze_intent("Search latest AI news")

    assert memory_intent.primary_route == "memory"
    assert "memory" in memory_intent.required_tools
    assert web_intent.primary_route == "web"


def test_planner_creates_internal_multi_step_plan_for_comparison() -> None:
    """Planner creates internal steps for multi-chapter comparison requests."""
    intent = analyze_intent("Compare chapter 2 with chapter 5 and summarize.")
    plan = create_plan(intent, "Compare chapter 2 with chapter 5 and summarize.")

    assert len(plan) >= 3
    assert any(step.tool == "pdf" for step in plan)
    assert plan[-1].tool == "llm"


def test_fusion_ranks_memory_before_web_and_deduplicates() -> None:
    """Fusion prioritizes memory and removes duplicate sections."""
    outputs = [
        ToolOutput("web", "shared fact", 0.9, 10.0, "web", True),
        ToolOutput("memory", "shared fact", 0.8, 5.0, "memory", True),
        ToolOutput("notes", "unique note", 0.7, 4.0, "notes", True),
    ]

    fused = fuse_tool_outputs(outputs)

    assert "shared fact" in fused
    assert fused.index("Learned Memories") < fused.index("## Web Context")
    assert fused.count("shared fact") == 1


def test_recovery_continues_after_tool_failure() -> None:
    """Recovery returns warnings instead of aborting the pipeline."""
    value, warning = run_with_recovery(
        "pdf retrieval",
        lambda: (_ for _ in ()).throw(RuntimeError("pdf down")),
        fallback=lambda: "notes fallback",
        warning_message="pdf unavailable",
    )

    assert value == "notes fallback"
    assert warning == "pdf unavailable"


def test_retry_once_retries_failed_operation() -> None:
    """Retry helper attempts an operation twice."""
    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary")
        return "ok"

    value, warning = retry_once("web search", flaky)

    assert value == "ok"
    assert warning is None
    assert attempts["count"] == 2


def test_verifier_requests_clarification_when_context_is_empty() -> None:
    """Verifier asks for clarification when no reliable context exists."""
    state = AgentState(
        conversation_id="test",
        goal="Summarize chapter 9",
        intent=analyze_intent("Summarize chapter 9"),
    )
    state.execution = ExecutionResult(success=False, outputs=[], warnings=[], errors=["pdf failed"])

    result = verify_agent_state(state)

    assert result.needs_clarification is True


@patch("agents.executor._run_tool")
def test_executor_collects_partial_outputs(mock_run_tool) -> None:
    """Executor keeps successful tool outputs when another tool fails."""
    mock_run_tool.side_effect = lambda tool, query, detail, state: ToolOutput(
        tool,
        "" if tool == "pdf" else f"{tool} content",
        0.0 if tool == "pdf" else 0.8,
        1.0,
        tool,
        tool != "pdf",
        error="missing" if tool == "pdf" else "",
    )
    state = AgentState(
        conversation_id="test",
        goal="Compare chapter 1 and chapter 2",
        intent=analyze_intent("Compare chapter 1 and chapter 2"),
        plan=[
            PlanStep(1, "retrieve", "memory", "memory"),
            PlanStep(2, "retrieve", "pdf", "chapter 1"),
        ],
    )

    result = execute_agent_plan(state)

    assert result.success is True
    assert any(output.tool == "memory" for output in result.outputs)


def test_project_report_detects_python_test_framework() -> None:
    """Project analyzer report includes language and test framework hints."""
    report = build_project_report()

    assert report.language == "python"
    assert report.test_framework == "pytest"
    assert "cli/main.py" in report.entry_points


@patch("agents.executor.execute_agent_plan")
@patch("agents.analyzer.run_project_analysis", return_value=(False, ""))
@patch("brain.context._build_chat_messages", return_value=[{"role": "system", "content": "ctx"}])
@patch("memory.history.get_history", return_value=[])
def test_orchestrator_skips_heavy_execution_for_simple_chat(
    _history,
    _build_messages,
    _analysis,
    mock_execute,
) -> None:
    """Simple conversation requests avoid multi-tool execution."""
    turn = orchestrate_chat_turn("Hello there")

    mock_execute.assert_not_called()
    assert turn.messages is not None


@patch("agents.executor.execute_agent_plan")
@patch("agents.analyzer.run_project_analysis", return_value=(False, ""))
@patch("brain.context._build_chat_messages", return_value=[{"role": "system", "content": "ctx"}])
@patch("memory.history.get_history", return_value=[{"role": "user", "content": "Earlier"}])
def test_orchestrator_runs_plan_for_multi_tool_query(
    _history,
    _build_messages,
    _analysis,
    mock_execute,
) -> None:
    """Multi-tool planning executes retrieval with recovery support."""
    from agents.state import ExecutionResult

    mock_execute.return_value = ExecutionResult(success=True, outputs=[], warnings=[], errors=[])

    orchestrate_chat_turn("Compare chapter 2 with chapter 5 and summarize.")

    mock_execute.assert_called_once()


def test_intent_marks_project_analysis_requests() -> None:
    """Project analysis queries map to the project analysis intent."""
    intent = analyze_intent("Analyze this Python project and tell me how to improve it.")

    assert intent.type == IntentType.PROJECT_ANALYSIS
    assert "project_analysis" in intent.required_tools
