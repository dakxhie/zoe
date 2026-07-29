# Zoe AI Architecture

## System Overview

Zoe AI is a local-first personal assistant built around a Hugging Face chat model with tool-routed retrieval, web search, and vision analysis backed by ChromaDB.

```mermaid
flowchart TD
    CLI[cli/main.py]
    Pipeline[brain/pipeline.py]
    Context[brain/context.py]
    Generation[brain/generation.py]
    Router[tools/router.py]
    LLM[Hugging Face Model]
    Agents[agents/]
    Tools[tools/]
    Web[web/]
    Vision[vision/]
    Notes[rag/]
    Memory[memory/]
    PDF[pdf/]
    Code[codebase/]
    Chroma[(storage/chroma)]
    WebCache[(storage/web_cache)]

    CLI --> Pipeline
    Pipeline --> Router
    Pipeline --> Agents
    Pipeline --> Tools
    Pipeline --> Context
    Pipeline --> Generation
    Generation --> LLM
    Context --> Notes
    Context --> Memory
    Context --> PDF
    Context --> Code
    Context --> Web
    Context --> Vision
    Web --> WebCache
    Notes --> Chroma
    Memory --> Chroma
    PDF --> Chroma
    Code --> Chroma
```

## Folder Responsibilities

| Folder | Responsibility |
|--------|----------------|
| `brain/` | Chat pipeline, context building, model loading, generation |
| `cli/` | User commands: `chat`, `ingest`, `code`, `image`, `doctor`, `train` |
| `core/` | Config, Chroma helpers, logging, diagnostics, doctor, package checks |
| `rag/` | Personal notes loading, embedding, indexing, and search |
| `memory/` | Memory detection, storage, retrieval, conversation bridge |
| `conversation/` | Persistent dialogue storage, sessions, summarization, search |
| `pdf/` | PDF loading, chunking, indexing, and search |
| `codebase/` | Source code loading, chunking, indexing, and search |
| `web/` | Search, webpage reading, disk cache, retrieval pipeline |
| `vision/` | Image loading, OCR, captioning, unified analysis |
| `tools/` | Routing, calculator, datetime, filesystem execution |
| `agents/` | Project analysis planner and executor |
| `config/` | Runtime settings in `settings.txt` |
| `data/` | Notes and PDF input files |
| `scripts/` | Smoke and integration test scripts |
| `tests/` | Pytest regression suite |

## ChromaDB Collections

| Collection | Purpose |
|------------|---------|
| `zoe_notes` | Personal notes from `data/notes/` |
| `zoe_memory` | Learned conversation memories |
| `zoe_history` | Searchable conversation dialogue |
| `zoe_documents` | Chunked PDF text |
| `zoe_code` | Chunked project source code |

All collections share the same database path via `core/chroma.py`.

## Chat Pipeline

`brain/pipeline.generate_response()` executes in order:

1. Attempt memory save via `memory/store.py`
2. Execute lightweight tools via `tools/executor.py`
3. Run project analysis via `agents/analyzer.py` when matched
4. Handle vision requests via `vision/pipeline.analyze_image()`
5. Return empty-index guidance for notes, PDF, or code when applicable
6. Build routed context via `brain/context.py`
7. Inject conversation history from `conversation/retriever.py` when available
8. Generate LLM reply via `brain/generation.py`
9. Persist the exchange to `data/history/chat.jsonl`

## Retrieval Flow

The tool router selects **one** retrieval source per message:

| Route | Source |
|-------|--------|
| `memory` | `memory/retriever.py` |
| `conversation` | `conversation/retriever.py` (injected when history exists) |
| `notes` | `rag/retriever.py` |
| `pdf` | `pdf/retriever.py` |
| `code` | `codebase/retriever.py` |
| `web` | `web/retriever.py` |
| `vision` | `vision/pipeline.py` |
| `chat` | no retrieval |

Context is capped in `brain/context.py` (`MAX_CONTEXT_CHARS = 6000`).

## Web Flow

1. `web/search.py` queries DuckDuckGo
2. `web/reader.py` downloads and cleans pages
3. `web/cache.py` stores page text on disk
4. `web/retriever.py` assembles bounded context with source metadata

## Vision Flow

1. `vision/loader.py` loads and normalizes images
2. `vision/caption.py` generates BLIP captions
3. `vision/ocr.py` extracts text via EasyOCR
4. `vision/pipeline.py` merges caption + OCR + metadata
5. `brain/context.py` injects vision context into the system prompt

## CLI Commands

| Command | Purpose |
|---------|---------|
| `python cli/main.py chat` | Interactive conversation |
| `python cli/main.py ingest` | Build notes and PDF indexes |
| `python cli/main.py code PROJECT_PATH` | Index project source code |
| `python cli/main.py image IMAGE_PATH` | Analyze an image directly |
| `python cli/main.py image IMAGE_PATH --prompt "..."` | Ask a question about an image |

## Model Caching

| Component | Cache location |
|-----------|----------------|
| LLM | `brain/generation.py` global singleton |
| Embeddings | `rag/embedder.py` global singleton |
| BLIP caption model | `vision/caption.py` global singleton |
| EasyOCR reader | `vision/ocr.py` global singleton |
| Chroma client | `core/chroma.py` global singleton |
| Web pages | `storage/web_cache/` SHA256 files |

## Stability Notes

- Shared Chroma helpers live in `core/chroma.py`
- Shared chunk deduplication lives in `core/indexing.py`
- Retrieval failures are logged and do not stop chat generation
- Startup diagnostics run at chat session start via `core/diagnostics.py`
- CI runs pytest via `.github/workflows/tests.yml`
