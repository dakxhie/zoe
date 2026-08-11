# Zoe Fine-Tuning Readiness & Capability Audit

**Document type:** Authoritative fine-tuning readiness report  
**Date:** 2026-08-08  
**Method:** Read-only static repository analysis (no tests, training, git, or code changes)  
**Reported suite status:** 249 passed, 5 skipped, 0 failed  
**Product version:** v2.11 (Sprint 21 complete; stabilization/hardening done)

---

## Executive snapshot

| Question | Answer |
|----------|--------|
| Is Zoe ready to **prepare** for fine-tuning? | **Yes** |
| Is Zoe ready to **train today**? | **No** |
| Biggest missing piece | **Curated training dataset + training/eval infrastructure** (`train` CLI is a placeholder; no PEFT/LoRA/datasets tooling in repo) |
| Current status label | **PRE-FINETUNE** |
| Fine-tuning readiness | **38%** (justified below) |

Zoe is a **software-first** local assistant: most intelligence lives in deterministic routing, plugins, retrieval, memory heuristics, and agent orchestration. The LLM (`Qwen/Qwen2.5-3B-Instruct`) mainly **composes answers** after tools/context are assembled. Fine-tuning can improve style, instruction adherence, and grounded answering—but will **not** replace calculator, timezone, plugin management, Chroma retrieval, or security checks.

---

# 1. Complete current-state audit

## 1.1 Architecture map (verified)

```
User (CLI / Desktop / Voice)
        │
        ▼
brain/pipeline.generate_response
        │
        ├─ profile reply (rule memory) ─────────────► return (no LLM)
        ├─ save_memory / acknowledgement ───────────► return (no LLM)
        ├─ tools.executor.execute_tool ─────────────► return (no LLM)
        │     └─ plugins.manager route + builtins
        └─ agents.orchestrator.orchestrate_chat_turn
              ├─ intent / plan / analysis / autonomous / supervisor
              ├─ empty-index / vision short-circuits
              ├─ execute_agent_plan + fusion
              └─ brain.context._build_chat_messages
                    │
                    ▼
              brain.generation.load_model + generate_text
                    │
                    ▼
              post-turn memory finalize + history + telemetry
```

## 1.2 Subsystem inventory

### Base / local model & loading
| | |
|--|--|
| **Does** | Loads Hugging Face causal LM once per process; generates chat replies |
| **How** | `AutoTokenizer` + `AutoModelForCausalLM.from_pretrained`; CUDA `device_map="auto"` + float16, else CPU float32 |
| **Files** | `brain/generation.py`, `config/settings.txt` (`MODEL_NAME`), `config/default.yaml` model.name overlay |
| **Maturity** | High for inference; none for training |
| **Strong** | Lazy load; process cache; chat template when present |
| **Weak** | No quantization; no PEFT; print-based load UX; fixed generation knobs |
| **FT relevant** | **Yes** — this is the fine-tune target |

### Tokenizer / chat template
| | |
|--|--|
| **Does** | Formats role messages via tokenizer chat template |
| **How** | `apply_chat_template(..., add_generation_prompt=True)` if `chat_template` exists; else last user content only |
| **Files** | `brain/generation.py` `_format_prompt` |
| **Maturity** | Adequate for Instruct models |
| **Strong** | Correct Instruct path for Qwen |
| **Weak** | Fallback drops multi-turn structure if template missing |
| **FT relevant** | **Yes** — training data must match this template |

### Inference pipeline
| | |
|--|--|
| **Does** | End-to-end turn: memory/tools/orchestrate → LLM → history |
| **How** | Short-circuits before LLM whenever possible |
| **Files** | `brain/pipeline.py` |
| **Maturity** | High |
| **Strong** | Clear precedence: profile → memory ack → tools → agents → LLM |
| **Weak** | LLM only sees assembled messages; no tool-call schema |
| **FT relevant** | **Yes** — defines when model is invoked |

### System prompts / context construction
| | |
|--|--|
| **Does** | Builds system + history + user messages with retrieved context |
| **How** | Multiple prompt builders: base / web / vision / analysis |
| **Files** | `brain/context.py` |
| **Maturity** | Medium–high for RAG grounding; low for personality |
| **Strong** | Context caps (6000 chars); retrieval-first empty index; analysis injection |
| **Weak** | Personality doc **not loaded**; prompts scattered; generic “You are Zoe” |
| **FT relevant** | **Critical** — prompt consistency precedes training |

