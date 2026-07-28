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


def is_calculator_request(query: str) -> bool:
    """Return True when the query looks like a calculator expression."""
    expression = query.strip()
    if not expression:
        return False

    allowed_characters = set("0123456789+-*/().% ")
    if not all(character in allowed_characters for character in expression):
        return False

    try:
        calculate(expression)
    except CalculatorError:
        return False

    return True


def calculate(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression."""
    parsed = ast.parse(expression.strip(), mode="eval")
    result = _evaluate_node(parsed.body)

    if isinstance(result, float) and result.is_integer():
        return str(int(result))

    return str(result)
