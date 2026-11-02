"""Pure research-only contracts for RR@1e-8 versus Ganak@2e-5 probes."""
from scripts import tacas26_rr_vs_ganak_calibration as t


def test_shards_are_bounded_and_all_source_pinned():
    cases, historical = t.check_plan(t.ROOT)
    assert len(t.SHARDS) == 11
    assert sum(len(shard) for shard in t.SHARDS) >= 35
    assert all(len(shard) <= 6 for shard in t.SHARDS)
    for shard in t.SHARDS:
        for case_id, solver, backend, method, distance, rr in shard:
            assert case_id in cases and case_id in historical
            assert t.binary(historical[case_id]["verdict"]) is not None
            if solver == "ganak":
                assert distance == "2e-5"
                assert rr == "1e-10"
            else:
                assert distance == "1e-8"


def test_distance_strict_and_rr_high_both_positive_and_negative_controls():
    for c in (t.RR_QPE20, t.RR_QPE24):
        specs = [r for group in t.SHARDS for r in group if r[0] == c and r[1] == "gpmc"]
        assert {x[5] for x in specs if x[2] == "rust"} == set(t.RR_LEVELS)
    for c in (t.RR_QAOA_NEG, t.RR_QWALK_NEG):
        specs = [r for group in t.SHARDS for r in group if r[0] == c and r[1] == "gpmc"]
        assert {x[5] for x in specs} == {"1e-10", "2e-5", "1e-4"}


def test_wmc_only_is_mechanistically_rr_invariant():
    for c in (t.WMC_QFT20, t.WMC_QFT22):
        specs = [r for group in t.SHARDS for r in group if r[0] == c and r[1] == "gpmc"]
        assert len(specs) == 2
        assert {x[5] for x in specs} == {"1e-10", "1e-4"}
        assert all(x[3] == "wmc_only" and x[4] == "1e-8" for x in specs)


def test_ganak_both_backends_and_both_binary_directions():
    items = [r for group in t.SHARDS for r in group if r[1] == "ganak"]
    assert len(items) >= 20
    assert all(r[4] == "2e-5" and r[5] == "1e-10" for r in items)
    assert {"rust", "python"} == {r[2] for r in items}
    negatives = {r[0] for r in items if ":negative:" in r[0]}
    positives = {r[0] for r in items if ":positive:" in r[0]}
    assert len(negatives) >= 3
    assert len(positives) >= 3
    assert any(x.endswith(":wmc_only") for x in negatives | positives)


def test_verdict_error_and_timeout_are_never_success():
    assert t.classification("equivalent*", {"run_status": "COMPLETED",
                                            "verdict": "equivalent"}) == "BINARY_MATCH"
    assert t.classification("not_equivalent", {"run_status": "COMPLETED",
                                              "verdict": "equivalent*"}) == "BINARY_MISMATCH"
    assert t.classification("equivalent", {"run_status": "COMPLETED",
                                           "verdict": "not_equivalent"}) == "BINARY_MISMATCH"
    assert t.classification("not_equivalent", {"run_status": "WATCHDOG_CENSORED",
                                              "verdict": "not_equivalent"}) == "CENSORED_OR_INVALID"
    assert t.classification("not_equivalent", {"run_status": "COMPLETED",
                                              "verdict": "unknown"}) == "CENSORED_OR_INVALID"
