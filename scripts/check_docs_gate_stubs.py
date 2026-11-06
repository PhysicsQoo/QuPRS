#!/usr/bin/env python3
"""Check generated PathSum gate stubs against source without importing QuPRS.

QuPRS injects gate methods into PathSum at runtime. Griffe/mkdocstrings uses
core.pyi instead of runtime inspection; this gate verifies source/stub parity
and checks that Griffe statically discovers every dynamic method.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_ROOT = ROOT / "src" / "QuPRS" / "pathsum" / "gates"
NON_GATE_MODULES = {"__init__.py", "base.py", "builder.py", "patcher.py",
                    "applier.py", "utils.py"}
STUB_PATH = ROOT / "src" / "QuPRS" / "pathsum" / "core.pyi"
STATIC_PACKAGE = "QuPRS.pathsum.core"
STUB_MARKER = "# --- Dynamically Injected Gate Methods ---"


def source_gate_classes() -> tuple[dict[str, ast.ClassDef], dict[str, ast.ClassDef]]:
    """Collect only declared Gate classes with literal gate_name values."""
    result: dict[str, ast.ClassDef] = {}
    by_class: dict[str, ast.ClassDef] = {}
    for source_file in sorted(GATE_ROOT.glob("*.py")):
        if source_file.name in NON_GATE_MODULES:
            continue
        file_name = source_file.name
        source = source_file.read_text(encoding="utf-8")
        parsed = ast.parse(source, filename=file_name)
        for node in parsed.body:
            if not isinstance(node, ast.ClassDef):
                continue
            by_class[node.name] = node
            names = [
                target.value
                for stmt in node.body
                if isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
                for target_node in stmt.targets
                if isinstance(target_node, ast.Name) and target_node.id == "gate_name"
                for target in (stmt.value,)
            ]
            if names:
                if len(names) != 1 or names[0] in result:
                    raise AssertionError(f"Ambiguous Gate name in {file_name}:{node.lineno}")
                result[names[0]] = node
    if not result:
        raise AssertionError("No gate classes discovered in source")
    return result, by_class


def method_in_hierarchy(
    cls: ast.ClassDef,
    method_name: str,
    classes: dict[str, ast.ClassDef],
) -> ast.FunctionDef | None:
    for item in cls.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
            if not isinstance(item, ast.FunctionDef):
                raise AssertionError(f"Unexpected async Gate method: {cls.name}")
            return item
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id in classes:
            method = method_in_hierarchy(classes[base.id], method_name, classes)
            if method is not None:
                return method
    return None


def _annotation(argument: ast.arg) -> str | None:
    value = argument.annotation
    if value is None:
        return None
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return ast.unparse(value)


def parameter_shape(
    method: ast.FunctionDef, ignored: set[str]
) -> list[tuple[str, str, str | None, str | None]]:
    args = method.args
    positional = args.posonlyargs + args.args
    default_start = len(positional) - len(args.defaults)
    result = []
    for index, parameter in enumerate(positional):
        if parameter.arg in ignored:
            continue
        default = (
            ast.unparse(args.defaults[index - default_start])
            if index >= default_start else None
        )
        result.append((parameter.arg, "positional", _annotation(parameter), default))
    if args.vararg is not None:
        result.append((args.vararg.arg, "vararg", _annotation(args.vararg), None))
    for parameter, default in zip(args.kwonlyargs, args.kw_defaults):
        if parameter.arg not in ignored:
            result.append((
                parameter.arg, "keyword_only", _annotation(parameter),
                ast.unparse(default) if default is not None else None,
            ))
    if args.kwarg is not None:
        result.append((args.kwarg.arg, "kwargs", _annotation(args.kwarg), None))
    return result


def check_gate_stub() -> set[str]:
    gates, classes = source_gate_classes()
    stub_text = STUB_PATH.read_text(encoding="utf-8")
    if stub_text.count(STUB_MARKER) != 1:
        raise AssertionError("Generated core.pyi gate section marker missing or duplicated")
    marker_line = next(
        i for i, line in enumerate(stub_text.splitlines(), start=1) if STUB_MARKER in line
    )
    parsed_stub = ast.parse(stub_text, filename=str(STUB_PATH))
    pathsum = next(
        (c for c in parsed_stub.body if isinstance(c, ast.ClassDef) and c.name == "PathSum"),
        None,
    )
    if pathsum is None:
        raise AssertionError("Generated stub has no PathSum class")
    methods = {
        node.name: node for node in pathsum.body
        if isinstance(node, ast.FunctionDef) and node.lineno > marker_line
    }
    if set(methods) != set(gates):
        raise AssertionError(
            f"PathSum gate stub differs from Gate classes: "
            f"missing={sorted(set(gates)-set(methods))}, "
            f"stale={sorted(set(methods)-set(gates))}"
        )
    for name, cls in sorted(gates.items()):
        init = method_in_hierarchy(cls, "__init__", classes)
        apply = method_in_hierarchy(cls, "apply", classes)
        if apply is None:
            raise AssertionError(f"{name} has no resolvable Gate.apply declaration")
        expected = (
            (parameter_shape(init, {"self"}) if init is not None else [])
            + parameter_shape(apply, {"self", "pathsum"})
        )
        actual = parameter_shape(methods[name], {"self"})
        if expected != actual:
            raise AssertionError(
                f"{name} stub params differ from Gate implementation:\n"
                f"source={expected}\nstub={actual}"
            )
        if ast.get_docstring(methods[name]) is None:
            raise AssertionError(f"Missing generated Gate method docstring: {name}")
    return set(gates)


def check_griffe(gates: set[str]) -> None:
    # This call must be entirely static. No QuPRS or Qiskit imports are made.
    import griffe

    module = griffe.load(
        STATIC_PACKAGE,
        search_paths=[str(ROOT / "src")],
        allow_inspection=False,
    )
    cls = module["PathSum"]
    missing = gates - set(cls.members)
    if missing:
        raise AssertionError(
            f"Griffe did not merge core.pyi dynamic Gate methods: {sorted(missing)}"
        )
    for name in gates:
        if cls.members[name].docstring is None:
            raise AssertionError(f"Griffe dropped the docstring for {name}")
    for name in ("Register", "F"):
        if name not in module.members:
            raise AssertionError(f"Missing advanced Python API class: {name}")
    print(f"Source/stub/Griffe static PathSum Gate parity PASS: {len(gates)} methods")


def check_site() -> None:
    html = (ROOT / "site" / "pathsum-api" / "index.html").read_text(encoding="utf-8")
    for name, anchor in (
        ("PathSum", 'id="QuPRS.pathsum.core.PathSum"'),
        ("Register", 'id="QuPRS.pathsum.core.Register"'),
        ("F", 'id="QuPRS.pathsum.core.F"'),
        ("StatisticsManager", 'id="QuPRS.pathsum.statistics.StatisticsManager"'),
    ):
        if anchor not in html:
            raise AssertionError(f"Static advanced API HTML missing class {name}")
    gate_names = check_gate_stub()
    for name in gate_names:
        anchor = f'id="{STATIC_PACKAGE}.PathSum.{name}"'
        if anchor not in html:
            raise AssertionError(f"Rendered PathSum gate method missing: {name}")
    print(f"Rendered advanced PathSum Gate reference PASS: {len(gate_names)} methods")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--site", action="store_true")
    args = parser.parse_args()
    if not args.check and not args.site:
        parser.error("select --check and/or --site")
    if args.check:
        check_griffe(check_gate_stub())
    if args.site:
        check_site()


if __name__ == "__main__":
    main()
