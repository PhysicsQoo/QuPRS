"""Guard pinned, research-only d4 precision initialization and exact controls."""
import unittest
from fractions import Fraction
from d4_mpf_init_ab import MARKER, patched_source
from poc_d4 import oracle_count
from precision_probe import cases


class GMPInitializationTests(unittest.TestCase):
    def test_injection_occurs_before_counter_construction(self):
        fixture = (
            "#include <cassert>\n"
            "T result = counter->run();\n"
            "void counter() {\n  // Use the provided configuration.\n}\n"
        )
        altered = patched_source(fixture)
        self.assertIn(MARKER, altered)
        self.assertIn("#include <cstdlib>", altered)
        self.assertLess(altered.index(MARKER),
                        altered.index("  // Use the provided configuration."))
        with self.assertRaisesRegex(ValueError, "already applied"):
            patched_source(altered)

    def test_layout_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "source structure changed"):
            patched_source("void counter() {}")

    def test_small_nonzero_witness_is_exact_in_independent_oracle(self):
        examples = cases()
        for component in ("real", "imag"):
            for exponent in (16, 20, 28, 40, 60):
                key = f"{component}_residual_1e-{exponent}"
                if key not in examples:
                    continue
                result = oracle_count(examples[key])
                value = result[0] if component == "real" else result[1]
                self.assertEqual(value, Fraction(1, 10**exponent))


if __name__ == "__main__":
    unittest.main()
