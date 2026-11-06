"""Offline negative contracts for the full generated-stub comparison."""

from __future__ import annotations

import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_SPEC = spec_from_file_location(
    "quprs_generated_stub_parity",
    Path(__file__).resolve().parents[1] / "scripts/check_generated_stub.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_CHECKER = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECKER)


ORIGINAL = '''
import QuPRS
import symengine as se

class PathSum:
    """Symbolic circuit.

    Static documentation.
    """

    @staticmethod
    def QuantumCircuit(qubits: int) -> "PathSum":
        """Create a circuit."""
        ...

    def cx(
        self,
        control: "int | str",
        target: "int | str",
        is_bra: bool = False,
    ) -> "PathSum":
        """Apply a CX gate.

        Returns:
            PathSum: New object.
        """
        ...

    def reduction(self) -> "PathSum":
        """Apply reduction rules."""
        ...
'''


FORMATTED = """
import symengine as se
import QuPRS

class PathSum:
    \"\"\"
    Symbolic circuit.

    Static documentation.
    \"\"\"
    @staticmethod
    def QuantumCircuit(qubits: int) -> 'PathSum':
        \"\"\"Create a circuit.\"\"\"
        ...

    def cx(self, control: 'int | str', target: 'int | str', is_bra: bool = False) -> 'PathSum':
        \"\"\"
        Apply a CX gate.

        Returns:
            PathSum: New object.
        \"\"\"
        ...

    def reduction(self) -> 'PathSum':
        \"\"\"Apply reduction rules.\"\"\"
        ...
"""


class GeneratedStubParityTest(unittest.TestCase):
    def test_format_only_differences_allowed(self):
        _CHECKER.compare_stubs(ORIGINAL, FORMATTED)

    def test_changed_return_type_detected(self):
        mutated = FORMATTED.replace(
            "def reduction(self) -> 'PathSum':",
            "def reduction(self) -> bool:",
        )
        with self.assertRaisesRegex(AssertionError, "class.PathSum.reduction.signature"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)

    def test_changed_parameter_or_default_detected(self):
        mutated = FORMATTED.replace(
            "is_bra: bool = False",
            "is_bra: bool = True",
        )
        with self.assertRaisesRegex(AssertionError, "class.PathSum.cx.signature"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)

    def test_changed_docstring_detected(self):
        mutated = FORMATTED.replace("New object.", "Mutated object.")
        with self.assertRaisesRegex(AssertionError, "class.PathSum.cx.docstring"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)

    def test_missing_gate_detected(self):
        mutated = FORMATTED[:FORMATTED.index("    def cx(")]
        with self.assertRaisesRegex(AssertionError, "Stub declarations changed"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)

    def test_decorator_changed_detected(self):
        mutated = FORMATTED.replace("    @staticmethod\n", "    @classmethod\n")
        with self.assertRaisesRegex(AssertionError, "class.PathSum.QuantumCircuit.signature"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)

    def test_import_removed_detected(self):
        mutated = FORMATTED.replace("import QuPRS\n", "")
        with self.assertRaisesRegex(AssertionError, "module.imports"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)

    def test_duplicate_method_detected(self):
        mutated = FORMATTED + "\n    def reduction(self) -> 'PathSum': ...\n"
        with self.assertRaisesRegex(AssertionError, "Duplicate stub method"):
            _CHECKER.compare_stubs(ORIGINAL, mutated)


if __name__ == "__main__":
    unittest.main()
