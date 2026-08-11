# Zoe Fine-Tuning Guide

**Status:** Engineering-complete for **Google Colab GPU QLoRA**; **no adapter trained**  
**Base model:** `Qwen/Qwen2.5-3B-Instruct`  
**Canonical config:** [`training/config/colab_qlora.yaml`](../training/config/colab_qlora.yaml)  
**Colab runbook:** [`docs/COLAB_FINE_TUNING_RUNBOOK.md`](COLAB_FINE_TUNING_RUNBOOK.md)  
**Readiness:** [`docs/FINAL_FINE_TUNING_READINESS.md`](FINAL_FINE_TUNING_READINESS.md) · [`docs/SPRINT26_FINAL_READINESS.md`](SPRINT26_FINAL_READINESS.md) (**92%** — waiting for Colab confirmation)  
**Checklist:** [`docs/FINAL_FINE_TUNING_CHECKLIST.md`](FINAL_FINE_TUNING_CHECKLIST.md)  
**Canonical clean SFT for first FT:** `training/data/clean/sft_sprint26_balanced.jsonl`

CPU fine-tuning is **not supported**.

---

## Why fine-tune Zoe?

Fine-tuning is for behaviors that are awkward to enforce only with prompts:

- consistent **Zoe personality** (professional + intelligent + fun + confident + witty)
- stronger **instruction adherence** and structured output
- better **grounded** answers when context is provided
- clearer **refusal / uncertainty** habits
- improved style for coding explanations and project analysis

### What fine-tuning will change

- How the LLM **phrases** and prioritizes content within a turn
- Preference for Zoe’s voice over generic assistant voice

### What remains outside the model

**Fine-tuning is not a replacement for Zoe’s tools, memory, retrieval, routing, or deterministic systems.**

Still owned by software:

- calculator / datetime / timezone tools
- plugin routing and sandboxing
- agent planning orchestration
- Chroma memory / RAG retrieval
- security checks and path guards
- conversation history persistence

The trained adapter should make Zoe *compose* better—not reinvent tool execution.

---

## Personality specification

Canonical doc: [`docs/ZOE_PERSONALITY.md`](ZOE_PERSONALITY.md)  
Behavior matrix: [`docs/ZOE_PERSONALITY_BEHAVIOR_MATRIX.md`](ZOE_PERSONALITY_BEHAVIOR_MATRIX.md)  
Eval rubric: [`docs/FINE_TUNING_EVAL_RUBRIC.md`](FINE_TUNING_EVAL_RUBRIC.md)  
Comparison protocol: [`docs/FINE_TUNING_COMPARISON_PROTOCOL.md`](FINE_TUNING_COMPARISON_PROTOCOL.md)  
Training plan: [`docs/FINE_TUNING_TRAINING_PLAN.md`](FINE_TUNING_TRAINING_PLAN.md)  
Dataset readiness: [`docs/FINE_TUNING_DATASET_READINESS.md`](FINE_TUNING_DATASET_READINESS.md)  
Sprint 24 pilot: [`docs/SPRINT24_FINE_TUNING_PILOT_REPORT.md`](SPRINT24_FINE_TUNING_PILOT_REPORT.md) · [`docs/SPRINT24_PILOT_RUNBOOK.md`](SPRINT24_PILOT_RUNBOOK.md) · [`docs/SPRINT24_DATASET_AUDIT.md`](SPRINT24_DATASET_AUDIT.md)  
Acceptance: [`docs/ADAPTER_ACCEPTANCE_CRITERIA.md`](ADAPTER_ACCEPTANCE_CRITERIA.md)  
Colab runbook: [`docs/COLAB_FINE_TUNING_RUNBOOK.md`](COLAB_FINE_TUNING_RUNBOOK.md)  
Checklist: [`docs/FINAL_FINE_TUNING_CHECKLIST.md`](FINAL_FINE_TUNING_CHECKLIST.md)  
**Final gate:** [`docs/FINAL_FINE_TUNING_READINESS.md`](FINAL_FINE_TUNING_READINESS.md)

Priority when traits conflict:

1. Safety → 2. Accuracy → 3. User intent → 4. Helpfulness → 5. Clarity → 6. Professionalism → 7. Humor → 8. Sarcasm

Humor is seasoning, not the meal.

---

## Dataset format

Qwen Instruct–compatible chat JSONL. Each training line:

```json
{
  "id": "ex_001",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "category": "coding",
    "difficulty": "medium",
    "source": "seed",
    "quality": 0.9,
    "personality_mode": "lightly_witty",
    "personality_required": true,
    "tool_required": false,
    "expected_behavior": "explain_bug_then_fix",
    "safety_sensitive": false
  }
}
```

**Critical:** `metadata` is for humans / validators only. Training code must pass **only** `messages` into the chat template. Metadata must never appear in model input.

Schema and validators live under `training/`.

### Categories

| Code | Name | Teaches |
|------|------|---------|
| `general_conversation` | A | Natural, concise, useful chat |
| `personality` | B | Wit / sarcasm calibration + serious mode |
| `tool_routing` | C | When to use / not use tools |
| `agent_planning` | D | Decomposition, sequencing, recovery |
| `memory` | E | What to remember / ignore |
| `retrieval_rag` | F | Use context; don’t invent |
| `coding` | G | Debug / implement without needless rewrites |
| `project_analysis` | H | Evidence → root cause → actions |
| `structured_output` | I | Format fidelity |
| `error_handling` | J | Honest failure + next step |

