# Zoe AI

My personal AI assistant — a local-first LLM with notes, memory, PDF, code, web, and vision capabilities.

Version: v2.5

## Voice assistant (offline)

Enable voice in **Settings → Voice** (requires `pip install -r requirements-voice.txt`), then use the microphone button or **Ctrl+Shift+V** to enable push-to-talk.

- **Space** — push to talk (when focus is not in the text box)
- **Esc** — stop speaking
- Pipeline: microphone → Whisper → `brain.pipeline.generate_response()` → pyttsx3

## Zoe Desktop (primary UI)

```bash
python desktop/app.py
```

The desktop UI calls the existing backend (`brain.pipeline.generate_response`, vision pipeline, indexers, doctor) on background threads. The CLI remains fully supported.

Zoe AI is built around a Hugging Face chat model with tool routing, multiple retrieval layers backed by ChromaDB, web search, and vision analysis.

```mermaid
flowchart TD
    CLI[cli/main.py]
    Desktop[desktop/app.py]
    Pipeline[brain/pipeline.py]
    Context[brain/context.py]
    Generation[brain/generation.py]
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

    CLI --> Pipeline
    Desktop --> Pipeline
    Pipeline --> Tools
    Pipeline --> Agents
    Pipeline --> Context
    Pipeline --> Generation
    Generation --> LLM
    Context --> Notes
    Context --> Memory
    Context --> PDF
    Context --> Code
    Context --> Web
    Context --> Vision
    Notes --> Chroma
    Memory --> Chroma
    PDF --> Chroma
    Code --> Chroma
```

### Request flow

1. **Memory detection** — personal statements are saved before generation.
2. **Tool execution** — calculator, datetime, and filesystem requests are handled without the LLM.
3. **Project analysis** — analysis queries trigger plan → execute → gather context.
4. **Vision routing** — image queries analyze the referenced file via OCR + captioning.
5. **Context retrieval** — the router selects one source: memory, notes, PDF, code, or web.
6. **Generation** — the LLM replies using system context, conversation history, and the user message.

## Folder Structure

| Folder | Responsibility |
|--------|----------------|
| `brain/` | Model loading, context building, chat pipeline, and generation |
| `desktop/` | PySide6 desktop UI and voice controls |
| `voice/` | Offline voice capture, Whisper STT, pyttsx3 TTS, local commands |
| `cli/` | Terminal commands: `chat`, `ingest`, `code`, `image`, `doctor`, `history`, `train` |
| `core/` | Shared config, Chroma helpers, logging, indexing utilities |
| `rag/` | Personal notes loading, embedding, indexing, and search |
| `memory/` | Memory detection, storage, retrieval, and conversation history |
| `pdf/` | PDF loading, chunking, indexing, and search |
| `codebase/` | Source code loading, chunking, indexing, and search |
| `web/` | DuckDuckGo search, webpage reading, caching, and retrieval |
| `vision/` | Image loading, OCR, captioning, and unified vision pipeline |
| `tools/` | Tool routing, calculator, datetime, and filesystem tools |
| `agents/` | Agent orchestration: intent, planning, multi-tool execution, recovery, and verification |
| `config/` | Runtime settings in `settings.txt` |
| `data/` | Notes and PDF input files |
| `scripts/` | Standalone smoke and integration test scripts |
| `tests/` | Pytest test suite |
| `docs/` | Architecture, roadmap, and status documentation |

### Brain module layout

| File | Responsibility |
|------|----------------|
| `brain/model.py` | Public API entry point (re-exports) |
| `brain/pipeline.py` | Overall chat request flow |
| `brain/context.py` | Context building and retrieval |
| `brain/generation.py` | Model loading and text generation |

## How to Install

1. Clone the repository:

