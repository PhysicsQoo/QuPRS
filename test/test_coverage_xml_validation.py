"""Negative contracts for Codecov's source-generated XML acceptance guard."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_coverage_xml import validate_coverage_xml


class CoverageXmlContractTests(unittest.TestCase):
    GOOD_LINES = '<line number="1" hits="1"/><line number="2" hits="0"/>'

    @staticmethod
    def report(valid: object = 2, covered: object = 1, lines: str | None = None) -> str:
        if lines is None:
            lines = CoverageXmlContractTests.GOOD_LINES
        return (
            f'<coverage lines-valid="{valid}" lines-covered="{covered}">'
            '<packages><package><classes>'
            f'<class filename="src/QuPRS/example.py"><lines>{lines}</lines></class>'
            '</classes></package></packages></coverage>'
        )

    def test_accept_realistic_covered_and_missed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "coverage.xml"
            report.write_text(self.report(), encoding="utf-8")
            self.assertEqual(validate_coverage_xml(report), (2, 1))

    def test_reject_malformed_and_inconsistent_reports(self) -> None:
        bad = {
            "empty": "",
            "xml_parse": "<coverage>",
            "wrong_root": '<report lines-valid="2" lines-covered="1"><class/></report>',
            "zero_valid": self.report(0, 0, ""),
            "negative_valid": self.report(-1, 0, ""),
            "negative_covered": self.report(2, -1),
            "overcovered": self.report(2, 3),
            "wrong_valid_count": self.report(100, 1),
            "wrong_covered_count": self.report(2, 2),
            "no_line_records": self.report(2, 1, ""),
            "negative_hits": self.report(1, 0, '<line number="1" hits="-1"/>'),
            "missing_hits": self.report(1, 0, '<line number="1"/>'),
            "invalid_line_number": self.report(1, 1, '<line number="0" hits="1"/>'),
            "missing_class": (
                '<coverage lines-valid="1" lines-covered="0"><package/></coverage>'
            ),
            "missing_filename": (
                '<coverage lines-valid="1" lines-covered="1">'
                '<class><lines><line number="1" hits="1"/></lines></class>'
                '</coverage>'
            ),
            "missing_counters": (
                '<coverage><class filename="src/QuPRS/x.py">'
                '<lines><line number="1" hits="1"/></lines></class></coverage>'
            ),
            "invalid_counters": self.report("nan", 1),
        }
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "coverage.xml"
            with self.subTest(case="missing"):
                with self.assertRaises(ValueError):
                    validate_coverage_xml(report)
            for case, xml in bad.items():
                with self.subTest(case=case):
                    report.write_text(xml, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        validate_coverage_xml(report)


if __name__ == "__main__":
    unittest.main()
