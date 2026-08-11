# Coding Dataset Audit (Sprint 25)

**Status:** Elite coding instruction track curated  
**Export:** `training/data/clean/sft_coding_sprint25.jsonl`  
**Held-out:** `eval_coding_sprint25.jsonl`, `eval_tool_honesty_sprint25.jsonl`

---

## Objective

Teach Zoe to behave like a strong production engineer **with Zoe personality**:

- correctness, readability, maintainability
- security & error handling
- prototype vs production-ready distinction
- debugging: symptom → root cause → fix → why → edge case
- code review that explains important changes
- **tool honesty:** never claim ran/tested/searched/opened repo without tools

---

## Sources

| Source | Role |
|--------|------|
| Zoe curated coding banks (`training/data/curation/coding/`) | **Primary — used** |
| Public docs patterns (generic REST, Appwrite SDK names, React/JS/Python idioms) | Inspiration only |
| Large public code corpora (The Stack, etc.) | **Not ingested** |

No bulk GitHub scrape. No license-grey code dumps.

---

## Bank layout

| Module | Focus |
|--------|--------|
| `bank_core.py` | Languages, APIs, architecture, security, performance |
| `bank_debug.py` | Debugging narratives |
| `bank_review.py` | Code review / refactor guidance |
| `bank_tool_honesty.py` | Anti-fabrication of tool actions |
| `held_out.py` | Coding + tool-honesty evaluation |

---

## Quality gates applied

- Schema validation (`validate_paths`)
- Held-out ID / user-prompt leakage guards
- Serious mode for security / destructive topics
- Explicit “I have not run this” style honesty where relevant
- No Marvel imitation
- Assumptions stated when API/version-sensitive

---

## Balance note

Full coding bank is large by design. For the **first Colab QLoRA**, use:

`training/data/clean/sft_sprint25_balanced.jsonl`

which samples coding so it does not overwhelm legacy Zoe SFT.

---

## Remaining weaknesses

- Not every library version matrix is covered (state assumptions in answers)
- Multi-file repo refactors are underrepresented vs single-snippet tasks
- Live execution-verified examples are intentionally absent (tool honesty)