```bash
git clone https://github.com/dakxhie/zoe.git
cd zoe
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

Optional offline voice (microphone, Whisper, TTS):

```bash
pip install -r requirements-voice.txt
```

PyAudio is **not** required. Zoe captures audio with `sounddevice`. Install PyAudio only if you use other SpeechRecognition microphone backends.

4. Configure settings in `config/settings.txt` (especially `MODEL_NAME`).

## How to Chat

Start an interactive session from the repository root:

```bash
python cli/main.py chat
```

Type your message and press Enter. Type `exit` or `quit` to leave.

Examples:

- `What is my favorite color?` → memory retrieval
- `Summarize Chapter 2.` → PDF retrieval
- `Find generate_response().` → code retrieval
- `Latest Python news` → web retrieval
- `Describe screenshot.png` → vision analysis

## How to Index PDFs

Place PDF files in `data/pdfs/`, then run:

```bash
python cli/main.py ingest
```

This builds both the notes index and the PDF index.

## How to Index Code

```bash
python cli/main.py code .
```

Replace `.` with any project path.

## How to Analyze Images

Direct mode (no LLM):

```bash
python cli/main.py image photo.jpg
```

With a question:

```bash
python cli/main.py image screenshot.png --prompt "Explain the error."
```

In chat:

```bash
python cli/main.py chat
# Then: Describe screenshot.png
```

## How Memory Works

1. **Detection** — `memory/detector.py` decides whether a message contains personal information.
2. **Storage** — accepted messages are saved to `zoe_memory` via `memory/store.py`.
3. **Retrieval** — memory-related queries are routed to the memory tool.
4. **Conversation history** — persistent dialogue is stored in `data/history/chat.jsonl`, indexed in `zoe_history`, and the last 20 messages are included in prompts via `conversation/`.

## Conversation History

Persistent dialogue is separate from long-term memory facts.

| Component | Location |
|-----------|----------|
| Raw messages | `data/history/chat.jsonl` |
| Session id | `data/history/session.json` |
| Summary | `data/history/summary.json` |
| Semantic index | Chroma collection `zoe_history` |

CLI commands:

```bash
python cli/main.py history
python cli/main.py history sessions
python cli/main.py history summary
python cli/main.py history clear
python cli/main.py history stats
```

Summarization runs automatically after 40 messages using the local LLM. Prompts use the latest summary plus the 20 most recent raw messages.

## How Tools Work

The tool router (`tools/router.py`) classifies queries into: `chat`, `memory`, `notes`, `pdf`, `code`, `web`, `vision`, or `filesystem`.

| Tool | Examples |
|------|----------|
| Calculator | `2+2`, `10*(5+2)` |
| Datetime | `Current time`, `Today's date`, `What time is it in India?`, `UTC time` |
| Filesystem | `list files`, `read file README.md` |
| Web | `latest news`, `current weather` |
| Vision | `describe image.jpg`, `read receipt.png` |

## How Planners Work

For project analysis and multi-tool requests, the agent layer analyzes intent, builds an internal plan, executes tools with recovery, fuses ranked context, verifies quality, then generates the answer. Project analysis still runs: search code → read files → gather context → summarize → recommend, with an added structured project report.

## How to Run Tests

### Regression (release verification)

End-to-end functional checks against the real Zoe stack (not a pytest replacement):

```bash
python tests/regression.py          # quick suite
python tests/regression.py --full   # indexes, web, vision, imports, performance
```

Results print to the terminal and to `tests/reports/latest.txt`.

### Pytest

```bash
pytest tests/ -v
```

### Script smoke tests

```bash
python cli/main.py doctor
python scripts/system_check.py
python scripts/test_web_pipeline.py
python scripts/test_vision_pipeline.py
python scripts/test_chat_vision.py
```

## How CI Works

GitHub Actions (`.github/workflows/tests.yml`) runs `pytest tests/ -v` on every push and pull request.

## Goals

- Friend-like conversations
- Coding assistant
- Teaching assistant
- Research assistant
- PDF knowledge
- Long-term memory
- Web research
- Image understanding
