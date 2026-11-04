"""QOO-157 P5: no-timing native d4 cache on/off x BiPe science screen."""
import argparse, json, re, subprocess
from pathlib import Path
from hashlib import sha256
from decimal import Decimal, localcontext
from fractions import Fraction
from gpmc_td_ablation import COMPLEX
from gpmc_vs_td_factorial import close_enough
from qoo157_preprocess_compare import D4_RESULT, D4_COUNTS

CASES = ("qaoa7_neq", "qft16_eq")
BIPE = {
    "auto": (),
    "none": ("--preproc.auto-config=false", "--preproc.preproc-method=none"),
}
FLAG = re.compile(r"--(?:[a-zA-Z0-9_]+\.)*cache\.isActivated\b")
COUNTERS = {
    "Number of recursive call": "recursive_calls",
    "Number of split formula": "splits",
    "Number of decision": "decisions",
    "Number of positive hit": "positive_hits",
    "Number of negative hit": "negative_hits",
}
METRICS = re.compile(
    r"(?m)^c (Number of (?:recursive call|split formula|decision|positive hit|negative hit)):\s*(\d+)\s*$"
)

def discover(binary):
    p = subprocess.run([str(binary), "-h"], capture_output=True,
                       text=True, timeout=15, check=True)
    found = set(FLAG.findall(p.stdout))
    if len(found) != 1 or "actual-gmp-precision-bits 128" not in p.stdout:
        raise ValueError("native cache CLI flag or 38d/128bit provenance ambiguous: " +
                         repr(sorted(found)))
    return found.pop(), sha256(p.stdout.encode()).hexdigest()

