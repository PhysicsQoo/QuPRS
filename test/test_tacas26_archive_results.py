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
    assert record["paper_hybrid_time_s"]==0.027
    assert record["verification_time_s"] is None
    assert record["pathsum_time_s"] is None
    assert record["time_evidence_status"]=="NOT_CAPTURED_IN_ARCHIVED_RUN"
    assert record["codspeed_certified"] is False
    assert record["original_sha256"]=="a"*64
    assert "original GPMC trace" in json.dumps(archived["selected_raw_evidence"][raw["id"]])
    missing=next(x for x in archived["rows"] if x["id"]==
                 "table3_positive:wstate32:positive:wmc_only")
    assert missing["classification"]=="MISSING_RESULT"
    assert missing["observed_verdict"] is None
    assert missing["time_evidence_status"]=="NO_RESULT_FILE"
    assert counts["MATCH"]==1
    assert len((dest/"results.csv").read_text().splitlines())==185
    assert len((dest/"derived_rr.csv").read_text().splitlines())==38
    assert "Paper Hybrid (s)" in (dest/"README.md").read_text()
    assert "46 / 74" in (dest/"README.md").read_text()


def test_timeout_policy_does_not_claim_missing_result_is_match():
    assert classify("Timeout","RETURNED","Timeout")=="MATCH"
    assert classify("Timeout","EXTERNAL_TIMEOUT",None)=="CENSORED_WATCHDOG_COMPATIBLE"
    assert classify("Timeout","MISSING_RESULT",None)=="MISSING_RESULT"
    assert classify("equivalent*","RETURNED","Timeout")=="RESOURCE_LIMIT_INCOMPLETE"
    assert classify("equivalent*","RETURNED","not_equivalent")=="VERDICT_DIFFERENCE_REVIEW"


def test_original_quprs_time_fields_remain_distinct_from_paper_reference(tmp_path):
    from scripts.tacas26_paper_matrix import original_source_timings
    from types import SimpleNamespace
    from scripts.tacas26_archive_results import generate
    instrument=original_source_timings(SimpleNamespace(
        verification_time=0.247, pathsum_time=0.050,
        to_DIMACS_time=0.020, gpmc_time=0.177, wmc_time=0.197))
    assert instrument["values"]["verification_time"]==0.247
    assert instrument["codspeed_certified"] is False
    assert original_source_timings(SimpleNamespace(
        verification_time=">200",pathsum_time=">200",to_DIMACS_time=None,
        gpmc_time=None,wmc_time=None))["values"]["verification_time"]==">200"

    root=tmp_path/"historical-artifacts"
    sub=root/"tacas26-quprs-v091-shard-0"/"tacas26-quprs-only"
    sub.mkdir(parents=True)
    obs={"id":"table2:ghz32:positive:hybrid","status":"RETURNED",
         "verdict":"equivalent*","source_sha":
         "e928abc47dd15926364ec77905eb0d5dc92ce8cc",
         "timing":instrument}
    name="table2_ghz32_positive_hybrid.json"
    (sub/name).write_text(json.dumps(obs))
    (sub/"summary.json").write_text(json.dumps({"results":[{
        "id":obs["id"],"status":"RETURNED","verdict":"equivalent*",
        "source_result_file":name}]}))
    out=tmp_path/"generated"
    generate(root,out)
    archive=json.loads((out/"results.json").read_text())
    row=next(r for r in archive["rows"] if r["id"]==obs["id"])
    assert row["verification_time_s"]==0.247
    assert row["pathsum_time_s"]==0.050
    assert row["to_DIMACS_time_s"]==0.020
    assert row["gpmc_time_s"]==0.177
    assert row["wmc_time_s"]==0.197
    assert row["paper_hybrid_time_s"]==0.027
    assert row["time_evidence_status"]=="ORIGINAL_V091_TIME_CAPTURED"
    assert row["codspeed_certified"] is False


def test_watchdog_timeout_is_not_recorded_as_full_execution_time(tmp_path):
    from scripts.tacas26_archive_results import generate
    root=tmp_path/"source"
    folder=root/"tacas26-quprs-v091-shard-1"/"tacas26-quprs-only"
    folder.mkdir(parents=True)
    id_="table3_negative:wstate32:negative:wmc_only"
    name="table3_negative_wstate32_negative_wmc_only.json"
    payload={"id":id_,"status":"EXTERNAL_TIMEOUT","verdict":None,
             "timeout_seconds":200,"science":"CENSORED_NOT_NOT_EQUIVALENT"}
    (folder/name).write_text(json.dumps(payload))
    (folder/"summary.json").write_text(json.dumps({"results":[{
        "id":id_,"status":"EXTERNAL_TIMEOUT","verdict":None,
        "source_result_file":name}]}))
    target=tmp_path/"output"
    generate(root,target)
    data=json.loads((target/"results.json").read_text())
    row=next(x for x in data["rows"] if x["id"]==id_)
    assert row["time_evidence_status"]=="CENSORED_EXTERNAL_WATCHDOG"
    assert row["verification_time_s"] is None
    assert row["classification"]=="CENSORED_WATCHDOG_COMPATIBLE"
