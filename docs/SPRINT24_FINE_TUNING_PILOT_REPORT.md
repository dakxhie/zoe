# Sprint 24 Fine-Tuning Pilot Report

**Date:** 2026-08-08  
**Mode:** Controlled pilot **preparation** (Cursor task did not train or download weights)  
**Base model:** `Qwen/Qwen2.5-3B-Instruct`  
**Personality target:** Professional enough to trust · smart enough to impress · witty enough to enjoy · sarcastic enough to have a pulse · responsible enough to shut up and solve the problem when needed.

---

## Executive summary

Sprint 24 hardened the training/evaluation path, audited the 345-row SFT set (no held-out leakage), prepared pilot train/val splits (293/52), and froze a conservative QLoRA pilot config.

**Training was not started.** The acknowledgement-gated command is documented below and was verified to refuse without the flag.

**Adapter verdict: EXPERIMENTAL / NEEDS ITERATION** — more precisely: **NOT YET TRAINED**. No base-vs-adapter scores exist yet.

Success criterion remains:

> Does fine-tuning make Zoe more distinctly Zoe without becoming less reliable?

Not:

> Did training loss go down?

---

## Pipeline status

| Component | Status |
|-----------|--------|
| Dataset audit | Pass (`docs/SPRINT24_DATASET_AUDIT.md`) |
| `prepare_dataset --pilot` | Done locally (293 train / 52 val) |
| Held-out ID blocklist | Written (`held_out_ids.txt`) |
| Leakage guards | Strengthened in `training/scripts/guards.py` + trainer |
| Pilot config | `training/config/pilot_qlora.yaml` |
| Train ack gate | Verified: refuses without `--i-understand-this-starts-training` |
| Eval ack gate | Verified dry plan; requires `--execute --i-understand-this-loads-models` |
| Production runtime | **Untouched** |

### Defects found and fixed (training infra only)

1. **Weak held-out guard** — previously only compared path equality; now checks IDs + user-prompt overlap for train/val.  
2. **Empty/implicit train paths** — pilot config points at explicit `sft_pilot.jsonl` files; dry-check fails if missing.  
3. **Prepare didn’t auto-block held-out** — now blocks by id and user text; writes `held_out_ids.txt`.  
4. **Eval reproducibility gaps** — runner now records seed, generation settings, tools_available, rubric version, timestamps; prefers `eval_sprint23.jsonl`.  
5. **TRL/Transformers API drift** — trainer tries `eval_strategy` then `evaluation_strategy`; SFTTrainer `processing_class` then `tokenizer`.  
6. **Run card missing** — trainer writes `run_card.json` under the output dir when training actually starts.  
7. **Default config** — pilot defaults to conservative 1 epoch / 1e-4 LR for stability.

---

## Dataset status

- 345 SFT / 70 held-out / 40 corrections  
- Integrity: no leakage, no exact duplicates, no Marvel hits, no flagged tool-hallucination teaching  
- Personality: professional majority; sarcasm minority; serious slightly high (documented)  
- Details: `docs/SPRINT24_DATASET_AUDIT.md`

---

## Baseline status

**Not executed** (would download/load model weights).

Documented command:

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/pilot_qlora.yaml \
  --split held_out_eval \
  --compare base \
  --execute \
  --i-understand-this-loads-models
```

Frozen settings: temperature 0.7, top_p 0.9, max_new_tokens 256, seed 42, tools_available false, prompts from held-out messages.

Comparison sheet: `docs/SPRINT24_BASELINE_VS_ADAPTER.md` (pending numbers).

---

## Training configuration (pilot)

| Setting | Value | Why |
|---------|-------|-----|
| LoRA r | 16 | Enough capacity for style/behavior on small data; limits overfit vs huge ranks |
| LoRA alpha | 32 | Common 2×rank scaling |
| LoRA dropout | 0.05 | Light regularization |
| Target modules | q/k/v/o + MLP gates | Standard Qwen-style full attention+MLP adapters |
| LR | 1e-4 | More stable than 2e-4 for first pilot |
| Scheduler | cosine | Smooth decay |
| Epochs | **1** | Stability over maximum fit |
| Batch / accum | 1 × 8 | Effective batch ~8 on limited VRAM |
| Warmup | 5% | Avoid early shock |
| Max seq | 2048 | Covers curated single-turn chats with margin |
| Precision | fp16 + 4-bit NF4 | QLoRA memory path |
| Grad checkpoint | true | VRAM stability |
| Seed | 42 | Reproducibility |
| Output | `training/adapters/runs/sprint24_pilot` | Explicit, non-default scratch path |
| Packing | false | Avoid accidental example blending on first run |

Priority: **STABILITY > SPEED > MAXIMUM TRAINING**.

---

## Pilot status

### Exact train command (NOT executed; STOP here unless intentionally training)

```bash
python -m training.scripts.prepare_dataset --pilot
python -m training.scripts.train_qlora --config training/config/pilot_qlora.yaml --dry-check-config
python -m training.scripts.train_qlora \
  --config training/config/pilot_qlora.yaml \
  --i-understand-this-starts-training
```

Verified without ack: script exits in SAFE MODE and downloads nothing.

---

## Base vs adapter results

**N/A — adapter not trained; baseline not scored.**  
See pending table in `docs/SPRINT24_BASELINE_VS_ADAPTER.md`.

---

## Personality improvement

Pending measurement. Target remains answer-first with calibrated wit—not comedian-first.

---

## Reliability / tool-awareness / overfitting

Pending measurement. Eval includes tool-claim heuristics and serious-slice checks.

---

## Problems discovered

1. First pilot cannot be judged until baseline+adapter generations exist.  
2. Offline eval cannot truly execute tools—tool tests are behavioral (claims/deferrals).  
3. Train/val JSONL are gitignored; must re-prepare on each machine.  
4. `model.revision` still null until a scored run pins it.  
5. Human rubric scoring still required (auto metrics are partial).

---

## Recommended changes before / after first GPU run

**Before train (on GPU host):**

1. Re-run `prepare_dataset --pilot` + `audit_dataset`  
2. Pin model revision in `pilot_qlora.yaml`  
3. Install `requirements-training.txt`  
4. Run baseline with ack flags  
5. Only then train with ack flag  

**If pilot fails:** diagnose before raising epochs—check formatting, LR, truncation, sarcasm imbalance, tool-claim regressions, eval mismatch. Prefer smallest data/config fix.

**If pilot succeeds:** still do not ship—review serious/tool/hallucination/verbosity/repetition; second eval pass; then consider second experiment.

---

## Adapter verdict

**EXPERIMENTAL / NEEDS ITERATION**

(Not trained in this sprint task. Not production. Not mergeable.)

---

## Acceptance criteria (for when scores exist)

Reject if accepted merely because loss fell, training finished, or sarcasm increased.

Accept toward “READY FOR SECOND PILOT” only if held-out shows personality gains without unacceptable regressions on correctness, grounding, tool awareness, uncertainty, and serious-context behavior—and without joke injection everywhere / phrase parroting / verbosity collapse.
