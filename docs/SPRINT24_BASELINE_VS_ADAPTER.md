# Sprint 24 — Base vs Adapter Comparison

**Status:** **PENDING RESULTS** — no baseline or adapter generations were executed in this Cursor task (weights not downloaded; training not started).

**Protocol:** `docs/FINE_TUNING_COMPARISON_PROTOCOL.md`  
**Rubric:** `docs/FINE_TUNING_EVAL_RUBRIC.md` + Sprint 24 dimensions in `training/evaluation/metrics.py`  
**Held-out set (frozen):** `training/data/held_out_eval/eval_sprint23.jsonl` (70 prompts)  
**Config:** `training/config/pilot_qlora.yaml`

---

## Run identity (to fill when executed)

| Field | Value |
|-------|-------|
| Base model | `Qwen/Qwen2.5-3B-Instruct` |
| Model revision | _(pin when running)_ |
| Adapter path | `training/adapters/runs/sprint24_pilot/` _(after train)_ |
| Temperature | 0.7 |
| Top-p | 0.9 |
| Max new tokens | 256 |
| Seed | 42 |
| System prompt | From each held-out example `messages` (dataset), not production `brain/context.py` |
| Tools available in offline eval | **false** |
| Rubric version | `sprint24_v1` |
| Timestamp | _TBD_ |

### Exact baseline command (NOT executed here)

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/pilot_qlora.yaml \
  --split held_out_eval \
  --compare base \
  --execute \
  --i-understand-this-loads-models
```

### Exact adapter comparison command (after a trained adapter exists)

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/pilot_qlora.yaml \
  --split held_out_eval \
  --compare base,adapter \
  --adapter-path training/adapters/runs/sprint24_pilot \
  --execute \
  --i-understand-this-loads-models
```

Do not change held-out prompts between baseline and adapter runs.

---

## Aggregate scores (1–5, human / judge) — PENDING

| Metric | Base | Adapter | Change |
| ------------------------ | ---: | ------: | -----: |
| Correctness | — | — | — |
| Helpfulness | — | — | — |
| Clarity | — | — | — |
| Concision | — | — | — |
| Professionalism | — | — | — |
| Intelligence | — | — | — |
| Confidence | — | — | — |
| Wit | — | — | — |
| Humor | — | — | — |
| Sarcasm | — | — | — |
| Naturalness | — | — | — |
| Emotional calibration | — | — | — |
| Tool awareness | — | — | — |
| Grounding | — | — | — |
| Hallucination resistance | — | — | — |
| Uncertainty handling | — | — | — |
| Instruction following | — | — | — |

### Slice checks (required)

| Slice | What to verify |
|-------|----------------|
| Serious / no-humor | Humor/sarcasm drop; no cruelty |
| Witty / playful | Personality without answer displacement |
| Tool-routing | Defers; does not invent results |
| RAG / empty context | No fabricated facts |
| Structured output | Format fidelity |

---

## Qualitative examples — PENDING

### Improvements

**BEFORE (base)**  
→ **AFTER (adapter)**  
→ **WHY IT IS BETTER**

_(fill after scoring)_

### Regressions

**BEFORE (base)**  
→ **AFTER (adapter)**  
→ **WHY IT IS WORSE**  
→ **RECOMMENDED FIX**

_(fill after scoring)_

---

## Tool-preservation findings — PENDING

Flag any response that claims:

- calculator / datetime / web / plugin / DB / filesystem actions without tooling

Offline eval sets `tools_available: false`; fabricated claims are automatic failures on tool awareness.

---

## Ship gate reminder

Accept adapter only if personality/helpfulness improve **without** material regressions on correctness, grounding, tool awareness, serious-context behavior, and hallucination resistance.

Lower training loss alone is **not** acceptance.
