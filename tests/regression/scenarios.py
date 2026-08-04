"""Individual end-to-end regression scenarios for Zoe AI."""

from __future__ import annotations

import importlib
import time
from pathlib import Path
from typing import Callable

from tests.regression.assertions import (
    RegressionAssertionError,
    assert_contains,
    assert_equals,
    assert_not_empty,
    assert_true,
)
from tests.regression.report import ScenarioOutcome, ScenarioStatus
from tests.regression.utils import (
    ROOT,
    measure_seconds,
    regression_marker,
    tagged_memory_text,
)


def _outcome(
    key: str,
    label: str,
    status: ScenarioStatus,
    detail: str = "",
    duration_s: float = 0.0,
) -> ScenarioOutcome:
    return ScenarioOutcome(
        key=key,
        label=label,
        status=status,
        detail=detail,
        duration_s=duration_s,
    )


def _run_guarded(key: str, label: str, fn: Callable[[], None]) -> ScenarioOutcome:
    timing: list[float] = [0.0]
    try:
        with measure_seconds() as bucket:
            fn()
        timing[0] = bucket[0]
        return _outcome(key, label, ScenarioStatus.PASS, duration_s=timing[0])
    except RegressionAssertionError as exc:
        return _outcome(key, label, ScenarioStatus.FAIL, str(exc), timing[0])
    except Exception as exc:
        return _outcome(key, label, ScenarioStatus.FAIL, f"{type(exc).__name__}: {exc}", timing[0])


def scenario_doctor() -> ScenarioOutcome:
    try:
        with measure_seconds() as bucket:
            from core.doctor import CheckStatus, run_doctor

            report = run_doctor()
            assert_true(report is not None, "Doctor returned no report")
            if report.overall_status == CheckStatus.FAIL:
                raise RegressionAssertionError("Doctor overall status is FAIL")
            duration = bucket[0]
            if report.overall_status == CheckStatus.WARN:
                return _outcome(
                    "doctor",
                    "Doctor",
                    ScenarioStatus.WARN,
                    "Doctor reported warnings",
                    duration,
                )
        return _outcome("doctor", "Doctor", ScenarioStatus.PASS, duration_s=duration)
    except RegressionAssertionError as exc:
        return _outcome("doctor", "Doctor", ScenarioStatus.FAIL, str(exc))
    except Exception as exc:
        return _outcome("doctor", "Doctor", ScenarioStatus.FAIL, f"{type(exc).__name__}: {exc}")


def scenario_memory_save() -> ScenarioOutcome:
    def _check() -> None:
        from memory.store import save_memory

        marker = regression_marker()
        text = tagged_memory_text(marker, "My favorite animal is wolf.")
        saved = save_memory(text)
        assert_true(saved, "Memory save returned False")

    return _run_guarded("memory_save", "Memory save", _check)


def scenario_memory_retrieval() -> ScenarioOutcome:
    def _check() -> None:
        from memory.retriever import search_memories
        from memory.store import save_memory

        marker = regression_marker()
        text = tagged_memory_text(marker, "My favorite animal is wolf.")
        assert_true(save_memory(text), "Could not save wolf memory")
        results = search_memories("What is my favorite animal?", top_k=5)
        combined = " ".join(item["content"] for item in results)
        assert_contains(combined, "wolf", "Favorite animal wolf was not retrieved")

    return _run_guarded("memory_recall", "Memory retrieval", _check)


def scenario_conversation_memory() -> ScenarioOutcome:
    def _check() -> None:
        from memory.retriever import search_memories
        from memory.store import save_memory

        marker = regression_marker()
        assert_true(
            save_memory(tagged_memory_text(marker, "My name is Alice.")),
            "Failed to save name memory",
        )
        assert_true(
            save_memory(tagged_memory_text(marker, "My favorite language is Python.")),
            "Failed to save language memory",
        )
        results = search_memories("What do you know about me?", top_k=8)
        combined = " ".join(item["content"] for item in results)
        assert_contains(combined, "Alice", "Alice not found in memory recall")
        assert_contains(combined, "Python", "Python not found in memory recall")

    return _run_guarded("conversation", "Conversation", _check)