### RAG / retrieval / code / PDF / notes / web
| | |
|--|--|
| **Does** | Semantic search over Chroma collections + web fetch |
| **How** | `all-MiniLM-L6-v2` embeddings; collections `zoe_notes`, `zoe_memory`, `zoe_documents`, `zoe_code`, `zoe_history` |
| **Files** | `rag/*`, `pdf/*`, `codebase/*`, `memory/retriever.py`, `web/*`, `core/chroma.py` |
| **Maturity** | High (software) |
| **Strong** | Dedup indexing; empty-index UX; web cache |
| **Weak** | Quality depends on index freshness; embedder separate from chat model |
| **FT relevant** | **Mostly no** — keep as RAG; FT should learn to *use* context, not memorize corpora |

### Memory stack (detect → score → reinforce → forget → store → profile)
| | |
|--|--|
| **Does** | Decides what to store; reinforces; builds profile replies |
| **How** | Rule phrases + heuristics; Chroma persistence |
| **Files** | `memory/detector.py`, `memory/inference.py`, `memory/intelligence/*`, `memory/store.py` |
| **Maturity** | Medium–high rules; no learned classifier |
| **Strong** | Explicit forget filters; PROJECT before IDENTITY; get_collection mock compat |
| **Weak** | False positive/negative risk; duplicated regexes; post-turn review every chat |
| **FT relevant** | **Partial** — FT can improve *phrasing* of memory acks / profile answers; decisions should stay coded unless carefully labeled |

### History / summarization
| | |
|--|--|
| **Does** | JSONL history, sessions, stats, LLM summary after 40 messages |
| **How** | `conversation/*`; summarizer calls same chat model |
| **Files** | `conversation/history.py`, `storage.py`, `summarizer.py`, `session.py` |
| **Maturity** | High storage; medium summarization quality (model-dependent) |
| **FT relevant** | Summaries = possible future data source (privacy-sensitive) |

### Tools / routing / plugins
| | |
|--|--|
| **Does** | Deterministic tool answers; plugin priority routing |
| **How** | Plugin matchers → executor; filesystem legacy path |
| **Files** | `tools/*`, `plugins/*` |
| **Maturity** | High |
| **Strong** | Calculator AST-safe; NL math; timezone None on unknown; sandbox hooks |
| **Weak** | Shallow sandbox; no model tool-calling protocol |
| **FT relevant** | Routing is **code**; FT might teach *when to defer to tools* if Zoe ever emits tool calls—today tools short-circuit **before** LLM |

### Agents / autonomous / analysis
| | |
|--|--|
| **Does** | Intent, multi-step plans, fusion, specialists, autonomous project tasks |
| **How** | Rule intent + plan steps; autonomous task graph for heavy goals |
| **Files** | `agents/*`, `agents/tasks/*`, `agents/specialists/*` |
| **Maturity** | Medium–high engineering; behavior still heuristic |
| **Strong** | Multi-tool no longer hijacked by autonomous; fusion stubs |
| **Weak** | Large orchestrator; plans not LLM-generated |
| **FT relevant** | **Medium** — FT could improve final report writing; planning stays code for now |

### Vision / voice
| | |
|--|--|
| **Vision** | BLIP caption + EasyOCR (`vision/*`) — separate models, not Qwen |
| **Voice** | Optional Whisper STT (`voice/*`) — separate |
| **FT relevant** | Not for Qwen SFT; multimodal FT is out of scope for first run |

### CLI / doctor / config / lifecycle
| | |
|--|--|
| **Files** | `cli/main.py`, `core/doctor.py`, `core/diagnostics.py`, `deployment/*`, `core/config.py` |
| **Maturity** | High ops surface |
| **FT relevant** | Indirect — protects regression during FT experiments |
| **Note** | `cli train` prints *“Training will be added later.”* — **VERIFIED** |

### Persistence / logging / errors
| | |
|--|--|
| **Stores** | Chroma, `data/history/`, `data/telemetry/`, plugin `enabled.json`, web cache |
| **Logging** | DEBUG for optional failures post-hardening |
| **FT relevant** | Telemetry/history are **sensitive** and not training-ready as-is |

---

# 2. Current model analysis

## Verified model identity

