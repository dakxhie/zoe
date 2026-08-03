# Zoe AI Roadmap

## Completed

### Sprint 1 — Foundation
- Local LLM chat loop
- Config loading
- CLI structure

### Sprint 2 — Personal Notes (RAG)
- Notes loader, embeddings, ChromaDB indexing, retrieval in chat

### Sprint 3 — Persistent Memory
- Memory detection, storage, retrieval, chat integration

### Sprint 4 — PDF Intelligence
- PDF loading, chunking, indexing, search, `ingest` CLI

### Sprint 5 — Code Intelligence
- Code loader, chunker, indexer, search, `code` CLI

### Sprint 5.5 — Integration and Stability
- Shared Chroma helpers, context limits, deduplication, logging, system tests

### Sprint 6 — Agent Foundations
- Tool routing layer, calculator, datetime, filesystem tools

### Sprint 7 — Conversation History
- In-memory FIFO conversation history in chat prompts

### Sprint 8 — Web Research
- DuckDuckGo search, webpage reading, disk cache, retrieval pipeline
- Web routing, source-aware answers, empty-index fallback

### Sprint 9 — Vision
- Image loading (Pillow)
- OCR (EasyOCR)
- Image captioning (BLIP)
- Unified vision pipeline
- Vision routing and `image` CLI command

### v1.0 — Production Stabilization
- Brain module split (`pipeline`, `context`, `generation`)
- Pytest suite and GitHub Actions CI
- Startup diagnostics and system check script
- Documentation refresh

### v2.1 — Persistent Conversation History
- JSONL storage in `data/history/`
- Session management and startup restore
- Conversation summarization after 40 messages
- Semantic search via `zoe_history`
- CLI `history` commands

### v2.0 — Final Integration
- Timezone-aware datetime tool
- Conversational memory inference
- Reliable system doctor (`python cli/main.py doctor`)
- Guaranteed project analysis context injection
- Lazy LLM loading for non-chat commands
- Web deduplication and vision partial-result handling
- Expanded pytest coverage

## Next

### Sprint 10 — Teaching Mode
- Lesson plans from notes and PDFs
- Quiz generation
- Learning progress tracking

### Sprint 11 — Voice and Multimodal
- Speech input and output
- Optional screen/context ingestion

### Sprint 11 — Agent Orchestration (complete)
- Intent analysis, internal planning, multi-tool execution, recovery, verification, and retrieval fusion
- Structured project analysis reports
- DEBUG execution timings

### Sprint 12 — Zoe Desktop (complete)
- PySide6 primary GUI with workers, history panel, settings, index manager, doctor view

### Sprint 13 — Voice Assistant (complete)
- Offline Whisper + pyttsx3 pipeline integrated with desktop

### Sprint 14 — Packaging and Deployment
- Installable package metadata (`pyproject.toml`)
- Reproducible environment presets
- Local GPU and Colab presets

### Sprint 13 — Quality and Observability
- Expanded pytest coverage (web, vision, indexers)
- Performance profiling for indexing and inference
- Persistent conversation history (SQLite/JSON)

## Long-Term Goals

- Fine-tuning and personalization
- Production deployment workflow
- VS Code / IDE integration