def scenario_memory_persistence() -> ScenarioOutcome:
    def _check() -> None:
        from memory import retriever as retriever_module
        from memory import store as store_module
        from memory.retriever import search_memories
        from memory.store import save_memory

        marker = regression_marker()
        statement = tagged_memory_text(marker, "My favorite color is teal.")
        assert_true(save_memory(statement), "Persistence memory save failed")

        importlib.reload(store_module)
        importlib.reload(retriever_module)
        from memory.retriever import search_memories as search_after_reload

        results = search_after_reload("favorite color", top_k=5)
        combined = " ".join(item["content"] for item in results)
        assert_contains(combined, "teal", "Memory did not survive reload")

    return _run_guarded("memory_persist", "History persistence", _check)


def scenario_calculator() -> ScenarioOutcome:
    def _check() -> None:
        from tools.executor import execute_tool

        handled, result = execute_tool("2*(15+3)")
        assert_true(handled, "Calculator was not handled")
        assert_equals(result, "36", "Calculator result mismatch")

    return _run_guarded("calculator", "Calculator", _check)


def scenario_time() -> ScenarioOutcome:
    def _check() -> None:
        from tools.executor import execute_tool

        handled, result = execute_tool("What time is it in India?")
        assert_true(handled, "Time tool was not handled")
        assert_not_empty(result, "Time tool returned empty response")

    return _run_guarded("time", "Time tool", _check)


def scenario_history() -> ScenarioOutcome:
    def _check() -> None:
        from conversation.history import append_message, last_messages

        marker = regression_marker()
        probe = f"{marker} regression history probe"
        append_message("user", probe)
        recent = last_messages(40)
        texts = [message.content for message in recent]
        assert_true(any(probe in text for text in texts), "History message not persisted")

    return _run_guarded("history", "History", _check)


def scenario_agents() -> ScenarioOutcome:
    def _check() -> None:
        from agents.intent import analyze_intent
        from agents.orchestrator import orchestrate_chat_turn
        from agents.planner import create_plan, is_project_analysis_query

        query = "Analyze this Python project and tell me how to improve it."
        assert_true(is_project_analysis_query(query), "Project analysis query not detected")
        intent = analyze_intent(query)
        plan = create_plan(intent, query)
        assert_true(len(plan) >= 3, "Agent plan too short")
        turn = orchestrate_chat_turn("What is in my notes about testing?")
        assert_true(turn is not None, "Orchestrator returned nothing")

    return _run_guarded("agents", "Agent planner", _check)


def scenario_project_analyzer() -> ScenarioOutcome:
    def _check() -> None:
        from agents.analyzer import run_project_analysis
        from agents.project_report import build_project_report, format_project_report

        query = "Analyze this Python project."
        is_analysis, context = run_project_analysis(query)
        assert_true(is_analysis, "Project analysis was not triggered")
        assert_contains(context, "Structured Report", "Structured report missing")
        report = format_project_report(build_project_report(ROOT))
        assert_contains(report.lower(), "python", "Language not detected")
        assert_contains(context.lower(), "framework", "Framework section missing")
        assert_true(
            "recommend" in context.lower() or "improvement" in context.lower(),
            "Recommendations missing from analysis context",
        )

    return _run_guarded("project", "Project analyzer", _check)


def scenario_tools() -> ScenarioOutcome:
    def _check() -> None:
        from tools.executor import execute_tool
        from tools.router import route_query

        assert_equals(route_query("Hello!"), "chat", "Router chat mismatch")
        assert_equals(route_query("What is my favorite color?"), "memory", "Router memory mismatch")
        handled, result = execute_tool("3+4")
        assert_true(handled and result == "7", "Tool executor calculator failed")

    return _run_guarded("tools", "Tools", _check)


def scenario_code_search() -> ScenarioOutcome:
    try:
        with measure_seconds() as bucket:
            from codebase.indexer import build_code_index
            from codebase.retriever import search_code
            from core.chroma import collection_count
            from core.index_status import COLLECTION_CODE

            if collection_count(COLLECTION_CODE) == 0:
                build_code_index(ROOT)
            results = search_code("generate_response", top_k=5)
            if not results:
                return _outcome(
                    "code",
                    "Code search",
                    ScenarioStatus.WARN,
                    "Index empty or no matches for generate_response",
                    bucket[0],
                )
            combined = " ".join(item["content"] for item in results)
            assert_not_empty(combined)
        return _outcome("code", "Code search", ScenarioStatus.PASS, duration_s=bucket[0])
    except RegressionAssertionError as exc:
        return _outcome("code", "Code search", ScenarioStatus.FAIL, str(exc))
    except Exception as exc:
        return _outcome("code", "Code search", ScenarioStatus.FAIL, f"{type(exc).__name__}: {exc}")


