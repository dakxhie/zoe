# Fine-Tuning Dataset Readiness (Sprint 23)

**Date:** 2026-08-08  
**Status:** Curated dataset prepared — **no adapter trained**  
**Previous audit:** ~38% PRE-FINETUNE (`ZOE_FINE_TUNING_READINESS_REPORT.md`)  
**This sprint:** personality formalization + curated SFT/eval/corrections expansion

---

## Current state

| Asset | Count | Location |
|-------|------:|----------|
| SFT (clean, validated) | **345** | `training/data/clean/sft_sprint23.jsonl` |
| Held-out eval (gold) | **70** | `training/data/held_out_eval/eval_sprint23.jsonl` |
| Corrections | **40** | `training/data/corrections/corrections_sprint23.jsonl` |
| Format seeds (reference) | 13 | `training/data/seeds/` (not auto-merged) |
| Manifest | — | `training/data/clean/sprint23_manifest.json` |

Validation (export-time): SFT / held-out / corrections — **0 errors**.

### Category distribution (SFT)

| Category | n | ~% |
|----------|--:|---:|
| coding | 66 | 19% |
| personality | 62 | 18% |
| general_conversation | 58 | 17% |
| tool_routing | 37 | 11% |
| error_handling | 26 | 8% |
| memory | 26 | 8% |
| retrieval_rag | 26 | 8% |
| agent_planning | 23 | 7% |
| project_analysis | 20 | 6% |
| structured_output | 14 | 4% |

Approximate mapping to Sprint 23 target themes:

| Theme target | Target % | Coverage note |
|--------------|--------:|---------------|
| Personality / conversation | 20% | Strong (personality + much of general) |
| Technical assistance | 20% | Strong (general + analysis) |
| Coding / debugging | 15% | Strong |
| Reasoning / analysis | 10% | Adequate (analysis + planning) |
| Tool-aware | 10% | Met |
| Memory-aware | 5% | Met |
| RAG / grounded | 5% | Met |
| Error / uncertainty | 5% | Met+ |
| Safety / serious | 5% | Present inside personality/error/serious modes |
| Humor / wit / sarcasm | 5% | Present but intentionally minority via modes |

### Personality mode distribution (SFT)

| Mode | n | % | Target |
|------|--:|--:|--------|
| professional_neutral | 198 | 57.4% | 55–65% |
| lightly_witty | 59 | 17.1% | 15–20% |
| playful_sarcastic | 16 | 4.6% | 5–10% (slightly low) |
| serious_no_humor | 72 | 20.9% | 10–20% (slightly high — intentional safety weight) |

### Missing / thinner areas

- Multi-turn dialogues (most rows are single-turn)
- Zoe-repo-specific coding at scale (some analysis rows; more possible)
- Plugin sandbox edge cases beyond registration/timeouts
- Tamil/Tanglish personality examples (spec allows; dataset still English-heavy)
- Human-reviewed teacher generations (pipeline exists; not batch-run)
- Live baseline scores (eval not executed — by design)

### Quality problems noted

- One near-duplicate was removed by not auto-merging historical seeds into clean
- Synthetic curation — high care, but not yet battle-tested against base-model failures
- No private history ingested (intentional)

---

## Personality readiness — **82 / 100**

| Dimension | Score | Notes |
|-----------|------:|-------|
| Professionalism | 90 | Default mode + matrix + serious rules |
| Intelligence | 85 | Technical/coding/analysis coverage |
| Confidence | 80 | Confidence-without-bluff examples present |
| Wit | 82 | Lightly witty band populated |
| Humor | 78 | Rules clear; examples not overfitted |
| Sarcasm | 75 | Small calibrated set; still easy to overuse if expanded carelessly |
| Emotional calibration | 85 | Frustration, grief, safety, incident modes |
| Consistency | 80 | Canonical spec + behavior matrix |
| Technical tone | 88 | Answer-first reinforced |

**Why not higher:** runtime prompts still generic; personality not yet proven vs base on held-out generations.

---

## Dataset readiness — **74 / 100**

In the 300–500 band (345), schema-valid, category-balanced enough for a **first pilot**, corrections + held-out present.

**Why not higher:** single-turn bias; English-only; not yet iterated from real base-model failure mining; volume still modest for broad coverage.

---

## Evaluation readiness — **78 / 100**

70 held-out gold prompts, rubric (`docs/FINE_TUNING_EVAL_RUBRIC.md`), comparison protocol (`docs/FINE_TUNING_COMPARISON_PROTOCOL.md`), runner skeleton from Sprint 22.

**Why not higher:** no baseline numbers yet (execution forbidden this sprint); human scoring not done; adversarial set could be larger.

---

## QLoRA readiness — **72 / 100**

Config + trainer skeleton + explicit ack flags + optional `requirements-training.txt` remain in place.

**Why not higher:** deps not installed/verified in a training env; no dry GPU smoke; CLI `zoe train` still stubbed (intentional); adapter load path not in runtime.

---

## Overall fine-tuning readiness — **68 / 100**

| Before Sprint 23 | After Sprint 23 |
|------------------|-----------------|
| ~38% PRE-FINETUNE (infra without data) | **~68% EXPERIMENT-READY** (data + eval design; still untrained) |

**Interpretation:** Ready to prepare splits and run a **controlled first QLoRA experiment when authorized**. Not ready to claim Zoe is fine-tuned. Not ready to ship an adapter to production.

---

## Personality docs

- Canonical: `docs/ZOE_PERSONALITY.md` (refined Sprint 23)
- Behavior matrix (27 situations): `docs/ZOE_PERSONALITY_BEHAVIOR_MATRIX.md`
- Mantra: **Answer first. Personality second.**
- Energy inspiration only — **no** Marvel/Tony dialogue copying

---

## Realistic training plan

See `docs/FINE_TUNING_TRAINING_PLAN.md` (Phases 1–9) and time **estimates** therein.

---

## Biggest remaining risks

1. **Personality overfitting** if witty/sarcastic share drifts up during later expansion  
2. **Tool hallucination** if future data teaches invented calculator/time/file results  
3. **Eval contamination** if held-out prompts leak into train  
4. **Synthetic–reality gap** — curated ideals may not match hardest live failures  
5. **False confidence from loss curves** — must use rubric ship gate  
6. **Runtime still generic** — users won’t feel FT until adapter is loaded post-eval  

---

## Recommended next sprint (Sprint 24 candidate)

**Controlled pilot:** install training deps → `prepare_dataset` → baseline held-out scoring → tiny QLoRA smoke → full first run → rubric compare → keep/reject adapter.

## What must happen before the first training run

1. Human spot-review of a sample of `sft_sprint23.jsonl`  
2. `prepare_dataset` → train/validation splits with held-out IDs blocked  
3. Install `requirements-training.txt` in a dedicated env  
4. `train_qlora --dry-check-config`  
5. Explicit `--i-understand-this-starts-training` only when intentionally starting  
6. Commit to the comparison protocol before looking at loss  

---

## Explicit non-claims

- Zoe has **not** been fine-tuned.  
- No model weights were downloaded for training this sprint.  
- Production runtime behavior was **not** changed for humor/personality.  
- Training loss has **not** been measured.