| Property | Value | Evidence |
|----------|-------|----------|
| Model name | `Qwen/Qwen2.5-3B-Instruct` | `config/settings.txt` |
| Approx. size | ~3B parameters (Instruct) | Model card convention; name encodes size |
| Architecture | Causal LM (HF `AutoModelForCausalLM`) | `brain/generation.py` |
| Tokenizer | `AutoTokenizer.from_pretrained(model_name)` | same |
| Context length | **UNKNOWN in-repo** (not configured; relies on model default) | No `max_length` / rope settings in code |
| Quantization | **None** (fp16 GPU / fp32 CPU) | `_torch_dtype`, `from_pretrained` args |
| Inference backend | PyTorch + Hugging Face Transformers (+ accelerate on GPU) | `requirements.txt`, generation path |
| Device | CUDA if available else CPU | `_use_cuda()` |
| Loading strategy | Lazy singleton; `_model_load_count` | `load_model()` |
| Caching | Process-global `tokenizer` / `model` | same |
| Generation | `do_sample=True`, `temperature=0.7`, `top_p=0.9`, `max_new_tokens=256` default | `generate_text` |
| Chat template | Used when tokenizer provides one | `_format_prompt` |
| System prompt | Minimal “You are Zoe…” + context variants | `brain/context.py` |
| LoRA / QLoRA / PEFT | **Not present** | No peft/bitsandbytes/trl in requirements; no training modules |
| Training scripts | **Not present** (`train` placeholder) | `cli/main.py` |
| Dataset tooling | **Not present** | No dataset/ dirs or trainers |
| Eval for FT | **Not present** (pytest/regression ≠ FT eval) | `tests/`, `tests/regression/` |

## YAML model config

`config/default.yaml` has `model.name: ""` — effective name comes from legacy `settings.txt` via overlay (`deployment/config.py`). **VERIFIED.**

## Separate models (not FT targets for Sprint 22)

| Model | Role | File |
|-------|------|------|
| `all-MiniLM-L6-v2` | Embeddings for RAG/memory | `rag/embedder.py` |
| `Salesforce/blip-image-captioning-base` | Image captions | `vision/caption.py` |
| Whisper `base` | STT (optional) | `voice/recognizer.py` |

## Responsibility split

| Layer | Owns |
|-------|------|
| **Zoe software** | Routing, tools, plugins, retrieval, memory decisions, agent plans, empty-index, doctor, persistence |
| **Qwen 3B Instruct** | Natural-language reply given system/context/history/user; conversation summarization text |
| **Other models** | Embeddings, captions, STT |

---

# 3. What fine-tuning can actually improve

## A. GOOD CANDIDATES FOR FINE-TUNING

| Capability | Why (repo evidence) |
|------------|---------------------|
| Response style / personality | `docs/personality.md` exists but **is not loaded**; runtime prompt is generic |
| Grounded answering from context | System prompts already say “use provided context”; FT can harden compliance |
| Concise helpful coding explanations | Coding is a product goal; model still free-form |
| Project-analysis report writing | Analysis injects structured context; quality of prose is model-side |
| Summarization style | `conversation/summarizer.py` uses same LLM with section format |
| Instruction following on Zoe-specific conventions | Scattered prompt rules could be internalized carefully |
| Multilingual Tanglish/Tamil style | Documented personality goal; not enforced in code |

## B. BETTER HANDLED BY RAG / RETRIEVAL

- Notes, PDFs, code index, web pages, conversation semantic search  
- User project files and changing facts  
- Anything in Chroma that updates without retraining  

## C. BETTER HANDLED BY NORMAL CODE

- Calculator (`tools/calculator.py` AST)  
- Datetime/timezones  
- Plugin enable/reload/permissions  
- Filesystem list/read/find  
- Empty-index detection  
- Doctor/diagnostics  
- Intent keyword routing & planner steps  
- Memory forget filters for calculator/greetings (deterministic)  

## D. SHOULD NOT BE FINE-TUNED

- Security / path validation / sandbox policy  
- Exact arithmetic  
- Embedding model (separate purpose)  
- Memorizing private user history or notes as weights  
- Replacing plugin routing with opaque model guesses (unless a real tool-call protocol is designed first)  
- Vision/OCR/STT models in the first Qwen FT experiment  

---

# 4. Current Zoe effectiveness (evidence-based scores)

Scores are **engineering maturity assessments**, not measured LLM benchmarks. Labels: **VERIFIED** / **STRONG EVIDENCE** / **PARTIAL EVIDENCE** / **UNKNOWN**.

