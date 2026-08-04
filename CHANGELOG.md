# Changelog

All notable changes to Zoe AI are documented here.

## v2.11.0 — 2026-08-04 (Sprint 21 — Production Readiness & Deployment)

### Added
- **`deployment/`** package: unified config, startup/shutdown managers, health, diagnostics, resource monitor, benchmark, telemetry (local-only)
- YAML profiles: `config/default.yaml`, `development.yaml`, `production.yaml`
- Scripts: `install.py`, `benchmark.py`, `doctor.py`, `export_settings.py`, `import_settings.py`
- Deployment profiles: developer, production, portable, testing
- Health checks for memory DB, GPU, plugins, voice, tasks, supervisor, memory intelligence
- Pytest: `test_health`, `test_startup`, `test_shutdown`, `test_configuration`, `test_resource_monitor`, `test_benchmark`, `test_telemetry`, `test_deployment_profiles` (not run)

### Changed
- `core/config.load_settings()` merges deployment config over legacy `settings.txt`
- `core/logging_config` respects `ZOE_LOG_LEVEL` and deployment profile
- CLI chat and desktop startup invoke `run_startup_sequence()`; pipeline records local telemetry

## v2.10.0 — 2026-08-04 (Sprint 20 — Plugin & Extension Framework)

### Added
- **Manifest-based extensions** (`plugin.json` + `main.py`) with `PluginContext` stable API
- `plugins/manifest.py`, `plugin_api.py`, `events.py`, `state.py`; `PluginManager` class
- Example plugins: `example_clock`, `example_notes`, `example_translate` (disabled by default)
- Event bus: startup, shutdown, conversation, memory, tools, voice, tasks, plugin lifecycle
- Chat, memory, and voice hooks; per-plugin storage under `data/plugins/<id>/`
- CLI: `plugins`, `plugins list`, `plugins enable|disable|reload`
- Pytest modules: `test_plugin_loader`, `test_plugin_permissions`, `test_plugin_events`, `test_plugin_reload`, `test_plugin_api`, `test_plugin_storage`, `test_plugin_tools` (not run in sprint)

### Changed
- Tool router/executor **extends** routing with registered extension tools (builtins unchanged)
- Chat pipeline applies chat hooks and emits conversation events; voice manager optional hook points
- Memory saves emit `memory_saved` and run memory hooks (permission-gated registration)
- Autonomous tasks emit `task_started` / `task_finished` plugin events

## v2.9.0 — 2026-08-04 (Long-Term Memory Intelligence & Self-Learning)

### Added
- **`memory/intelligence/`** — importance scoring, forgetting, reinforcement, consolidation, profile builder, memory review
- Memory types: semantic, procedural, preference, identity, project, episode, temporary
- Chroma metadata: importance, confidence, frequency, category, last_used
- Profile summaries for *What do you know about me?* and *What have you learned?*
- Post-turn pipeline via `finalize_conversation_memory()` in orchestrator
- Pytest: `test_memory_scoring.py`, `test_profile_builder.py`, `test_reinforcement.py`, `test_forgetting.py`, `test_consolidation.py` (not run in sprint)

### Changed
- `save_memory()` routes through the intelligence pipeline
- `brain/pipeline.py` finalizes memory after each completed turn

## v2.8.0 — 2026-08-04 (Sprint 18 — Tool Ecosystem & Plugin Framework)

### Added
- **Plugin framework** under `plugins/` (registry, loader, lifecycle, permissions, sandbox, manager)
- Builtin plugins: memory, web, pdf, code, calculator, datetime (+ notes routing)
- Discovery from `plugins/builtin`, `plugins/community`, `plugins/local` at startup (cached)
- Dependency resolution, hot reload, health states (loaded, disabled, failed, missing dependency, crashed)
- Supervisor permission gate (`supervisor_may_use_plugin`) for internet and other capabilities
- Desktop helper `list_desktop_plugin_summary()`; startup diagnostics plugin count
- Pytest modules: `test_plugin_registry.py`, `test_plugin_loader.py`, `test_plugin_permissions.py`, `test_plugin_lifecycle.py`, `test_plugin_routing.py` (not run in sprint)