def native(binary, cnf, flag, bipe, enabled):
    args = ["-i", str(cnf), f"{flag}={'true' if enabled else 'false'}",
            *BIPE[bipe]]
    try:
        p = subprocess.run([str(binary), *args], capture_output=True,
                           text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {"status": "CENSORED_TIMEOUT", "timeout": 30, "args": args[2:]}
    if p.returncode:
        return {"status": "CENSORED_NATIVE_ERROR", "exit": p.returncode,
                "stderr": p.stderr[-400:], "args": args[2:],
                "stdout_tail": p.stdout[-500:]}
    found = D4_RESULT.findall(p.stdout)
    if len(found) != 1:
        return {"status": "CENSORED_COUNT_NOT_FOUND", "count_matches": len(found),
                "stdout_tail": p.stdout[-500:]}
    match = COMPLEX.fullmatch(found[0].strip())
    if match is None:
        return {"status": "CENSORED_MALFORMED_WMC"}
    value = tuple(Decimal(z) for z in match.groups())
    if not all(z.is_finite() for z in value):
        return {"status": "CENSORED_NONFINITE"}
    stats = {COUNTERS[k]: int(n) for k, n in METRICS.findall(p.stdout)}
    if len(stats) != len(COUNTERS):
        return {"status": "CENSORED_MISSING_NATIVE_COUNTERS",
                "stats": stats, "stdout_tail": p.stdout[-600:]}
    if not enabled and (stats["positive_hits"] or stats["negative_hits"]):
        raise ValueError("native cache-off flag had nonzero cache hits")
    stages = {}
    for stage, vars_, clauses, active, protected, weights, projected in D4_COUNTS.findall(p.stdout):
        if stage in stages:
            raise ValueError("duplicate BiPe stage")
        stages[stage] = dict(vars=int(vars_), clauses=int(clauses),
                             active=int(active), protected=int(protected),
                             weights=int(weights), projected=int(projected))
    if set(stages) != {"before", "after"}:
        raise ValueError("source-pinned output-only BiPe diagnostic missing")
    if bipe == "none" and any(stages["before"][k] != stages["after"][k]
                              for k in ("vars", "clauses", "active")):
        raise ValueError("BiPe none unexpectedly changed Boolean dimensions")
    return {"status": "NATIVE_COMPLETED", "value": [str(x) for x in value],
            "native_stats": stats, "bipe_stages": stages, "flags": args[2:],
            "stdout_sha256": sha256(p.stdout.encode()).hexdigest()}

def study(binary, cnfs, archive, out):
    source = json.loads(archive.read_text())
    if source.get("complete") is not True:
        raise ValueError("archived source science incomplete")
    flag, native_help_sha = discover(binary)
    report = {
        "status": "INCOMPLETE", "issue": "QOO-157",
        "d4_source_pin": "be15f91f3e9769e1f5cb175fa27e3eca3a1ea690",
        "native_cache_flag": flag, "native_help_sha256": native_help_sha,
        "binary_sha256": sha256(binary.read_bytes()).hexdigest(),
        "effective_decimal_digits": 38, "actual_gmp_bits": 128,
        "original_archive_run_id": 41822549728,
        "performance_instrument": "NONE",
        "internal_roundoff_certified": False,
        "cases": {}, "censored": [], "scientific_failures": [],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        cnf = cnfs / f"{case}.cnf"
        anchor = source["cases"][case]
        digest = sha256(cnf.read_bytes()).hexdigest()
        if digest != anchor["same_cnf_sha256"]:
            raise ValueError("Original source CNF SHA mismatch: " + case)
        observation = anchor["precision_pairs"]["38"]["observations"]["d4-38"]
        if observation["status"] != "COMPLETED":
            raise ValueError("Archived native d4 baseline incomplete")
        with localcontext() as ctx:
            ctx.prec = 110
            oracle = tuple(Decimal(Fraction(observation[k]).numerator) /
                           Decimal(Fraction(observation[k]).denominator)
                           for k in ("real", "imag"))
        row = {"source_cnf_sha256": digest, "variants": {}, "effects": {}}
        report["cases"][case] = row
        for bipe in BIPE:
            for enabled in (True, False):
                key = f"{bipe}_cache_{'on' if enabled else 'off'}"
                result = native(binary, cnf, flag, bipe, enabled)
                if result["status"] == "NATIVE_COMPLETED":
                    ok, delta, bound = close_enough(
                        tuple(Decimal(x) for x in result["value"]), oracle)
                    result.update(count_delta=delta, count_bound=bound,
                                  status="PASS" if ok else "NUMERICAL_MISMATCH",
                                  count_screen="COUNT_CONCORDANT_UNCERTIFIED" if ok
                                                else "CENSORED_NUMERICAL_MISMATCH")
                    if not ok:
                        report["scientific_failures"].append([case, key, delta, bound])
                else:
                    report["censored"].append([case, key, result["status"]])
                row["variants"][key] = result
                out.write_text(json.dumps(report, indent=2) + "\n")
            on = row["variants"][f"{bipe}_cache_on"]
            off = row["variants"][f"{bipe}_cache_off"]
            if on["status"] != "PASS":
                report["scientific_failures"].append([case, bipe, "BASELINE_NOT_ADMITTED"])
            if on["status"] == off["status"] == "PASS":
                x, y = on["native_stats"], off["native_stats"]
                row["effects"][bipe] = {
                    "status": "ON_OFF_COUNT_CONCORDANT",
                    "positive_cache_hits_on": x["positive_hits"],
                    "negative_cache_hits_on": x["negative_hits"],
                    "cache_hits_off": y["positive_hits"] + y["negative_hits"],
                    "additional_decisions_off": y["decisions"] - x["decisions"],
                    "additional_recursive_calls_off": y["recursive_calls"] - x["recursive_calls"],
                }
            else:
                row["effects"][bipe] = {"status": "CENSORED_UNPAIRED"}
    report["admitted_pairs"] = [
        [c, b] for c, v in report["cases"].items() for b, effect in v["effects"].items()
        if effect["status"] == "ON_OFF_COUNT_CONCORDANT"]
    report["status"] = (
        "D4_CACHE_SCIENCE_FAILED" if report["scientific_failures"] else
        "D4_CACHE_SCIENCE_WITH_CENSORING" if report["censored"] else
        "D4_CACHE_SCIENCE_PASS_8_OF_8")
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "censored": report["censored"],
                      "admitted_pairs": report["admitted_pairs"],
                      "effects": {c: v["effects"] for c, v in report["cases"].items()}}))
    if report["scientific_failures"]:
        raise ValueError("d4 cache science failed")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for a in ("binary", "cnfs", "archive", "out"):
        p.add_argument("--" + a, type=Path, required=True)
    args = p.parse_args()
    study(args.binary, args.cnfs, args.archive, args.out)