def _pdf_outcome() -> ScenarioOutcome:
    try:
        with measure_seconds() as bucket:
            from core.chroma import collection_count
            from core.index_status import COLLECTION_PDF
            from pdf.retriever import search_documents

            if collection_count(COLLECTION_PDF) == 0:
                return _outcome(
                    "pdf",
                    "PDF search",
                    ScenarioStatus.WARN,
                    "PDF index empty (graceful fallback)",
                    bucket[0],
                )
            results = search_documents("introduction", top_k=3)
            assert_not_empty(results)
        return _outcome("pdf", "PDF search", ScenarioStatus.PASS, duration_s=bucket[0])
    except RegressionAssertionError as exc:
        return _outcome("pdf", "PDF search", ScenarioStatus.FAIL, str(exc))
    except Exception as exc:
        return _outcome("pdf", "PDF search", ScenarioStatus.FAIL, f"{type(exc).__name__}: {exc}")


def scenario_notes_search() -> ScenarioOutcome:
    try:
        with measure_seconds() as bucket:
            from core.chroma import collection_count
            from core.index_status import COLLECTION_NOTES
            from rag.retriever import search

            if collection_count(COLLECTION_NOTES) == 0:
                return _outcome(
                    "notes",
                    "Notes search",
                    ScenarioStatus.WARN,
                    "Notes index empty (graceful fallback)",
                    bucket[0],
                )
            results = search("personal notes", top_k=3)
            assert_not_empty(results)
        return _outcome("notes", "Notes search", ScenarioStatus.PASS, duration_s=bucket[0])
    except RegressionAssertionError as exc:
        return _outcome("notes", "Notes search", ScenarioStatus.FAIL, str(exc))
    except Exception as exc:
        return _outcome("notes", "Notes search", ScenarioStatus.FAIL, f"{type(exc).__name__}: {exc}")


def scenario_web_search() -> ScenarioOutcome:
    try:
        with measure_seconds() as bucket:
            from web.search import search_web

            results = search_web("Python programming language", max_results=3)
            if not results:
                return _outcome(
                    "web",
                    "Web search",
                    ScenarioStatus.WARN,
                    "No web results (network or dependency)",
                    bucket[0],
                )
            first = results[0]
            blob = f"{first.get('title', '')} {first.get('body', '')}".strip()
            assert_not_empty(blob)
        return _outcome("web", "Web search", ScenarioStatus.PASS, duration_s=bucket[0])
    except Exception as exc:
        return _outcome("web", "Web search", ScenarioStatus.WARN, f"{type(exc).__name__}: {exc}")


def scenario_vision() -> ScenarioOutcome:
    candidates = [
        ROOT / "data" / "images",
        ROOT / "storage" / "images",
        ROOT / "tests" / "fixtures",
    ]
    image_path: Path | None = None
    for folder in candidates:
        if not folder.is_dir():
            continue
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            matches = list(folder.glob(pattern))
            if matches:
                image_path = matches[0]
                break
        if image_path:
            break

    if image_path is None:
        return _outcome("vision", "Vision", ScenarioStatus.WARN, "No sample image; skipped")

    try:
        with measure_seconds() as bucket:
            from vision.pipeline import analyze_image

            result = analyze_image(str(image_path))
            metadata = result.get("metadata", {})
            assert_true(isinstance(result, dict), "Vision result not a dict")
            width = metadata.get("width", 0) if isinstance(metadata, dict) else 0
            assert_true(width > 0 or bool(result.get("ocr_text")), "Vision produced no output")
        return _outcome("vision", "Vision", ScenarioStatus.PASS, duration_s=bucket[0])
    except Exception as exc:
        return _outcome("vision", "Vision", ScenarioStatus.FAIL, f"{type(exc).__name__}: {exc}")


def scenario_desktop_import() -> ScenarioOutcome:
    def _check() -> None:
        import desktop.app as desktop_app

        assert_true(hasattr(desktop_app, "main"), "desktop.app missing main()")

    try:
        with measure_seconds() as bucket:
            import desktop.app as desktop_app

            assert_true(hasattr(desktop_app, "main"))
        return _outcome("desktop", "Desktop", ScenarioStatus.PASS, duration_s=bucket[0])
    except Exception as exc:
        return _outcome("desktop", "Desktop", ScenarioStatus.WARN, f"{type(exc).__name__}: {exc}")