| Capability | Score | Evidence label | Evidence |
|------------|------:|----------------|----------|
| General conversation | 70 | STRONG | Full chat path + Instruct model; personality not injected |
| Instruction following | 55 | PARTIAL | Minimal system rules; no FT eval set |
| Tool routing | 88 | VERIFIED | Plugin registry + tests for calculator/clock routes |
| Tool execution | 90 | VERIFIED | Tools short-circuit LLM; AST calculator; timezone None |
| Agent planning | 72 | STRONG | Rule planner + fusion; not LLM planner |
| Agent execution | 70 | STRONG | Executor/recovery/verifier present; orchestrator complexity |
| Memory | 75 | STRONG | Full intelligence pipeline + green memory tests |
| Long-term personalization | 60 | PARTIAL | Profile builder + notes; personality doc unused |
| Retrieval/RAG | 85 | VERIFIED | Multi-collection Chroma + empty-index + retrieval-first |
| Code assistance | 65 | PARTIAL | Code index/search strong; generation quality UNKNOWN |
| Project analysis | 70 | STRONG | Guaranteed context injection path tested |
| Structured output | 50 | PARTIAL | Summary section format requested; brittle parse |
| Plugin system | 88 | VERIFIED | Builtins + extensions + lifecycle |
| Error recovery | 72 | STRONG | Agent recovery; doctor never raises; DEBUG logging |
| Context management | 78 | STRONG | Truncation, fusion ranking, history limit 20 |
| Conversation continuity | 80 | VERIFIED | Persistent history + restore |
| Model efficiency | 55 | PARTIAL | 3B fp16 OK; no quant; max_new_tokens 256 |
| Overall assistant readiness | 82 | STRONG | v2.11 + green suite + RC docs |
| **Fine-tuning readiness** | **38** | VERIFIED | No train infra/data/eval; placeholder CLI |

### Fine-tuning readiness breakdown

| Dimension | Score | Notes |
|-----------|------:|-------|
| Base model readiness | 75 | Clear HF Instruct target, load path solid |
| Dataset readiness | 10 | No curated FT dataset |
| Data collection readiness | 25 | History/telemetry exist but raw/sensitive |
| Prompt/template readiness | 45 | Template OK; prompts inconsistent/personality unused |
| Training infrastructure | 5 | Placeholder `train`; no PEFT |
| Evaluation readiness | 30 | Pytest/regression ≠ FT metrics |
| Hardware readiness | 40 | Colab/CUDA path assumed; VRAM UNKNOWN in-repo |
| Deployment readiness | 70 | Profiles, doctor, shutdown exist |
| Regression protection | 85 | 249/5/0 reported; targeted pytest policy |
| Observability | 55 | Local telemetry; not training-oriented |

**Fine-Tuning Readiness: 38%**  
Weighted judgment: strong product shell (high), zero training stack (near zero), weak dataset/prompt unification (low). Average of dimensions ≈ 44; discounted to **38%** because missing dataset + trainer are hard blockers (P0).

---

# 5. Actual weaknesses (prioritized)

## P0 — blocks fine-tuning

1. **No training implementation** — `cli/main.py` `train()` is a placeholder.  
2. **No PEFT/LoRA/QLoRA/TRL/datasets dependencies or scripts.**  
3. **No curated, labeled fine-tuning dataset** (or schema/versioning).  
4. **No FT-specific evaluation harness** (tool-selection accuracy, groundedness, style rubrics).

## P1 — should fix before first training run

1. **`docs/personality.md` not loaded at runtime** (`PROJECT_STATUS.md` Known Limitations) — training without freezing the served prompt/persona will waste runs.  
2. **Prompt construction scattered** across analysis/web/vision/base builders — need one canonical prompt policy for dataset labels.  
3. **No tool-calling format** — model never emits structured tool calls; decide whether FT targets *answer style* only (recommended for v1) vs future tool JSON.  
4. **Privacy policy for history/memory → dataset** — `data/history`, memories, notes are personal.  
5. **Context length / truncation policy undocumented for training** — `MAX_CONTEXT_CHARS=6000` vs model window UNKNOWN.  
6. **Generation hyperparameters hardcoded** — temperature 0.7 / top_p 0.9 must be matched or recorded in experiment config.

## P2 — useful improvements

1. Duplicated memory heuristics → hard to label consistently.  
2. Post-turn memory review cost every turn.  
3. Summarizer section parsing brittle.  
4. Orchestrator complexity (harder to attribute failures to model vs software).  
5. No quantization for cheaper local eval of adapters.

## P3 — optional / future

1. Voice shutdown / Chroma close.  
2. Preference tuning (DPO) after SFT.  
3. Multimodal FT.  
4. Teaching-mode quizzes (roadmap aspirational; not core FT).

### Hallucination / grounding risks

- Base prompt allows “If the answer is not in the context, answer normally” — **encourages unconstrained answers** when retrieval misses (**PARTIAL EVIDENCE** of hallucination risk).  
- Web/vision prompts are stricter (“prefer sources / state not found”) — inconsistency across routes.

