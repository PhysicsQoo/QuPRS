#!/usr/bin/env python3
"""Validate the generated Cobertura XML before publishing Python coverage."""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def validate_coverage_xml(path: Path) -> tuple[int, int]:
    """Reject missing, malformed, empty, or internally inconsistent reports."""
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Missing or empty coverage.xml")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Malformed coverage.xml: {exc}") from exc
    if root.tag != "coverage":
        raise ValueError("Expected Cobertura coverage root")
    try:
        valid = int(root.attrib["lines-valid"])
        covered = int(root.attrib["lines-covered"])
    except (KeyError, ValueError) as exc:
        raise ValueError("Missing or invalid coverage counters") from exc
    if valid <= 0 or covered < 0 or covered > valid:
        raise ValueError("Impossible coverage counters")

    classes = list(root.iter("class"))
    if not classes:
        raise ValueError("Coverage XML contains no source classes")
    line_count = hit_count = 0
    for source_class in classes:
        if not source_class.attrib.get("filename"):
            raise ValueError("Source class missing filename")
        for line in source_class.findall("./lines/line"):
            try:
                number = int(line.attrib["number"])
                hits = int(line.attrib["hits"])
            except (KeyError, ValueError) as exc:
                raise ValueError("Invalid source line counters") from exc
            if number <= 0 or hits < 0:
                raise ValueError("Negative hits or invalid line number")
            line_count += 1
            hit_count += int(hits > 0)

    if (valid, covered) != (line_count, hit_count):
        raise ValueError(
            f"Coverage counters disagree with source lines: "
            f"header={valid}/{covered}, observed={line_count}/{hit_count}"
        )
    return valid, covered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        valid, covered = validate_coverage_xml(args.report)
    except ValueError as exc:
        parser.exit(1, f"Invalid Python coverage report: {exc}\n")
    print(f"Validated coverage.xml: {valid} source lines, {covered} covered")


if __name__ == "__main__":
    main()
