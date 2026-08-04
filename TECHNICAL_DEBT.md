# Remaining Technical Debt — Zoe v2.11

Issues deferred after final stabilization sprint. Not blockers for starting regression, but track before production deploy.

## Plugins

- Auto-load legacy `plugins/local/*.py` plugins as **enabled** (unlike manifest extensions).
- Extension crash does not auto-disable in `PluginManager`; health stays `crashed` until manual disable/reload.
- `register_command()` stored but not wired to CLI Typer.
- Community folder manifest discovery only at `plugins/<dir>/plugin.json` top level.
- Full import sandbox not implemented (permission + try/except only).

## Memory intelligence

- Post-turn `run_memory_review(lightweight=True)` on every completed chat turn (CPU/Chroma cost).
- Consolidation/reinforcement uses heuristics, not embedding clustering.
- Temporary memory TTL rarely set on candidates (`MemoryType.TEMPORARY` underused).
- Third-party plugin memory writes not gated on `Permission.MEMORY` in core brain path.

## Startup / performance

- `generate_response()` calls `initialize_plugins()` every turn (cached no-op after first call).
- `deployment/__init__.py` eager imports if package root imported.
- Benchmark suite runs full startup (intentional for bench, heavy for dev).
- Vision caption / generation import `torch` at module import time.

## Shutdown

- Voice capture threads — daemon threads; no explicit microphone release hook on shutdown.
- Plugin event subscribers not cleared on production shutdown (by design; only test helper clears).
- Chroma client not explicitly closed on exit.

## Configuration

- Minimal YAML parser when PyYAML absent — complex YAML may mis-parse.
- `effective_settings` cache invalidated only via `invalidate_settings_cache()` / test reset.
- Desktop Qt preferences not fully covered by export/import (optional JSON path only).

## Testing / CI

- Full pytest suite not validated in this sprint.
- Some plugin tests may assume old `matches()` health rules.
- Windows MSVC requirement for `chroma-hnswlib` on some Python versions.

## Documentation

- Version strings should stay aligned across README, PROJECT_STATUS, CHANGELOG after RC tag.
- Colab-specific runbook could be expanded (optional).

## Security / hardening

- Tool/plugin error messages may include exception text in user-visible tool output.
- No rate limiting on local telemetry file growth.

## Future (post-RC, not feature work)

- Performance tuning from regression metrics.
- Model fine-tuning on curated dataset.
- Packaging/installer for production deploy.
