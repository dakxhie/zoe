# Final Fine-Tuning Checklist

**Canonical training target:** Google Colab + NVIDIA GPU + QLoRA  
**Canonical config:** `training/config/colab_qlora.yaml`  
**Authoritative readiness:** [`FINAL_FINE_TUNING_READINESS.md`](FINAL_FINE_TUNING_READINESS.md)  
**Operator runbook:** [`COLAB_FINE_TUNING_RUNBOOK.md`](COLAB_FINE_TUNING_RUNBOOK.md)

Use this as the gate list before any weight-loading training step.

---

## Engineering (completed in-repo)

- [x] Code audit complete (training pipeline + adapter hook; static)
- [x] Dataset audit complete (345 / 293 / 52 / 70 / 40 verified)
- [x] Held-out data protected (prepare + train guards)
- [x] Personality finalized (`docs/ZOE_PERSONALITY.md` + matrix + SFT modes)
- [x] Tool honesty protected (dataset + acceptance hard rejects)
- [x] Colab GPU configuration ready (`training/config/colab_qlora.yaml`)
- [x] QLoRA configuration ready (4-bit NF4, PEFT, ack-gated)
- [x] Training dependencies documented (`requirements-training.txt`)
- [x] Training guards verified statically (no-ack → SAFE MODE; CUDA/4-bit required)
- [x] Checkpoint handling ready (save steps + save_total_limit)
- [x] Adapter output handling ready (COMPLETE / INCOMPLETE / FAILED markers; overwrite refuse)
- [x] Evaluation protocol ready
- [x] Base-vs-adapter comparison ready
- [x] Rollback ready (`ADAPTER_ENABLED=false`)
- [x] Production adapter disabled by default
- [x] Deployment path documented
- [x] Colab runbook complete
- [x] Final readiness report complete

---

## External prerequisites (not code)

- [ ] Colab GPU runtime available
- [ ] Training deps installed on that runtime
- [ ] Hugging Face access/authentication if required for model download
- [ ] Pilot train/val splits regenerated on Colab (`prepare_dataset --pilot`)

---

## Final gate

- [ ] **USER CONFIRMED FINE-TUNING**

Leave unchecked until the user explicitly authorizes the Colab baseline → QLoRA → compare sequence.