def scenario_voice_import() -> ScenarioOutcome:
    try:
        with measure_seconds() as bucket:
            import voice.manager as voice_manager

            assert_true(hasattr(voice_manager, "VoiceManager"))
        return _outcome("voice", "Voice", ScenarioStatus.PASS, duration_s=bucket[0])
    except Exception as exc:
        return _outcome("voice", "Voice", ScenarioStatus.WARN, f"{type(exc).__name__}: {exc}")


def scenario_startup_diagnostics() -> ScenarioOutcome:
    def _check() -> None:
        from core.diagnostics import run_startup_diagnostics

        lines = run_startup_diagnostics()
        assert_not_empty(lines, "Startup diagnostics returned no lines")
        joined = "\n".join(lines)
        assert_contains(joined.lower(), "collection", "Diagnostics missing collection info")

    return _run_guarded("startup", "Startup diagnostics", _check)


def scenario_performance() -> ScenarioOutcome:
    timings: list[str] = []

    def _timed(label: str, fn: Callable[[], None]) -> None:
        start = time.perf_counter()
        fn()
        timings.append(f"{label}={1000 * (time.perf_counter() - start):.0f}ms")

    try:
        with measure_seconds() as bucket:
            from core.doctor import run_doctor
            from memory.retriever import search_memories
            from tools.executor import execute_tool

            _timed("doctor", lambda: run_doctor())
            _timed("memory", lambda: search_memories("favorite", top_k=2))
            _timed("calculator", lambda: execute_tool("2+2"))
            _timed("time", lambda: execute_tool("What time is it?"))

            chat_ms: list[float] = []

            def _chat() -> None:
                from agents.orchestrator import orchestrate_chat_turn

                orchestrate_chat_turn("Hello")

            start = time.perf_counter()
            try:
                _chat()
                chat_ms.append((time.perf_counter() - start) * 1000)
                timings.append(f"simple_chat={chat_ms[0]:.0f}ms")
            except Exception as exc:
                timings.append(f"simple_chat=skipped ({exc})")

        detail = "; ".join(timings)
        return _outcome("performance", "Performance", ScenarioStatus.PASS, detail, bucket[0])
    except Exception as exc:
        return _outcome("performance", "Performance", ScenarioStatus.WARN, str(exc))


def scenario_conversation_chat() -> ScenarioOutcome:
    """Lightweight chat path via tools/memory without requiring LLM weights."""

    def _check() -> None:
        from brain.pipeline import generate_response

        reply = generate_response("2+2")
        assert_equals(reply.strip(), "4", "Chat pipeline tool routing failed")

    try:
        with measure_seconds() as bucket:
            from brain.pipeline import generate_response

            reply = generate_response("2+2")
            assert_equals(reply.strip(), "4")
        return _outcome("chat", "Simple chat", ScenarioStatus.PASS, duration_s=bucket[0])
    except RegressionAssertionError as exc:
        return _outcome("chat", "Simple chat", ScenarioStatus.FAIL, str(exc))
    except Exception as exc:
        return _outcome("chat", "Simple chat", ScenarioStatus.WARN, f"{type(exc).__name__}: {exc}")


QUICK_SCENARIOS: tuple[Callable[[], ScenarioOutcome], ...] = (
    scenario_doctor,
    scenario_memory_save,
    scenario_memory_retrieval,
    scenario_calculator,
    scenario_time,
    scenario_history,
    scenario_conversation_memory,
    scenario_agents,
    scenario_project_analyzer,
)

FULL_EXTRA_SCENARIOS: tuple[Callable[[], ScenarioOutcome], ...] = (
    scenario_memory_persistence,
    scenario_tools,
    scenario_code_search,
    _pdf_outcome,
    scenario_notes_search,
    scenario_web_search,
    scenario_vision,
    scenario_desktop_import,
    scenario_voice_import,
    scenario_startup_diagnostics,
    scenario_performance,
)

# Full mode re-runs the quick suite plus extras (conversation chat uses pipeline once).
FULL_SCENARIOS: tuple[Callable[[], ScenarioOutcome], ...] = (
    *QUICK_SCENARIOS,
    scenario_conversation_chat,
    *FULL_EXTRA_SCENARIOS,
)