### Places learned behavior could replace rules (carefully)

- Softer memory detection beyond keyword lists.  
- Style/personality instead of hoping Instruct defaults.  
**Dangerous to replace:** calculator, timezone resolution, plugin permissions, empty-index gates.

---

# 6. Fine-tuning readiness narrative

Zoe is **product-ready as a local assistant stack**, but **research-unready for training**.

What exists: stable inference, green regression, retrieval, tools, agents, memory, RC docs.  
What does not: datasets, trainers, FT metrics, experiment tracking, adapter load path.

**Missing pieces (exact):**

1. Dataset schema (JSONL chat messages compatible with Qwen template).  
2. Collection/cleaning pipeline with PII scrubbing.  
3. Train/val/test splits + frozen regression prompts.  
4. Training entrypoint (e.g. QLoRA via PEFT+TRL) replacing placeholder `train`.  
5. Adapter save/load integrated with `load_model()` (optional path).  
6. Eval scripts for groundedness + style + non-regression of tool short-circuits.  
7. Hardware budget doc for 3B QLoRA on Colab vs local GPU.

---

# 7. Training data audit (what exists TODAY)

| Source | Location | Classification | Notes |
|--------|----------|----------------|-------|
| Chat history JSONL | `data/history/` | **potentially sensitive**; usable after cleaning | Contains user conversations |
| History summary | `data/history/summary.json` | sensitive / eval-only | Sample looks like **test fixture content** (“User likes wolves”) |
| Telemetry JSONL | `data/telemetry/runtime.jsonl` | **unsuitable** for SFT | Events like shutdown; not dialogues |
| Notes | `data/notes/about_me.md` | RAG corpus / **not** chat SFT | Personal profile facts |
| PDFs | `data/pdfs/` | RAG only | `.gitkeep` / user content |
| Web cache | `storage/web_cache/` | unsuitable / sensitive | Scraped pages |
| Chroma DB | `storage/chroma/` | unsuitable as raw FT text | Vectors + docs; private |
| Pytest fixtures / cases | `tests/**` | **useful for evaluation** / synthetic seeds | Routing, memory, doctor cases |
| Regression scenarios | `tests/regression/scenarios.py` | **evaluation / smoke**, not SFT rows | Doctor, memory, tools, chat |
| Docs examples | `docs/personality.md`, README | **human-written seed prompts** | Personality not runtime |
| Plugin examples | `plugins/example_*` | eval of routing | Not chat quality data |
| Export bundles | scripts export/import | must **exclude** memories/history (already policy) | — |

### Realistic extractable examples

**Cannot claim a large count from the repo.** Checked-in conversational FT data is effectively **near-zero**.

- Directly usable SFT rows in-repo: **~0** (no curated chat JSONL dataset).  
- Seeds from docs/tests that could be **manually expanded**: on the order of **tens**, not thousands (**PARTIAL EVIDENCE**).  
- After privacy-reviewed export of real usage logs: **UNKNOWN** (depends on operator data volume outside git).

---

# 8. Ideal Zoe dataset design

Emphasize **quality over quantity**. First useful adapter: **1.5k–5k high-quality SFT examples** (estimate), not millions.

| Category | Approx. share | Purpose | Example input | Expected output traits | Difficulty | Importance | Suggested count (v1) |
|----------|---------------|---------|---------------|------------------------|------------|------------|----------------------|
| Personality / style | 20% | Match `docs/personality.md` | “Explain recursion simply” | Friendly, calm, step-by-step, admit uncertainty | Medium | High | 400–800 |
| Grounded RAG answers | 20% | Use injected context only when present | Context about notes + question | Cite context; say missing if absent | Medium | High | 400–800 |
| Coding help | 15% | Clean explanations | “Why is this Python bug happening?” | Best practices; ask before huge dumps | Medium–Hard | High | 300–600 |
| Project analysis writing | 10% | Turn analysis context into report | Injected architecture context | Concrete recommendations, no file begging | Medium | Medium | 200–400 |
| Summarization format | 8% | Stable summary sections | Long transcript | Summary/Topics/Facts/Tasks structure | Medium | Medium | 150–300 |
| Web/vision grounded | 7% | Prefer sources / vision context | Web or vision block + Q | Evidence-based; no fake consensus | Medium | Medium | 150–300 |
| Memory acknowledgement phrasing | 5% | Natural ack (optional) | “Remember my dog is Max” | Short confirm — **or keep code ack** | Easy | Low–Med | 100–200 |
| Error recovery / uncertainty | 5% | Admit gaps | Ambiguous ask | Honest uncertainty | Easy | Medium | 100–200 |
| Multilingual Tanglish/Tamil | 5% | Natural switch | Mixed language user turn | Natural code-switching | Hard | Medium | 100–200 |
| Negative / non-tool confusion | 5% | Don’t invent tool results | “What’s 2+2” in pure chat setting | Prefer deferring — careful: tools already intercept | Hard | Low for v1 | 100 |

