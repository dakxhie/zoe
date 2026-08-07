"""Safe calculator using AST parsing."""

from __future__ import annotations

import ast
import operator
from typing import Callable

CalculatorError = ValueError

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


def _ensure_number(value: float | int) -> float | int:
    """Return numeric values unchanged."""
    if isinstance(value, (int, float)):
        return value
    raise CalculatorError("Only numeric values are allowed")


def _evaluate_node(node: ast.AST) -> float | int:
    """Evaluate one allowed AST node."""
    if isinstance(node, ast.Constant):
        return _ensure_number(node.value)

    if isinstance(node, ast.UnaryOp):
        operator_fn = _ALLOWED_UNARY_OPS.get(type(node.op))
        if operator_fn is None:
            raise CalculatorError("Unsupported unary operator")
        return operator_fn(_evaluate_node(node.operand))

    if isinstance(node, ast.BinOp):
        operator_fn = _ALLOWED_BINARY_OPS.get(type(node.op))
        if operator_fn is None:
            raise CalculatorError("Unsupported binary operator")
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        return operator_fn(left, right)

    raise CalculatorError("Unsupported expression")


def _evaluate_expression(expression: str) -> str:
    """Evaluate a pure arithmetic string (no natural-language prefixes)."""
    parsed = ast.parse(expression.strip(), mode="eval")
    result = _evaluate_node(parsed.body)

    if isinstance(result, float) and result.is_integer():
        return str(int(result))

    return str(result)


def _extract_calculator_expression(query: str) -> str | None:
    """Pull a safe arithmetic substring from natural-language calculator requests."""
    text = query.strip()
    if not text:
        return None

    allowed_characters = set("0123456789+-*/().% ")
    if all(character in allowed_characters for character in text):
        try:
            _evaluate_expression(text)
        except CalculatorError:
            return None
        return text

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
            if candidate and all(ch in allowed_characters for ch in candidate):
                try:
                    _evaluate_expression(candidate)
                except CalculatorError:
                    return None
                return candidate
    return None


def is_calculator_request(query: str) -> bool:
    """Return True when the query looks like a calculator expression."""
    return _extract_calculator_expression(query) is not None


def calculate(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression."""
    extracted = _extract_calculator_expression(expression)
    if extracted is None:
        raise CalculatorError("Unsupported expression")
    return _evaluate_expression(extracted)
