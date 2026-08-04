# Changelog

All notable changes to Zoe AI are documented here.

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
