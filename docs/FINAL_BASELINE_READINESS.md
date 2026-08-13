# Final Baseline Readiness

**Date:** 2026-08-13 (updated — blocker fix)  
**Scope:** Static audit + baseline/evaluation pipeline fix only  
**Not done:** re-running baseline, tests, training, weight downloads, commits, pushes, production/runtime changes

---

## Exact root cause (blocker)

The previous “success” could happen while Sprint 26 artifacts were missing because:

1. **Success was not gated on on-disk verification** — the runner printed a success banner after calling the writer without re-checking that  
   `baseline_generations.jsonl`, `baseline_scores.json`, and `baseline_report.md` exist, are non-empty, and parse.
2. **Artifact directory could diverge from the tree being inspected** — defaults were derived from `__file__` (package location). On Colab / Drive / multi-checkout setups, that path can differ from `Path.cwd()` where the operator looks for  
   `training/evaluation/results/sprint26/`.
3. **No hard fail if generation produced zero usable responses** — per-example exceptions were swallowed into empty responses; the run could still exit 0 after writing weak/empty-feeling outputs (or appear complete while the operator checked the wrong absolute path).
4. **Misleading completeness messaging** — dry-run or unverified paths could be confused with a finished baseline. The string `BASELINE MEASUREMENT COMPLETE` must only appear after verification.

Note: the repo previously printed `BASELINE EVALUATION ARTIFACTS WRITTEN` without verification. That contract was insufficient for the Colab gate.

---

## Exact files changed

| File | Change |
|------|--------|
| `training/evaluation/artifacts.py` | cwd-aware `resolve_artifact_dir`; `verify_mode_artifacts`; refuse empty writes; store `prompt_messages` + full `metadata` in JSONL |
| `training/evaluation/runner.py` | Strong logging; require `eval_sprint26.jsonl` with 110 rows; write+verify; non-zero on failure; print `BASELINE MEASUREMENT COMPLETE` only after verify |
| `training/scripts/evaluate_baseline.py` | Resolve artifact dir via cwd/repo; never print COMPLETE itself; dry-run clarifies no artifacts |
| `docs/FINAL_BASELINE_READINESS.md` | This update |

**Training / QLoRA code:** not touched.  
**Production Zoe runtime:** not touched.  
**Held-out / train datasets:** not modified.

---

## Corrected execution flow

```
CLI argparse (--execute, --i-understand-this-loads-models)
  → dry-run? print plan + "NO ARTIFACTS" + exit 0
  → missing ack? refuse + exit 2
  → run_evaluation(plan)
       → resolve config (cwd then repo)
       → resolve held-out = eval_sprint26.jsonl (must exist; n==110)
       → load base model (no adapter when --compare base)
       → generate one response per example (log progress)
       → write_mode_artifacts → sprint26/{baseline_generations,scores,report}
       → verify_mode_artifacts (exists, non-empty, valid JSON/schema)
       → if verify OK and ≥1 successful generation:
            print BASELINE MEASUREMENT COMPLETE + absolute paths + exit 0
         else:
            print BASELINE MEASUREMENT FAILED + exit 1
```

---

## Artifact contract

Directory (absolute, logged):  
`<cwd-or-repo>/training/evaluation/results/sprint26/`

| File | Contract |
|------|----------|
| `baseline_generations.jsonl` | ≥1 JSONL rows; each has id, mode=`base`, `prompt_messages`, `metadata`, `response`, `ok`, null rubric slots |
| `baseline_scores.json` | Valid JSON; `schema_version=zoe_eval_artifacts_v1`; counts; heuristic rates; human rubric fields `unavailable` (not invented) |
| `baseline_report.md` | Non-empty human-readable summary + absolute paths |

Future adapter run uses the **same schema** with `adapter_*` filenames / `mode=adapter`.

---

## Failure behavior

| Condition | Result |
|-----------|--------|
| No `--execute` | exit 0, **no** COMPLETE, no files |
| `--execute` without ack | exit 2, no COMPLETE |
| Wrong/missing held-out | exit 1 |
| Held-out ≠ 110 for Sprint 26 | exit 1 |
| Zero successful generations | exit 1 (no COMPLETE) |
| Write/verify failure | exit 1, `BASELINE MEASUREMENT FAILED` |

---

## Exact command (operator runs later — not executed in this task)

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base \
  --execute \
  --i-understand-this-loads-models
```

Prefer `python -m` from the repo root (`%cd zoe-ai` on Colab).

---

## Static confirmation

- `--execute` + ack reaches `run_evaluation` (no alternate silent path).
- Sprint 26 held-out is enforced by filename + count.
- Writer always targets resolved absolute `artifact_dir`.
- COMPLETE banner is behind `verify_mode_artifacts`.
- No placeholder/fake generations in code paths.

---

## Verdict

**READY FOR BASELINE MEASUREMENT**

Re-run the execute+ack command once on Colab, confirm the three files exist under the logged absolute `artifact_dir`, then proceed to QLoRA.