### Changed
- `tools/router.py` and `tools/executor.py` route through plugin registry (vision/filesystem legacy fallback)
- `agents/intent.py` DEBUG logs planner plugin candidates
- Planner/supervisor discover tools dynamically instead of hardcoded lists

## v2.7.0 — 2026-08-04 (Sprint 17 — Autonomous Task Engine)

### Added
- **Autonomous task engine** under `agents/tasks/` (queue, scheduler, executor, progress, planner)
- Multi-step internal tasks with dependencies, retries, backoff, pause/resume, cancel
- `run_autonomous_goal()` integrated in orchestrator for complex goals (bypasses simple chat/tools)
- Progress events (`subscribe_progress`) for future desktop/voice UI; voice status command
- Optional memory summary after successful autonomous runs
- Pytest modules for task manager, queue, scheduler, dependencies, cancellation (not run in sprint)

### Changed
- `agents/supervisor.requires_autonomous_execution()` routes to task engine
- `desktop/workers.py` helpers for autonomous status and progress relay

## v2.6.0 — 2026-08-04 (Sprint 16 — Multi-Agent Intelligence)

### Added
- **Multi-agent architecture**: internal Supervisor plus Memory, Research, Coding, Reasoning, and Creative specialists
- `agents/supervisor.py`, `agents/coordinator.py`, `agents/agent_result.py`, `agents/specialists/*`
- Parallel specialist execution, confidence scores, conflict resolution, DEBUG supervisor logs
- Pytest: `test_supervisor.py`, `test_specialists.py`, `test_parallel_agents.py`, `test_conflict_resolution.py`

### Changed
- `agents/orchestrator.py` extends (does not replace) planner/executor with supervisor cycle
- Architecture and roadmap docs describe internal multi-agent flow

## v2.5.1 — 2026-08-04

### Changed
- Pytest infrastructure: headless detection for Colab/CI, shared `qapp` fixture, GUI and optional-voice skips
- Desktop and voice widget tests skip instead of aborting when no display or optional voice deps
- Conversation history unit tests use isolated temp storage paths

## v2.5.0 — 2026-08-04

### Added
- **Automated regression framework** (`tests/regression.py`, `tests/regression/`) for end-to-end release verification
- Quick mode (`python tests/regression.py`) and full mode (`--full`) with colored console report and `tests/reports/latest.txt`
- Reusable regression assertions, scenario runner (continues on failure), and cleanup of tagged test memories

## v2.4.1 — 2026-08-04

### Changed
- Voice dependencies moved to optional `requirements-voice.txt` (no PyAudio required for install)
- Doctor reports **Voice** as WARN when optional packages are missing, never FAIL
- Desktop disables microphone gracefully when `sounddevice` is unavailable; TTS skipped without `pyttsx3`

## v2.4.0 — 2026-08-03

### Added
- Offline **voice assistant** package (`voice/`) with Whisper STT, pyttsx3 TTS, push-to-talk, and silence detection
- `VoiceManager` state machine (idle → listen → recognize → think → speak)
- Local voice commands (settings, doctor, indexing, datetime/calculator tools)
- Desktop voice UI: `voice_widget.py`, `microphone_button.py`, Settings **Voice** tab
- Voice pytest suite (manager, recognizer, speaker, commands, pipeline)

### Changed
- Desktop Stop cancels TTS and LLM workers
- Voice uses `brain.pipeline.generate_response()` and Sprint 11/12 backend automatically

## v2.3.0 — 2026-08-03

### Added
- **Zoe Desktop** (`desktop/`) — PySide6 Qt Widgets application and primary GUI
- MVC-style UI: chat bubbles, sidebar, history dock, settings, index manager, doctor cards
- Background workers (`QThread` / `QRunnable`) for chat, vision, indexing, and doctor
- Drag-and-drop for images, PDFs, and notes
- Desktop pytest coverage: startup, workers, history panel, settings

### Changed
- README and architecture docs describe desktop + CLI dual entrypoints
- `requirements.txt` includes `PySide6`

## v2.2.0 — 2026-08-03

### Added
- Agent orchestration layer: intent analysis, internal planning, multi-tool execution, recovery, verification, and retrieval fusion
- `agents/state.py`, `agents/intent.py`, `agents/fusion.py`, `agents/recovery.py`, `agents/verifier.py`, `agents/orchestrator.py`, `agents/project_report.py`
- Structured project analysis report (language, framework, tests, entry points, hotspots)
- DEBUG timing metrics for planner, retrieval, tools, and generation
- Pytest suite `tests/test_agent_system.py`

