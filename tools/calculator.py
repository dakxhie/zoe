"""Safe calculator using AST parsing.

Natural-language prefixes (``what is``, ``calculate``, …) are stripped before
evaluation so plugin routing and memory forgetting share one detector. Only a
closed set of AST node types is evaluated — never ``eval``/``exec``.

Phase B3 (crash-proofing, A.1 §1.1, §8.4, §8.5, §24.2):

- Detection is pure: ``is_calculator_request`` parses and validates but never
  evaluates, so routing can no longer raise ``ZeroDivisionError``.
- Every expression is validated before evaluation: length <= 256 characters,
  parenthesis depth <= 16, AST depth <= 128, AST node count <= 256, and only
  ``+ - * / %`` (binary), unary ``+ -``, numeric literals and parentheses.
  ``**`` stays unsupported.
- Evaluation keeps intermediate integers within 1024 bits and floats finite;
  the formatted result is at most 64 characters.
- Failures are typed and safe: ``CalculatorError`` (``invalid_arguments``),
  ``CalculatorMathError`` (``math_error``: division/modulo by zero, limits,
  non-finite values) and ``CalculatorInternalError`` (``internal_error``: any
  unexpected arithmetic failure). All are ``CalculatorError`` subclasses (and
  therefore still ``ValueError``), so existing callers keep working.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Callable

from core.safe_errors import TypedSafeError

MAX_EXPRESSION_CHARS = 256
MAX_PAREN_DEPTH = 16
MAX_AST_DEPTH = 128
MAX_AST_NODES = 256
MAX_INT_BITS = 1024
MAX_RESULT_CHARS = 64

INVALID_ARGUMENTS = "invalid_arguments"
MATH_ERROR = "math_error"
INTERNAL_ERROR = "internal_error"

_SUPPORTED_HINT = "I can calculate +, -, *, / and % with numbers and parentheses."


class CalculatorError(ValueError, TypedSafeError):
    """Base calculator error (``invalid_arguments``). The message is always safe text."""

    error_type = INVALID_ARGUMENTS

    def __init__(self, safe_message: str = f"Unsupported expression. {_SUPPORTED_HINT}", reason: str = "unsupported") -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message
        self.reason = reason


class CalculatorMathError(CalculatorError):
    """A well-formed expression that cannot be computed safely (``math_error``)."""

    error_type = MATH_ERROR


class CalculatorInternalError(CalculatorError):
    """An unexpected failure while computing (``internal_error``)."""

    error_type = INTERNAL_ERROR


def _math_error(reason: str, detail: str) -> CalculatorMathError:
    return CalculatorMathError(f"I can't calculate that: {detail}", reason=reason)


_ALLOWED_BINARY_OPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_ALLOWED_UNARY_OPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_CHARACTERS = frozenset("0123456789+-*/().% ")


# ---------------------------------------------------------------------------
# Pure validation (no evaluation)
# ---------------------------------------------------------------------------


def _paren_depth(text: str) -> int:
    depth = deepest = 0
    for character in text:
        if character == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif character == ")":
            depth -= 1
    return deepest


def _ast_depth(root: ast.AST) -> int:
    deepest = 0
    stack: list[tuple[ast.AST, int]] = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        deepest = max(deepest, depth)
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return deepest


def _check_number(value: object) -> float | int:
    """Validate a numeric literal or intermediate value against the limits."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculatorError(f"Only numbers are allowed. {_SUPPORTED_HINT}", reason="non_numeric")
    if isinstance(value, float) and not math.isfinite(value):
        raise _math_error("non_finite", "the result is not a finite number.")
    if isinstance(value, int) and value.bit_length() > MAX_INT_BITS:
        raise _math_error("integer_too_large", f"a number grew beyond {MAX_INT_BITS} bits.")
    return value


def _check_node(node: ast.AST) -> None:
    if isinstance(node, (ast.Expression, ast.operator, ast.unaryop)):
        if isinstance(node, ast.Pow):
            raise CalculatorError(
                f"Exponents (**) aren't supported. {_SUPPORTED_HINT}", reason="exponent_unsupported"
            )
        if isinstance(node, ast.operator) and type(node) not in _ALLOWED_BINARY_OPS:
            raise CalculatorError(f"Unsupported operator. {_SUPPORTED_HINT}", reason="unsupported_operator")
        if isinstance(node, ast.unaryop) and type(node) not in _ALLOWED_UNARY_OPS:
            raise CalculatorError(f"Unsupported operator. {_SUPPORTED_HINT}", reason="unsupported_operator")
        return
    if isinstance(node, ast.Constant):
        _check_number(node.value)
        return
    if isinstance(node, (ast.BinOp, ast.UnaryOp)):
        return
    raise CalculatorError(f"Unsupported expression. {_SUPPORTED_HINT}", reason="unsupported_syntax")


