"""Safe mathematical expression evaluator (no eval/exec).

The expression is parsed with `ast` and walked by a whitelist: numbers, + - * / // % **,
unary +/-, parentheses, a fixed set of functions and constants. Everything else
(names, attributes, subscripts, lambdas, strings, comprehensions...) is rejected.
"""
from __future__ import annotations

import ast
import math
import operator
import re

from app.utils.language import normalize_text

MAX_EXPRESSION_LENGTH = 200
MAX_POWER_BITS = 2000      # integer powers whose result would exceed ~2000 bits are refused
MAX_FACTORIAL = 500
MAX_ARGS = 4


class CalculatorError(ValueError):
    """Invalid, unsafe or non-computable expression (message is user-presentable)."""


def _factorial(n: object) -> int:
    if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > MAX_FACTORIAL:
        raise CalculatorError(f"factorial needs an integer between 0 and {MAX_FACTORIAL}")
    return math.factorial(n)


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1 / 3), x)


_BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "cbrt": _cbrt, "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil, "min": min, "max": max,
    "exp": math.exp, "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "factorial": _factorial,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}

# "15%" -> "(15/100)"; a '%' followed by an operand ("17 % 5") stays the modulo operator.
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%(?!\s*[\d(A-Za-z])")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def prepare(expression: str) -> str:
    """Normalise digits/operators and rewrite ``^`` and ``n%`` into plain Python syntax."""
    expr = normalize_text(expression).replace("^", "**")
    expr = _THOUSANDS.sub("", expr)
    return _PERCENT.sub(r"(\1/100)", expr)


def _power(base: object, exponent: object) -> object:
    if isinstance(base, int) and isinstance(exponent, int) and exponent > 0 and abs(base) > 1:
        if exponent * math.log2(abs(base)) > MAX_POWER_BITS:
            raise CalculatorError("the power is too large to compute")
    return base ** exponent


def _eval(node: ast.AST) -> object:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("only numbers are allowed")
        return node.value
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalculatorError(f"unknown name '{node.id}'")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            return _power(_eval(node.left), _eval(node.right))
        if type(node.op) in _BINARY:
            return _BINARY[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise CalculatorError("this function is not supported")
        if node.keywords or not node.args or len(node.args) > MAX_ARGS:
            raise CalculatorError("invalid function call")
        return _FUNCTIONS[node.func.id](*[_eval(arg) for arg in node.args])
    raise CalculatorError("unsupported operation")


def format_number(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculatorError("the result is not a real number")
    if isinstance(value, int):
        return str(value)
    if math.isnan(value) or math.isinf(value):
        raise CalculatorError("the result is not a finite number")
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return format(value, ".12g")  # 12 significant digits hides binary float noise (0.1+0.2 -> 0.3)


def calculate(expression: str) -> str:
    """Evaluate ``expression`` and return the result as text; raise `CalculatorError` otherwise."""
    expr = prepare(expression)
    if not expr:
        raise CalculatorError("the expression is empty")
    if len(expr) > MAX_EXPRESSION_LENGTH:
        raise CalculatorError(f"the expression is longer than {MAX_EXPRESSION_LENGTH} characters")
    try:
        return format_number(_eval(ast.parse(expr, mode="eval")))
    except CalculatorError:
        raise
    except ZeroDivisionError:
        raise CalculatorError("division by zero is undefined") from None
    except (SyntaxError, RecursionError, MemoryError):
        raise CalculatorError("the expression could not be parsed") from None
    except OverflowError:
        raise CalculatorError("the result is too large") from None
    except (ValueError, TypeError) as exc:
        raise CalculatorError(f"mathematical error: {exc}") from None
