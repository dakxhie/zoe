"""Structured project inspection for Zoe AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectReport:
    """Structured project analysis report."""

    language: str = "unknown"
    framework: str = "unknown"
    folder_structure: list[str] = field(default_factory=list)
    architecture: str = ""
    build_system: str = ""
    test_framework: str = ""
    dependency_manager: str = ""
    config_files: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    dead_code_candidates: list[str] = field(default_factory=list)
    large_files: list[str] = field(default_factory=list)
    complexity_hotspots: list[str] = field(default_factory=list)


def _detect_language(root: Path) -> str:
    counts = {
        "python": len(list(root.rglob("*.py"))),
        "javascript": len(list(root.rglob("*.js"))),
        "typescript": len(list(root.rglob("*.ts"))),
    }
    language, count = max(counts.items(), key=lambda item: item[1])
    return language if count else "unknown"


def _detect_framework(root: Path) -> str:
    names = {path.name.lower() for path in root.rglob("*") if path.is_file()}
    if "manage.py" in names:
        return "django"
    if any(name in names for name in ("next.config.js", "next.config.mjs")):
        return "next.js"
    if (root / "brain").exists() and (root / "cli").exists():
        return "zoe-ai"
    return "unknown"


def build_project_report(root: Path | None = None) -> ProjectReport:
    """Inspect repository structure and return a structured analysis report."""
    project_root = root or Path(__file__).resolve().parent.parent
    report = ProjectReport(
        language=_detect_language(project_root),
        framework=_detect_framework(project_root),
        folder_structure=sorted(
            {
                str(path.relative_to(project_root)).split("\\")[0].split("/")[0]
                for path in project_root.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            }
        )[:20],
        architecture="Modular packages with CLI entry, brain pipeline, retrieval indexes, and tools.",
        build_system="requirements.txt" if (project_root / "requirements.txt").exists() else "",
        test_framework="pytest" if (project_root / "tests").exists() else "",
        dependency_manager="pip" if (project_root / "requirements.txt").exists() else "",
        config_files=sorted(
            str(path.relative_to(project_root))
            for path in project_root.rglob("*")
            if path.is_file()
            and path.name in {"settings.txt", "pyproject.toml", "requirements.txt", "settings.json"}
        ),
        entry_points=[name for name in ("cli/main.py", "brain/pipeline.py") if (project_root / name).exists()],
    )

    large_files: list[tuple[int, str]] = []
    for path in project_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "storage" in path.parts:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 100_000:
            large_files.append((size, str(path.relative_to(project_root))))

    report.large_files = [name for _, name in sorted(large_files, reverse=True)[:5]]
    report.complexity_hotspots = [
        "brain/pipeline.py",
        "brain/context.py",
        "agents/executor.py",
    ]
    report.dead_code_candidates = ["scripts/"] if (project_root / "scripts").exists() else []
    return report


def format_project_report(report: ProjectReport) -> str:
    """Format a structured project report for prompt injection."""
    lines = [
        f"Language: {report.language}",
        f"Framework: {report.framework}",
        f"Architecture: {report.architecture}",
        f"Build system: {report.build_system or 'unknown'}",
        f"Test framework: {report.test_framework or 'unknown'}",
        f"Dependency manager: {report.dependency_manager or 'unknown'}",
        f"Folder structure: {', '.join(report.folder_structure) or 'unknown'}",
        f"Config files: {', '.join(report.config_files) or 'none detected'}",
        f"Entry points: {', '.join(report.entry_points) or 'none detected'}",
        f"Large files: {', '.join(report.large_files) or 'none detected'}",
        f"Complexity hotspots: {', '.join(report.complexity_hotspots) or 'none detected'}",
        f"Dead code candidates: {', '.join(report.dead_code_candidates) or 'none detected'}",
    ]
    return "\n".join(lines)
