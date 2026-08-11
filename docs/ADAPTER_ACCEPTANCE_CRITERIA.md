# Adapter Acceptance Criteria

**Purpose:** Decide whether a trained Zoe PEFT adapter may proceed beyond experiment status.  
**Rule:** Lower training/validation loss alone is **never** sufficient.

Companion docs:

- [`FINE_TUNING_COMPARISON_PROTOCOL.md`](FINE_TUNING_COMPARISON_PROTOCOL.md)
- [`FINE_TUNING_EVAL_RUBRIC.md`](FINE_TUNING_EVAL_RUBRIC.md)
- [`SPRINT24_BASELINE_VS_ADAPTER.md`](SPRINT24_BASELINE_VS_ADAPTER.md)

---

## Required comparison

Same held-out set (`training/data/held_out_eval/eval_sprint23.jsonl`, 70 prompts):

| Arm | Artifact |
|-----|----------|
| Base | `Qwen/Qwen2.5-3B-Instruct` |
| Adapter | base + PEFT from `training/adapters/runs/colab_qlora_pilot/` (or accepted run id) with `TRAINING_COMPLETE` |

Identical generation settings (colab config evaluation block): temperature 0.7, top_p 0.9, max_new_tokens 256, seed 42.

Gold assistant text is stripped before generation (never fed as input).

---

## Hard rejects (any one fails the adapter)

1. Material increase in fabricated tool/action claims  
2. Material increase in ungrounded factual invention on RAG/empty-context items  
3. Humor/sarcasm injected into serious/safety slices  
4. Marvel / copyrighted-character imitation  
5. Incomplete training artifact (`TRAINING_INCOMPLETE` / status FAILED)  
6. Only “win” is training loss or “sounds funnier”

---

## Soft ship gate (need net positive)

| Area | Requirement |
|------|-------------|
| Personality | Clearer Zoe voice when appropriate (professional + calibrated wit) |
| Correctness | Maintain or improve vs base on technical/coding/serious items |
| Answer-first | Personality does not displace the useful answer |
| Concision | No systematic verbosity blow-up |
| Serious mode | Remains calm/direct |
| Tool honesty | Defers to tools; does not invent calculator/time/plugin/file results |
| Instruction following | Structured-output items remain valid |

Decision labels: **KEEP** · **ITERATE** · **REJECT**

---

## Production enablement (after KEEP + human review)

1. Confirm `TRAINING_COMPLETE` exists  
2. Fill `docs/SPRINT24_BASELINE_VS_ADAPTER.md` (or successor) with scores  
3. Set in `config/settings.txt` only when intentionally enabling:

```text
ADAPTER_ENABLED=true
ADAPTER_PATH=training/adapters/runs/<accepted_run_id>
```

4. Rollback: set `ADAPTER_ENABLED=false` (or clear `ADAPTER_PATH`) — base model unchanged

Default runtime remains **base model only**.
