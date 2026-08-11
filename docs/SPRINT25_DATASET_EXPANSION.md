# Sprint 25 Dataset Expansion

**Date:** 2026-08-11  
**Scope:** Tanglish + elite coding tracks for final Colab QLoRA prep  
**Training:** NOT started · **Weights:** not downloaded · **Git:** no commit/push  

---

## Executive outcome

Expanded Zoe’s fine-tuning data in **two separated tracks**, preserved the original **345-row** Sprint 23 SFT file, added held-out suites, and produced a **balanced** training candidate for the first Colab run.

### Final decision

# READY FOR COLAB FINE-TUNING

No genuine dataset blockers remain for using the balanced Sprint 25 file in the existing Colab QLoRA pipeline (after user confirmation).

---

## Previous dataset size

| Asset | Count |
|-------|------:|
| Sprint 23 clean SFT | **345** (preserved at `training/data/clean/sft_sprint23.jsonl`) |
| Sprint 23 held-out | 70 |
| Corrections bank | 40 (unchanged; not auto-mixed) |

---

## Tanglish additions

| Asset | Count | Path |
|-------|------:|------|
| Full Tanglish train bank | **445** | `training/data/clean/sft_tanglish_sprint25.jsonl` |
| Tanglish held-out | **55** | `training/data/held_out_eval/eval_tanglish_sprint25.jsonl` |
| Tanglish+coding held-out | **25** | `training/data/held_out_eval/eval_tanglish_coding_sprint25.jsonl` |

Audit: `docs/TANGLISH_DATASET_AUDIT.md`  
External corpora (Tanglish-Corpus-185k, TamilTech-QA, DravidianCodeMix): **audited, not bulk-ingested**.

---

## Coding additions

| Asset | Count | Path |
|-------|------:|------|
| Full elite coding train bank | **575** | `training/data/clean/sft_coding_sprint25.jsonl` |
| Coding held-out | **75** | `training/data/held_out_eval/eval_coding_sprint25.jsonl` |
| Tool-honesty held-out | **25** | `training/data/held_out_eval/eval_tool_honesty_sprint25.jsonl` |

Audit: `docs/CODING_DATASET_AUDIT.md`

---

## Total dataset size

| Set | Count | Use |
|-----|------:|-----|
| Combined (all tracks) | **1365** | Full inventory / later experiments |
| **Balanced (recommended first FT)** | **630** | First Colab QLoRA |
| New held-out total | **180** | Eval only |
| Prior Sprint 23 held-out | **70** | Still protected |

---

## Train / validation / held-out

- Balanced clean file is the **source** for `prepare_dataset` on Colab (same split tooling as before).
- Held-out JSONL files must **never** be passed as train.
- IDs listed in `training/data/held_out_eval/held_out_ids_sprint25.txt`
- Leakage guards: OK on export (`leakage_ok: true`)

### Recommended prepare (Colab)

```bash
python -m training.data.curation.export_sprint25   # if regenerating from banks
python -m training.scripts.prepare_dataset \
  --input training/data/clean/sft_sprint25_balanced.jsonl \
  --pilot \
  --held-out training/data/held_out_eval/eval_sprint23.jsonl
# Additionally block Sprint 25 held-outs via guards during train (paths in colab config / audit)
```

Update train config `data.clean_source` / prepare input to the balanced file before the Colab run.

---

## Category / track distribution (balanced)

From `sprint25_manifest.json`:

| Track | Rows | % |
|-------|-----:|--:|
| legacy_s23 | 345 | ~54.8% |
| tanglish | 115 | ~18.3% |
| elite_coding | 170 | ~27.0% |

Within recommended band (legacy majority; Tanglish ~15–20%; coding ~20–27%).

Full banks remain available if a later experiment wants heavier Tanglish or coding.

---

## Source / licensing

- Sprint 23 + Sprint 25 banks: Zoe curated (original)
- External Tanglish resources: reference-only (see Tanglish audit)
- No Stack/GitHub bulk dump

---

## Quality gates

- Schema validation: **errors=0** on exported JSONL
- Held-out leakage: **none detected**
- Sprint 23 file: **not overwritten**
- Tool-honesty examples included (train + held-out)
- Personality: professional-first; humor sparse; serious for security
- Warnings exist (mostly soft quality heuristics on long coding answers) — not blockers

---

## Rejected data

- Raw social Tanglish corpora dumps
- Blind TamilTech-QA row copies
- Synthetic prefix-multiplication duplicates (removed from Tanglish framing)

---

## Leakage controls

- Separate held-out files + ID list
- `assert_train_not_held_out` against Sprint 23 + Sprint 25 held-outs on export
- Train scripts already refuse held-out path overlap

---

## Personality balance

Legacy Sprint 23 personality mix preserved as majority of balanced set.  
New tracks mostly professional / lightly witty; sarcastic sparse; serious for safety.

---

## Tool-honesty coverage

- Dedicated coding tool-honesty bank + 25 held-out prompts
- Tanglish examples that refuse fake “I ran/tested/repo” claims
- Acceptance criteria already hard-reject tool fabrication regressions

---

## Remaining weaknesses

- Coding warnings volume (verbosity heuristic) — monitor in human eval
- Appwrite/library answers state assumptions; not version-pinned exhaustive
- Balanced set samples banks — full Tanglish/coding depth deferred to later FT rounds if needed
- Corrections bank still not auto-merged (intentional)

---

## Files to know

| Path | Role |
|------|------|
| `training/data/clean/sft_sprint23.jsonl` | Preserved original |
| `training/data/clean/sft_sprint25_balanced.jsonl` | **First Colab train source** |
| `training/data/clean/sft_tanglish_sprint25.jsonl` | Full Tanglish bank |
| `training/data/clean/sft_coding_sprint25.jsonl` | Full coding bank |
| `training/data/clean/sprint25_manifest.json` | Counts + validation |
| `docs/TANGLISH_DATASET_AUDIT.md` | External source audit |
| `docs/CODING_DATASET_AUDIT.md` | Coding track audit |

---

## Ready?

**READY FOR COLAB FINE-TUNING**

Next meaningful step remains the user-confirmed Colab GPU QLoRA experiment using the balanced Sprint 25 dataset + existing `colab_qlora.yaml` pipeline (update prepare input to the balanced file).

**STOP — do not train from this pass.**