**Sources mix (recommended):**

- **Human-written** gold for personality + safety  
- **Teacher-model distilled** for volume coding/RAG grounded pairs  
- **Extracted + corrected** Zoe failures (after privacy review)  
- **Synthetic** tool-adjacent dialogues only if labeled carefully  
- **Not** raw telemetry dumps  

**Format:** ShareGPT/HF messages list aligned with Qwen chat template: `system` / `user` / `assistant` (optionally multi-turn ≤ history policy).

---

# 9. Training strategy

## Recommended staged approach

### Stage 1 — QLoRA SFT (first experiment)

**Why it fits Zoe:**

- 3B Instruct already chat-tuned; need **domain/style adaptation**, not from-scratch pretraining.  
- QLoRA keeps Colab/local VRAM feasible (**estimate**).  
- PEFT adapters avoid replacing base weights; easy rollback beside software stack.  
- SFT teaches: persona, groundedness, report/summary formats.

**What SFT should teach:**

- Zoe voice and teaching style  
- Obey route-specific system rules (especially grounding)  
- Structured summarization sections  
- Clear coding help habits  

**What must remain outside the model:** tools, routing, permissions, arithmetic, timezone, plugin lifecycle, retrieval.

### Stage 2 — optional DPO / preference tuning (later)

Needs preference pairs (chosen/rejected Zoe replies). **Do not start here** — no preference data exists.

### Not recommended now

- Full continued pretraining on notes/PDFs (use RAG).  
- Unsupervised finetune on raw history (privacy + style collapse).  
- Replacing MiniLM/BLIP/Whisper in the same run.

### Integration pattern after success

- Load base Qwen + LoRA adapter in `load_model()` behind config flag.  
- Keep fp16/CPU paths working without adapter.

---

# 10. Before vs after fine-tuning

| Capability | Current | Expected FT improvement | Confidence | How to measure |
|------------|---------|-------------------------|------------|----------------|
| Personality consistency | Weak (doc unused) | **HIGH** | High | Blind rubric vs personality.md |
| Grounded RAG answers | Medium | **MEDIUM–HIGH** | Medium | Context-obligated QA set; hallucination rate |
| Coding explanations | Medium/UNKNOWN | **MEDIUM** | Medium | Human/teacher rubric on coding prompts |
| Project analysis prose | Medium | **MEDIUM** | Medium | Rubric on injected-context reports |
| Summaries | Medium | **MEDIUM** | Medium | Section parse success + factuality |
| Tool routing | Already strong (code) | **LOW** | High | Must not regress pytest plugin routes |
| Calculator/datetime | Perfect in code | **NONE / negative if broken** | High | Keep short-circuit tests |
| Retrieval recall | Software/index | **LOW** | High | Index metrics, not FT |
| Memory store decisions | Heuristic code | **LOW** (unless separate classifier) | Medium | Memory unit tests |
| Autonomous planning | Rule engine | **LOW** for v1 | Medium | Agent plan tests |
| Latency/VRAM | fp16 3B | **LOW** unless quant+adapter carefully | Low | Tokens/sec, VRAM |

---

# 11. Evaluation strategy (design only — do not run now)

## Metrics that matter for Zoe

| Metric | Definition |
|--------|------------|
| Tool non-interference | Tool queries still never need LLM (or LLM not wrongly preferred) |
| Groundedness | Claims supported by provided context when context present |
| Hallucination rate | Unsupported facts when context empty/partial |
| Instruction adherence | Follows system constraints (analysis/web/vision) |
| Personality rubric | Friendly/honest/calm/encouraging scores |
| Summary structure | Required sections present |
| Coding help quality | Correctness + clarity rubric |
| Regression rate | Pytest + regression scenarios still green |
| Refusal/uncertainty | Admits unknown appropriately |

## Splits

| Split | Role |
|-------|------|
| Train | SFT updates |
| Validation | Early stopping / hyperparams |
| Held-out test | Final report once |
| Adversarial | Prompt injection, “ignore context”, math traps, privacy probes |
| Regression | Existing pytest + `tests/regression` scenarios (software) |

