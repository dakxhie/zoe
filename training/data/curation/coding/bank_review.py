"""Sprint 25 code-review examples (100 rows)."""
from __future__ import annotations

from training.data.curation.coding import coding_sft


FINDINGS: list[tuple[str, str, str, bool]] = [
    ("A function catches `Exception` and returns None.", "Catch only expected exceptions and preserve context for unexpected failures.", "Callers cannot distinguish a valid empty result from a broken operation.", False),
    ("A SQL query uses an f-string with request data.", "Replace interpolation with parameter binding.", "Raw request data can change query structure and enable injection.", True),
    ("A React list uses its array index as key.", "Use a stable domain ID when rows can change order.", "Index keys can retain the wrong component state.", False),
    ("A password is written to an application log.", "Remove the field, redact the log pipeline, and rotate any exposed credential.", "Logs are not a secret store.", True),
    ("A Node fetch has no timeout.", "Use AbortSignal or the client timeout facility with an appropriate budget.", "A stalled dependency can consume all request capacity.", False),
    ("A migration drops a column in the same deploy that removes usage.", "Use an expand/migrate/contract sequence and verify no old version still reads it.", "Rolling deployments can run old and new code together.", True),
    ("A helper accepts twelve positional parameters.", "Group related inputs into a named options object or domain type.", "Named structure makes calls and future changes safer.", False),
    ("A boolean is named `isNotDisabled`.", "Rename to a positive business predicate such as `isEnabled`.", "Double negatives make conditions easy to misread.", False),
    ("A retry loop repeats POST requests without an idempotency key.", "Retry only safe operations or send a persisted idempotency key.", "Timeout does not prove the first write failed.", False),
    ("A test asserts internal private method calls.", "Assert externally observable behavior unless the internal interaction is the contract.", "Implementation-coupled tests block refactoring.", False),
    ("A route returns a stack trace to clients.", "Return a safe error envelope and log the detailed exception server-side with redaction.", "Stack traces expose internals and sometimes secrets.", True),
    ("A cache lookup has no TTL or invalidation plan.", "Specify freshness, invalidation triggers, and behavior on cache failure.", "Without them, speed eventually becomes stale correctness.", False),
    ("A config default contains a production API key.", "Read secrets from a managed secret source and remove/rotate the committed key.", "Repository history and builds can expose the key.", True),
    ("A loop performs one database query per item.", "Batch, prefetch, or join according to the access pattern.", "N+1 work grows latency and database load linearly.", False),
    ("An HTML input has placeholder text but no label.", "Add a visible or programmatic label associated with the control.", "Placeholder disappears and is not a reliable accessible name.", False),
    ("An API accepts arbitrary sort field names.", "Allowlist supported fields and map them to trusted query expressions.", "Dynamic identifiers cannot be safely parameterized like values.", True),
    ("A promise is launched without await, return, or catch.", "Make the background contract explicit and handle/report failures.", "Otherwise errors are detached from the request and may be unhandled.", False),
    ("A git instruction recommends force-pushing main.", "Use a normal revert or coordinated recovery for shared branches.", "Rewriting shared history can discard others' work.", True),
    ("A service constructs its own database client in every method.", "Inject a shared dependency behind an interface or factory.", "Construction is expensive and makes tests and configuration harder.", False),
    ("The PR changes behavior and formatting in one huge diff.", "Split formatting from behavior or use separate commits.", "Reviewers need to see the semantic change through the noise.", False),
]

REQUESTS = [
    "Review this finding: {finding}",
    "Write a constructive PR comment for: {finding}",
    "What improvement would you request? {finding}",
    "Give a concise code-review suggestion: {finding}",
    "Review for correctness and maintainability: {finding}",
]


def examples() -> list[dict]:
    out: list[dict] = []
    for finding_index, (finding, improvement, rationale, sensitive) in enumerate(FINDINGS):
        for request_index, request in enumerate(REQUESTS):
            number = 441 + finding_index * len(REQUESTS) + request_index
            mode = "serious_no_humor" if sensitive else "professional_neutral"
            answer = (
                f"Review: {improvement} Why: {rationale} "
                "Suggested next step: add or update a focused test and document any changed contract. "
                "This is a review recommendation, not a claim that I changed or tested the code."
            )
            out.append(coding_sft(
                f"s25_code_{number:03d}",
                request.format(finding=finding),
                answer,
                category="structured_output" if request_index == 3 else "coding",
                personality_mode=mode,
                difficulty="medium",
                safety_sensitive=sensitive,
                subtopic="code_review",
            ))
    return out
