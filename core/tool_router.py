from __future__ import annotations

import ast
import math
import operator
import re
from datetime import datetime
from typing import Optional


class LocalToolRouter:
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def run(self, text: str) -> Optional[str]:
        lowered = (text or "").lower()
        if any(term in lowered for term in ("ce dată", "data de azi", "ce zi este", "ce oră", "cât e ceasul", "cat e ceasul")):
            now = datetime.now().astimezone()
            weekdays = ("luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică")
            months = (
                "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
                "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
            )
            return f"Este {weekdays[now.weekday()]}, {now.day} {months[now.month - 1]} {now.year}, ora {now:%H:%M}."

        match = re.search(r"(?:cât face|cat face|calculează|calculeaza|rezolvă|rezolva)\s+(.+?)\??$", lowered)
        if not match:
            return None
        expression = match.group(1).replace("×", "*").replace("x", "*").replace(",", ".")
        if not re.fullmatch(r"[\d\s.+\-*/()%]+", expression):
            return None
        try:
            result = self._evaluate(ast.parse(expression, mode="eval").body)
            if not math.isfinite(float(result)):
                return "Calculul nu produce un rezultat finit."
            rendered = int(result) if float(result).is_integer() else round(float(result), 8)
            return f"Rezultatul este {rendered}."
        except (ArithmeticError, SyntaxError, ValueError, TypeError, OverflowError):
            return "Nu pot calcula expresia; verifică operațiile și încearcă din nou."

    def _evaluate(self, node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.OPERATORS:
            return self.OPERATORS[type(node.op)](self._evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in self.OPERATORS:
            left = self._evaluate(node.left)
            right = self._evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large")
            return self.OPERATORS[type(node.op)](left, right)
        raise ValueError("Unsupported expression")
