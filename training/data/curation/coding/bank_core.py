"""Sprint 25 core coding examples (260 rows)."""
from __future__ import annotations

from training.data.curation.coding import coding_sft


TOPICS: list[tuple[str, str, str, str, bool]] = [
    ("Python", "Python function", "Use small pure functions, type hints where useful, and explicit error handling.", "Keep I/O at the boundary so the logic is testable.", False),
    ("JavaScript", "JavaScript module", "Prefer const, clear names, and explicit handling for rejected promises.", "A predictable module is easier to change safely.", False),
    ("TypeScript", "TypeScript API", "Model valid states with types; narrow unknown input before using it.", "Types document contracts but runtime validation still protects boundaries.", False),
    ("React", "React component", "Keep derived values derived, use stable keys, and put side effects in useEffect only when needed.", "This avoids stale UI and unnecessary state.", False),
    ("Node", "Node handler", "Validate request input, set timeouts for outbound calls, and return deliberate status codes.", "A handler is an untrusted-input boundary.", False),
    ("HTML", "HTML form", "Use semantic elements, labels connected to controls, and native validation as a first layer.", "Accessibility and usability improve together.", False),
    ("CSS", "CSS layout", "Use layout primitives such as flex or grid and avoid magic positioning where flow should decide.", "Responsive behavior stays easier to reason about.", False),
    ("SQL", "SQL query", "Use bound parameters, select only needed columns, and inspect the query plan before adding indexes.", "This protects data and makes performance work evidence-based.", True),
    ("REST", "REST endpoint", "Use resource-oriented paths, meaningful HTTP status codes, and a documented error shape.", "Clients can then handle success and failure consistently.", False),
    ("Appwrite", "Appwrite integration", "Assuming the current Web SDK patterns, create a client, configure endpoint/project, then call documented service methods such as databases.createDocument.", "Confirm the installed SDK version before relying on version-sensitive options.", False),
    ("Git", "Git workflow", "Make small focused commits, review the diff before committing, and avoid rewriting shared history.", "Focused history makes rollback and review safer.", False),
    ("architecture", "service boundary", "Separate transport, application logic, and persistence behind explicit interfaces.", "The boundary limits coupling and makes tests cheaper.", False),
    ("security", "security-sensitive feature", "Treat all external input as untrusted; use least privilege, secret storage, and auditable access.", "Security controls belong in the design, not only in incident response.", True),
    ("performance", "performance change", "Measure a representative baseline, identify the bottleneck, then benchmark the proposed change.", "Optimizing without a measurement can make the wrong path faster.", False),
    ("async", "async workflow", "Await asynchronous work, propagate cancellation where supported, and bound concurrent work.", "This prevents orphaned work and resource exhaustion.", False),
    ("environment", "configuration path", "Read configuration from validated environment variables and keep secrets out of source control and logs.", "Configuration is deployment input, not application code.", True),
    ("logging", "logging change", "Log structured event names and safe identifiers; redact tokens, passwords, and personal data.", "Useful telemetry should not create a secret leak.", True),
    ("API integration", "third-party API client", "Set connect/read timeouts, classify transient failures, and use idempotency keys for retryable writes.", "Network calls fail in more ways than happy-path demos show.", False),
    ("testing", "test suite", "Test observable behavior, cover boundaries and error paths, and keep fixtures deterministic.", "Stable tests provide signal instead of ceremony.", False),
    ("data modeling", "data model", "Define ownership, invariants, and migration compatibility before adding fields.", "Data outlives a single deployment.", False),
    ("caching", "cache layer", "Define cache keys, TTL, invalidation, and behavior when the cache is unavailable.", "A cache is a consistency decision, not just a speed switch.", False),
    ("authentication", "authentication flow", "Use established identity protocols and server-side token validation; never put long-lived secrets in browser code.", "Authentication mistakes expose accounts.", True),
    ("observability", "production metric", "Record latency, error rate, and saturation with request correlation IDs where appropriate.", "Metrics explain whether a change improved the service.", False),
    ("deployment", "deployment plan", "Use a reversible rollout, health checks, and a rollback condition before expanding traffic.", "A deploy is safer when recovery is preplanned.", False),
    ("dependency", "dependency update", "Read release notes, lock known-good versions, and test the compatibility surface before rollout.", "Version changes can alter behavior outside the direct import.", False),
    ("validation", "input validator", "Reject malformed input early with actionable client errors and allowlist expected values.", "Validation reduces ambiguous downstream failures.", False),
]

ANGLES = [
    ("What is the first design rule for this {label}?", "{advice}"),
    ("Give concise production advice for a {label}.", "{advice} {why}"),
    ("What should I verify before changing a {label}?", "{advice} Verify the existing contract and add a focused test or measurement first."),
    ("A junior developer asks how to make a {label} maintainable.", "{advice} {why}"),
    ("What common mistake should I avoid in a {label}?", "Do not assume the happy path is enough. {advice}"),
    ("How should I document a {label}?", "Document inputs, outputs, failure behavior, and assumptions. {advice}"),
    ("How do I review a {label} quickly?", "Check the contract, failure paths, security boundary, and operational impact. {advice}"),
    ("What makes a {label} production-ready?", "{advice} Include tests and observability appropriate to its risk."),
    ("How do I reduce risk in a {label}?", "Make the change small and reversible. {advice}"),
    ("What is a sensible default for a {label}?", "{advice} Change the default only with a stated requirement and evidence."),
]


def examples() -> list[dict]:
    out: list[dict] = []
    for index, (topic, label, advice, why, sensitive) in enumerate(TOPICS, start=1):
        for angle_index, (prompt, response) in enumerate(ANGLES, start=1):
            eid = f"s25_code_{(index - 1) * len(ANGLES) + angle_index:03d}"
            mode = "serious_no_humor" if sensitive else (
                "lightly_witty" if topic in {"CSS", "Git"} and angle_index == 5 else "professional_neutral"
            )
            out.append(coding_sft(
                eid,
                prompt.format(label=label),
                response.format(advice=advice, why=why),
                category="error_handling" if topic in {"async", "API integration", "validation"} and angle_index in {3, 7} else "coding",
                personality_mode=mode,
                personality_required=mode != "professional_neutral",
                difficulty="medium",
                safety_sensitive=sensitive,
                subtopic=topic,
            ))
    return out
