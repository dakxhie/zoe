# Adapters

PEFT / QLoRA adapter outputs live under `runs/<run_id>/`.

**No adapter in this repository is production-approved by default.**  
**Canonical first Colab run output:** `training/adapters/runs/colab_qlora_pilot/`

## Required run markers

After a successful Colab train, the run directory should contain:

| File | Meaning |
|------|---------|
| `TRAINING_COMPLETE` | Successful finish marker (**required** to enable in runtime) |
| `TRAINING_STATUS.json` | `COMPLETE` / `FAILED` / `RUNNING` |
| `TRAINING_INCOMPLETE` / `TRAINING_FAILED` | Failure / unfinished markers — never ship |
| `training_summary.json` | Metrics + config snapshot |
| `run_card.json` / `config_snapshot.yaml` | Reproducibility |
| `adapter_config.json` + weights | PEFT artifacts |

Refuse to treat a directory as shippable if incomplete/failed markers exist, or `TRAINING_COMPLETE` is missing.

## Enable / disable in runtime

Optional keys in `config/settings.txt` (default off):

```text
ADAPTER_ENABLED=false
ADAPTER_PATH=training/adapters/runs/colab_qlora_pilot
```

Rollback = disable the flag (base model unchanged).

## Gitignore

Local run weights are ignored (`training/adapters/runs/`).

See `docs/COLAB_FINE_TUNING_RUNBOOK.md`.
