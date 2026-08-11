# Final Pre-Colab Gate

**Date:** 2026-08-11  
**Scope:** Static release-gate audit only (no tests, training, downloads, inference, git)  
**Canonical config:** `training/config/colab_qlora.yaml`  
**Runbook:** `docs/COLAB_FINE_TUNING_RUNBOOK.md`

---

## Gate checklist

| Check | Result | Evidence |
|-------|--------|----------|
| Canonical train source is Sprint 26 balanced | **PASS** | `data.clean_source` → `training/data/clean/sft_sprint26_balanced.jsonl` (786); prepare `--sprint26-balanced` |
| Held-out isolated from training | **PASS** | `eval_sprint26.jsonl` (110); manifest `leakage_ok: true`; no `s26_ho_*` IDs in balanced clean; prepare + train refuse overlap |
| Corrections not in held-out | **PASS** | `corrections_sprint26.jsonl` (51); no `corr_*` in held-out; no `s26_ho_*` in corrections |
| Qwen chat template matches runtime | **PASS** | Train: TRL messages + tokenizer chat template; eval/runtime: `apply_chat_template(..., add_generation_prompt=True)` |
| Assistant-only loss configured | **PASS** | `SFTConfig(assistant_only_loss=True)` in `train_qlora.py` |
| Config is CUDA / 4-bit QLoRA only | **PASS** | `load_in_4bit: true`; `safety.require_cuda` / `require_4bit: true`; trainer refuses otherwise |
| No CPU training fallback | **PASS** | Explicit refuse when CUDA missing; no CPU LoRA path |
| Cannot overwrite base model | **PASS** | PEFT `save_pretrained` to adapter `output_dir` only |
| Cannot accidentally overwrite adapters | **PASS** | Refuse if artifacts present unless `--force-overwrite-output` |
| Incomplete/failed adapters not loadable in prod | **PASS** | Runtime requires `TRAINING_COMPLETE`; refuses `TRAINING_INCOMPLETE` / `TRAINING_FAILED` / bad status |
| Adapter disable / rollback | **PASS** | Default `ADAPTER_ENABLED` unset/false; rollback = `ADAPTER_ENABLED=false` |
| Eval compares same prompts base vs adapter | **PASS** | Same held-out path + gen settings; `--compare base,adapter` |
| Held-out covers required slices | **PASS** | Tanglish (tl), coding (cd), personality (pe), general (gen), tool honesty (th); humor/sarcasm via `playful_sarcastic` + serious controls |
| Runtime does not require adapter | **PASS** | Base `Qwen/Qwen2.5-3B-Instruct` loads without adapter |
| Zoe usable if adapter rejected | **PASS** | Leave adapter off; base path unchanged |
| Runbook paths/commands match repo | **PASS** | Sprint 26 prepare/train/eval paths align with config + scripts |

---

## Blocking defects found and fixed this gate

1. **`training/config/colab_qlora.yaml` was invalid YAML** under `data:` (bad indentation) and still pointed held-out at `eval_sprint23.jsonl`.  
   **Fixed:** valid `data` block; `held_out_eval_path` → `eval_sprint26.jsonl`; `clean_source` → `sft_sprint26_balanced.jsonl`.

2. **`prepare_dataset --sprint26-balanced` still post-asserted against Sprint 23 held-out by default.**  
   **Fixed:** when `--sprint26-balanced` and default held-out path, assert against `eval_sprint26.jsonl`.

3. **Minor runbook/train hint drift** (~293-row note; prepare hint without Sprint 26 flag).  
   **Fixed:** align with Sprint 26 Colab path.

No dataset expansion performed.

---

## Canonical Colab path (after explicit user confirmation)

```bash
python -m training.data.curation.export_sprint26
python -m training.scripts.prepare_dataset --sprint26-balanced --pilot
python -m training.scripts.train_qlora --config training/config/colab_qlora.yaml --dry-check-config
python -m training.scripts.evaluate_baseline --config training/config/colab_qlora.yaml --split held_out_eval --compare base --execute --i-understand-this-loads-models
python -m training.scripts.train_qlora --config training/config/colab_qlora.yaml --i-understand-this-starts-training
python -m training.scripts.evaluate_baseline --config training/config/colab_qlora.yaml --split held_out_eval --compare base,adapter --adapter-path training/adapters/runs/colab_qlora_pilot --execute --i-understand-this-loads-models
```

---

## Final verdict

READY — START COLAB FINE-TUNING