Correction records (preference / DPO later) use a separate schema under `training/data/corrections/`.

---

## Train / validation / held-out eval

```
training/data/
  raw/              # ingested candidates (not training-ready)
  clean/            # validated + privacy-filtered
  train/            # SFT training split
  validation/       # tuning / early stop
  held_out_eval/    # NEVER mixed into training
  corrections/      # bad → ideal pairs
  seeds/            # curated format exemplars
```

Held-out evaluation prompts must stay disjoint from train/validation.

---

## Evaluation methodology

Goal of the first experiment:

> Did the adapter make Zoe **better** on held-out tasks than the base model—not merely lower training loss?

Same prompts → base vs adapter. Metrics (see `training/evaluation/`):

- instruction adherence
- tool-routing accuracy
- structured-output validity
- grounding / hallucination rate
- memory-decision accuracy
- response quality
- personality score
- humor / sarcasm appropriateness
- regression rate vs known good behaviors

Personality eval must check:

1. Has personality when appropriate?  
2. Still professional?  
3. Sarcasm appropriate?  
4. Humor drops in serious contexts?  
5. Still accurate while witty?  
6. Avoids repetitive jokes?

**Do not run evaluation in this preparation sprint unless explicitly authorized later.**

---

## QLoRA architecture

Canonical Colab GPU config: `training/config/colab_qlora.yaml`  
Trainer: `training/scripts/train_qlora.py`  
Runbook: `docs/COLAB_FINE_TUNING_RUNBOOK.md`

Intended stack (install via optional `requirements-training.txt` on Colab GPU):

- Transformers
- PEFT (LoRA)
- TRL (SFTTrainer)
- BitsAndBytes (4-bit)
- datasets / accelerate / safetensors

Typical flow:

```
prepare_dataset → validate_dataset → inspect_dataset
      → train_qlora (explicit flag on Colab GPU) → evaluate → export adapter
```

Adapters save under `training/adapters/runs/` (gitignored weights; README only in repo).  
CPU fine-tuning is not supported.

---

## Training prerequisites (Colab)

- Google Colab NVIDIA GPU runtime
- Curated `train/` + `validation/` JSONL that pass `validate_dataset` (regenerate on Colab; gitignored)
- Optional deps from `requirements-training.txt`
- Explicit CLI flag (see below)—never import-time training

---

## How to prepare a dataset

```bash
# Export curated JSONL from banks (no training)
python -m training.data.curation.export_sprint23

# From repo root (when ready — not required for Sprint 23)
python -m training.scripts.prepare_dataset --help
python -m training.scripts.validate_dataset --path training/data/clean
python -m training.scripts.inspect_dataset --path training/data/clean
```

Teacher / synthetic pipeline stages (designed; not auto-accepted):

1. generate → 2. validate → 3. dedupe → 4. quality score → 5. human review → 6. accept/reject

Real Zoe history/telemetry must go through the **selective ingestion** interface with privacy filtering—never bulk-dump conversations into train.

---

## How to eventually train (Colab GPU)

Training is **disabled by default** and requires an explicit acknowledgement flag on a **CUDA** host:

```bash
python -m training.scripts.train_qlora \
  --config training/config/colab_qlora.yaml \
  --i-understand-this-starts-training
```

Without that flag, the script exits without loading weights or contacting Hugging Face for model download.  
Full procedure: [`COLAB_FINE_TUNING_RUNBOOK.md`](COLAB_FINE_TUNING_RUNBOOK.md).

---

## How to evaluate

```bash
python -m training.scripts.evaluate_baseline \
  --config training/config/colab_qlora.yaml \
  --split held_out_eval \
  --compare base,adapter \
  --adapter-path training/adapters/runs/colab_qlora_pilot \
  --execute \
  --i-understand-this-loads-models
```

Do not claim results without a run. Loss alone is never acceptance.

---

## How to load an adapter (after KEEP)

Optional runtime keys in `config/settings.txt` (default **off**):

```text
ADAPTER_ENABLED=true
ADAPTER_PATH=training/adapters/runs/colab_qlora_pilot
```

Requires `TRAINING_COMPLETE` + valid PEFT files. Rollback: set `ADAPTER_ENABLED=false`.

1. Load base `Qwen/Qwen2.5-3B-Instruct`
2. Attach PEFT adapter from the accepted run directory
3. Keep tool/memory/RAG pipeline unchanged
4. A/B compare on held-out eval before any default enablement

Production remains base-model-only until an accepted KEEP + explicit enablement.

---

## Safety against accidental training

- No training on `import training`
- No auto-download of training weights in prep scripts
- No auto-ingest of full conversation history
- No auto-upload of datasets
- CLI `zoe train` prints instructions only (does not train)
- Trainer refuses without `--i-understand-this-starts-training` and without CUDA
- Adapter directory does not contain trained weights in-repo

---

## Related documents

- `docs/COLAB_FINE_TUNING_RUNBOOK.md` — Colab operator procedure
- `docs/FINAL_FINE_TUNING_READINESS.md` — authoritative gate
- `docs/FINAL_FINE_TUNING_CHECKLIST.md` — checklist
- `docs/ZOE_PERSONALITY.md` — canonical personality
- `docs/ADAPTER_ACCEPTANCE_CRITERIA.md` — KEEP / ITERATE / REJECT
- `training/DATASET_READINESS.md` — data readiness status
