"""Paper resource limits are observations, not contradictory quantum verdicts."""
import json
from pathlib import Path

import pytest

from scripts.tacas26_compare_paper import compare, expected
from scripts.tacas26_paper_matrix import matrix

ROOT = Path(__file__).resolve().parents[1]
SHA = "e928abc47dd15926364ec77905eb0d5dc92ce8cc"
ORACLE = json.loads((ROOT / "docs/development/tacas26-paper-verdict-oracle.json").read_text())


@pytest.mark.parametrize("id,status,verdict,want,classification", [
    ("table2:qft24:positive:hybrid", "RETURNED", "Timeout",
     "Timeout", "MATCH"),
    ("table2:graphstate16:positive:hybrid", "RETURNED", "Timeout",
     "equivalent", "RESOURCE_LIMIT_INCOMPLETE"),
    ("table3_negative:qpeinexact20:negative:wmc_only", "RETURNED",
     "not_equivalent", "Timeout", "RESOURCE_LIMIT_DIFFERENCE"),
    ("table3_negative:wstate32:negative:hybrid", "EXTERNAL_TIMEOUT",
     None, "Timeout", "CENSORED_WATCHDOG_COMPATIBLE"),
    ("table2:graphstate16:positive:hybrid", "EXTERNAL_TIMEOUT",
     None, "equivalent", "CENSORED_WATCHDOG_UNRESOLVED"),
    ("table3_negative:ghz32:negative:hybrid", "RETURNED",
     "equivalent", "not_equivalent", "VERDICT_MISMATCH"),
])
def test_paper_timeout_science_is_not_a_false_verdict_conflict(
        tmp_path, id, status, verdict, want, classification):
    case = next(x for x in matrix(ROOT) if x["id"] == id)
    assert expected(ORACLE, case) == want
    (tmp_path / "evidence.json").write_text(json.dumps({
        "id": id, "status": status, "verdict": verdict,
        "source_sha": SHA,
    }))
    result = compare(ROOT, [tmp_path])
    row = next(x for x in result["rows"] if x["id"] == id)
    assert row["classification"] == classification
    # Even a paper-compatible censored observation is not strict proof.
    assert result["strict_paper_match_certified"] is False
