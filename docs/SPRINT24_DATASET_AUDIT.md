# Sprint 24 Dataset Audit

**Date:** 2026-08-08  
**Method:** Static integrity scan via `python -m training.scripts.audit_dataset` (no training, no weight download)  
**Machine-readable:** `training/data/clean/sprint24_audit.json`

---

## Totals

| Asset | Count |
|-------|------:|
| SFT clean (`sft_sprint23.jsonl`) | **345** |
| Held-out eval (`eval_sprint23.jsonl`) | **70** |
| Corrections | **40** |
| Pilot train split (after prepare) | **293** |
| Pilot validation split | **52** |

Prepare command used (no training):

```bash
python -m training.scripts.prepare_dataset --pilot
```

Held-out IDs blocked: **70** (`training/data/held_out_eval/held_out_ids.txt`)  
Rows removed from clean→split due to held-out overlap: **0**

---

## Category distribution (SFT 345)

| Category | n |
|----------|--:|
| coding | 65 |
| personality | 59 |
| general_conversation | 57 |
| tool_routing | 35 |
| error_handling | 25 |
| memory | 25 |
| retrieval_rag | 25 |
| agent_planning | 22 |
| project_analysis | 19 |
| structured_output | 13 |

---

## Personality modes (SFT 345)

| Mode | n | % | Target |
|------|--:|--:|--------|
| professional_neutral | 198 | 57.4% | 55–65% |
| lightly_witty | 59 | 17.1% | 15–20% |
| playful_sarcastic | 16 | 4.6% | 5–10% |
| serious_no_humor | 72 | 20.9% | 10–20% |

### Personality imbalance notes

- **Sarcasm slightly under** target floor (4.6% vs 5%). Not corrected this sprint—avoid boosting sarcasm just to hit a percentage.
- **Serious slightly over** target ceiling (20.9% vs 20%). Acceptable for safety/tool-preservation calibration on a first pilot.
- No evidence of “jokes everywhere” overfitting in labels: professional remains majority.

---

## Duplicate findings

| Check | Result |
|-------|--------|
| Duplicate IDs | **None** |
| Exact duplicate assistant texts | **None** |
| Exact duplicate user prompts | **None** |

Near-semantic duplicates were not exhaustively clustered (would require embedding pass). Manual spot checks during Sprint 23 curation remain the quality bar.

---

## Leakage findings

| Check | Result |
|-------|--------|
| Shared IDs SFT ↔ held-out | **None** |
| Shared user prompts SFT ↔ held-out | **None** |
| Post-split train/val vs held-out guard | **Pass** |

---

## Content safety / style flags

| Check | Result |
|-------|--------|
| Tony Stark / Marvel dialogue hits | **None** |
| Fabricated tool-execution claims (heuristic) | **None** |
| Obvious secret patterns (API keys/PEM) | **None** |
| Unsolicited “today is / current date is” claims | **None** |

---

## Tool-awareness review

Dataset design reinforces:

`USER → INTENT → TOOL WHEN REQUIRED → RESULT → EXPLANATION`

Examples teach:

- calculator / datetime / retrieval / plugins / filesystem need real tools
- explaining **after** tool results is OK
- inventing tool outcomes is not OK

No silent rewrite performed. No rows flagged by the tool-claim heuristic.

**Residual risk:** offline generation eval cannot execute tools; tool awareness must be scored from whether the model *claims* actions or correctly defers.

---

## Correction coverage (40)

| Category | n |
|----------|--:|
| personality | 11 |
| error_handling | 5 |
| general_conversation | 5 |
| tool_routing | 4 |
| retrieval_rag | 4 |
| memory | 4 |
| coding | 3 |
| agent_planning | 2 |
| structured_output | 1 |
| project_analysis | 1 |

Corrections are valuable for later preference/corrective SFT; pilot QLoRA uses the main SFT split first.

---

## Recommendations (no silent mass rewrite)

1. Keep sarcasm minority; if pilot under-delivers wit, add **paired** witty/professional twins—not sarcasm dumps.  
2. After baseline generations, mine **real** base-model failures into corrections.  
3. Optional: add a few more playful_sarcastic rows only if eval shows under-expression—not for quota.  
4. Consider multi-turn examples in a later sprint (current set is mostly single-turn).  
5. Always re-run `prepare_dataset --pilot` before training (train/val JSONL are local/gitignored).  
6. Pin `model.revision` in the pilot config when a scored run begins.

---

## Verdict

**Dataset integrity: PASS for controlled pilot use.**  
No held-out leakage, no exact duplicates, no Marvel imitation hits, no flagged tool-hallucination teaching rows.
