#!/usr/bin/env python3
"""Check published example syntax against the live API and run each example."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "site" / "examples.md"
API_SOURCE = ROOT / "src" / "QuPRS" / "interface" / "load_qiskit.py"
FENCES = re.compile(r"(?ms)^```(python|bash)\n(.*?)^```[ \t]*$")


def examples() -> tuple[list[str], list[str]]:
    page = PAGE.read_text(encoding="utf-8")
    blocks = [(language, code) for language, code in FENCES.findall(page)]
    python_blocks = [code for language, code in blocks if language == "python"]
    shell_blocks = [code for language, code in blocks if language == "bash"]
    if len(python_blocks) != 5 or len(shell_blocks) != 1:
        raise AssertionError("Expected five standalone Python and one CLI shell example")
    return python_blocks, shell_blocks


def public_signature() -> set[str]:
    source = ast.parse(API_SOURCE.read_text(encoding="utf-8"), filename=str(API_SOURCE))
    functions = [node for node in source.body if isinstance(node, ast.FunctionDef)
                 and node.name == "check_equivalence"]
    if len(functions) != 1:
        raise AssertionError("Missing or ambiguous public check_equivalence declaration")
    f = functions[0]
    return {arg.arg for arg in f.args.posonlyargs + f.args.args + f.args.kwonlyargs}


def verify_keywords(block: str, accepted: set[str]) -> None:
    tree = ast.parse(block, filename="published-example")
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
               and node.module == "QuPRS"
               and any(alias.name == "check_equivalence" for alias in node.names)]
    if not imports:
        raise AssertionError("Example does not import the public QuPRS entry point")
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "check_equivalence"]
    if not calls:
        raise AssertionError("Example does not call check_equivalence")
    if not any(isinstance(node, ast.Assert) for node in ast.walk(tree)):
        raise AssertionError("Example does not assert an expected result")
    for call in calls:
        bad = [kw.arg for kw in call.keywords if kw.arg not in accepted]
        if bad:
            raise AssertionError(f"Unsupported check_equivalence keyword(s): {bad}")
        if len(call.args) < 2:
            raise AssertionError("Example omits one of the two circuits")


def syntax_check() -> tuple[list[str], list[str]]:
    python_blocks, shell_blocks = examples()
    accepted = public_signature()
    for block in python_blocks:
        compile(block, str(PAGE), "exec")
        verify_keywords(block, accepted)
    # A negative fixture ensures missing API parameters fail closed.
    invalid = ("from QuPRS import check_equivalence\n"
               "assert check_equivalence(None, None, imaginary_option=True)\n")
    try:
        verify_keywords(invalid, accepted)
    except AssertionError as exc:
        if "imaginary_option" not in str(exc):
            raise
    else:
        raise AssertionError("Invalid API arguments were accepted")
    for block in shell_blocks:
        result = subprocess.run(
            ["bash", "-n"], input=block, text=True, capture_output=True,
            timeout=10, check=False,
        )
        if result.returncode:
            raise AssertionError(f"Invalid CLI shell example: {result.stderr}")
    return python_blocks, shell_blocks


def execute() -> None:
    python_blocks, shell_blocks = syntax_check()
    for index, block in enumerate(python_blocks, start=1):
        try:
            result = subprocess.run(
                [sys.executable, "-c", block], cwd=ROOT, capture_output=True,
                text=True, timeout=90, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AssertionError(f"Python example {index} exceeded 90 s") from exc
        if result.returncode:
            raise AssertionError(
                f"Python example {index} failed (exit={result.returncode}):\n"
                + (result.stdout + result.stderr)[-6000:]
            )
        print(f"Python example {index}: PASS")
    for index, block in enumerate(shell_blocks, start=1):
        try:
            result = subprocess.run(
                ["bash", "-euo", "pipefail", "-c", block], cwd=ROOT,
                capture_output=True, text=True, timeout=180, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AssertionError(f"CLI example {index} exceeded 180 s") from exc
        if result.returncode:
            raise AssertionError(
                f"CLI example {index} failed (exit={result.returncode}):\n"
                + (result.stdout + result.stderr)[-6000:]
            )
        print(f"CLI example {index}: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not (args.check or args.run):
        parser.error("select --check or --run")
    if args.run:
        execute()
    else:
        python_blocks, shell_blocks = syntax_check()
        print(f"Documentation example syntax: PASS ({len(python_blocks)} Python, "
              f"{len(shell_blocks)} shell)")


if __name__ == "__main__":
    main()
