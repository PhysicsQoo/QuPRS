"""Source-only tests for durable TACAS results archival; no Solver calls."""
import json
from pathlib import Path

from scripts.tacas26_archive_results import classify, generate


def test_archiver_keeps_raw_original_verdicts_and_184_rows(tmp_path):
    download=tmp_path/"download"
    base=download/"tacas26-quprs-v091-shard-0"/"tacas26-quprs-only"
    base.mkdir(parents=True)
    raw={"id":"table2:ghz32:positive:hybrid","status":"RETURNED",
         "verdict":"equivalent*",
         "source_sha":"e928abc47dd15926364ec77905eb0d5dc92ce8cc",
         "original":{"sha256":"a"*64},
         "counterpart":{"sha256":"b"*64},
         "solver_calls":[{"stdout":"original GPMC trace"}],
         "derived_rr":{"provenance":"SAME_HYBRID_INVOCATION",
                       "verdict":"equivalent*"}}
    (base/"table2_ghz32_positive_hybrid.json").write_text(json.dumps(raw))
    (base/"summary.json").write_text(json.dumps({"results":[
        {"id":raw["id"],"status":"RETURNED","verdict":"equivalent*",
         "source_result_file":"table2_ghz32_positive_hybrid.json"},
        {"id":"table3_positive:wstate32:positive:wmc_only",
         "status":"MISSING_RESULT","verdict":None,
         "source_result_file":"table3_positive_wstate32_positive_wmc_only.json"}
    ]}))
    dest=tmp_path/"results"
    counts=generate(download,dest)
    archived=json.loads((dest/"results.json").read_text())
    assert len(archived["rows"])==184
    assert len(archived["derived_rr"])==37
    record=next(x for x in archived["rows"] if x["id"]==raw["id"])
    assert record["classification"]=="MATCH"
    assert record["original_sha256"]=="a"*64
    assert "original GPMC trace" in json.dumps(archived["selected_raw_evidence"][raw["id"]])
    missing=next(x for x in archived["rows"] if x["id"]==
                 "table3_positive:wstate32:positive:wmc_only")
    assert missing["classification"]=="MISSING_RESULT"
    assert missing["observed_verdict"] is None
    assert counts["MATCH"]==1
    assert len((dest/"results.csv").read_text().splitlines())==185
    assert len((dest/"derived_rr.csv").read_text().splitlines())==38


def test_timeout_policy_does_not_claim_missing_result_is_match():
    assert classify("Timeout","RETURNED","Timeout")=="MATCH"
    assert classify("Timeout","EXTERNAL_TIMEOUT",None)=="CENSORED_WATCHDOG_COMPATIBLE"
    assert classify("Timeout","MISSING_RESULT",None)=="MISSING_RESULT"
    assert classify("equivalent*","RETURNED","Timeout")=="RESOURCE_LIMIT_INCOMPLETE"
    assert classify("equivalent*","RETURNED","not_equivalent")=="VERDICT_DIFFERENCE_REVIEW"
