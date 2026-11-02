"""Science-only contract for entire original TACAS 101-case modern Ganak check."""
from scripts import tacas26_modern_ganak_full101 as g
from scripts.tacas26_modern_full_101 import comparable_source_records, slice_corpus, ROOT

def test_ganak_corpus_is_exactly_the_101_original_gpmc_output_cases():
    rows = comparable_source_records(ROOT)
    assert len(rows) == 101
    assert sum(x[0]["method"] == "hybrid" for x in rows) == 44
    assert sum(x[0]["method"] == "wmc_only" for x in rows) == 57
    assert sum(g.binary(x[1]["verdict"]) == "EQUIVALENT" for x in rows) == 45
    assert sum(g.binary(x[1]["verdict"]) == "NOT_EQUIVALENT" for x in rows) == 56

def test_24_disjoint_shards_cover_exactly_101_without_duplicate():
    rows = [row for shard in range(24) for row in slice_corpus(ROOT, shard, 24)]
    assert len(rows) == 101
    assert len({r[0]["id"] for r in rows}) == 101
    assert all(4 <= len(slice_corpus(ROOT, s, 24)) <= 5 for s in range(24))

def test_ganak_not_equivalent_must_be_determinate_not_timeout_or_unknown():
    assert g.classify("not_equivalent", {"run_status": "COMPLETED",
                                        "verdict": "not_equivalent"}) == "BINARY_MATCH"
    assert g.classify("not_equivalent", {"run_status": "COMPLETED",
                                        "verdict": "equivalent"}) == "BINARY_MISMATCH"
    assert g.classify("equivalent*", {"run_status": "COMPLETED",
                                     "verdict": "not_equivalent"}) == "BINARY_MISMATCH"
    assert g.classify("not_equivalent", {"run_status": "EXTERNAL_WATCHDOG_CENSORED",
                                        "verdict": "not_equivalent"}) == "CENSORED_OR_UNCLASSIFIABLE"
    assert g.classify("not_equivalent", {"run_status": "COMPLETED",
                                        "verdict": "unknown"}) == "CENSORED_OR_UNCLASSIFIABLE"
