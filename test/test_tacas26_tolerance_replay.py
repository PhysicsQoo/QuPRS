"""Only source-data/rational-math checks; never execute Solver or CodSpeed."""
import json
from fractions import Fraction
from decimal import Decimal

from scripts.tacas26_tolerance_replay import predict, metrics, generate


def test_projective_distance_fraction_classifier_is_not_old_rounded_log():
    # exact normalized defect 1 - (9999/10000)^2, independent of float rounding
    count={"id":"synthetic","solver_real_printed":"0.9999",
           "solver_imag_printed":"+0","expected_log2":0}
    defect,phase=metrics(count)
    assert defect==1-Fraction(9999,10000)**2
    assert phase==0
    assert predict(defect,phase,"0.02","1e-8")=="equivalent"
    assert predict(defect,phase,"0.01","1e-8")=="not_equivalent"


def test_phase_wrapping_explicitly_differs_from_legacy_get_theta():
    r={"id":"synthetic","solver_real_printed":"1",
       "solver_imag_printed":"-0.000000000000001","expected_log2":0}
    d,p=metrics(r)
    assert 0<p<2e-15
    assert predict(d,p,"2e-5","1e-8")=="equivalent"
    assert predict(d,p,"2e-5","1e-16")=="equivalent*"


def test_full_historical_numeric_corpus_sweep(tmp_path):
    report=generate(out=tmp_path)
    assert report["population"]=={"all":184,"wmc":101,"positive":45,"negative":56}
    by_key={(s["distance_tolerance"],s["phase_tolerance"]):s for s in report["sweep"]}
    for epsilon,match,exact in [("1e-8",79,78),("1e-6",94,89),
                                 ("1e-5",98,93),("2e-5",101,96),
                                 ("1e-4",101,96)]:
        observed=by_key[(epsilon,"1e-8")]
        assert (observed["binary_match"],observed["exact_match"])==(match,exact)
    assert report["phase_infeasibility"]["single_phase_tolerance_possible"] is False
    assert report["max_accepted_distance"]["id"]=="table2:qpeinexact24:positive:hybrid"
    assert report["min_rejected_distance"]["id"]=="table3_negative:qaoa11:negative:hybrid"
    assert 1.37e-5<float(report["max_accepted_distance"]["value"])<1.39e-5
    assert 0.246<float(report["min_rejected_distance"]["value"])<0.247
    assert len((tmp_path/"cases.csv").read_text().splitlines())==185
    assert len((tmp_path/"sweep.csv").read_text().splitlines())==1+len(report["sweep"])
    snapshot=json.loads((tmp_path/"report.json").read_text())
    assert snapshot["source_sha"]=="e928abc47dd15926364ec77905eb0d5dc92ce8cc"
