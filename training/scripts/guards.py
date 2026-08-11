"""Shared leakage / path guards for training scripts (no model I/O)."""

from __future__ import annotations

import json
from pathlib import Path


def resolve_jsonl_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(path.glob("*.jsonl"))


def iter_jsonl_rows(path: Path):
    for file_path in resolve_jsonl_files(path):
        for raw in file_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            yield file_path, json.loads(line)


def user_contents(row: dict) -> list[str]:
    out: list[str] = []
    for msg in row.get("messages") or []:
        if isinstance(msg, dict) and msg.get("role") == "user":
            out.append(str(msg.get("content", "")).strip().lower())
    return out


def assert_train_not_held_out(
    train_path: Path,
    held_path: Path,
    validation_path: Path | None = None,
) -> list[str]:
    """Return human-readable errors if train/val overlap held-out by path, id, or user text."""
    errors: list[str] = []
    train_files = resolve_jsonl_files(train_path)
    if not train_files:
        errors.append(f"No training JSONL found under {train_path}")
        return errors

    if train_path.resolve() == held_path.resolve():
        errors.append("train_path resolves to the same path as held_out_eval_path")

    held_ids: set[str] = set()
    held_users: set[str] = set()
    for _, row in iter_jsonl_rows(held_path):
        held_ids.add(str(row.get("id", "")))
        held_users.update(user_contents(row))

    check_paths = list(train_files)
    if validation_path is not None:
        check_paths.extend(resolve_jsonl_files(validation_path))

    for file_path in check_paths:
        # Path-name heuristic
        if "held_out" in str(file_path).replace("\\", "/").lower():
            errors.append(f"Refusing file that looks like held-out data: {file_path}")
            continue
        for _, row in iter_jsonl_rows(file_path):
            eid = str(row.get("id", ""))
            if eid and eid in held_ids:
                errors.append(f"Held-out id leaked into {file_path}: {eid}")
            for user in user_contents(row):
                if user and user in held_users:
                    errors.append(
                        f"Held-out user prompt leaked into {file_path} (id={eid or '?'})"
                    )
                    break
    # Deduplicate while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for err in errors:
        if err not in seen:
            seen.add(err)
            uniq.append(err)
    return uniq
