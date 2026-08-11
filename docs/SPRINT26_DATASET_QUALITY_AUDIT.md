# Sprint 26 Dataset Quality Audit

**Date:** 2026-08-11  
**Method:** Static inspection only (no training, no weight downloads, no tests)  
**Preserved:** `sft_sprint23.jsonl` (345), `sft_sprint25_balanced.jsonl` (630)

---

## Executive findings

Sprint 25 expanded coverage successfully but introduced **template-driven assistant near-duplicates** in the elite coding bank (81 exact assistant dup groups in the full 575-row bank) and a **Tanglish bank skewed heavily to coding topics** (~304/445 coding category).

Sprint 26 response: **quality over quantity**

- Deduped coding assistants before sampling  
- Diversified Tanglish selection (prefer non-coding)  
- Added curated gap-fill for hard debugging, tool honesty, personality calibration, natural Tanglish  
- New balanced file: `sft_sprint26_balanced.jsonl` (**786** rows, **0** assistant dup groups, schema **errors=0 warnings=0**)

---

## Audit checklist results

| # | Check | Finding | Action |
|---|-------|---------|--------|
| 1 | Exact user duplicates | None in S23 / bal25 / S26 | NO ACTION |
| 2 | Near/exact assistant duplicates | Severe in S25 coding bank (template angles) | Deduped in S26 |
| 3 | Personality contradictions | Rare; S25 coding lacked witty/sarcastic modes | Added calibrated personality + when-not-to-joke |
| 4–5 | Weak / generic answers | Some S25 coding advice strings reused | Prefer unique longer answers |
| 6–9 | Tanglish quality | Repetitive subject×intent patterns; coding-heavy; mostly natural code-switch | Diversified pick + S26 Tanglish gap-fill |
| 10–11 | Unrealistic / bad practices | Few; SQL concat examples correctly taught as bad in S26 | Keep security serious |
| 12–13 | Fake execution / invented APIs | No claim flags in S25 exports; S26 adds explicit refusals | Strengthened |
| 14–15 | Verbosity / under-explain | S25 coding median ~198 chars (OK); some templated short clones | Deduped |
| 16–18 | Humor/sarcasm calibration | Sarcasm low; risk of missing “when not to joke” | Added serious + witty examples |
| 19 | Generic chatbot voice | Mostly avoided in curated banks | Corrections attack filler |
| 20 | Personality overfitting | Full S25 combined would overweight coding (42%) | S26 balanced ~44% legacy |

---

## Sprint 25 composition issues (pre-fix)

| Asset | Issue |
|-------|-------|
| `sft_coding_sprint25.jsonl` | Combinatorial templates → 81 assistant dup groups |
| `sft_tanglish_sprint25.jsonl` | ~68% coding category; casual/personality thin |
| `sft_sprint25_balanced.jsonl` | Good track mix, but inherited 30 assistant dup groups from coding sample |

---

## External Tanglish corpora

| Source | License | Use |
|--------|---------|-----|
| Tanglish-Corpus-185k | CC BY 4.0 | Reference only — **not ingested** |
| TamilTech-QA | MIT/code; dataset card provenance | Reference only — **not bulk-copied** |
| DravidianCodeMix | CC BY 4.0 | Rejected for SFT dump (noise/offense/privacy) |

Reason: raw social text ≠ Zoe instruction behavior; privacy/noise risks.

---

## Sprint 26 outputs

| File | Count | Role |
|------|------:|------|
| `sft_sprint26_balanced.jsonl` | **786** | Recommended Colab train source |
| `eval_sprint26.jsonl` | **110** | Held-out |
| `corrections_sprint26.jsonl` | **51** | Corrections bank |
| `held_out_ids_sprint26.txt` | 110 | Blocklist |

### Balanced track mix (approx.)

| Track | % |
|-------|--:|
| legacy_s23 | ~44% |
| tanglish | ~24% |
| elite_coding | ~29% |
| personality / tool honesty (gap) | ~3% |

### Personality modes (balanced)

| Mode | % |
|------|--:|
| professional_neutral | ~66% |
| lightly_witty | ~11% |
| playful_sarcastic | ~3% |
| serious_no_humor | ~20% |

Professional-first; sarcasm scarce by design.

---

## Leakage

`leakage_ok: true` against Sprint 26 held-out and prior Sprint 23/25 held-outs.

---

## Remaining dataset risks (non-blocking)

1. Full S25 coding/tanglish banks still contain template duplication if used raw — **do not train on full combined 1365 for first FT**.  
2. Tanglish share (~24%) slightly above the old 15–20% guidance — acceptable for fluency goal; monitor personality eval.  
3. Appwrite examples intentionally refuse invented APIs — coverage depends on user-provided SDK snippets.  
4. Corrections bank is separate (not auto-merged into SFT) — intentional.

---

## Recommendation

Use **`sft_sprint26_balanced.jsonl`** for the final Colab QLoRA prepare step.
