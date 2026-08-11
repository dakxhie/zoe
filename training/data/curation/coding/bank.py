"""Sprint 25 coding training bank aggregation; excludes held-out evaluations."""
from __future__ import annotations

from training.data.curation.coding.bank_core import examples as core_examples
from training.data.curation.coding.bank_debug import examples as debug_examples
from training.data.curation.coding.bank_review import examples as review_examples
from training.data.curation.coding.bank_tool_honesty import examples as tool_honesty_examples


def examples() -> list[dict]:
    """Return only training examples; held_out.py is intentionally excluded."""
    return [
        *core_examples(),
        *debug_examples(),
        *review_examples(),
        *tool_honesty_examples(),
    ]
