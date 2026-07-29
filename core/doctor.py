"""System health checks for Zoe AI."""

from __future__ import annotations

import importlib
import platform
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from core.config import ROOT, load_settings
from core.index_status import (
    COLLECTION_CODE,
    COLLECTION_MEMORY,
    COLLECTION_NOTES,
    COLLECTION_PDF,
)

MIN_PYTHON_VERSION = (3, 10)

REQUIRED_SETTINGS_KEYS: tuple[str, ...] = (
    "MODEL_NAME",
    "MEMORY_DB",
    "PDF_FOLDER",
    "NOTES_FOLDER",
)

EXPECTED_FOLDERS: tuple[tuple[str, bool], ...] = (
    ("data", True),
    ("data/memory", False),
    ("data/notes", True),
    ("data/pdfs", True),
    ("data/code", False),
    ("data/history", False),
    ("cache", False),
    ("docs", True),
    ("scripts", True),
    ("tests", True),
)

KNOWN_COLLECTIONS: tuple[tuple[str, str], ...] = (
    (COLLECTION_MEMORY, "docs"),
    (COLLECTION_NOTES, "docs"),
    (COLLECTION_PDF, "chunks"),
    (COLLECTION_CODE, "files"),
    ("zoe_history", "messages"),
)


class CheckStatus(str, Enum):
    """Outcome for one doctor check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    """Structured result for one doctor check."""

    name: str
    status: CheckStatus
    details: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)


@dataclass
class CollectionInfo:
    """Document count for one Chroma collection."""

    name: str
    count: int
    unit: str


@dataclass
class DoctorReport:
    """Full doctor report."""

    checks: list[CheckResult]
    collections: list[CollectionInfo]
    runtime: dict[str, str]
    overall_status: CheckStatus
    recommended_fixes: list[str] = field(default_factory=list)


def _safe_call(name: str, check_fn: Callable[[], CheckResult]) -> CheckResult:
    """Run one check and never raise."""
    try:
        return check_fn()
    except Exception as exc:
        return CheckResult(
            name=name,
            status=CheckStatus.FAIL,
            details=[f"Unexpected error: {exc}"],
        )


def check_python() -> CheckResult:
    """Verify the Python runtime version."""
    version = sys.version_info
    version_text = f"{version.major}.{version.minor}.{version.micro}"
    details = [f"Python {version_text}"]

    if (version.major, version.minor) >= MIN_PYTHON_VERSION:
        return CheckResult("Python", CheckStatus.PASS, details=details)

    minimum = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
    return CheckResult(
        name="Python",
        status=CheckStatus.FAIL,
        details=details + [f"Requires Python >={minimum}"],
        fixes=[f"Upgrade Python to {minimum} or newer."],
    )


def check_dependencies() -> CheckResult:
    """Verify important packages can be imported."""
    from core.package_check import check_required_packages

    ok, details = check_required_packages()
    fixes = [
        f"Install: pip install {detail.split()[0]}"
        for detail in details
        if "FAIL" in detail
    ]
    status = CheckStatus.PASS if ok else CheckStatus.FAIL
    return CheckResult("Dependencies", status, details=details, fixes=fixes)


def check_configuration() -> CheckResult:
    """Verify settings load and required keys exist."""
    try:
        settings = load_settings()
    except Exception as exc:
        return CheckResult(
            name="Configuration",
            status=CheckStatus.FAIL,
            details=[f"Could not load settings: {exc}"],
            fixes=["Verify config/settings.txt exists and is readable."],
        )

    if not settings:
        return CheckResult(
            name="Configuration",
            status=CheckStatus.FAIL,
            details=["Settings file is empty or missing."],
            fixes=["Create config/settings.txt with required keys."],
        )

    missing = [key for key in REQUIRED_SETTINGS_KEYS if not settings.get(key, "").strip()]
    details = [f"Loaded {len(settings)} setting(s)."]

    if missing:
        return CheckResult(
            name="Configuration",
            status=CheckStatus.FAIL,
            details=details + [f"Missing keys: {', '.join(missing)}"],
            fixes=["Add missing keys to config/settings.txt."],
        )

    return CheckResult("Configuration", CheckStatus.PASS, details=details)


def check_folders() -> CheckResult:
    """Verify expected repository folders exist."""
    details: list[str] = []
    fixes: list[str] = []
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for folder_path, required in EXPECTED_FOLDERS:
        full_path = ROOT / folder_path
        if full_path.is_dir():
            details.append(f"{folder_path}/ .............. present")
            continue

        details.append(f"{folder_path}/ .............. missing")
        if required:
            missing_required.append(folder_path)
        else:
            missing_optional.append(folder_path)

    if missing_required:
        fixes.extend(f"Create folder: {path}" for path in missing_required)
        return CheckResult(
            name="Folders",
            status=CheckStatus.FAIL,
            details=details,
            fixes=fixes,
        )

    if missing_optional:
        fixes.extend(f"Create folder (optional): {path}" for path in missing_optional)
        return CheckResult(
            name="Folders",
            status=CheckStatus.WARN,
            details=details,
            fixes=fixes,
        )

    return CheckResult("Folders", CheckStatus.PASS, details=details)


def _count_unique_code_files(collection: Any) -> int:
    """Count unique indexed code files from collection metadata."""
    if collection.count() == 0:
        return 0

    stored = collection.get(include=["metadatas"])
    metadatas = stored.get("metadatas") or []
    unique_paths: set[str] = set()

    for metadata in metadatas:
        if not isinstance(metadata, dict):
            continue
        path = str(metadata.get("path") or metadata.get("filename") or "").strip()
        if path:
            unique_paths.add(path)

    return len(unique_paths) if unique_paths else collection.count()


def check_chroma() -> tuple[CheckResult, list[CollectionInfo]]:
    """Initialize Chroma and list collection counts."""
    from core.chroma import ChromaError, get_chroma_client, get_chroma_path, get_collection

    collections: list[CollectionInfo] = []

    try:
        chroma_path = get_chroma_path()
    except Exception as exc:
        return (
            CheckResult(
                name="Chroma",
                status=CheckStatus.FAIL,
                details=[f"Could not resolve Chroma path: {exc}"],
            ),
            collections,
        )

    try:
        client = get_chroma_client()
        listed = client.list_collections()
        names = sorted({collection.name for collection in listed})
    except ChromaError as exc:
        if chroma_path.exists():
            return (
                CheckResult(
                    name="Chroma",
                    status=CheckStatus.FAIL,
                    details=[f"Database exists but cannot be opened: {exc}"],
                    fixes=["Verify MEMORY_DB path in config/settings.txt is writable."],
                ),
                collections,
            )
        return (
            CheckResult(
                name="Chroma",
                status=CheckStatus.FAIL,
                details=[str(exc)],
                fixes=["Verify MEMORY_DB path in config/settings.txt is writable."],
            ),
            collections,
        )
    except Exception as exc:
        return (
            CheckResult(
                name="Chroma",
                status=CheckStatus.FAIL,
                details=[f"Could not open ChromaDB: {exc}"],
            ),
            collections,
        )

    if not names:
        details = [f"Database accessible at {chroma_path}", "No collections indexed yet (empty database)."]
    else:
        details = [f"Database accessible at {chroma_path}", f"Found {len(names)} collection(s)."]

    for collection_name, unit in KNOWN_COLLECTIONS:
        try:
            collection = get_collection(collection_name)
            count = collection.count()
            if collection_name == COLLECTION_CODE:
                count = _count_unique_code_files(collection)
            collections.append(CollectionInfo(collection_name, count, unit))
            details.append(f"{collection_name}: {count} {unit}")
        except Exception as exc:
            details.append(f"{collection_name}: unavailable ({exc})")

    for collection_name in names:
        if any(info.name == collection_name for info in collections):
            continue
        try:
            count = get_collection(collection_name).count()
            collections.append(CollectionInfo(collection_name, count, "docs"))
            details.append(f"{collection_name}: {count} docs")
        except Exception as exc:
            details.append(f"{collection_name}: unavailable ({exc})")

    return CheckResult("Chroma", CheckStatus.PASS, details=details), collections


def check_memory() -> CheckResult:
    """Verify the memory collection is accessible."""
    from core.chroma import collection_count
    from core.index_status import COLLECTION_MEMORY

    try:
        count = collection_count(COLLECTION_MEMORY)
        return CheckResult(
            name="Memory",
            status=CheckStatus.PASS,
            details=[f"Collection accessible ({count} document(s))."],
        )
    except Exception as exc:
        return CheckResult(
            name="Memory",
            status=CheckStatus.FAIL,
            details=[str(exc)],
            fixes=["Verify ChromaDB is available and memory collection is accessible."],
        )


def check_notes(collections: list[CollectionInfo]) -> CheckResult:
    """Verify the notes retriever initializes."""
    from rag.retriever import search

    count = next((item.count for item in collections if item.name == COLLECTION_NOTES), 0)

    try:
        search("doctor health check", top_k=1)
    except Exception as exc:
        return CheckResult(
            name="Notes",
            status=CheckStatus.FAIL,
            details=[str(exc)],
            fixes=["Run: python cli/main.py ingest"],
        )

    if count == 0:
        return CheckResult(
            name="Notes",
            status=CheckStatus.WARN,
            details=["No notes indexed."],
            fixes=["Run: python cli/main.py ingest"],
        )

    return CheckResult(
        name="Notes",
        status=CheckStatus.PASS,
        details=[f"{count} document(s) indexed."],
    )


def check_pdf(collections: list[CollectionInfo]) -> CheckResult:
    """Verify the PDF retriever initializes."""
    from pdf.retriever import search_documents

    count = next((item.count for item in collections if item.name == COLLECTION_PDF), 0)

    try:
        search_documents("doctor health check", top_k=1)
    except Exception as exc:
        return CheckResult(
            name="PDF",
            status=CheckStatus.FAIL,
            details=[str(exc)],
            fixes=["Run: python cli/main.py ingest"],
        )

    if count == 0:
        return CheckResult(
            name="PDF",
            status=CheckStatus.WARN,
            details=["No PDFs indexed."],
            fixes=["Add PDFs to data/pdfs/ and run: python cli/main.py ingest"],
        )

    return CheckResult(
        name="PDF",
        status=CheckStatus.PASS,
        details=[f"{count} chunk(s) indexed."],
    )


def check_code(collections: list[CollectionInfo]) -> CheckResult:
    """Verify the code retriever initializes."""
    from codebase.retriever import search_code

    count = next((item.count for item in collections if item.name == COLLECTION_CODE), 0)

    try:
        search_code("doctor health check", top_k=1)
    except Exception as exc:
        return CheckResult(
            name="Code",
            status=CheckStatus.FAIL,
            details=[str(exc)],
            fixes=["Run: python cli/main.py code ."],
        )

    if count == 0:
        return CheckResult(
            name="Code",
            status=CheckStatus.WARN,
            details=["No code indexed."],
            fixes=["Run: python cli/main.py code ."],
        )

    return CheckResult(
        name="Code",
        status=CheckStatus.PASS,
        details=[f"{count} file(s) indexed."],
    )


def check_web() -> CheckResult:
    """Verify web search and reader modules import without network calls."""
    details: list[str] = []
    fixes: list[str] = []
    failed = False

    try:
        from web.search import search_web

        if not callable(search_web):
            raise TypeError("search_web is not callable")
        details.append("search_web .............. available")
    except Exception as exc:
        failed = True
        details.append(f"search_web .............. FAIL ({exc})")
        fixes.append("Install: pip install duckduckgo-search")

    try:
        from web.reader import read_webpage

        if not callable(read_webpage):
            raise TypeError("read_webpage is not callable")
        details.append("read_webpage ............ available")
    except Exception as exc:
        failed = True
        details.append(f"read_webpage ............ FAIL ({exc})")
        fixes.append("Install: pip install requests beautifulsoup4")

    status = CheckStatus.FAIL if failed else CheckStatus.PASS
    return CheckResult("Web", status, details=details, fixes=fixes)


def check_vision() -> CheckResult:
    """Verify vision dependencies import without loading models."""
    details: list[str] = []
    fixes: list[str] = []
    failed = False

    try:
        from PIL import Image

        if Image is None:
            raise ImportError("Pillow import failed")
        details.append("Pillow .................. available")
    except Exception as exc:
        failed = True
        details.append(f"Pillow .................. FAIL ({exc})")
        fixes.append("Install: pip install Pillow")

    try:
        import easyocr

        if easyocr is None:
            raise ImportError("easyocr import failed")
        details.append("OCR (easyocr) ........... available")
    except Exception as exc:
        failed = True
        details.append(f"OCR (easyocr) ........... FAIL ({exc})")
        fixes.append("Install: pip install easyocr")

    try:
        from transformers import BlipForConditionalGeneration, BlipProcessor

        if BlipForConditionalGeneration is None or BlipProcessor is None:
            raise ImportError("caption model classes unavailable")
        details.append("Caption model ........... available")
    except Exception as exc:
        failed = True
        details.append(f"Caption model ........... FAIL ({exc})")
        fixes.append("Install: pip install transformers torch")

    status = CheckStatus.FAIL if failed else CheckStatus.PASS
    return CheckResult("Vision", status, details=details, fixes=fixes)


def check_agents() -> CheckResult:
    """Verify agent planner, executor, and analyzer import."""
    details: list[str] = []
    fixes: list[str] = []
    failed = False

    modules = (
        ("planner", "agents.planner"),
        ("executor", "agents.executor"),
        ("analyzer", "agents.analyzer"),
    )

    for label, module_name in modules:
        try:
            importlib.import_module(module_name)
            details.append(f"{label} .................. available")
        except Exception as exc:
            failed = True
            details.append(f"{label} .................. FAIL ({exc})")
            fixes.append(f"Verify {module_name} imports successfully.")

    status = CheckStatus.FAIL if failed else CheckStatus.PASS
    return CheckResult("Agents", status, details=details, fixes=fixes)


def check_tools() -> CheckResult:
    """Verify calculator, datetime, filesystem, and router load."""
    details: list[str] = []
    fixes: list[str] = []
    failed = False

    modules = (
        ("calculator", "tools.calculator"),
        ("datetime", "tools.datetime_tool"),
        ("filesystem", "tools.filesystem"),
        ("router", "tools.router"),
    )

    for label, module_name in modules:
        try:
            importlib.import_module(module_name)
            details.append(f"{label} .................. available")
        except Exception as exc:
            failed = True
            details.append(f"{label} .................. FAIL ({exc})")

    status = CheckStatus.FAIL if failed else CheckStatus.PASS
    return CheckResult("Tools", status, details=details, fixes=fixes)


def check_cli() -> CheckResult:
    """Verify CLI commands are registered."""
    from core.cli_commands import EXPECTED_COMMANDS, discover_cli_commands

    try:
        commands = discover_cli_commands()
    except Exception as exc:
        return CheckResult(
            name="CLI",
            status=CheckStatus.FAIL,
            details=[str(exc)],
        )

    if not commands:
        return CheckResult(
            name="CLI",
            status=CheckStatus.FAIL,
            details=["No CLI commands discovered in cli/main.py."],
        )

    missing = sorted(EXPECTED_COMMANDS - set(commands))
    if missing:
        return CheckResult(
            name="CLI",
            status=CheckStatus.FAIL,
            details=[
                f"Discovered: {', '.join(commands)}",
                f"Missing expected commands: {', '.join(missing)}",
            ],
        )

    return CheckResult(
        name="CLI",
        status=CheckStatus.PASS,
        details=[f"Commands: {', '.join(commands)}"],
    )


def check_model() -> CheckResult:
    """Report configured model without loading weights."""
    settings = load_settings()
    model_name = settings.get("MODEL_NAME", "").strip()

    if not model_name:
        return CheckResult(
            name="Model",
            status=CheckStatus.FAIL,
            details=["MODEL_NAME is not configured."],
            fixes=["Set MODEL_NAME in config/settings.txt."],
        )

    model_path = Path(model_name)
    if model_path.is_absolute() and model_path.exists():
        return CheckResult(
            name="Model",
            status=CheckStatus.PASS,
            details=[f"Local model path: {model_path}"],
        )

    if model_path.exists() and not model_path.is_absolute():
        resolved = (ROOT / model_path).resolve()
        if resolved.exists():
            return CheckResult(
                name="Model",
                status=CheckStatus.PASS,
                details=[f"Local model path: {resolved}"],
            )

    return CheckResult(
        name="Model",
        status=CheckStatus.PASS,
        details=[f"Hugging Face model: {model_name}"],
    )


def check_conversation_history() -> CheckResult:
    """Verify conversation history storage, files, and Chroma collection."""
    from conversation.retriever import COLLECTION_NAME
    from conversation.storage import (
        CHAT_FILE,
        HISTORY_DIR,
        SESSION_FILE,
        SUMMARY_FILE,
        chat_file_exists,
        ensure_history_dir,
        iter_messages,
        read_json_file,
    )
    from core.chroma import ChromaError, collection_count

    details: list[str] = []
    fixes: list[str] = []
    failed = False
    warned = False

    try:
        ensure_history_dir()
        details.append(f"{HISTORY_DIR}/ available")
    except Exception as exc:
        failed = True
        details.append(f"History folder missing: {exc}")
        fixes.append("Create data/history/ or run python cli/main.py chat")

    if chat_file_exists():
        details.append("chat.jsonl readable")
        corrupt_lines = 0
        if CHAT_FILE.exists():
            import json

            with CHAT_FILE.open(encoding="utf-8") as handle:
                for _line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        corrupt_lines += 1
                        warned = True
        if corrupt_lines:
            details.append(f"chat.jsonl has {corrupt_lines} corrupt line(s)")
    else:
        details.append("chat.jsonl missing or empty")

    session_payload = read_json_file(SESSION_FILE)
    if session_payload is None and SESSION_FILE.exists():
        failed = True
        details.append("session.json unreadable")
    elif session_payload is not None:
        details.append("session.json readable")

    summary_payload = read_json_file(SUMMARY_FILE)
    if summary_payload is None and SUMMARY_FILE.exists():
        warned = True
        details.append("summary.json unreadable")
    elif summary_payload is not None:
        details.append("summary.json readable")

    try:
        count = collection_count(COLLECTION_NAME)
        details.append(f"{COLLECTION_NAME}: {count} message(s)")
    except ChromaError as exc:
        failed = True
        details.append(f"{COLLECTION_NAME} unavailable: {exc}")

    if failed:
        status = CheckStatus.FAIL
    elif warned:
        status = CheckStatus.WARN
    else:
        status = CheckStatus.PASS

    return CheckResult("Conversation", status, details=details, fixes=fixes)


def check_runtime() -> tuple[CheckResult, dict[str, str]]:
    """Collect runtime environment information."""
    runtime: dict[str, str] = {
        "Operating System": f"{platform.system()} {platform.release()}",
        "CPU": platform.processor() or platform.machine() or "unknown",
    }

    try:
        import torch

        runtime["Torch version"] = torch.__version__
        runtime["CUDA available"] = str(torch.cuda.is_available())
        if torch.cuda.is_available():
            runtime["GPU"] = torch.cuda.get_device_name(0)
        else:
            runtime["GPU"] = "not available"
    except Exception as exc:
        runtime["Torch version"] = f"unavailable ({exc})"
        runtime["CUDA available"] = "unknown"
        runtime["GPU"] = "unknown"

    try:
        import transformers

        runtime["Transformers version"] = transformers.__version__
    except Exception as exc:
        runtime["Transformers version"] = f"unavailable ({exc})"

    try:
        import psutil

        total_gb = psutil.virtual_memory().total / (1024**3)
        runtime["RAM"] = f"{total_gb:.1f} GB"
    except Exception:
        runtime["RAM"] = "unavailable (install psutil for RAM info)"

    details = [f"{key}: {value}" for key, value in runtime.items()]
    return CheckResult("Runtime", CheckStatus.PASS, details=details), runtime


def _dedupe_fixes(fixes: list[str]) -> list[str]:
    """Return fixes in first-seen order without duplicates."""
    seen: set[str] = set()
    ordered: list[str] = []
    for fix in fixes:
        if fix in seen:
            continue
        seen.add(fix)
        ordered.append(fix)
    return ordered


def _determine_overall_status(checks: list[CheckResult]) -> CheckStatus:
    """Compute overall health from individual check results."""
    if any(check.status == CheckStatus.FAIL for check in checks):
        return CheckStatus.FAIL
    if any(check.status == CheckStatus.WARN for check in checks):
        return CheckStatus.WARN
    return CheckStatus.PASS


def run_doctor() -> DoctorReport:
    """Run all doctor checks and return a structured report. Never raises."""
    checks: list[CheckResult] = []
    collections: list[CollectionInfo] = []
    runtime: dict[str, str] = {}
    fixes: list[str] = []

    for name, check_fn in (
        ("Python", check_python),
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Folders", check_folders),
    ):
        result = _safe_call(name, check_fn)
        checks.append(result)
        fixes.extend(result.fixes)

    try:
        chroma_result, collections = check_chroma()
    except Exception as exc:
        chroma_result = CheckResult(
            name="Chroma",
            status=CheckStatus.FAIL,
            details=[f"Unexpected error: {exc}"],
        )
        collections = []
    checks.append(chroma_result)
    fixes.extend(chroma_result.fixes)

    for check_fn in (
        check_memory,
        lambda: check_notes(collections),
        lambda: check_pdf(collections),
        lambda: check_code(collections),
        check_web,
        check_vision,
        check_agents,
        check_tools,
        check_cli,
        check_conversation_history,
        check_model,
    ):
        result = _safe_call("Check", check_fn)
        checks.append(result)
        fixes.extend(result.fixes)

    try:
        runtime_result, runtime = check_runtime()
    except Exception as exc:
        runtime_result = CheckResult(
            name="Runtime",
            status=CheckStatus.FAIL,
            details=[f"Unexpected error: {exc}"],
        )
        runtime = {}
    checks.append(runtime_result)

    overall = _determine_overall_status(checks)
    return DoctorReport(
        checks=checks,
        collections=collections,
        runtime=runtime,
        overall_status=overall,
        recommended_fixes=_dedupe_fixes(fixes),
    )


def _format_status_label(status: CheckStatus) -> str:
    """Map check status to report label."""
    if status == CheckStatus.PASS:
        return "PASS"
    if status == CheckStatus.WARN:
        return "WARN"
    return "FAIL"


def _format_overall_status(status: CheckStatus) -> str:
    """Map overall status to human-readable label."""
    if status == CheckStatus.PASS:
        return "HEALTHY"
    if status == CheckStatus.WARN:
        return "WARNINGS"
    return "FAILED"


def _print_section_line(label: str, status: CheckStatus) -> None:
    """Print one aligned doctor status line."""
    dots = "." * max(1, 20 - len(label))
    print(f"{label} {dots} {_format_status_label(status)}")


def print_doctor_report(report: DoctorReport) -> None:
    """Print a human-readable doctor report. Never raises."""
    print("=" * 40)
    print("ZOE SYSTEM DOCTOR")
    print("=" * 40)
    print()

    for check in report.checks:
        _print_section_line(check.name, check.status)

    print()
    print("=" * 40)
    print("Collections")
    print("-" * 40)

    if report.collections:
        for collection in report.collections:
            dots = "." * max(1, 20 - len(collection.name))
            print(f"{collection.name} {dots} {collection.count} {collection.unit}")
    else:
        print("No collections available.")

    print()
    print("=" * 40)
    print("System Status")
    print(_format_overall_status(report.overall_status))
    print("=" * 40)

    if report.recommended_fixes:
        print()
        print("Recommended fixes:")
        for fix in report.recommended_fixes:
            print(f"• {fix}")