def validate_expression(expression: str) -> ast.Expression:
    """Parse and validate an arithmetic expression without evaluating it.

    Raises ``CalculatorMathError`` for limit violations and
    ``CalculatorError`` for anything that is not supported arithmetic.
    """
    if not isinstance(expression, str):
        raise CalculatorError(reason="non_text")
    text = expression.strip()
    if not text:
        raise CalculatorError(reason="empty")
    if len(text) > MAX_EXPRESSION_CHARS:
        raise _math_error("expression_too_long", f"the expression is longer than {MAX_EXPRESSION_CHARS} characters.")
    if _paren_depth(text) > MAX_PAREN_DEPTH:
        raise _math_error("too_many_parentheses", f"parentheses are nested more than {MAX_PAREN_DEPTH} levels deep.")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        raise CalculatorError(reason="syntax") from None
    except (RecursionError, MemoryError):
        raise _math_error("too_complex", "the expression is too complex.") from None
    except ValueError:
        raise CalculatorError(reason="syntax") from None
    if _ast_depth(tree) > MAX_AST_DEPTH:
        raise _math_error("ast_too_deep", "the expression is nested too deeply.")
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise _math_error("too_many_nodes", "the expression has too many parts.")
    for node in ast.walk(tree):
        _check_node(node)
    return tree


# ---------------------------------------------------------------------------
# Evaluation (only after validation)
# ---------------------------------------------------------------------------


def _evaluate_node(node: ast.AST) -> float | int:
    """Evaluate one validated AST node, checking limits after every step."""
    if isinstance(node, ast.Constant):
        return _check_number(node.value)

    if isinstance(node, ast.UnaryOp):
        operator_fn = _ALLOWED_UNARY_OPS.get(type(node.op))
        if operator_fn is None:
            raise CalculatorError(f"Unsupported operator. {_SUPPORTED_HINT}", reason="unsupported_operator")
        return _check_number(operator_fn(_evaluate_node(node.operand)))

    if isinstance(node, ast.BinOp):
        operator_fn = _ALLOWED_BINARY_OPS.get(type(node.op))
        if operator_fn is None:
            raise CalculatorError(f"Unsupported operator. {_SUPPORTED_HINT}", reason="unsupported_operator")
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            if isinstance(node.op, ast.Div):
                raise _math_error("division_by_zero", "division by zero is undefined.")
            raise _math_error("modulo_by_zero", "modulo by zero is undefined.")
        return _check_number(operator_fn(left, right))

    raise CalculatorError(f"Unsupported expression. {_SUPPORTED_HINT}", reason="unsupported_syntax")


def _format_result(result: float | int) -> str:
    result = _check_number(result)
    if isinstance(result, float) and result.is_integer():
        text = str(int(result))
    else:
        text = str(result)
    if len(text) > MAX_RESULT_CHARS:
        raise _math_error("result_too_long", f"the result is longer than {MAX_RESULT_CHARS} characters.")
    return text


def _evaluate_expression(expression: str) -> str:
    """Validate, then evaluate a pure arithmetic string (no natural-language prefixes)."""
    tree = validate_expression(expression)
    try:
        return _format_result(_evaluate_node(tree.body))
    except CalculatorError:
        raise
    except ZeroDivisionError:
        raise _math_error("division_by_zero", "division by zero is undefined.") from None
    except OverflowError:
        raise _math_error("overflow", "a number is too large to compute.") from None
    except Exception:
        # Unexpected arithmetic failure: typed and safe; the raw message is dropped.
        raise CalculatorInternalError(
            "I couldn't calculate that because of an unexpected calculator error.", reason="unexpected"
        ) from None


# ---------------------------------------------------------------------------
# Detection (pure: parse + validate, never evaluate)
# ---------------------------------------------------------------------------


def _looks_like_math(candidate: str) -> bool:
    """Pure check: True for well-formed arithmetic, or arithmetic-shaped text over the limits."""
    try:
        validate_expression(candidate)
    except CalculatorMathError:
        # Clearly arithmetic but beyond the safe limits: handle it as a
        # calculator request so the user gets a typed math_error.
        return any(character.isdigit() for character in candidate)
    except CalculatorError:
        return False
    except Exception:
        return False
    return True


def _extract_calculator_expression(query: str) -> str | None:
    """Pull an arithmetic substring from natural-language calculator requests (no evaluation)."""
    text = query.strip()
    if not text:
        return None

    if all(character in _ALLOWED_CHARACTERS for character in text):
        return text if _looks_like_math(text) else None

    lowered = text.lower()
    prefixes = (
        "what is ",
        "what's ",
        "whats ",
        "calculate ",
        "compute ",
        "evaluate ",
        "solve ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            candidate = text[len(prefix) :].strip(" ?=:,")
            if candidate and all(ch in _ALLOWED_CHARACTERS for ch in candidate):
                return candidate if _looks_like_math(candidate) else None
    return None


def is_calculator_request(query: str) -> bool:
    """Return True when the query looks like a calculator expression (never evaluates)."""
    try:
        return _extract_calculator_expression(query) is not None
    except Exception:
        return False


def calculate(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression.

    Raises ``CalculatorError`` (or a typed subclass) with a safe message.
    """
    extracted = _extract_calculator_expression(expression) if isinstance(expression, str) else None
    if extracted is None:
        if isinstance(expression, str) and "**" in expression:
            raise CalculatorError(
                f"Exponents (**) aren't supported. {_SUPPORTED_HINT}", reason="exponent_unsupported"
            )
        raise CalculatorError()
    return _evaluate_expression(extracted)
