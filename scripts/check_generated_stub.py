#!/usr/bin/env python3
"""Compare committed and regenerated Python stubs without formatting noise.

This is an *exhaustive* comparison of declarations in both .pyi modules:
imports, all classes, member signatures/defaults/returns/decorators, method
bodies, and cleaned docstrings. It does not import QuPRS or execute Python
source. Comments, quote style, line wrapping, and import ordering are ignored.

Use this after a real 'generate_stubs.py --write' in an installed environment.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _dump(node: ast.AST | None) -> str | None:
    return ast.dump(node, include_attributes=False) if node is not None else None


def _doc_and_body(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
    """Preserve actual declarations; normalize only docstring indentation."""
    body = list(node.body)
    doc = ast.get_docstring(node, clean=True)
    if doc is not None:
        body.pop(0)
    return doc, body


def _put(result: dict[str, object], key: str, value: object) -> None:
    if key in result:
        raise AssertionError(f"Duplicate generated stub declaration: {key}")
    result[key] = value


def _declarations(source: str, filename: str) -> dict[str, object]:
    module = ast.parse(source, filename=filename)
    result: dict[str, object] = {}
    imports = []
    other_index = 0

    def visit_class(node: ast.ClassDef, prefix: str) -> None:
        key = f"{prefix}.{node.name}"
        _put(result, f"{key}.definition", (
            tuple(_dump(x) for x in node.bases),
            tuple(_dump(x) for x in node.keywords),
            tuple(_dump(x) for x in node.decorator_list),
            tuple(_dump(x) for x in getattr(node, "type_params", ())),
        ))
        doc, members = _doc_and_body(node)
        _put(result, f"{key}.docstring", doc)
        seen: set[str] = set()
        for index, member in enumerate(members):
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if member.name in seen:
                    raise AssertionError(f"Duplicate stub method: {key}.{member.name}")
                seen.add(member.name)
                visit_function(member, key)
            elif isinstance(member, ast.ClassDef):
                if member.name in seen:
                    raise AssertionError(f"Duplicate nested stub class: {key}.{member.name}")
                seen.add(member.name)
                visit_class(member, key)
            else:
                _put(result, f"{key}.other[{index}]", _dump(member))

    def visit_function(
        node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str
    ) -> None:
        key = f"{prefix}.{node.name}"
        _put(result, f"{key}.signature", (
            type(node).__name__,
            _dump(node.args),
            _dump(node.returns),
            tuple(_dump(x) for x in node.decorator_list),
            tuple(_dump(x) for x in getattr(node, "type_params", ())),
            node.type_comment,
        ))
        doc, body = _doc_and_body(node)
        _put(result, f"{key}.docstring", doc)
        _put(result, f"{key}.body", tuple(_dump(x) for x in body))

    for stmt in module.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            imports.append(_dump(stmt))
        elif isinstance(stmt, ast.ClassDef):
            visit_class(stmt, "class")
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visit_function(stmt, "function")
        else:
            _put(result, f"module.other[{other_index}]", _dump(stmt))
            other_index += 1
    _put(result, "module.imports", tuple(sorted(imports)))
    return result


def compare_stubs(committed: str, regenerated: str) -> None:
    """Raise with a precise declaration path on any real stub divergence."""
    source = _declarations(committed, "committed core.pyi")
    output = _declarations(regenerated, "regenerated core.pyi")
    missing = sorted(set(source) - set(output))
    unexpected = sorted(set(output) - set(source))
    if missing or unexpected:
        raise AssertionError(
            f"Stub declarations changed: missing={missing}, added={unexpected}"
        )
    changed = [key for key in sorted(source) if source[key] != output[key]]
    if changed:
        details = "\n".join(
            f"{key}: committed={source[key]!r}; regenerated={output[key]!r}"
            for key in changed[:12]
        )
        raise AssertionError(
            f"Stub API/documentation divergence ({len(changed)} fields):\n{details}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("committed", type=Path, help="Saved committed core.pyi")
    parser.add_argument("regenerated", type=Path, help="Newly generated core.pyi")
    args = parser.parse_args()
    compare_stubs(
        args.committed.read_text(encoding="utf-8"),
        args.regenerated.read_text(encoding="utf-8"),
    )
    print("Committed vs regenerated .pyi declarations and docstrings: PASS")


if __name__ == "__main__":
    main()
