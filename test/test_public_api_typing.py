"""Regression checks for annotations on documented public API helpers.

This source-only contract avoids importing compiled dependencies.
"""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _return_annotations(path: str, class_name: str | None = None) -> dict[str, str | None]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    body = tree.body
    if class_name is not None:
        cls = next(
            node for node in body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        body = cls.body
    return {
        node.name: ast.unparse(node.returns) if node.returns else None
        for node in body
        if isinstance(node, ast.FunctionDef)
    }


def test_documented_statistics_returns_are_explicit():
    actual = _return_annotations(
        "src/QuPRS/pathsum/statistics.py", "StatisticsManager"
    )
    expected = {
        "__init__": "None",
        "__repr__": "str",
        "get_reduction_counts": "dict[str, int]",
        "get_reduction_count": "int",
        "increment_reduction_count": "None",
        "get_reduction_hitrate": "float",
        "reset_reduction_counts": "None",
        "set_reduction_switch": "None",
        "is_reduction_enabled": "bool",
    }
    assert {name: actual.get(name) for name in expected} == expected


def test_documented_gate_discovery_returns_are_explicit():
    actual = _return_annotations("src/QuPRS/pathsum/gates/__init__.py")
    assert actual["support_gate_set"] == "set[str]"
    assert actual["list_supported_gates"] == "None"
    assert actual["get_gates_by_type"] == "list[str]"
