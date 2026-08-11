# Dataset Readiness Report

**Sprint:** 23 — Fine-tuning dataset & personality preparation  
**Date:** 2026-08-08  
**Status:** Curated SFT/eval/corrections ready for a controlled first experiment  
**Trained adapter:** none

Authoritative scored report: [`docs/FINE_TUNING_DATASET_READINESS.md`](../docs/FINE_TUNING_DATASET_READINESS.md)

---

## Counts (validated export)

| Split | Count | File |
|-------|------:|------|
| SFT clean | 345 | `training/data/clean/sft_sprint23.jsonl` |
| Held-out eval | 70 | `training/data/held_out_eval/eval_sprint23.jsonl` |
| Corrections | 40 | `training/data/corrections/corrections_sprint23.jsonl` |

Manifest: `training/data/clean/sprint23_manifest.json`  
Regenerate via: `python -m training.data.curation.export_sprint23` (export only — not training)

---

## Personality modes (SFT)

| Mode | n | % |
|------|--:|--:|
| professional_neutral | 198 | 57.4% |
| lightly_witty | 59 | 17.1% |
| playful_sarcastic | 16 | 4.6% |
| serious_no_humor | 72 | 20.9% |

Slightly high serious share is intentional for safety calibration; sarcastic share stays a minority.

---

## Sources

| Source | Role |
|--------|------|
| Sprint 23 curation banks | Primary SFT |
| `training/data/seeds/` | Format exemplars only (not auto-merged) |
| History / telemetry | Not bulk-ingested |
| Teacher pipeline | Available; not batch-executed |

---

## Next steps before train

1. Spot-review clean JSONL  
2. `prepare_dataset` → train/val  
3. Baseline held-out scoring  
4. Explicit QLoRA ack flag when intentionally training  

**Fine-tuning is not a replacement for Zoe’s tools, memory, retrieval, routing, or deterministic systems.**
