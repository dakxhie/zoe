# Final Baseline Readiness

**Date:** 2026-08-13  
**Scope:** Static audit + baseline/evaluation pipeline fix only  
**Not done:** re-running baseline, tests, training, weight downloads, commits, pushes, production/runtime changes

---

## Root cause

`python training/scripts/evaluate_baseline.py` could look “successful” **without** leaving a usable Sprint 26 baseline because:

1. **Dry-run default** — Without `--execute` **and** `--i-understand-this-loads-models`, the script printed a plan and exited `0`. **No files were written.**
2. **Wrong / hidden output path** — Even on execute, the default dump was  
   `training/adapters/runs/sprint24_pilot/eval_baseline.json`, which is:
   - Sprint-24-named (stale)
   - under `training/adapters/runs/` (**gitignored**)
   - a single combined JSON, **not** generations JSONL + scores + report
3. **No score/report artifacts** — Rubric slots were left `null` with no `baseline_scores.json` / `baseline_report.md`, so inspection only found docs and scripts.
4. **No clear “artifacts written” contract** — Success messaging did not require the Sprint 26 result directory.

Calling the script without the ack flags therefore cannot produce baseline scores; an executed run could still bury output where it was easy to miss.

---

## Exact fix

| Change | Purpose |
|--------|---------|
| `training/evaluation/artifacts.py` | Shared writer for generations JSONL, scores JSON, markdown report (`zoe_eval_artifacts_v1`) |
| `training/evaluation/runner.py` | Per-example success/failure; write Sprint 26 artifacts; prefer `eval_sprint26.jsonl`; optional legacy dump only if `--output` |
| `training/scripts/evaluate_baseline.py` | Default `--artifact-dir` → `training/evaluation/results/sprint26/`; dry-run prints **NO ARTIFACTS WERE WRITTEN** + exact re-run command |
| `training/scripts/score_generations.py` | Rebuild scores/report from generations JSONL without loading models |
| `training/evaluation/results/README.md` | Documents expected files |
| `docs/COLAB_FINE_TUNING_RUNBOOK.md` | Points Phase 3/5 at new artifact paths |

**Not changed:** production Zoe (`brain/`, runtime defaults), training data, QLoRA trainer safety gates, adapter-off-by-default.

**Scores policy:** No invented rubric averages. Human 1–5 dimensions and overall score are marked `unavailable` with reasons. Only generation counts + offline heuristics (empty, tool-claim regex, humor-in-serious, etc.) are filled.

---

## Files modified / added

- `training/evaluation/artifacts.py` *(new)*
- `training/evaluation/runner.py`
- `training/evaluation/__init__.py`
- `training/evaluation/results/README.md` *(new)*
- `training/scripts/evaluate_baseline.py`
- `training/scripts/score_generations.py`
- `docs/COLAB_FINE_TUNING_RUNBOOK.md`
- `docs/FINAL_BASELINE_READINESS.md` *(this file)*

---

## Expected baseline artifacts (after a real execute)

Directory: `training/evaluation/results/sprint26/`

| File | Contents |
|------|----------|
| `baseline_generations.jsonl` | One row per held-out example: id, response, ok/error, category, track, personality_mode, auto heuristics, null rubric slots |
| `baseline_scores.json` | Model/dataset IDs, timestamp, gen config, counts, category/track breakdowns, heuristic rates, **unavailable** human metrics |
| `baseline_report.md` | Human-readable summary of the above + limitations + paths |

Future adapter run writes the same schema as `adapter_generations.jsonl` / `adapter_scores.json` / `adapter_report.md` for BASELINE → ADAPTER comparison.

---

## Exact command to measure baseline (user runs later; not executed here)

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base \
  --execute \
  --i-understand-this-loads-models
```

Uses `data.held_out_eval_path` → `training/data/held_out_eval/eval_sprint26.jsonl` (110 examples).  
Does **not** load or create an adapter when `--compare base`.

Optional heuristic re-score (no model load):

```bash
python -m training.scripts.score_generations \
  --input training/evaluation/results/sprint26/baseline_generations.jsonl \
  --artifact-dir training/evaluation/results/sprint26
```

---

## Gate answers

| Question | Answer |
|----------|--------|
| Ready for baseline measurement? | **YES** — pipeline now writes concrete Sprint 26 artifacts on execute+ack |
| Baseline already measured with new artifacts? | **NO** — this task did not re-run evaluation |
| Ready for Colab QLoRA after baseline? | **YES, after** you run the baseline command above and confirm the three files exist |
| Anything still blocking QLoRA itself? | **No infra blocker** from this audit; procedural: finish baseline → train with ack → compare same held-out → human KEEP/REJECT |
| Can dry-run fake success? | Dry-run still exits 0 but now **explicitly** says no artifacts were written |

---

## Comparison intent (unchanged)

Adapter KEEP must answer: **Did fine-tuning actually improve Zoe?** on correctness, grounding, tool honesty, Tanglish, coding, and calibrated personality — **not** training loss or “funnier only.”

Safety gates preserved: train ack, refuse incomplete adapters in production, adapter off by default, base weights never overwritten.

---

## Verdict

**READY FOR BASELINE MEASUREMENT**

Next human/Colab action: run the execute+ack baseline command once, verify the three Sprint 26 artifact files, then proceed to QLoRA.
