"""Deterministic preflight for new source-pinned CodSpeed QASM261 matrix."""
from benchmarks.codspeed.qasm261_paired_cases import GPMC_PAIRS, POSITIONS
from scripts.report_codspeed_qasm261_paired import EXPECTED, ORDER

def test_qasm261_abba_inventory_and_scientific_selection():
    assert len(GPMC_PAIRS) == 5
    assert {row[0] for row in GPMC_PAIRS} == set(EXPECTED)
    assert POSITIONS == (("A1", "base"), ("B1", "head"), ("B2", "head"), ("A2", "base"))
    assert ORDER == dict(POSITIONS)
    assert len({(row[0], position) for row in GPMC_PAIRS for position, _ in POSITIONS}) == 20
    assert {row[4] for row in GPMC_PAIRS} == {"random_rotation", "transpiled"}
    assert {row[5] for row in GPMC_PAIRS} == {"not_equivalent", "equivalent"}
    assert all(row[0].startswith("q261_") for row in GPMC_PAIRS)
