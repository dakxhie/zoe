# Technical Debt — Zoe AI v2.11

Updated: 2026-08-07 (post green regression + release review)  
Status: **Non-blocking for RC.** Track before hard production deploy / installer.

---

## Plugins

- Legacy `plugins/local/*.py` plugins load as **enabled** by default (manifest extensions stay disabled until enabled).
- Extension crash does not auto-disable in `PluginManager`; health stays `crashed` until manual disable/reload.
- `PluginContext.register_command()` is stored but not wired to Typer CLI.
- Manifest discovery is top-level `plugins/<dir>/plugin.json` only (no nested community trees).
- Sandbox is permission + try/except only — not a process/interpreter jail.

## Memory intelligence

- Post-turn `run_memory_review(lightweight=True)` runs on every completed chat turn (CPU/Chroma cost).
- Consolidation/reinforcement are heuristic, not embedding clustering.
- `MemoryType.TEMPORARY` / TTL underused.
- Personal-info regexes duplicated across importance / reinforcement / consolidation / profile_builder.
- Third-party plugin memory writes are not re-gated on `Permission.MEMORY` inside the core brain path.

## Startup / performance

- `generate_response()` still calls `initialize_plugins()` each turn (cached no-op after first).
- `deployment/__init__.py` eagerly imports benchmark/health/startup surfaces.
- Vision caption / `brain.generation` may import `torch` at module import time.
- `capture_resource_snapshot()` may `rglob` the Chroma directory (costly on large DBs).
- Supervisor/specialist fan-out under parallel load not stress-characterized beyond unit tests.

## Shutdown

- Voice capture uses daemon threads; `_shutdown_voice()` is intentionally a no-op (no mic release hook).
- Plugin event subscribers are not cleared on production shutdown (test helper only).
- Chroma persistent client is not explicitly closed on exit.
- Desktop/event/vector_db shutdown steps are placeholders in the ordered sequence.

## Configuration

- Minimal YAML parser fallback when PyYAML is absent — complex YAML may mis-parse.
- Effective settings cache requires explicit `invalidate_settings_cache()` / test reset.
- Desktop Qt preferences are only partially covered by export/import (optional JSON path).
- `PROJECT_STATUS.md` “Last updated” may lag the true suite-green date (docs drift).

## Architecture maintainability

- `agents/orchestrator.orchestrate_chat_turn` mixes analysis, autonomous, supervisor, execution, and prompt build (large function).
- `brain/context.py` remains a hub for retrieval + prompt assembly + empty-index policy.
- Doctor / diagnostics / resource_monitor duplicate “optional probe” try/except patterns.

## Testing / CI / platforms

- Full suite green on Colab report (249/5/0); keep Windows + CI matrix in mind.
- GUI tests skip on headless/`CI=true`.
- Windows MSVC / `chroma-hnswlib` / torch build fragility on some Python versions.
- Targeted pytest policy required on Windows to avoid overheating (full discovery is heavy).

## Security / hardening

- Tool/plugin error strings may include exception text in user-visible tool output.
- No rate limit / rotation on local telemetry JSONL growth.
- Filesystem tool paths should continue to be reviewed for traversal on any future expansion.

## Documentation

- Prefer `RELEASE_CHECKLIST.md` for go/no-go; `RELEASE_CANDIDATE_CHECKLIST.md` is historical pre-regression.
- Keep version strings aligned (README / CHANGELOG / PROJECT_STATUS / manifests) at tag time.
- Colab operator runbook (targeted pytest batches) could be expanded in `docs/`.

## Future (post-RC — do not implement before tag)

- Performance tuning from regression metrics.
- Model fine-tuning on curated dataset.
- Packaging / installer for production deploy.
- Split orchestrator stages behind characterization tests.
- Telemetry rotation; auto-disable crashed extensions; explicit Chroma close + voice teardown.
