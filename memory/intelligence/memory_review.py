"""Memory intelligence pipeline: scoring, consolidation, reinforcement, review."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from memory.detector import should_remember
from memory.inference import infer_memory
from memory.intelligence.consolidation import consolidate_with_existing
from memory.intelligence.forgetting import is_explicit_remember_request, should_forget
from memory.intelligence.memory_scoring import score_memory_text
from memory.intelligence.memory_types import MemoryType, ScoredMemory
from memory.intelligence.profile_builder import build_user_profile
from memory.intelligence.reinforcement import reinforce_scored_memory

logger = logging.getLogger(__name__)

MIN_STORE_IMPORTANCE = 0.35


@dataclass
class MemoryReviewStats:
    """Summary of a periodic memory review pass."""

    merged: int = 0
    deleted_expired: int = 0
    reinforced: int = 0
    examined: int = 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_store_helpers():
    from memory.store import (
        delete_memory_by_id,
        iter_memory_documents,
        save_scored_memory,
        update_scored_memory,
    )

    return delete_memory_by_id, iter_memory_documents, save_scored_memory, update_scored_memory


def _resolve_candidate_text(user_text: str, assistant_text: str | None = None) -> str | None:
    if should_remember(user_text):
        return user_text.strip()

    from memory.history import get_history

    previous_assistant = assistant_text
    if previous_assistant is None:
        for message in reversed(get_history()):
            if message["role"] == "assistant":
                previous_assistant = message["content"]
                break

    inferred = infer_memory(user_text, previous_assistant)
    if inferred:
        return inferred.strip()
    return None


def _find_reinforcement_target(
    candidate: str,
    documents: list[dict[str, Any]],
    *,
    explicit: bool,
) -> tuple[str, ScoredMemory] | None:
    for doc in documents:
        text = doc.get("text", "")
        meta = doc.get("metadata", {})
        reinforced = reinforce_scored_memory(text, meta, candidate, explicit=explicit)
        if reinforced is not None:
            return doc["id"], reinforced
    return None


def process_memory_candidate(
    user_text: str,
    *,
    route_hint: str = "",
    assistant_text: str | None = None,
) -> bool:
    """
    Run the intelligence pipeline for one candidate utterance.

    Scoring → forget filter → reinforcement → consolidation → store.
    """
    resolved = _resolve_candidate_text(user_text, assistant_text)
    if not resolved:
        return False

    explicit = is_explicit_remember_request(user_text) or should_remember(user_text)

    if should_forget(resolved, route_hint=route_hint) and not explicit:
        return False

    scored = score_memory_text(resolved, explicit=explicit)

    if scored.importance < MIN_STORE_IMPORTANCE and not explicit:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Ignored trivial memory: importance below threshold")
        return False

    delete_memory_by_id, iter_memory_documents, save_scored_memory, update_scored_memory = (
        _load_store_helpers()
    )

    try:
        documents = iter_memory_documents()
    except Exception as exc:
        logger.warning("Memory intelligence skipped (storage unavailable): %s", exc)
        return False

    existing_texts = [d.get("text", "") for d in documents]

    target = _find_reinforcement_target(resolved, documents, explicit=explicit)
    if target is not None:
        memory_id, reinforced = target
        others = [d.get("text", "") for d in documents if d["id"] != memory_id]
        reinforced.text = consolidate_with_existing(reinforced.text, others)
        return update_scored_memory(memory_id, reinforced)

    consolidated_text = consolidate_with_existing(resolved, existing_texts)
    scored.text = consolidated_text
    if scored.memory_type == MemoryType.TEMPORARY:
        scored.expires_at = _utc_now_iso()

    return save_scored_memory(scored)


def process_post_turn_memory(user_prompt: str, assistant_reply: str, *, route_hint: str = "") -> None:
    """After each conversation turn, process memory and run a lightweight review."""
    try:
        process_memory_candidate(
            user_prompt,
            route_hint=route_hint,
            assistant_text=assistant_reply,
        )
    except Exception as exc:
        logger.warning("Post-turn memory processing failed: %s", exc)

    try:
        run_memory_review(lightweight=True)
    except Exception as exc:
        logger.warning("Memory review failed: %s", exc)


def run_memory_review(*, lightweight: bool = False) -> MemoryReviewStats:
    """
    Periodically merge duplicates, drop expired temporary memories, refresh profile.

    When lightweight=True, only expiration cleanup and profile refresh run.
    """
    stats = MemoryReviewStats()
    delete_memory_by_id, iter_memory_documents, save_scored_memory, update_scored_memory = (
        _load_store_helpers()
    )

    try:
        documents = iter_memory_documents()
    except Exception:
        return stats

    stats.examined = len(documents)
    now = datetime.now(timezone.utc)

    for doc in list(documents):
        meta = doc.get("metadata", {})
        expires = meta.get("expires_at", "")
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                if exp_dt <= now:
                    delete_memory_by_id(doc["id"])
                    stats.deleted_expired += 1
            except ValueError:
                pass

    if lightweight:
        _refresh_internal_profile(documents)
        return stats

    texts_by_id = {d["id"]: d.get("text", "") for d in documents}
    seen: set[str] = set()

    for doc in documents:
        doc_id = doc["id"]
        if doc_id in seen:
            continue
        text = doc.get("text", "")
        for other_id, other_text in texts_by_id.items():
            if other_id == doc_id or other_id in seen:
                continue
            from memory.intelligence.consolidation import try_merge_pair

            merged = try_merge_pair(text, other_text)
            if merged and merged != text:
                meta = doc.get("metadata", {})
                scored = score_memory_text(
                    merged,
                    frequency=int(meta.get("frequency", "1")) + 1,
                    existing_confidence=float(meta.get("confidence", "0.75")),
                )
                scored.created = meta.get("created_at", scored.created)
                update_scored_memory(doc_id, scored)
                delete_memory_by_id(other_id)
                seen.add(other_id)
                stats.merged += 1
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Merged duplicate during review")

    _refresh_internal_profile(iter_memory_documents())
    return stats


def _refresh_internal_profile(documents: list[dict[str, Any]]) -> None:
    records: list[dict[str, str]] = []
    for doc in documents:
        meta = doc.get("metadata", {})
        records.append(
            {
                "text": doc.get("text", ""),
                "category": meta.get("category", meta.get("memory_type", "")),
                "importance": meta.get("importance", "0"),
            }
        )
    build_user_profile(records)


def respond_to_profile_query(user_prompt: str) -> str | None:
    """Return a direct reply for profile / learned-summary questions."""
    from memory.intelligence.profile_builder import (
        format_profile_summary_for_user,
        is_learned_summary_query,
    )
    from memory.store import iter_memory_documents

    if not is_learned_summary_query(user_prompt):
        return None

    try:
        documents = iter_memory_documents()
    except Exception:
        documents = []

    records = [
        {
            "text": d.get("text", ""),
            "category": d.get("metadata", {}).get("category", ""),
            "importance": d.get("metadata", {}).get("importance", "0"),
        }
        for d in documents
    ]
    profile = build_user_profile(records)
    return format_profile_summary_for_user(profile)
