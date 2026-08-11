# Base vs Fine-Tuned Comparison Protocol

## Goal

Decide whether a Zoe SFT/QLoRA adapter is **actually better** than `Qwen/Qwen2.5-3B-Instruct` on Zoe-relevant behavior—not whether training loss decreased.

## Models

| Arm | Description |
|-----|-------------|
| **Base** | `Qwen/Qwen2.5-3B-Instruct` with current Zoe chat template / decoding knobs |
| **Adapter** | Same base + PEFT adapter from `training/adapters/runs/<id>/` |

Keep decoding settings identical (`max_new_tokens`, temperature, top_p).

## Data

- Use **only** `training/data/held_out_eval/` prompts.  
- Never train on held-out IDs or near-duplicate user prompts.  
- Score with [`FINE_TUNING_EVAL_RUBRIC.md`](FINE_TUNING_EVAL_RUBRIC.md).

## Procedure

1. **Freeze** held-out JSONL + rubric version.  
2. Generate responses for **base** on all held-out prompts (strip final gold assistant message; generate anew).  
3. Generate responses for **adapter** on the same prompts.  
4. Blind-score (or dual-score) with the rubric.  
5. Compute aggregates + serious/witty slices + regression rate.  
6. Decision:

### Adopt adapter only if

See also: [`ADAPTER_ACCEPTANCE_CRITERIA.md`](ADAPTER_ACCEPTANCE_CRITERIA.md)

**Hard rejects:** tool-claim regressions, ungrounded RAG invention, jokes in serious/safety slices, Marvel imitation, incomplete/failed training artifacts, “loss went down” as sole evidence.

**Soft ship gate:**

- Net improvement on personality **and** helpfulness where intended  
- No material regression on correctness, grounding, tool awareness, safety, concision  
- Humor/sarcasm appropriateness does not degrade on serious items  
- Answer-first behavior preserved (personality does not displace the answer)  

### Reject / iterate if

- Witty everywhere (mode collapse)  
- Invents tool results more often  
- Ignores retrieval context more often  
- Safety/serious tone regressions  
- Only metric win is training loss  
- Systematic verbosity increase without quality gain  

## Non-goals

- Replacing calculator, datetime, plugins, memory, RAG, or routing with the LLM  
- Shipping prompt humor into production before this comparison passes  

## Recording

Write results under `training/adapters/eval_results_<run_id>.json` (gitignored patterns already cover local eval dumps).
