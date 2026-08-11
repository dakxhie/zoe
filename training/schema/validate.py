"""Validate Zoe SFT / correction JSONL records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from training.schema import (
    ALLOWED_ROLES,
    CATEGORIES,
    DIFFICULTIES,
    PERSONALITY_MODES,
    CorrectionExample,
    SFTExample,
)


@dataclass
class ValidationIssue:
    path: str
    line: int
    level: str  # error | warning
    code: str
    message: str


@dataclass
class ValidationReport:
    files_checked: int = 0
    examples_checked: int = 0
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        return (
            f"files={self.files_checked} examples={self.examples_checked} "
            f"errors={len(self.errors)} warnings={len(self.warnings)}"
        )


def _issue(
    path: str,
    line: int,
    level: str,
    code: str,
    message: str,
) -> ValidationIssue:
    return ValidationIssue(path=path, line=line, level=level, code=code, message=message)


def validate_messages(messages: Any, path: str, line: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(messages, list) or not messages:
        return [
            _issue(path, line, "error", "messages_missing", "messages must be a non-empty list")
        ]

    roles_seen: list[str] = []
    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            issues.append(
                _issue(path, line, "error", "message_type", f"messages[{idx}] must be an object")
            )
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in ALLOWED_ROLES:
            issues.append(
                _issue(
                    path,
                    line,
                    "error",
                    "bad_role",
                    f"messages[{idx}].role must be system|user|assistant",
                )
            )
        else:
            roles_seen.append(str(role))
        if not isinstance(content, str) or not content.strip():
            issues.append(
                _issue(
                    path,
                    line,
                    "error",
                    "empty_content",
                    f"messages[{idx}].content must be non-empty string",
                )
            )
        # Guard: metadata keys accidentally nested into content is hard to detect;
        # reject explicit metadata field on message objects.
        if "metadata" in msg:
            issues.append(
                _issue(
                    path,
                    line,
                    "error",
                    "metadata_in_message",
                    "message objects must not contain metadata",
                )
            )

    if "user" not in roles_seen or "assistant" not in roles_seen:
        issues.append(
            _issue(
                path,
                line,
                "error",
                "missing_roles",
                "example must include at least one user and one assistant message",
            )
        )
    if roles_seen and roles_seen[-1] != "assistant":
        issues.append(
            _issue(
                path,
                line,
                "warning",
                "last_not_assistant",
                "last message should be assistant for SFT targets",
            )
        )
    return issues


def validate_metadata(meta: Any, path: str, line: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if meta is None:
        issues.append(_issue(path, line, "warning", "no_metadata", "metadata missing"))
        return issues
    if not isinstance(meta, dict):
        return [_issue(path, line, "error", "metadata_type", "metadata must be an object")]

    category = meta.get("category")
    if category not in CATEGORIES:
        issues.append(
            _issue(
                path,
                line,
                "error",
                "bad_category",
                f"category must be one of {CATEGORIES}",
            )
        )

    difficulty = meta.get("difficulty", "medium")
    if difficulty not in DIFFICULTIES:
        issues.append(
            _issue(path, line, "error", "bad_difficulty", f"difficulty must be one of {DIFFICULTIES}")
        )

    mode = meta.get("personality_mode", "professional_neutral")
    if mode not in PERSONALITY_MODES:
        issues.append(
            _issue(
                path,
                line,
                "error",
                "bad_personality_mode",
                f"personality_mode must be one of {PERSONALITY_MODES}",
            )
        )

    quality = meta.get("quality", 1.0)
    if not isinstance(quality, (int, float)) or not (0.0 <= float(quality) <= 1.0):
        issues.append(
            _issue(path, line, "error", "bad_quality", "quality must be a float in [0, 1]")
        )

    for key in ("personality_required", "tool_required", "safety_sensitive"):
        if key in meta and not isinstance(meta[key], bool):
            issues.append(_issue(path, line, "error", f"bad_{key}", f"{key} must be boolean"))

    return issues


def validate_sft_record(record: dict[str, Any], path: str, line: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if "id" not in record or not str(record["id"]).strip():
        issues.append(_issue(path, line, "error", "missing_id", "id is required"))
    issues.extend(validate_messages(record.get("messages"), path, line))
    issues.extend(validate_metadata(record.get("metadata"), path, line))

    # Reject if metadata leaked into a top-level field that might be concatenated into prompts.
    forbidden_top = {"prompt", "completion", "text", "input", "output"}
    for key in forbidden_top:
        if key in record:
            issues.append(
                _issue(
                    path,
                    line,
                    "warning",
                    "alt_format_field",
                    f"unexpected field '{key}'; prefer messages-only chat format",
                )
            )
    return issues


def validate_correction_record(
    record: dict[str, Any], path: str, line: int
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    required = (
        "id",
        "user_request",
        "bad_response",
        "why_bad",
        "ideal_response",
        "lesson",
    )
    for key in required:
        val = record.get(key)
        if not isinstance(val, str) or not val.strip():
            issues.append(
                _issue(path, line, "error", f"missing_{key}", f"{key} must be a non-empty string")
            )
    category = record.get("category", "error_handling")
    if category not in CATEGORIES:
        issues.append(
            _issue(path, line, "error", "bad_category", f"category must be one of {CATEGORIES}")
        )
    return issues


def _iter_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    text = path.read_text(encoding="utf-8")
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON ({exc})") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: each line must be a JSON object")
        rows.append((line_no, obj))
    return rows


def validate_jsonl_file(path: Path, *, kind: str = "sft") -> ValidationReport:
    report = ValidationReport(files_checked=1)
    try:
        rows = _iter_jsonl(path)
    except ValueError as exc:
        report.errors.append(
            _issue(str(path), 0, "error", "jsonl_parse", str(exc))
        )
        return report

    seen_ids: set[str] = set()
    content_hashes: set[str] = set()

    for line_no, record in rows:
        report.examples_checked += 1
        if kind == "correction":
            issues = validate_correction_record(record, str(path), line_no)
        else:
            issues = validate_sft_record(record, str(path), line_no)

        example_id = str(record.get("id", ""))
        if example_id:
            if example_id in seen_ids:
                issues.append(
                    _issue(str(path), line_no, "error", "duplicate_id", f"duplicate id {example_id}")
                )
            seen_ids.add(example_id)

        # Soft dedupe on assistant content / ideal response
        if kind == "sft":
            messages = record.get("messages") or []
            assistant_bits = [
                m.get("content", "")
                for m in messages
                if isinstance(m, dict) and m.get("role") == "assistant"
            ]
            blob = "\n".join(assistant_bits).strip().lower()
        else:
            blob = str(record.get("ideal_response", "")).strip().lower()
        if blob:
            digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
            if digest in content_hashes:
                issues.append(
                    _issue(
                        str(path),
                        line_no,
                        "warning",
                        "near_duplicate_assistant",
                        "assistant/ideal text duplicates an earlier example",
                    )
                )
            content_hashes.add(digest)

        for issue in issues:
            if issue.level == "error":
                report.errors.append(issue)
            else:
                report.warnings.append(issue)

    return report


def validate_paths(paths: list[Path], *, kind: str = "sft") -> ValidationReport:
    combined = ValidationReport()
    for path in paths:
        if path.is_dir():
            files = sorted(path.glob("*.jsonl"))
        else:
            files = [path]
        for file_path in files:
            part = validate_jsonl_file(file_path, kind=kind)
            combined.files_checked += part.files_checked
            combined.examples_checked += part.examples_checked
            combined.errors.extend(part.errors)
            combined.warnings.extend(part.warnings)
    return combined


def parse_sft_example(record: dict[str, Any]) -> SFTExample:
    """Parse a validated-ish dict into SFTExample (caller should validate first)."""
    from training.schema import ChatMessage, ExampleMetadata

    meta_raw = record.get("metadata") or {}
    meta = ExampleMetadata(
        category=str(meta_raw.get("category", "general_conversation")),
        difficulty=str(meta_raw.get("difficulty", "medium")),
        source=str(meta_raw.get("source", "unknown")),
        quality=float(meta_raw.get("quality", 1.0)),
        personality_mode=str(meta_raw.get("personality_mode", "professional_neutral")),
        personality_required=bool(meta_raw.get("personality_required", False)),
        tool_required=bool(meta_raw.get("tool_required", False)),
        expected_behavior=str(meta_raw.get("expected_behavior", "")),
        safety_sensitive=bool(meta_raw.get("safety_sensitive", False)),
        extra=dict(meta_raw.get("extra") or {}),
    )
    messages = [
        ChatMessage(role=m["role"], content=m["content"])  # type: ignore[arg-type]
        for m in record["messages"]
    ]
    return SFTExample(id=str(record["id"]), messages=messages, metadata=meta)


def parse_correction_example(record: dict[str, Any]) -> CorrectionExample:
    return CorrectionExample(
        id=str(record["id"]),
        user_request=str(record["user_request"]),
        bad_response=str(record["bad_response"]),
        why_bad=str(record["why_bad"]),
        ideal_response=str(record["ideal_response"]),
        lesson=str(record["lesson"]),
        category=str(record.get("category", "error_handling")),
        source=str(record.get("source", "regression_inspired")),
        safety_sensitive=bool(record.get("safety_sensitive", False)),
    )
