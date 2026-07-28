"""Rule-based detection of messages worth remembering."""

from __future__ import annotations

from core.text_utils import matches_any, normalize_text

# Phrases that suggest personal information worth remembering.
# More specific phrases are checked before broader ones like "i am".
MEMORY_PHRASES: tuple[str, ...] = (
    "my favorite",
    "i like",
    "i love",
    "my name is",
    "i am building",
    "i live in",
    "i work on",
    "my goal is",
    "i am",
)

# Short greetings Zoe should not treat as memory.
GREETINGS: frozenset[str] = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "howdy",
    }
)

# Starters that usually indicate a question rather than a memory.
QUESTION_STARTERS: tuple[str, ...] = (
    "what ",
    "who ",
    "when ",
    "where ",
    "why ",
    "how ",
    "can you ",
    "could you ",
    "do you ",
    "does ",
    "is ",
    "are ",
)

# Phrases that usually indicate a task request, not personal memory.
CODING_PHRASES: tuple[str, ...] = (
    "write code",
    "write a function",
    "write a script",
    "fix this code",
    "fix my code",
    "debug",
    "implement ",
    "build a website",
    "create a function",
    "python script",
)

# Phrases that indicate explanation requests.
EXPLANATION_PHRASES: tuple[str, ...] = (
    "explain ",
    "what is ",
    "what are ",
    "how does ",
    "how do ",
    "tell me about ",
    "describe ",
)

# Phrases that indicate joke requests.
JOKE_PHRASES: tuple[str, ...] = (
    "tell me a joke",
    "make me laugh",
    "say something funny",
)


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    """Return True when any phrase appears in the text."""
    return matches_any(text, phrases)


def _is_question(text: str) -> bool:
    """Return True for question-style messages."""
    if text.endswith("?"):
        return True
    return any(text.startswith(starter) for starter in QUESTION_STARTERS)


def _is_greeting(text: str) -> bool:
    """Return True for short greeting messages."""
    if text in GREETINGS:
        return True
    return any(text.startswith(f"{greeting} ") for greeting in GREETINGS)


def _is_coding_request(text: str) -> bool:
    """Return True for coding help requests."""
    return _contains_phrase(text, CODING_PHRASES)


def _is_explanation_request(text: str) -> bool:
    """Return True for explanation requests."""
    return _contains_phrase(text, EXPLANATION_PHRASES)


def _is_joke_request(text: str) -> bool:
    """Return True for joke requests."""
    return _contains_phrase(text, JOKE_PHRASES)


def _should_skip(text: str) -> bool:
    """Return True when the message should not be remembered."""
    return (
        _is_question(text)
        or _is_greeting(text)
        or _is_coding_request(text)
        or _is_explanation_request(text)
        or _is_joke_request(text)
    )


def _has_memory_signal(text: str) -> bool:
    """Return True when the message contains personal information signals."""
    return _contains_phrase(text, MEMORY_PHRASES)


def should_remember(text: str) -> bool:
    """Return True when a message looks like personal information to remember."""
    normalized = normalize_text(text)

    if not normalized:
        return False

    if _should_skip(normalized):
        return False

    return _has_memory_signal(normalized)
