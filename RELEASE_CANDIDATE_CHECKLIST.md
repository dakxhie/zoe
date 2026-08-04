# Zoe v2.11 — Release Candidate Checklist

Feature freeze active. Use this checklist before tagging a release candidate and running full regression.

## Startup

- [ ] `python cli/main.py chat` — welcome, diagnostics lines once, no duplicate plugin discovery errors
- [ ] `LOG_LEVEL=DEBUG` — startup step timings present
- [ ] `python desktop/app.py` — splash completes, index counts shown
- [ ] `python scripts/install.py` — verification steps succeed
- [ ] `ZOE_PROFILE=production` — INFO logging, no DEBUG spam by default
- [ ] Legacy `config/settings.txt` still respected when YAML model name empty

## Shutdown

- [ ] CLI exit (`exit` / Ctrl+C) — process exits without hung threads (atexit shutdown)
- [ ] Desktop window close — app quits cleanly
- [ ] Enabled extension plugins — disable/unload does not crash host
- [ ] Autonomous task in progress — cancel on shutdown where applicable

## Memory

- [ ] Explicit “remember” utterances — acknowledgement path unchanged
- [ ] Profile queries — “What do you know about me?” / “What have you learned?”
- [ ] Reinforcement — repeated facts update frequency, not duplicate documents
- [ ] Trivial chat filtered — greetings/calculator not stored
- [ ] Chroma unavailable — chat continues, memory save skipped gracefully

## Agents

- [ ] Simple chat — orchestrator → context → generation
- [ ] Multi-tool / comparison intents — agent plan + fusion
- [ ] Project analysis — analysis context injected
- [ ] Empty index routes — friendly empty responses

## Supervisor

- [ ] Specialist selection for memory/research/coding queries
- [ ] Parallel specialists — no crash when one specialist fails
- [ ] Low-complexity chat — supervisor skipped when appropriate
- [ ] Web retrieval — permission gate for `builtin.web`

## Tasks

- [ ] Complex autonomous goal — task engine path
- [ ] Cancel / pause / resume (if exposed in UI/CLI hooks)
- [ ] Progress events — no exception in subscribers
- [ ] Task completion — optional memory summary

## Plugins

- [ ] Builtins enabled — calculator, datetime, memory routes
- [ ] `python cli/main.py plugins list`
- [ ] Enable `clock` extension — route works; disable removes route
- [ ] Reload extension after editing `main.py`
- [ ] Legacy `plugins/local/*.py` PLUGIN modules still load
- [ ] Crashed plugin — host continues

## Voice

- [ ] Without `requirements-voice.txt` — graceful errors, no import crash
- [ ] With voice deps — push-to-talk path (manual)
- [ ] Optional hooks — no change to core STT/TTS pipeline

## Desktop

- [ ] Chat worker — background generation, UI responsive
- [ ] Vision worker — image analysis path
- [ ] Settings persist — theme/preferences
- [ ] No UI redesign regressions

## CLI

- [ ] `chat`, `ingest`, `code`, `image`, `doctor`, `history`, `plugins *`
- [ ] Exit codes on plugin enable failure
- [ ] `python scripts/doctor.py` — deployment health section

## Deployment

- [ ] `config/default.yaml` + profile overlays load
- [ ] Env overrides: `ZOE_LOG_LEVEL`, `ZOE_PROFILE`, `ZOE_MEMORY_DB`
- [ ] Export/import settings — no memories/conversations in bundle
- [ ] Telemetry file append only under `data/telemetry/`

## Telemetry

- [ ] Local JSONL only — no network upload code paths
- [ ] Disabled in testing profile / when configured off
- [ ] No PII in payloads (review sample lines)

## Health

- [ ] `run_health_checks()` — configuration, plugins, vector DB, voice, tasks
- [ ] GPU check — CPU-only environment reports healthy/degraded, not crash
- [ ] Doctor report aligns with health checks

## Config

- [ ] Priority: CLI > env > YAML > defaults > settings.txt merge
- [ ] Portable mode flag `ZOE_PORTABLE`
- [ ] Invalid YAML — falls back or warns, no crash on chat start

## Performance

- [ ] Single plugin discovery per process (cached)
- [ ] No double diagnostics on CLI chat start (startup report lines)
- [ ] Model lazy load — doctor/ingest do not load LLM unless needed
- [ ] Route cache — repeated identical queries hit plugin registry cache

## Security

- [ ] Plugin storage path traversal blocked
- [ ] Manifest entry path validation
- [ ] No `eval`/`pickle` on untrusted plugin input
- [ ] Tool errors — no stack traces to end user by default

## Regression readiness

- [ ] `tests/regression.py` quick mode defined
- [ ] Headless CI — `CI=true` / `GITHUB_ACTIONS` skips GUI/voice
- [ ] Colab — no hard dependency on Qt/mic/GPU
- [ ] Test collection — no missing imports in `tests/conftest.py`

## Known risks

- Windows Python 3.14 / torch / chroma-hnswlib build fragility
- Parallel specialists + shared Chroma under load
- Legacy local example plugins enabled by default if present
- Post-turn memory review cost on every chat turn
- Extension reload without full process restart (edge cases)

## Remaining technical debt

See `TECHNICAL_DEBT.md`.

## Release readiness score (pre-regression)

**80 / 100** — Architecture integrated; critical extension and memory update fixes applied; startup deduplicated; shutdown hooks on CLI/desktop. Full score depends on green regression and environment matrix.

**Sign-off**

| Role | Name | Date |
|------|------|------|
| Engineering | | |
| QA / Regression | | |