### Changed
- `brain/pipeline.generate_response()` routes through `agents/orchestrator.orchestrate_chat_turn()` after memory save and lightweight tools
- `brain/context._build_chat_messages()` accepts fused agent context without duplicating sections
- Project analysis context includes a structured report before gathered files/code

### Fixed
- Partial tool failures no longer abort multi-step agent execution (notes/memory/web fallbacks)

## v2.1.0 — 2026-07-29

### Added
- Persistent conversation history (`conversation/`) with JSONL storage in `data/history/`
- Session management with UUID4 sessions per chat launch
- Conversation summarization for chats longer than 40 messages
- Semantic search over prior dialogue via `zoe_history` Chroma collection
- CLI history commands: `history`, `history sessions`, `history summary`, `history clear`, `history stats`
- Doctor checks for conversation storage, files, and `zoe_history` collection

### Changed
- Chat startup restores prior conversations and prints restore status
- Context pipeline injects conversation history after memory routing
- `memory/history.py` now delegates to persistent conversation storage

## v2.0.0 — 2026-07-28

### Added
- Timezone-aware datetime tool (`zoneinfo`) for cities, countries, and abbreviations
- Conversational memory inference from assistant follow-up questions
- Expanded pytest coverage: doctor, web, vision, analysis pipeline, lazy loading, datetime locations
- DEBUG retrieval logging for route, retriever, chunks, and context size
- `core/package_check.py`, `core/cli_commands.py`, `tools/timezones.py`

### Changed
- Startup diagnostics now show collection counts: `Memory (15)`, `Notes (42)`, etc.
- Doctor uses package metadata checks and CLI source discovery (no heavy imports)
- Web retrieval deduplicates URLs/snippets and caps at 3 pages
- Vision pipeline returns partial analysis when OCR or caption alone succeeds
- Project analysis context is always injected with debug logging across planner → executor → prompt
- CLI lazy-imports LLM modules so `doctor`, `ingest`, and `code` avoid model loading

### Fixed
- Doctor false negatives for CLI, dependencies (Pillow), and empty-vs-broken ChromaDB
- Analysis context silently discarded in some pipeline paths
- Datetime tool failing on location-based requests

## v1.0.0-rc2 — 2026-07-28

### Changed (repository polish only — no behavior changes)
- Consolidated text normalization into `core/text_utils.py`
- Added type hints to Chroma collection helpers
- Improved CLI `--help` output with examples and argument descriptions
- Added `Usage:` lines to all `scripts/*.py` docstrings
- Package-level docs in `brain/`, `core/`, and `tests/` `__init__.py`
- Removed unused dependencies: `python-dotenv`, `tqdm`, `rich`
- Updated `PROJECT_STATUS.md` and README examples

## v1.0.0 — 2026-07-28

### Added
- Web search, webpage reading, disk cache, and source-aware web answers (Sprint 8)
- Vision: image loading, OCR, BLIP captioning, unified pipeline, chat integration (Sprint 9)
- `python cli/main.py image` command with direct and prompt modes
- Brain module split: `pipeline.py`, `context.py`, `generation.py`
- Pytest suite (`tests/`) and GitHub Actions CI
- Startup diagnostics and `scripts/system_check.py`
- Project analysis agent layer (`agents/`)

### Changed
- Tool router now supports `web` and `vision` routes
- Single-source retrieval per message (memory, notes, PDF, code, web, or vision)
- Empty-index messages reference correct CLI commands
- Settings loader caches `config/settings.txt` reads
- CLI bootstraps `sys.path` before local imports

### Fixed
- Removed unused imports and dead code (`VALID_ROUTES`, unused context imports)
- Added debug logging for silent PDF and project-analysis failures
- `VisionLoaderError` now extends `RuntimeError` for consistency

## v0.1.0 — 2026-07-28

### Added
- Notes RAG, persistent memory, PDF intelligence, code intelligence
- Tool routing, calculator, datetime, filesystem tools
- Conversation history (in-memory FIFO)
- Shared Chroma helpers and integration tests
