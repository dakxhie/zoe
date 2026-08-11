# Training package

Fine-tuning **preparation** for Google Colab GPU QLoRA. No adapters are trained by default.

See:

- [`docs/COLAB_FINE_TUNING_RUNBOOK.md`](../docs/COLAB_FINE_TUNING_RUNBOOK.md)
- [`docs/FINAL_FINE_TUNING_READINESS.md`](../docs/FINAL_FINE_TUNING_READINESS.md)
- [`docs/FINE_TUNING.md`](../docs/FINE_TUNING.md)
- [`docs/ZOE_PERSONALITY.md`](../docs/ZOE_PERSONALITY.md)
- [`DATASET_READINESS.md`](DATASET_READINESS.md)

**Canonical config:** `training/config/colab_qlora.yaml`

## Layout

```
training/
  config/           # Colab QLoRA + dataset configs (separate from Zoe runtime)
  data/             # raw / clean / train / validation / held_out_eval / corrections / seeds
  schema/           # Python schema + validation
  scripts/          # prepare / validate / inspect / train / evaluate
  evaluation/       # metrics + runner
  adapters/         # adapter run outputs (weights not committed)
```

## Hard rules

- Never start training by importing a module
- Never download model weights unless an explicit train/eval command with opt-in flags is used
- Never mix `held_out_eval` into training
- Never put `metadata` into model chat inputs
- Do not modify Zoe production prompts from this package
- CPU fine-tuning is not supported — Colab GPU QLoRA only
