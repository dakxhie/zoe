"""Sprint 25 debugging examples (180 rows)."""
from __future__ import annotations

from training.data.curation.coding import coding_sft


CASES: list[tuple[str, str, str, str, str, bool]] = [
    ("Python list grows between calls", "A mutable default list is shared between calls.", "Use None as the default and create a list inside the function.", "Defaults are evaluated once when the function is defined.", "Call it twice to confirm state is not retained.", False),
    ("KeyError after JSON parsing", "The payload does not always contain the assumed key.", "Validate the schema and use an explicit missing-field error or a deliberate default.", "External JSON is not a typed contract.", "Do not hide a required field with get(..., None).", False),
    ("async endpoint becomes slow under load", "Blocking I/O is running on the event loop.", "Use an async client or move the blocking operation to a bounded worker pool.", "One blocking call stalls unrelated coroutines.", "Do not create unlimited threads as a workaround.", False),
    ("React list shows wrong rows after deletion", "Array indexes are being used as keys for changing data.", "Use a stable item ID as the key.", "React uses keys to preserve component identity.", "Index keys are acceptable only for static lists with no reorder.", False),
    ("useEffect loops forever", "The effect updates a value that changes one of its dependencies.", "Separate derived state, guard the update, or correct the dependency design.", "Each render schedules another effect when dependencies keep changing.", "Do not remove dependencies merely to silence the linter.", False),
    ("Node request hangs forever", "An outbound call has no timeout or the response stream is not completed.", "Set a timeout/abort signal and ensure every branch sends or ends a response.", "Network operations and open responses can wait indefinitely.", "Timeout values should fit the upstream service budget.", False),
    ("CORS works locally but fails in browser production", "The production origin is not allowed, or credentials conflict with a wildcard origin.", "Allow the exact trusted origin and configure credentials deliberately.", "Browsers enforce CORS; curl does not.", "Test preflight OPTIONS as well as the actual method.", False),
    ("SQL query is fast in development but slow in production", "Production cardinality or indexes differ from development.", "Inspect the production-like query plan and add or revise an index based on the filter/join pattern.", "Small dev tables hide full-scan costs.", "An index can slow writes and consume storage.", False),
    ("duplicate orders appear after a retry", "A timed-out client retried a non-idempotent create request.", "Use an idempotency key stored with the operation and return the original result on repeats.", "The first request may have succeeded before the timeout.", "Expire keys only after the business retry window.", False),
    ("Appwrite request is unauthorized", "The client endpoint/project/session or document permissions do not match the caller.", "Confirm configuration, authentication state, and document or collection permissions against the installed SDK docs.", "Authorization is evaluated for the current client context.", "Do not weaken permissions to make the error disappear.", True),
    ("Git merge has unexpected file changes", "The branches changed overlapping lines or generated files are stale.", "Inspect conflict markers and the diff; resolve intended behavior, then regenerate only if the project requires it.", "Git cannot infer semantic intent from overlapping edits.", "Run the relevant tests before declaring the merge safe.", False),
    ("environment variable is None in production", "The deployment did not inject it, the name differs, or the process read configuration before it existed.", "Validate required variables at startup and fail with a redacted actionable message.", "Local shell state is not production configuration.", "Never print the secret value while diagnosing.", True),
    ("logs expose authorization headers", "Request objects or headers are logged without redaction.", "Redact or allowlist fields before logging; rotate any credential already emitted.", "Logs often have broad retention and access.", "Check traces, error reports, and log exports too.", True),
    ("CSS overlay appears behind modal", "A stacking context or z-index hierarchy changes the expected order.", "Inspect positioned ancestors and stacking contexts; place the overlay in an appropriate top-level layer.", "z-index compares within stacking contexts, not globally.", "Transforms and opacity can create new stacking contexts.", False),
    ("HTML form field is not announced", "The input lacks a programmatic label or its error is not associated.", "Use label for/id and connect validation feedback with aria-describedby when needed.", "Visual proximity is not a label for assistive technology.", "Test keyboard focus and error announcement.", False),
    ("TypeScript compiles but crashes on API data", "A type assertion trusted unvalidated runtime input.", "Parse unknown input with a schema/guard before treating it as the expected type.", "TypeScript types are erased at runtime.", "Keep error messages safe when validation fails.", False),
    ("Promise rejection is unhandled", "A promise was created without await/catch, often in a fire-and-forget path.", "Await it, return it, or attach deliberate error handling with logging.", "Unhandled rejections lose context and may terminate the process.", "Do not catch and ignore operational errors.", False),
    ("memory usage climbs after every request", "A cache, listener, timer, or retained request object is never released.", "Profile allocations and bound caches; remove listeners/timers during cleanup.", "Long-lived references prevent garbage collection.", "Distinguish a one-time warm-up from an unbounded trend.", False),
    ("test passes alone but fails in suite", "Shared mutable state, order dependence, or leaked mocks affect later tests.", "Reset state in fixtures and isolate mocks, temp files, databases, and clocks.", "Tests must not depend on execution order.", "A retry may mask the dependency rather than fix it.", False),
    ("timezone date is off by one day", "A date-only value was parsed or rendered as a timezone-specific timestamp.", "Represent date-only fields separately; use explicit UTC/zone conversions for instants.", "A calendar date and a moment in time are different concepts.", "Test near midnight in more than one timezone.", False),
    ("pagination returns duplicate or missing records", "Offset pagination is used while the ordered data changes, or ordering is not stable.", "Use a stable sort with cursor pagination based on a unique tie-breaker.", "Changing rows shift offsets between requests.", "Define how clients handle deleted cursor records.", False),
    ("webhook events are processed twice", "The provider retries delivery or the receiver lacks deduplication.", "Verify signatures and persist event IDs before processing idempotently.", "At-least-once delivery is common for webhooks.", "Do not mark an event complete before durable work succeeds.", True),
    ("password reset token can be reused", "The token is not invalidated or is not checked for expiration and ownership.", "Store a hashed, short-lived, single-use token and invalidate it after success.", "Reset links are bearer credentials.", "Rate-limit requests and avoid account enumeration.", True),
    ("API returns 500 for bad client input", "Validation errors are escaping as generic server exceptions.", "Validate at the boundary and return a documented 4xx response for malformed input.", "A client-caused error should not look like a server outage.", "Do not disclose internal stack traces.", False),
    ("database migration locks writes", "The migration performs a long table rewrite or unindexed update in one transaction.", "Use a staged, online-compatible migration and rehearse on production-like data.", "Schema work competes with live traffic.", "Plan rollback and backup recovery before applying.", True),
    ("cache serves stale permissions", "Authorization decisions are cached beyond their safe invalidation point.", "Keep permission checks authoritative or invalidate immediately on role changes.", "Stale authorization can grant access after revocation.", "Use conservative TTLs and audit sensitive access.", True),
    ("rate limiter blocks every user", "The key is global or a proxy header is trusted incorrectly.", "Key by an authenticated identity or validated client address and configure trusted proxies.", "A shared bucket turns one noisy client into an outage.", "Attackers can forge forwarded headers unless the proxy is trusted.", True),
    ("file upload permits executable content", "Validation trusts a filename or client MIME type instead of content and storage policy.", "Allowlist types, inspect content where appropriate, store outside executable paths, and scan uploads.", "Client metadata is not trustworthy.", "Limit size and protect against decompression bombs.", True),
    ("API client silently drops errors", "A catch handler converts failures into an empty success-like value.", "Return a typed failure or rethrow with context and log safe diagnostics.", "Callers cannot recover from an error they cannot see.", "Differentiate not-found from transport failure.", False),
    ("connection pool exhausts", "Connections are leaked, requests hold transactions too long, or pool size exceeds database capacity.", "Close resources reliably, shorten transactions, and size pools across all instances.", "Pools are shared finite database capacity.", "Measure wait time before increasing limits.", False),
    ("circular import appears after refactor", "Two modules depend on each other's initialization order.", "Extract shared types/constants into a lower-level module or invert the dependency.", "Imports execute module top-level code.", "A local import can defer a cycle but may hide architecture debt.", False),
    ("GitHub-style CI differs from local", "The runtime, lockfile, environment, or test selection differs.", "Compare versions and commands, then reproduce the CI command locally if possible.", "Green local output is not evidence that CI used the same inputs.", "Do not claim the fix is verified until the relevant run succeeds.", False),
    ("REST DELETE returns success but data remains", "Deletion is asynchronous, soft, tenant-scoped, or reading from a stale replica.", "Document semantics, return an operation status if async, and verify against the authoritative store.", "HTTP success may acknowledge acceptance rather than completion.", "Protect idempotent repeated DELETE calls.", False),
    ("frontend shows old API response after deploy", "A CDN, service worker, browser cache, or incompatible API version is serving old assets.", "Version assets, set deliberate cache headers, and maintain compatibility during rollout.", "Clients update at different times.", "Include a rollback path for cached broken bundles.", False),
    ("metrics show impossible 1000% error rate", "The numerator and denominator use mismatched windows, labels, or units.", "Inspect the raw series and calculate both over the same population/window.", "A dashboard formula can be wrong while services are healthy.", "Alert on low traffic carefully to avoid noisy ratios.", False),
]


