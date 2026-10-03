"""Small, explicitly implemented tools available to the assistant."""

import ast
import math
import operator


# This allowlist limits the calculator to basic arithmetic only.
_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_MAX_EXPRESSION_LENGTH = 256
_MAX_ABS_VALUE = 1e100
_MAX_EXPONENT = 100
_MAX_AST_NODES = 100


def calculate(expression: str) -> int | float:
    """Evaluate a basic arithmetic expression without executing Python code.

    Only numeric constants, parentheses, unary +/- and the operators +, -, *,
    /, //, %, and ** are accepted. Names, function calls, imports, and all
    other Python syntax are rejected.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Enter a non-empty mathematical expression.")
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError("The expression is too long.")

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("The expression is not valid arithmetic.") from error

    visited_nodes = 0

    def evaluate(node: ast.AST) -> int | float:
        nonlocal visited_nodes
        visited_nodes += 1
        if visited_nodes > _MAX_AST_NODES:
            raise ValueError("The expression is too complex.")

        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
            _check_number(value)
            return value

        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            value = evaluate(node.operand)
            result = _UNARY_OPERATORS[type(node.op)](value)
            _check_number(result)
            return result

        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
                raise ValueError(f"Exponents must be between -{_MAX_EXPONENT} and {_MAX_EXPONENT}.")
            try:
                result = _BINARY_OPERATORS[type(node.op)](left, right)
            except (ArithmeticError, OverflowError) as error:
                raise ValueError("That arithmetic operation is not valid.") from error
            _check_number(result)
            return result

        raise ValueError("Only basic arithmetic is allowed in calculator expressions.")

    result = evaluate(parsed)
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result


def _check_number(value: int | float) -> None:
    """Reject non-finite or excessively large values at every evaluation step."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("The result is too large to represent safely.")
    if abs(value) > _MAX_ABS_VALUE:
        raise ValueError("The result is too large to calculate safely.")
