"""Sprint 24 dataset integrity audit (no model download / no training)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        obj = json.loads(line)
        obj["_line"] = line_no
        rows.append(obj)
    return rows


def _role_text(row: dict, role: str) -> str:
    return "\n".join(
        m.get("content", "")
        for m in row.get("messages", [])
        if isinstance(m, dict) and m.get("role") == role
    ).strip()


def audit(
    clean_path: Path,
    held_path: Path,
    corrections_path: Path | None = None,
) -> dict:
    sft = _load_jsonl(clean_path)
    held = _load_jsonl(held_path)
    corrections = _load_jsonl(corrections_path) if corrections_path and corrections_path.exists() else []

    held_ids = {str(r.get("id", "")) for r in held}
    held_users = {_role_text(r, "user").lower() for r in held if _role_text(r, "user")}

    leak_ids = sorted({str(r.get("id", "")) for r in sft} & held_ids)
    leak_users = [
        str(r.get("id", ""))
        for r in sft
        if _role_text(r, "user").lower() in held_users
    ]

    id_counts = Counter(str(r.get("id", "")) for r in sft)
    dup_ids = sorted([i for i, n in id_counts.items() if n > 1 and i])

    asst_map: dict[str, str] = {}
    near_asst: list[list[str]] = []
    for r in sft:
        blob = _role_text(r, "assistant").lower()
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        eid = str(r.get("id", ""))
        if digest in asst_map:
            near_asst.append([asst_map[digest], eid])
        else:
            asst_map[digest] = eid

    user_map: dict[str, str] = {}
    near_user: list[list[str]] = []
    for r in sft:
        blob = _role_text(r, "user").lower()
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        eid = str(r.get("id", ""))
        if digest in user_map:
            near_user.append([user_map[digest], eid])
        else:
            user_map[digest] = eid

    marvel_re = re.compile(
        r"\b(tony stark|iron man|jarvis|avengers|marvel comics|i'?m iron man)\b",
        re.I,
    )
    tool_claim_re = re.compile(
        r"\bi (?:just )?(?:ran|checked|searched|executed|queried) "
        r"(?:the )?(?:calculator|database|plugin|web|filesystem|chroma)\b",
        re.I,
    )
    secret_re = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")

    marvel_hits: list[str] = []
    tool_hall: list[str] = []
    secrets: list[str] = []
    current_date_claims: list[str] = []

    for r in sft:
        eid = str(r.get("id", ""))
        user = _role_text(r, "user")
        asst = _role_text(r, "assistant")
        if marvel_re.search(asst) or marvel_re.search(user):
            marvel_hits.append(eid)
        if tool_claim_re.search(asst):
            # Allow explaining after an explicit tool result in the user turn.
            if "tool result" not in user.lower() and "returned" not in user.lower():
                tool_hall.append(eid)
        if secret_re.search(user) or secret_re.search(asst):
            secrets.append(eid)
        if re.search(r"\btoday is\b|\bcurrent date is\b", asst, re.I):
            if "tool" not in user.lower() and "datetime" not in user.lower():
                current_date_claims.append(eid)

    modes = Counter((r.get("metadata") or {}).get("personality_mode", "?") for r in sft)
    cats = Counter((r.get("metadata") or {}).get("category", "?") for r in sft)
    n = len(sft) or 1

    return {
        "sft_rows": len(sft),
        "held_out_rows": len(held),
        "correction_rows": len(corrections),
        "categories": dict(cats),
        "personality_modes": dict(modes),
        "personality_mode_pct": {k: round(100 * v / n, 2) for k, v in modes.items()},
        "leakage": {
            "shared_ids": leak_ids,
            "shared_user_prompt_ids": leak_users,
            "ok": not leak_ids and not leak_users,
        },
        "duplicates": {
            "duplicate_ids": dup_ids,
            "exact_assistant_dup_pairs": near_asst,
            "exact_user_dup_pairs": near_user,
        },
        "content_flags": {
            "marvel_or_tony_hits": marvel_hits,
            "possible_tool_hallucination_claims": tool_hall,
            "possible_secrets": secrets,
            "unsolicited_current_date_claims": current_date_claims,
        },
        "correction_categories": dict(
            Counter(str(r.get("category", "?")) for r in corrections)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Zoe SFT vs held-out integrity.")
    parser.add_argument(
        "--clean",
        type=Path,
        default=_REPO / "training" / "data" / "clean" / "sft_sprint23.jsonl",
    )
    parser.add_argument(
        "--held-out",
        type=Path,
        default=_REPO / "training" / "data" / "held_out_eval" / "eval_sprint23.jsonl",
    )
    parser.add_argument(
        "--corrections",
        type=Path,
        default=_REPO / "training" / "data" / "corrections" / "corrections_sprint23.jsonl",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=_REPO / "training" / "data" / "clean" / "sprint24_audit.json",
    )
    args = parser.parse_args(argv)
    result = audit(args.clean, args.held_out, args.corrections)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["leakage"]["ok"] and not result["duplicates"]["duplicate_ids"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
