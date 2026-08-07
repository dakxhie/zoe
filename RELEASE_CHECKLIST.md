# Zoe v2.11 — Release Checklist

Use this checklist before tagging a release candidate or production release.  
**Do not** treat this as a substitute for the already-green automated suite (249 passed / 5 skipped).

Related docs: `FINAL_RELEASE_REVIEW.md`, `TECHNICAL_DEBT.md`, `POST_STABILIZATION_REVIEW.md`.

---

## Gate status

| Gate | Status |
|------|--------|
| Automated pytest (full / Colab) | ✅ Reported green (249 / 5 / 0) |
| Static release review | ✅ `FINAL_RELEASE_REVIEW.md` |
| Manual smoke (this file) | ☐ Pending sign-off |
| Tag / package | ☐ After smoke |

---

## 1. Startup

- [ ] `python cli/main.py chat` — welcome + diagnostics once; no duplicate plugin discovery errors
- [ ] `LOG_LEVEL=DEBUG` / `ZOE_LOG_LEVEL=DEBUG` — useful timings, no crash
- [ ] `python desktop/app.py` — splash completes; index counts shown (or graceful zeros)
- [ ] `python scripts/install.py` — verification steps succeed
- [ ] `ZOE_PROFILE=production` — INFO default; no DEBUG spam
- [ ] Legacy `config/settings.txt` honored when YAML model name empty

## 2. Shutdown

- [ ] CLI `exit` / Ctrl+C — process exits; no hung non-daemon work
- [ ] Desktop window close — clean quit
- [ ] Disable/unload enabled extension — host stable
- [ ] In-flight autonomous task — cancel/shutdown does not deadlock

## 3. Chat & retrieval

- [ ] Simple chat turn completes
- [ ] Calculator / datetime routes (`what is 2+2`, local time)
- [ ] Unknown timezone location returns no false local time (`Atlantis`)
- [ ] Empty notes/pdf/code index — friendly empty message, no crash
- [ ] Web route (if network allowed) — sources footer when content present

## 4. Memory

- [ ] Explicit remember → acknowledgement
- [ ] Profile query (“What do you know about me?”)
- [ ] “I am building …” classified/stored as project-relevant memory
- [ ] Trivial calculator/greetings not stored
- [ ] Chroma unavailable — chat continues

## 5. History

- [ ] Messages persist across restart
- [ ] `history` / `history stats` / `history summary` / `history clear`
- [ ] History size matches appended turns (no double-count)

## 6. Agents

- [ ] Multi-tool / compare chapters — plan executes (no autonomous hijack)
- [ ] Project analysis — analysis context path (not autonomous-only reply)
- [ ] Fusion keeps memory before web when both present

## 7. Plugins

- [ ] `plugins list`
- [ ] Builtin calculator route
- [ ] Enable `ext.clock` / `clock` — route + reload
- [ ] Disable clock — route removed
- [ ] Crashed/bad extension — host continues

## 8. Doctor / diagnostics

- [ ] `python cli/main.py doctor` or `python scripts/doctor.py`
- [ ] Startup banner exactly five lines (Memory, Notes, PDF, Code, Model)
- [ ] FAIL checks surface recommended fixes when details exist

## 9. Desktop / voice (environment-dependent)

- [ ] Chat worker keeps UI responsive
- [ ] Settings dialog opens; missing voice deps do not crash
- [ ] Without voice packages — graceful messaging
- [ ] With voice packages — push-to-talk smoke (manual)

## 10. Deployment / config / telemetry

- [ ] Profile overlays + `ZOE_LOG_LEVEL` / `ZOE_PROFILE` / `ZOE_MEMORY_DB`
- [ ] Export/import settings — no memories/conversations leaked into bundle
- [ ] Telemetry appends under `data/telemetry/` only when enabled
- [ ] Health checks: config, plugins, vector DB — no crash on CPU-only

## 11. Security smoke

- [ ] Plugin storage cannot write outside plugin data root
- [ ] Manifest `entry` with `..` rejected
- [ ] Calculator rejects non-arithmetic text
- [ ] User-facing errors do not dump full stack traces by default

## 12. Packaging readiness

- [ ] Version strings match tag intent (README, CHANGELOG, PROJECT_STATUS, manifests)
- [ ] `requirements.txt` / `requirements-voice.txt` reviewed for the release platform
- [ ] Known platform risks acknowledged (Windows chroma/torch builds)
- [ ] `TECHNICAL_DEBT.md` accepted as post-RC backlog

---

## Known risks (accept or mitigate)

- Windows Python + torch / chroma-hnswlib build fragility
- Parallel specialists + shared Chroma under heavy load
- Legacy local plugins enabled by default if present
- Post-turn memory review cost every chat turn
- Voice/Chroma not fully torn down on shutdown

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Engineering | | | ☐ Pass / ☐ Hold |
| QA / Manual smoke | | | ☐ Pass / ☐ Hold |
| Release owner | | | ☐ Tag RC / ☐ Block |

**Tag only when Engineering + QA are Pass and known risks are accepted.**