**Why separation matters:** Tuning to the same prompts used for go/no-go will overstate readiness and ship regressions.

## Baseline before any train

1. Freeze prompt policy (including whether to load personality.md).  
2. Run software regression (already green).  
3. Score a **fixed 100–200 prompt eval set** with base Qwen (human or teacher judge).  
4. Only then train adapter and re-score.

---

# 12. Hardware / training cost (estimates)

| Item | Assessment | Label |
|------|------------|-------|
| Local GPU FT | Feasible for 3B QLoRA if ≥~8–12GB VRAM class GPU (**estimate**) | ESTIMATE |
| Colab FT | Feasible for 3B QLoRA on common T4/L4-class runtimes (**estimate**) | ESTIMATE |
| Full bf16 FT without quant | Tighter VRAM; less ideal for first run | ESTIMATE |
| Dataset size v1 | 1.5k–5k chats | ESTIMATE |
| Duration | Hours not days for 3B QLoRA on small data (**estimate**) | ESTIMATE |
| Inference today | CPU possible but slow; CUDA preferred | VERIFIED path in code |

Repo does **not** pin GPU SKU or measure VRAM — treat all VRAM/time figures as **estimates**.

---

# 13. Roadmap to first fine-tune

### PHASE 0 — Current state
- **Objective:** Freeze understanding of software vs model responsibilities  
- **Work:** This report; RC docs already exist  
- **Deliverable:** Shared agreement on PRE-FINETUNE status  
- **Effort:** Done  
- **Criteria:** Stakeholders accept scope  

### PHASE 1 — Dataset infrastructure
- **Objective:** Schema, storage, versioning, PII policy  
- **Deps:** Phase 0  
- **Deliverables:** `datasets/` schema doc + JSONL validators (future code)  
- **Effort:** 2–4 days  
- **Criteria:** Can validate a sample file  

### PHASE 2 — Dataset collection
- **Objective:** Seed human + teacher examples per category  
- **Deps:** Phase 1  
- **Deliverables:** First 500 gold examples  
- **Effort:** 1–2 weeks  
- **Criteria:** Coverage across top categories  

### PHASE 3 — Dataset cleaning
- **Objective:** Dedup, PII scrub, template render check  
- **Deps:** Phase 2  
- **Deliverables:** Clean train/val/test splits  
- **Effort:** 3–5 days  
- **Criteria:** Automated checks pass  

### PHASE 4 — Evaluation baseline
- **Objective:** Score base Qwen on frozen eval set  
- **Deps:** Phase 3 + frozen prompts  
- **Deliverables:** Baseline metrics sheet  
- **Effort:** 2–4 days  
- **Criteria:** Reproducible scores  

### PHASE 5 — Training infrastructure
- **Objective:** Replace placeholder `train` with QLoRA entrypoint  
- **Deps:** Phase 1  
- **Deliverables:** Train script, adapter output dir, config flags  
- **Effort:** 3–7 days  
- **Criteria:** Dry-run on 10 examples completes  

### PHASE 6 — First LoRA/QLoRA experiment
- **Objective:** Train v0 adapter  
- **Deps:** Phases 3–5  
- **Deliverables:** Adapter weights + train log  
- **Effort:** 1–3 days wall time including debug  
- **Criteria:** Loss converges; no crash  

### PHASE 7 — Evaluation
- **Objective:** Compare adapter vs baseline  
- **Deps:** Phase 4 + 6  
- **Deliverables:** Delta report  
- **Criteria:** Personality/grounding up; tool pytest still green  

### PHASE 8 — Iteration
- **Objective:** Fix failure clusters with more gold data  
- **Deps:** Phase 7  
- **Effort:** Ongoing  
- **Criteria:** Clear win on ≥2 priority metrics  

### PHASE 9 — Integration into Zoe
- **Objective:** Optional adapter load in `load_model`  
- **Deps:** Phase 7 pass  
- **Deliverables:** Config `MODEL_ADAPTER` or similar  
- **Criteria:** Chat works with/without adapter  

### PHASE 10 — Production validation
- **Objective:** Manual RELEASE_CHECKLIST + targeted pytest  
- **Deps:** Phase 9  
- **Criteria:** No tool/memory regressions; UX accepted  

---

# 14. What should be built before training

## MUST HAVE

- Dataset schema + initial gold set (≥500, preferably ≥1500)  
- PII / privacy rules for any real logs  
- Frozen runtime prompt policy (decide on personality.md injection)  
- QLoRA training entrypoint (replace placeholder)  
- Held-out eval set + baseline scores  
- Regression gate: plugin/tool/memory pytest batches still pass after integrating adapter  

