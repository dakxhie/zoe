# Changelog

All notable changes to Zoe AI are documented here.

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
