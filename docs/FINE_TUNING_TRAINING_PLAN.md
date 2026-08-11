# Fine-Tuning Training Plan (Document only — not executed)

## Phase 1 — Dataset curation
Expand/review SFT to ~300–500 high-quality rows; maintain personality balance; keep tools outside the model.

## Phase 2 — Validation
Run `validate_dataset` / `inspect_dataset`; fix schema errors; dedupe; privacy scan; confirm held-out disjointness.

## Phase 3 — Baseline evaluation
Score **base** model on held-out with the rubric (requires explicit eval ack + weights when authorized).

## Phase 4 — Small pilot QLoRA run
Tiny subset or 1 short epoch; verify adapter artifacts save; no production wiring.

## Phase 5 — Evaluation
Base vs adapter on full held-out; apply ship gate.

## Phase 6 — Dataset correction
Add correction pairs for observed failures (over-humor, tool hallucination, etc.).

## Phase 7 — Second training run
Retrain on improved data; same eval protocol.

## Phase 8 — Adapter selection
Keep best adapter by held-out metrics; archive losers.

## Phase 9 — Production integration
Optional PEFT load path in runtime **after** explicit adoption decision; still do not replace tools/memory/RAG.

---

## Time estimates (approximate — not measured)

Assumes a typical Colab T4/A100-class GPU and ~300–500 SFT rows. **Estimates only.**

| Activity | Rough range |
|----------|-------------|
| Dataset preparation / human review | 1–3 days |
| Validation + disjointness checks | 30–90 minutes |
| Baseline inference on ~70 held-out prompts | 20–90 minutes |
| Pilot QLoRA (smoke) | 20–60 minutes |
| Full first QLoRA on 3B + 300–500 rows | ~1–4 hours |
| Rubric evaluation (human) | 2–6 hours |
| Full iteration cycle (data fix → retrain → rescore) | 1–3 days |

Exact runtime depends on GPU, sequence length, epochs, and batch/accum settings in `training/config/default_qlora.yaml`.
