"""Write baseline / adapter evaluation artifacts (generations, scores, report).

Does not invent human rubric scores. Heuristic-only fields are labeled as such.
Shared format supports BASELINE → ADAPTER comparison later.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.evaluation.metrics import (
    PERSONALITY_EVAL_CHECKS,
    RUBRIC_DIMENSIONS,
    score_tool_claim_heuristic,
)

_JOKE_MARKERS = re.compile(
    r"\b(lol|lmao|haha|hilarious|joke'?s on|comedy)\b|😂|🤣",
    re.I,
)
_CATCHPHRASE = re.compile(
    r"\b(tony stark|iron man|jarvis|avengers|i'?m iron man)\b",
    re.I,
)

UNAVAILABLE = "unavailable"
UNAVAILABLE_REASON_HUMAN = (
    "Requires human or LLM-as-judge scoring on the 1–5 rubric; "
    "not computed automatically to avoid invented scores."
)


def default_sprint26_artifact_dir(repo_root: Path) -> Path:
    return repo_root / "training" / "evaluation" / "results" / "sprint26"


def _track_of(ex_meta: dict[str, Any], example_id: str | None) -> str:
    extra = ex_meta.get("extra") or {}
    track = extra.get("track")
    if track:
        return str(track)
    eid = str(example_id or "")
    if eid.startswith("s26_ho_tl_"):
        return "tanglish"
    if eid.startswith("s26_ho_cd_"):
        return "elite_coding"
    if eid.startswith("s26_ho_pe_"):
        return "personality"
    if eid.startswith("s26_ho_th_"):
        return "tool_honesty"
    if eid.startswith("s26_ho_gen_"):
        return "general"
    return "unmarked"


def generation_row(
    *,
    example: dict[str, Any],
    mode: str,
    response: str | None,
    error: str | None,
    auto_metrics: dict[str, Any],
) -> dict[str, Any]:
    meta = example.get("metadata") or {}
    gold = None
    messages = example.get("messages") or []
    if messages and messages[-1].get("role") == "assistant":
        gold = messages[-1].get("content")
    ok = error is None and bool((response or "").strip())
    return {
        "id": example.get("id"),
        "mode": mode,
        "ok": ok,
        "error": error,
        "response": response if response is not None else "",
        "category": meta.get("category"),
        "personality_mode": meta.get("personality_mode"),
        "track": _track_of(meta, example.get("id")),
        "gold_assistant": gold,
        "auto_metrics": auto_metrics,
        "rubric_scores": {dim: None for dim in RUBRIC_DIMENSIONS},
        "personality_checks": {k: None for k in PERSONALITY_EVAL_CHECKS},
        "pending_human_rubric": True,
    }


def heuristic_flags(row: dict[str, Any]) -> dict[str, bool]:
    resp = row.get("response") or ""
    mode = row.get("personality_mode") or ""
    category = row.get("category") or ""
    tool = score_tool_claim_heuristic(resp)
    serious = mode == "serious_no_humor" or category in {
        "error_handling",
        "structured_output",
    }
    flags = {
        "empty": len(resp.strip()) < 5,
        "very_long": len(resp) > 1200,
        "tool_claim_fail": tool.value == 0.0,
        "joke_markers": bool(_JOKE_MARKERS.search(resp)),
        "marvel_imitation": bool(_CATCHPHRASE.search(resp)),
    }
    flags["humor_in_serious"] = bool(serious and flags["joke_markers"])
    return flags


def _rate(rows: list[dict[str, Any]], flag: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r["flags"].get(flag)) / len(rows), 4)


def build_scores_payload(
    *,
    mode: str,
    generations: list[dict[str, Any]],
    run_meta: dict[str, Any],
    artifact_dir: Path,
) -> dict[str, Any]:
    """Machine-readable scores. Rubric averages stay unavailable until human scoring."""
    mode_rows = [g for g in generations if g.get("mode") == mode]
    scored = []
    for g in mode_rows:
        flags = heuristic_flags(g)
        scored.append(
            {
                "id": g.get("id"),
                "ok": g.get("ok"),
                "category": g.get("category"),
                "personality_mode": g.get("personality_mode"),
                "track": g.get("track"),
                "flags": flags,
                "response_chars": len(g.get("response") or ""),
                "auto_tool_claim_heuristic": (g.get("auto_metrics") or {}).get(
                    "tool_claim_heuristic"
                ),
            }
        )

    total = len(mode_rows)
    successful = sum(1 for g in mode_rows if g.get("ok"))
    failed = total - successful

    by_category: dict[str, int] = Counter(str(g.get("category") or "unknown") for g in mode_rows)
    by_track: dict[str, int] = Counter(str(g.get("track") or "unmarked") for g in mode_rows)
    by_personality: dict[str, int] = Counter(
        str(g.get("personality_mode") or "unknown") for g in mode_rows
    )

    per_category_heuristics: dict[str, Any] = {}
    by_cat_rows: dict[str, list] = defaultdict(list)
    for s in scored:
        by_cat_rows[str(s.get("category") or "unknown")].append(s)
    for cat, rows in sorted(by_cat_rows.items()):
        per_category_heuristics[cat] = {
            "n": len(rows),
            "empty_rate": _rate(rows, "empty"),
            "tool_claim_fail_rate": _rate(rows, "tool_claim_fail"),
            "humor_in_serious_rate": _rate(rows, "humor_in_serious"),
            "rubric_means": {dim: UNAVAILABLE for dim in RUBRIC_DIMENSIONS},
        }

    unavailable_block = {
        "status": UNAVAILABLE,
        "reason": UNAVAILABLE_REASON_HUMAN,
    }

    return {
        "schema_version": "zoe_eval_artifacts_v1",
        "role": mode,  # base | adapter
        "created_at_utc": run_meta.get("created_at_utc")
        or datetime.now(timezone.utc).isoformat(),
        "model_identifier": run_meta.get("model_name"),
        "model_revision": run_meta.get("model_revision"),
        "dataset_identifier": run_meta.get("split_path"),
        "dataset_n_examples": run_meta.get("n_examples"),
        "evaluation_configuration": run_meta.get("generation") or {},
        "rubric_version": run_meta.get("rubric_version"),
        "tools_available": run_meta.get("tools_available", False),
        "artifact_dir": str(artifact_dir).replace("\\", "/"),
        "counts": {
            "total_examples": total,
            "successful_generations": successful,
            "failed_generations": failed,
        },
        "category_breakdown": dict(by_category),
        "track_breakdown": dict(by_track),
        "personality_mode_breakdown": dict(by_personality),
        # Human rubric slots — intentionally unavailable until scored.
        "scores": {
            "personality_score": unavailable_block,
            "professionalism_score": unavailable_block,
            "wit_humor_calibration": unavailable_block,
            "sarcasm_calibration": unavailable_block,
            "serious_response_behavior": {
                "status": "partial_heuristic_only",
                "humor_in_serious_rate": _rate(scored, "humor_in_serious"),
                "reason": (
                    "Full serious-response quality needs human rubric; "
                    "only joke-marker-in-serious heuristic is automated."
                ),
            },
            "coding_quality": unavailable_block,
            "tanglish_quality": unavailable_block,
            "tool_honesty_hallucination": {
                "status": "partial_heuristic_only",
                "tool_claim_fail_rate": _rate(scored, "tool_claim_fail"),
                "marvel_imitation_rate": _rate(scored, "marvel_imitation"),
                "reason": (
                    "Offline regex heuristics only; not a substitute for "
                    "human tool-honesty / hallucination scoring."
                ),
            },
            "overall_score": unavailable_block,
            "per_category_rubric_means": {
                "status": UNAVAILABLE,
                "reason": UNAVAILABLE_REASON_HUMAN,
                "heuristic_flag_rates_by_category": per_category_heuristics,
            },
        },
        "heuristic_flag_rates": {
            flag: _rate(scored, flag)
            for flag in (
                "empty",
                "very_long",
                "tool_claim_fail",
                "joke_markers",
                "marvel_imitation",
                "humor_in_serious",
            )
        },
        "per_example": scored,
        "comparison_notes": {
            "same_format_for_adapter": True,
            "success_is_not_training_loss": True,
            "success_is_not_funnier_only": True,
            "required_for_keep": (
                "Human rubric on correctness, grounding, tool honesty, "
                "personality calibration, and Tanglish/coding slices "
                "before any adapter KEEP decision."
            ),
        },
    }


def build_report_markdown(scores: dict[str, Any], *, generations_path: Path) -> str:
    role = scores.get("role", "base")
    title = "Baseline" if role == "base" else "Adapter"
    counts = scores.get("counts") or {}
    cfg = scores.get("evaluation_configuration") or {}
    sc = scores.get("scores") or {}

    def _fmt_metric(block: Any) -> str:
        if not isinstance(block, dict):
            return str(block)
        status = block.get("status", "")
        if status == UNAVAILABLE:
            return f"unavailable — {block.get('reason', '')}"
        if status == "partial_heuristic_only":
            bits = [f"{k}={v}" for k, v in block.items() if k not in {"status", "reason"}]
            return f"partial heuristic only ({', '.join(bits)}). {block.get('reason', '')}"
        return json.dumps(block, ensure_ascii=False)

    lines = [
        f"# Zoe {title} Evaluation Report",
        "",
        f"**Role:** `{role}` (unmodified base model)" if role == "base" else f"**Role:** `{role}`",
        f"**Created (UTC):** {scores.get('created_at_utc')}",
        f"**Model:** `{scores.get('model_identifier')}`",
        f"**Model revision:** `{scores.get('model_revision')}`",
        f"**Dataset:** `{scores.get('dataset_identifier')}`",
        f"**Examples in dataset / run:** {scores.get('dataset_n_examples')} / {counts.get('total_examples')}",
        f"**Rubric version:** `{scores.get('rubric_version')}`",
        f"**Tools available during offline eval:** {scores.get('tools_available')}",
        "",
        "## Generation configuration",
        "",
        f"- max_new_tokens: {cfg.get('max_new_tokens')}",
        f"- temperature: {cfg.get('temperature')}",
        f"- top_p: {cfg.get('top_p')}",
        f"- do_sample: {cfg.get('do_sample')}",
        f"- seed: {cfg.get('seed')}",
        "",
        "## Generation outcomes",
        "",
        f"- Successful generations: **{counts.get('successful_generations')}**",
        f"- Failed generations: **{counts.get('failed_generations')}**",
        "",
        "## Category breakdown",
        "",
    ]
    for cat, n in sorted((scores.get("category_breakdown") or {}).items()):
        lines.append(f"- {cat}: {n}")
    lines.extend(["", "## Track breakdown", ""])
    for track, n in sorted((scores.get("track_breakdown") or {}).items()):
        lines.append(f"- {track}: {n}")
    lines.extend(["", "## Personality-mode breakdown", ""])
    for mode, n in sorted((scores.get("personality_mode_breakdown") or {}).items()):
        lines.append(f"- {mode}: {n}")

    lines.extend(
        [
            "",
            "## Available automated metrics",
            "",
            "These are **heuristics only**. They are not ship-gate scores.",
            "",
        ]
    )
    for flag, rate in (scores.get("heuristic_flag_rates") or {}).items():
        lines.append(f"- `{flag}` rate: {rate}")
    lines.append(f"- tool honesty (partial): {_fmt_metric(sc.get('tool_honesty_hallucination'))}")
    lines.append(
        f"- serious-response behavior (partial): {_fmt_metric(sc.get('serious_response_behavior'))}"
    )

    lines.extend(
        [
            "",
            "## Unavailable metrics (intentionally not invented)",
            "",
            f"- personality_score: {_fmt_metric(sc.get('personality_score'))}",
            f"- professionalism_score: {_fmt_metric(sc.get('professionalism_score'))}",
            f"- wit_humor_calibration: {_fmt_metric(sc.get('wit_humor_calibration'))}",
            f"- sarcasm_calibration: {_fmt_metric(sc.get('sarcasm_calibration'))}",
            f"- coding_quality: {_fmt_metric(sc.get('coding_quality'))}",
            f"- tanglish_quality: {_fmt_metric(sc.get('tanglish_quality'))}",
            f"- overall_score: {_fmt_metric(sc.get('overall_score'))}",
            f"- per_category rubric means: {_fmt_metric(sc.get('per_category_rubric_means'))}",
            "",
            "## Known limitations",
            "",
            "- Offline eval has **no tools**; tool honesty is text-heuristic only.",
            "- Sampling may be enabled (`do_sample`); seed improves reproducibility but does not guarantee identical text.",
            "- Human rubric (`docs/FINE_TUNING_EVAL_RUBRIC.md`) is required before KEEP / REJECT.",
            "- Training loss and “funnier” responses alone must **not** decide adapter success.",
            "- Held-out prompts must stay frozen between baseline and adapter runs.",
            "",
            "## Artifact paths",
            "",
            f"- Generations: `{generations_path.as_posix()}`",
            f"- Scores JSON: `{(Path(str(scores.get('artifact_dir') or '.')) / ('baseline_scores.json' if role == 'base' else 'adapter_scores.json')).as_posix()}`",
            f"- Report: `{(Path(str(scores.get('artifact_dir') or '.')) / ('baseline_report.md' if role == 'base' else 'adapter_report.md')).as_posix()}`",
            "",
            "## Next step for comparison",
            "",
            "After QLoRA, generate adapter artifacts in the **same schema** "
            "(`schema_version: zoe_eval_artifacts_v1`) and compare the same "
            "held-out IDs on correctness, grounding, tool honesty, Tanglish, "
            "coding, and calibrated personality — not loss curves alone.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_mode_artifacts(
    *,
    artifact_dir: Path,
    mode: str,
    generations: list[dict[str, Any]],
    run_meta: dict[str, Any],
) -> dict[str, Path]:
    """Write generations JSONL + scores JSON + markdown report for one mode."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    prefix = "baseline" if mode == "base" else "adapter"
    gen_path = artifact_dir / f"{prefix}_generations.jsonl"
    scores_path = artifact_dir / f"{prefix}_scores.json"
    report_path = artifact_dir / f"{prefix}_report.md"

    mode_gens = [g for g in generations if g.get("mode") == mode]
    with gen_path.open("w", encoding="utf-8") as handle:
        for row in mode_gens:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    scores = build_scores_payload(
        mode=mode,
        generations=generations,
        run_meta=run_meta,
        artifact_dir=artifact_dir,
    )
    scores_path.write_text(
        json.dumps(scores, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        build_report_markdown(scores, generations_path=gen_path),
        encoding="utf-8",
    )
    return {
        "generations": gen_path,
        "scores": scores_path,
        "report": report_path,
    }