## SHOULD HAVE

- Adapter load path in generation  
- Experiment config (lr, ranks, epochs) checked into repo  
- Groundedness automatic checks (context entailment heuristic or judge model)  
- Truncation/window documentation aligned with training packing  

## NICE TO HAVE

- Preference pairs for later DPO  
- Quantized inference (bitsandbytes) for faster eval  
- Dataset viewer / CLI `zoe datasets validate`  

## NOT NEEDED (before first FT)

- Rewriting plugin system  
- Replacing Chroma  
- Multimodal Qwen FT  
- Full continued pretraining on PDFs  
- New desktop UI  
- Teaching-mode product features  

---

# 15. Final verdict

1. **Prepare for fine-tuning?** **Yes.**  
2. **Actually train today?** **No.**  
3. **Single biggest missing thing?** **Curated dataset + real training/eval stack** (placeholder `train`).  
4. **Already exceptionally good at?** **Deterministic tools, plugin routing, RAG plumbing, memory/history persistence, ops/doctor, regression discipline.**  
5. **Biggest weakness?** **LLM layer is under-specified for Zoe’s personality/grounding goals; almost all “character” lives in unused docs and thin system prompts.**  
6. **FT will realistically improve?** Style, grounded answering, analysis/summary prose, coding explanation habits.  
7. **FT will NOT improve?** Calculator/datetime correctness, plugin security, retrieval index quality, empty-index gates, Chroma ops.  
8. **Distance to first useful fine-tuned model?** Roughly **one focused sprint of data+infra (Sprint 22) + one experimental train/eval cycle** — on the order of **2–4 weeks calendar** if data work is prioritized (**estimate**).  
9. **Sprint 22 focus?** Dataset schema, gold collection, prompt freeze (personality wiring decision), eval baseline, QLoRA train skeleton — **not** broad refactors.  
10. **Do not touch before FT?** Working tool short-circuits, plugin contracts, green regression surfaces, retrieval-first empty-index behavior, calculator/timezone semantics.

### CURRENT ZOE: **PRE-FINETUNE**

---

# 16. Sprint 22 recommendation (actionable)

**Theme:** Fine-tune preparation — data and training skeleton only.

1. Decide: inject `docs/personality.md` (or a shortened runtime persona) into system prompts **before** collecting SFT labels.  
2. Define JSONL schema matching Qwen chat template.  
3. Author 500+ gold examples across personality + grounded RAG + coding.  
4. Build offline eval set (never train on it).  
5. Implement real `train` path (QLoRA) behind explicit opt-in; keep default chat unchanged.  
6. Do **not** destabilize plugins/tools/memory code paths.

---

## Evidence Index

| Source | What it proved |
|--------|----------------|
| `config/settings.txt` | Base chat model is `Qwen/Qwen2.5-3B-Instruct` |
| `brain/generation.py` | HF load path, dtype/device, chat template, generate hyperparams, singleton cache |
| `brain/pipeline.py` | Turn order: profile → memory → tools → orchestrator → LLM |
| `brain/context.py` | System prompt variants; 6000-char caps; personality not referenced |
| `cli/main.py` | `train` is placeholder text only |
| `requirements.txt` | torch/transformers/accelerate present; **no** peft/trl/bitsandbytes/datasets |
| `rag/embedder.py` | Separate MiniLM embedder for RAG |
| `vision/caption.py` | Separate BLIP caption model |
| `voice/recognizer.py` | Optional Whisper STT |
| `tools/calculator.py`, `tools/datetime_tool.py`, `tools/executor.py` | Deterministic tools short-circuit LLM |
| `plugins/*` | Mature routing/lifecycle; shallow sandbox |
| `memory/*` | Rule-based memory intelligence stack |
| `conversation/*` | Persistent history + LLM summarization |
| `agents/*` | Heuristic planning/autonomous/supervisor |
| `docs/personality.md` | Desired persona **not wired** to runtime |
| `PROJECT_STATUS.md` | Explicitly notes personality unused; train placeholder |
| `tests/regression/scenarios.py` | Software eval scenarios exist; not FT labels |
| `data/history/summary.json`, `data/telemetry/runtime.jsonl` | Little/no usable SFT gold in-repo; privacy-sensitive |
| `FINAL_RELEASE_REVIEW.md`, `TECHNICAL_DEBT.md` | RC posture; FT listed as future debt |
| `docs/roadmap.md` | Fine-tuning listed after stabilization |

---

*End of authoritative fine-tuning readiness report. No code, tests, or training were executed in producing this document.*
