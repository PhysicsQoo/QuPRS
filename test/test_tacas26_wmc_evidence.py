"""No-Solver contracts for historical WMC evidence extraction."""
import csv
import json

import pytest

from scripts.tacas26_wmc_evidence import extract_printed_count, generate, make_index


@pytest.mark.parametrize("printed,real,imag", [
    ("1.25000+2.50000i", "1.25000", "+2.50000"),
    ("-1.200e+05-3.450e-06i", "-1.200e+05", "-3.450e-06"),
    ("-0.000019", "-0.000019", "0"),
    ("+7.123e-07i", "0", "+7.123e-07"),
    ("0", "0", "0"),
])
def test_preserves_only_gpmc_printed_digits(printed, real, imag):
    outcome=extract_printed_count("c diagnostic\nc s exact double prec-sci "+printed+"\n")
    assert outcome["status"]=="PRINTED_COMPONENTS_AVAILABLE"
    assert outcome["real"]==real
    assert outcome["imag"]==imag
    assert outcome["raw_line"].endswith(printed)


def test_ambiguous_output_never_becomes_a_fabricated_zero():
    for s in ("", "c s exact double prec-sci NaN",
              "c s exact double prec-sci 1+2i\nc s exact double prec-sci 1+3i"):
        result=extract_printed_count(s)
        assert result["status"]!="PRINTED_COMPONENTS_AVAILABLE"
        assert result["real"] is None
        assert result["imag"] is None


def test_gpmc_output_and_old_float_classifier_remain_separate(tmp_path):
    ident="table2:qpeinexact20:positive:hybrid"
    observation={
        "id": ident, "source_sha":"e928abc47dd15926364ec77905eb0d5dc92ce8cc",
        "solver_invoked": True,
        "solver_calls":[{"command":["gpmc","-mode=1","tmp.cnf"],"returncode":0,
                         "stdout":"c s exact double prec-sci 1.234567890123456+0.000000000000001i\n",
                         "stderr":""}],
        "complex_counts":[{"real":1.234567890123456,"imag":1e-15}],
        "expected_log2":0.304, "rounded_log2":0.304,
        "raw_log2_abs_wmc":0.303776, "original_phase_rad":8.1e-16,
        "v091_replayed_verdict":"equivalent*"
    }
    archive={
        "source_sha":observation["source_sha"],
        "rows":[{
            "id":ident, "suite":"table2", "case":"qpeinexact20",
            "kind":"positive","method":"hybrid", "observed_verdict":"equivalent*",
            "status":"RETURNED","run_id":1234,"artifact":"historical-fixture",
            "original_sha256":"a"*64,"counterpart_sha256":"b"*64,
            "gpmc_sha256":"c"*64}],
        "selected_raw_evidence":{ident:{"raw":observation,"raw_json_sha256":"d"*64}}
    }
    # Generator enforces canonical 184-case cardinality. Test this targeted
    # extraction with 184 unique synthetic cases that keep real raw metadata.
    for i in range(183):
        other=f"figure3:synthetic-{i}:positive:reduction_rules"
        archive["rows"].append({
            "id":other,"suite":"figure3","case":f"synthetic-{i}",
            "kind":"positive","method":"reduction_rules",
            "observed_verdict":"equivalent","status":"RETURNED","run_id":1234,
            "artifact":"test-only", "original_sha256":None,
            "counterpart_sha256":None,"gpmc_sha256":None})
    inp=tmp_path/"original.json"
    inp.write_text(json.dumps(archive))
    output=tmp_path/"out"
    totals=generate(inp,output)
    with (output/"wmc-evidence.csv").open(newline="") as f:
        rows=list(csv.DictReader(f))
    result=next(x for x in rows if x["id"]==ident)
    assert len(rows)==184
    assert result["solver_real_printed"]=="1.234567890123456"
    assert result["solver_imag_printed"]=="+0.000000000000001"
    assert result["original_float_real"]=="1.234567890123456"
    assert result["v091_replayed_verdict"]=="equivalent*"
    assert result["source_result_sha256"]=="d"*64
    other=next(x for x in rows if x["id"]=="figure3:synthetic-0:positive:reduction_rules")
    assert other["wmc_evidence_status"]=="NO_WMC_COUNT_CAPTURED"
    assert other["solver_real_printed"]==""
    assert totals["WMC_PRINTED_VALUE_AVAILABLE"]==1
    archived=json.loads((output/"wmc-evidence.json").read_text())
    assert archived["records"][0]["gpmc_invocations"][0]["stderr"]==""
