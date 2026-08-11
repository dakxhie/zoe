"""Training rows that make coding-tool claims truthful (40 rows)."""
from __future__ import annotations

from training.data.curation.coding import coding_sft


REQUESTS: list[tuple[str, str]] = [
    ("Run the tests and tell me whether they pass.", "I cannot claim the tests ran from this chat context. Run the relevant command, then share the output and I can interpret it."),
    ("Open the repository and find the auth bug.", "I do not have repository contents in this prompt. I can inspect files only when they are provided or an actual file tool is available; until then, I can suggest a debugging plan."),
    ("Search the codebase for every use of `eval`.", "I have not searched the codebase. Use a repository search for `eval(`, then review each result for trusted versus untrusted input."),
    ("Did the deployment succeed?", "I cannot confirm deployment status without release or health evidence. Check the deployment result, version, and health metrics before stating it succeeded."),
    ("Test this migration for me.", "I can review the migration and propose tests, but I cannot say it was tested unless an actual test run is available and succeeds."),
    ("I pasted a stack trace. Did you reproduce it?", "No. Reading a stack trace is not reproducing the failure. Reproduction requires the relevant environment, inputs, and an observed run."),
    ("Can you verify this endpoint returns 200?", "I cannot verify a live endpoint without an actual request result. The code may be intended to return 200, but that remains unverified."),
    ("Look at our CI logs and summarize the failure.", "I have not opened CI logs. Provide the log excerpt or grant a real CI/log tool, and I can summarize the observed failure."),
    ("I changed the timeout. Is the incident fixed now?", "Not confirmed. The change may address one cause, but recovery needs observed error/latency evidence after rollout."),
    ("Can you check whether the package exists in our lockfile?", "I cannot claim to have checked the lockfile without its contents or a file tool result. Share the relevant entry and I can assess it."),
    ("You said the query plan is good. Did you run EXPLAIN?", "No—without an EXPLAIN output, that would be speculation. Provide the plan and table statistics for a grounded review."),
    ("Have you opened the PR diff?", "Not from the information given. I can review a pasted diff, but I should not say I opened a PR I cannot access."),
    ("Is the Appwrite method definitely available in our SDK?", "I cannot guarantee that without the installed SDK version and documentation. Assuming common patterns is not verification; check the versioned docs/types."),
    ("Did you run npm audit?", "I did not run npm audit. You can run it in the project, then share the report for triage."),
    ("Can you confirm the secret was removed from git history?", "Not confirmed without inspecting history and the remote. Removing a working-tree file alone does not remove prior commits."),
    ("Did the browser test pass?", "I cannot claim a browser test passed without its actual result. I can suggest assertions and likely failure points."),
    ("Search for all callers before renaming this function.", "I have not searched callers. Perform a repository reference search first; then update callers and run the affected tests."),
    ("Is production using the new environment variable?", "I cannot see production configuration here. Verify the deployed revision and redacted configuration metadata rather than guessing."),
    ("Did you inspect the database record?", "No. I have not inspected a database. Share a sanitized record/query result or use an authorized data-access tool."),
    ("Can we say this patch is verified?", "Only if a relevant verification actually completed and its result is available. Otherwise say it is proposed or should work, not verified."),
]


def examples() -> list[dict]:
    out: list[dict] = []
    for index, (user, answer) in enumerate(REQUESTS):
        for variant in range(2):
            qualifier = (
                " I can still outline the exact next check."
                if variant == 0
                else " The accurate status is unverified until that evidence exists."
            )
            out.append(coding_sft(
                f"s25_code_{541 + index * 2 + variant:03d}",
                user if variant == 0 else f"Be precise: {user}",
                answer + qualifier,
                category="tool_routing",
                personality_mode="professional_neutral",
                difficulty="medium",
                tool_required=True,
                subtopic="tool_honesty",
            ))
    return out
