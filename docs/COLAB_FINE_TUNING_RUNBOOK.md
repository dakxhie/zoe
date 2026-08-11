# Colab Fine-Tuning Runbook

**Target:** Google Colab + NVIDIA GPU + 4-bit QLoRA  
**Canonical config:** `training/config/colab_qlora.yaml`  
**Base model:** `Qwen/Qwen2.5-3B-Instruct`  
**Status:** Procedure documented — **do not execute** until the user explicitly confirms.

Companion docs:

- [`FINAL_FINE_TUNING_READINESS.md`](FINAL_FINE_TUNING_READINESS.md)
- [`FINAL_FINE_TUNING_CHECKLIST.md`](FINAL_FINE_TUNING_CHECKLIST.md)
- [`ADAPTER_ACCEPTANCE_CRITERIA.md`](ADAPTER_ACCEPTANCE_CRITERIA.md)
- [`FINE_TUNING_COMPARISON_PROTOCOL.md`](FINE_TUNING_COMPARISON_PROTOCOL.md)
- [`FINE_TUNING_EVAL_RUBRIC.md`](FINE_TUNING_EVAL_RUBRIC.md)
- [`ZOE_PERSONALITY.md`](ZOE_PERSONALITY.md)

**CPU fine-tuning is not supported.** Do not invent a laptop/CPU LoRA path.

---

## Phase 1 — Colab setup

1. Open a new Colab notebook.
2. Runtime → Change runtime type → **GPU** (T4 / L4 / A100).
3. Clone the repository (private: use a token; public: HTTPS/SSH as usual).

```bash
!git clone <YOUR_ZOE_REPO_URL> zoe-ai
%cd zoe-ai
```

4. Install training dependencies (see `requirements-training.txt`):

```python
# Needs TRL with SFTConfig(assistant_only_loss=True) — use >=0.15.0
%pip install -q "transformers>=4.46.0" "datasets>=2.18.0" "peft>=0.11.0" \
  "trl>=0.15.0" "bitsandbytes>=0.43.0" "accelerate>=0.30.0" "pyyaml>=6.0" safetensors
```

5. Verify environment (safe — no training):

```python
import torch
assert torch.cuda.is_available(), "Select a GPU runtime before training"
print(torch.cuda.get_device_name(0))
```

```bash
!python -m training.scripts.train_qlora --config training/config/colab_qlora.yaml --dry-check-config
```

Expected: CUDA available = True. Without `--i-understand-this-starts-training`, the trainer stays in SAFE MODE.

Optional HF auth (only if the base model or gated assets require it):

```python
from huggingface_hub import login
# login()  # only when needed
```

---

## Phase 2 — Dataset preparation

Train/validation JSONL files are **gitignored**. Regenerate on Colab.

**Sprint 26 (recommended first FT):**

```bash
!python -m training.data.curation.export_sprint26
!python -m training.scripts.prepare_dataset --sprint26-balanced --pilot
!python -m training.scripts.validate_dataset --path training/data/train/sft_pilot.jsonl
!python -m training.scripts.validate_dataset --path training/data/validation/sft_pilot.jsonl
```

Expected balanced clean source: `sft_sprint26_balanced.jsonl` (~786 rows).  
Sprint 23/25 files remain preserved.

Legacy-only prepare (not recommended for the expanded FT):

```bash
!python -m training.scripts.prepare_dataset --pilot
```

---

## Phase 3 — Baseline

Loads base weights. Requires explicit acknowledgement.

```bash
!python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base \
  --execute \
  --i-understand-this-loads-models
```

Record outputs for later base-vs-adapter comparison.  
Do **not** treat this as acceptance of any adapter.

---

## Phase 4 — QLoRA

Loads/downloads base weights and trains a PEFT adapter. Requires ack.

```bash
!python -m training.scripts.train_qlora \
  --config training/config/colab_qlora.yaml \
  --i-understand-this-starts-training
```

Output (default): `training/adapters/runs/colab_qlora_pilot/`

Required artifacts after success:

- `TRAINING_COMPLETE`
- `TRAINING_STATUS.json` (`COMPLETE`)
- `training_summary.json`
- `run_card.json`
- `config_snapshot.yaml`
- `adapter_config.json` + adapter weights

If the directory already has adapter artifacts, training refuses unless you pass `--force-overwrite-output` (intentional only).

Incomplete/failed runs write `TRAINING_INCOMPLETE` / `TRAINING_FAILED` and must not be shipped.

---

## Phase 5 — Evaluation

Same prompts, generation settings, and rubric as baseline:

```bash
!python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base,adapter \
  --adapter-path training/adapters/runs/colab_qlora_pilot \
  --execute \
  --i-understand-this-loads-models
```

Optional heuristic (no model load):

```bash
!python -m training.scripts.score_generations --help
```

Score with `docs/FINE_TUNING_EVAL_RUBRIC.md` and decide using `docs/ADAPTER_ACCEPTANCE_CRITERIA.md`.

Loss curves are diagnostics only.

---

## Phase 6 — Human review

Inspect held-out generations for:

- personality (professional + calibrated wit; no Marvel imitation)
- reliability / correctness
- tool honesty (no fabricated calculator/time/plugin/file/search results)
- sarcasm calibration (off for serious / safety / emotional slices)
- hallucination / overconfidence
- verbosity and answer-first behavior

---

## Phase 7 — Decision

| Label | Meaning |
|-------|---------|
| **KEEP** | Clear net improvement; no hard-reject regressions |
| **ITERATE** | Personality improved but reliability/regression issues remain |
| **REJECT** | Unacceptable regressions or hard-reject triggers |

---

## Phase 8 — Deployment (only after KEEP)

1. Download/copy the accepted adapter directory off Colab if needed.
2. Confirm `TRAINING_COMPLETE` exists.
3. Enable only intentionally in `config/settings.txt`:

```text
ADAPTER_ENABLED=true
ADAPTER_PATH=training/adapters/runs/colab_qlora_pilot
```

4. Restart Zoe. Default remains **adapter OFF**.

### Rollback

```text
ADAPTER_ENABLED=false
```

Base model weights are never overwritten by training (adapter-only PEFT save).

---

## Expected resource notes (not measured)

| Item | Label | Note |
|------|-------|------|
| Colab T4/L4 VRAM for 3B QLoRA | EXPECTED | Feasible with 4-bit + grad checkpoint + batch 1 |
| Adapter disk size | EXPECTED | Tens of MB (PEFT), not full 3B weights |
| Train duration (1 epoch, Sprint 26 balanced → pilot split) | EXPECTED | Often tens of minutes on T4-class; varies |
| First-run HF download | EXPECTED | Several GB for Qwen2.5-3B-Instruct |

Do not treat these as measured benchmarks.

---

## Absolute stop rules

- Do not train without user confirmation.
- Do not enable `ADAPTER_ENABLED` without KEEP + human review.
- Do not use held-out data for training.
- Do not accept an adapter based on training loss alone.
