# Zoe AI — Project Status

**Version:** v2.11  
**Last updated:** 2026-08-04  
**Branch:** `main`

## Summary

Zoe AI is a local-first personal assistant with tool-routed retrieval, web research, vision analysis, conversational memory inference, persistent conversation history, and system diagnostics.

## Subsystem Status

| Subsystem | Status | Entry point |
|-----------|--------|-------------|
| Chat / LLM | ✅ Complete | `brain/pipeline.py` |
| Notes RAG | ✅ Complete | `rag/retriever.py` |
| Memory | ✅ Complete | `memory/store.py` + `memory/intelligence/` |
| PDF | ✅ Complete | `pdf/retriever.py` |
| Code | ✅ Complete | `codebase/retriever.py` |
| Web | ✅ Complete | `web/retriever.py` |
| Vision | ✅ Complete | `vision/pipeline.py` |
| Tools | ✅ Complete | `tools/router.py` → `plugins/` |
| Plugins | ✅ Complete | `plugins/manager.py` + manifest extensions |
| Agents | ✅ Complete | `agents/orchestrator.py` + supervisor/specialists |
| Doctor | ✅ Complete | `core/doctor.py` |
| Conversation | ✅ Complete | `conversation/history.py` |
| CLI | ✅ Complete | `cli/main.py` |
| Desktop | ✅ Complete | `desktop/app.py` |
| Voice | ✅ Complete | `voice/manager.py` |
| Regression | ✅ Complete | `tests/regression.py` |
| Autonomous tasks | ✅ Complete | `agents/tasks/task_manager.py` |
| Deployment | ✅ Complete | `deployment/startup.py`, `deployment/health.py` |
| CI | ✅ Partial | `.github/workflows/tests.yml` |

## v2 Integration (2026-07-28)

| Area | Change |
|------|--------|
| Datetime | Timezone-aware requests via `zoneinfo` |
| Memory | Conversational inference from assistant follow-ups |
| Analysis | Guaranteed context injection with debug logging |
| Doctor | Reliable dependency, CLI, and Chroma checks |
| Startup | Collection counts in diagnostics |
| Model | Lazy LLM loading for non-chat commands |
| Web | URL/snippet deduplication, 3-page cap |
| Vision | Partial results when OCR or caption alone succeeds |
| Tests | doctor, web, vision, analysis, datetime, lazy loading |

## Test Coverage

| Layer | Pytest | Scripts |
|-------|--------|---------|
| Router / tools | ✅ | ✅ |
| Brain / context | ✅ | ✅ |
| Memory / RAG | ✅ | ✅ |
| Web | ✅ | ✅ |
| Vision | ✅ | ✅ |
| Doctor / diagnostics | ✅ | ✅ |
| Desktop UI | ✅ | ❌ |
| Voice | ✅ | ❌ |
| Conversation history | ✅ | ❌ |
| Analysis pipeline | ✅ | ✅ |
| Indexers | ❌ | ✅ |

## Known Limitations

- Conversation history persists to `data/history/` (Sprint 11); desktop GUI adds session rename/delete UX
- `train` CLI command is a placeholder
- Chroma deduplication scans full collections on index builds
- `docs/personality.md` is not loaded at runtime

## Quick Start

```bash
pip install -r requirements.txt
python desktop/app.py
python cli/main.py ingest
python cli/main.py code .
python cli/main.py chat
python cli/main.py doctor
pytest tests/ -v
```

## Documentation Index

| Document | Purpose |
|----------|---------|
| `README.md` | User guide and quick reference |
| `docs/ARCHITECTURE.md` | System design and data flows |
| `docs/ROADMAP.md` | Completed and planned sprints |
| `CHANGELOG.md` | Version history |
| `PROJECT_AUDIT.md` | Historical Sprint 1.2 audit |

## Multi-Agent subsystem (Sprint 16)

| Component | Path |
|-----------|------|
| Supervisor | `agents/supervisor.py` |
| Coordinator | `agents/coordinator.py` |
| Specialists | `agents/specialists/` |
| Result types | `agents/agent_result.py` |

Entry point unchanged: `brain.pipeline.generate_response()` → `agents.orchestrator.orchestrate_chat_turn()`.

## Autonomous tasks (Sprint 17)

| Component | Path |
|-----------|------|
| Models | `agents/tasks/task.py` |
| Planner | `agents/tasks/task_planner.py` |
| Queue | `agents/tasks/task_queue.py` |
| Scheduler | `agents/tasks/scheduler.py` |
| Executor | `agents/tasks/task_executor.py` |
| Manager | `agents/tasks/task_manager.py` |
| Progress | `agents/tasks/progress.py` |

Complex goals run as internal subtask graphs; results merge to one user-facing reply. Subscribe via `agents.tasks.subscribe_progress()` for desktop signals.

## Running regression tests

Before a release, run:

```bash
python tests/regression.py
python tests/regression.py --full
```

The runner exercises doctor, memory, tools, agents, retrieval layers, optional desktop/voice imports, and (in full mode) web search, vision, startup diagnostics, and performance timings. It does not delete user indexes or settings; temporary memories are tagged and removed when possible. See `tests/reports/latest.txt` for the last summary.