PHRASINGS = [
    "Debug this: {symptom}",
    "SYMPTOM: {symptom}. Give ROOT CAUSE, FIX, WHY, and EDGE CASE.",
    "Production symptom: {symptom}. What should I investigate?",
    "I see this issue: {symptom}. Explain the safest fix.",
    "Create a concise debugging note for: {symptom}.",
]


def examples() -> list[dict]:
    out: list[dict] = []
    for case_index, (symptom, root, fix, why, edge, sensitive) in enumerate(CASES):
        for phrasing_index, phrasing in enumerate(PHRASINGS):
            number = case_index * len(PHRASINGS) + phrasing_index + 261
            mode = "serious_no_humor" if sensitive else (
                "lightly_witty" if phrasing_index == 4 and case_index in {0, 4, 18} else "professional_neutral"
            )
            answer = (
                f"SYMPTOM: {symptom}\nROOT CAUSE: {root}\nFIX: {fix}\n"
                f"WHY: {why}\nEDGE CASE: {edge}\n"
                "This is a diagnosis to verify with the relevant logs, tests, or reproduction; it is not a claim that a fix was run."
            )
            out.append(coding_sft(
                f"s25_code_{number:03d}",
                phrasing.format(symptom=symptom),
                answer,
                category="error_handling",
                personality_mode=mode,
                personality_required=mode != "professional_neutral",
                difficulty="hard",
                safety_sensitive=sensitive,
                subtopic="debugging",
            ))
    return out
