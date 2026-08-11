# Sprint 24 Pilot Runbook (historical)

Superseded for the **canonical Colab GPU first run** by:

→ [`docs/COLAB_FINE_TUNING_RUNBOOK.md`](COLAB_FINE_TUNING_RUNBOOK.md)  
→ config: `training/config/colab_qlora.yaml`

This file remains as Sprint 24 history. Prefer the Colab runbook for the actual experiment.

---

# Sprint 24 Pilot Runbook (intentional execution only)

This runbook is for a **human-operated** Colab/GPU session.  
Cursor Sprint 24 preparation **did not** run these GPU steps.

## 0. Safety

- Do not modify production runtime.
- Do not ship the first adapter automatically.
- Every weight-loading step requires an acknowledgement flag.
- Prefer `training/config/colab_qlora.yaml` over `pilot_qlora.yaml`.

## 1. Prepare data (CPU OK for prepare only — train still needs GPU)

```bash
python -m training.scripts.audit_dataset
python -m training.scripts.prepare_dataset --pilot
python -m training.scripts.validate_dataset --path training/data/train/sft_pilot.jsonl
python -m training.scripts.validate_dataset --path training/data/validation/sft_pilot.jsonl
python -m training.scripts.train_qlora --config training/config/colab_qlora.yaml --dry-check-config
```

## 2. Baseline (loads base weights — explicit ack)

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base \
  --execute \
  --i-understand-this-loads-models
```

Score with `docs/FINE_TUNING_EVAL_RUBRIC.md` / Sprint 24 dimensions.  
Record into `docs/SPRINT24_BASELINE_VS_ADAPTER.md`.

## 3. Train pilot (loads/downloads weights — explicit ack)

```bash
python -m training.scripts.train_qlora \
  --config training/config/colab_qlora.yaml \
  --i-understand-this-starts-training
```

Adapter output: `training/adapters/runs/colab_qlora_pilot/`

## 4. Compare base vs adapter

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base,adapter \
  --adapter-path training/adapters/runs/colab_qlora_pilot \
  --execute \
  --i-understand-this-loads-models
```

## 5. Decide

Use `docs/ADAPTER_ACCEPTANCE_CRITERIA.md` (KEEP / ITERATE / REJECT).  
Do not confuse training completion with Zoe becoming better.
