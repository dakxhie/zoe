# Tanglish Dataset Audit (Sprint 25)

**Status:** Curated instruction track prepared — **no bulk corpus ingestion**  
**Export:** `training/data/clean/sft_tanglish_sprint25.jsonl`  
**Held-out:** `training/data/held_out_eval/eval_tanglish_sprint25.jsonl` (+ mixed coding set)

---

## Decision on external sources

| Source | Approx size | License (as published) | Useful for Zoe SFT? | Action |
|--------|------------:|------------------------|---------------------|--------|
| Tanglish-Corpus-185k (HF) | ~186k sentences | CC BY 4.0 | Language exposure only; raw social sentences ≠ instruction behavior | **Reference only — not ingested** |
| TamilTech-QA (HF/GitHub) | ~4.4k QA | MIT (code); dataset card / YouTube ToS provenance | Technical Tanglish QA style inspiration | **Reference only — not bulk-copied** |
| DravidianCodeMix | ~44k Ta-En comments | CC BY 4.0 | Sentiment/offense labels; noisy social text | **Rejected for SFT dump** (privacy/noise/offense risk) |

### Why not bulk ingest

- Raw comments teach register noise, not Zoe’s answer-first assistant behavior.
- Social corpora raise privacy / PII / offensive-content risk.
- Instruction tuning needs (user, assistant) pairs with tool-honesty and personality constraints.
- Avoid train contamination from unlabeled web text.

### Transformation method used instead

Hand-curated + controlled Zoe-style Tanglish instruction banks under:

- `training/data/curation/tanglish/`

Examples teach:

- casual Tanglish understanding
- romanization variation (epdi/eppadi, iruku/irukku, …)
- technical Tanglish
- Tanglish explanations / coding
- emotional & professional registers
- calibrated humor
- uncertainty / clarification
- tool honesty in Tanglish

### Privacy / duplication / quality

- No raw phone numbers/emails intentionally included
- Exact ID + held-out user-prompt leakage guards on export
- Romanization variants allowed (documented `variant_family`)
- Marvel / tool-hallucination claims avoided in gold assistants

---

## Counts (after export)

See `training/data/clean/sprint25_manifest.json` for live numbers.

**Recommended useful subset for first FT:** sampled into `sft_sprint25_balanced.jsonl` (~115 Tanglish rows) so Tanglish does not dominate legacy Zoe identity.

**Full Tanglish bank** retained for later expansion experiments.

---

## Rejected subset

- Entire raw Tanglish-Corpus-185k dump
- Entire DravidianCodeMix social dump
- Blind copies of TamilTech-QA rows (possible overlap with future public evals; style used as inspiration only)

---

## Attribution (reference)

If a future sprint selectively adapts CC BY material, attribute:

- Vishnu N — Tanglish-Corpus-185k (CC BY 4.0)
- Chakravarthi et al. — DravidianCodeMix (CC BY 4.0)
- Dheepak Karan — TamilTech-QA (inspect dataset card before any copy)
