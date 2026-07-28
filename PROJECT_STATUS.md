# Zoe AI — Project Status

**Version:** v1.0-rc2  
**Last updated:** 2026-07-28  
**Branch:** `main`

## Summary

Zoe AI is a local-first personal assistant with tool-routed retrieval, web research, and vision analysis. Sprints 1–9 are complete. RC2 focused on repository polish: shared utilities, docstrings, type hints, CLI help, and dependency cleanup — without behavior changes.

## Subsystem Status

| Subsystem | Status | Entry point |
|-----------|--------|-------------|
| Chat / LLM | ✅ Complete | `brain/pipeline.py` |
| Notes RAG | ✅ Complete | `rag/retriever.py` |
| Memory | ✅ Complete | `memory/store.py` |
| PDF | ✅ Complete | `pdf/retriever.py` |
| Code | ✅ Complete | `codebase/retriever.py` |
| Web | ✅ Complete | `web/retriever.py` |
| Vision | ✅ Complete | `vision/pipeline.py` |
| Tools | ✅ Complete | `tools/router.py` |
| Agents | ✅ Complete | `agents/analyzer.py` |
| CLI | ✅ Complete | `cli/main.py` |
| CI | ✅ Partial | `.github/workflows/tests.yml` |

## RC2 Cleanup (2026-07-28)

| Area | Change |
|------|--------|
| Shared utilities | `core/text_utils.py` — `normalize_text()`, `matches_any()` |
| Type hints | Chroma `Collection` return types on retriever helpers |
| Package docs | `brain/`, `core/`, `tests/` `__init__.py` |
| CLI help | Typer epilog with examples; improved argument descriptions |
| Scripts | `Usage:` line in every `scripts/*.py` docstring |
| Dependencies | Removed unused `python-dotenv`, `tqdm`, `rich` from `requirements.txt` |
| Router | Removed duplicate normalize/match wrappers |

## Test Coverage

| Layer | Pytest | Scripts |
|-------|--------|---------|
| Router / tools | ✅ | ✅ |
| Brain / context | ✅ | ✅ |
| Memory / RAG | ✅ | ✅ |
| Web | ❌ | ✅ |
| Vision | ❌ | ✅ |
| Indexers | ❌ | ✅ |

## Known Limitations

- Conversation history is in-memory only (lost on restart)
- `train` CLI command is a placeholder
- Web and vision modules are not in pytest CI
- Chroma deduplication scans full collections on index builds
- `docs/personality.md` is not loaded at runtime

## Quick Start

```bash
pip install -r requirements.txt
python cli/main.py ingest
python cli/main.py code .
python cli/main.py chat
python cli/main.py image photo.jpg
python scripts/system_check.py
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