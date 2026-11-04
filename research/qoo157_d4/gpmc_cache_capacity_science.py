"""QOO-157 P4 GPMC bounded cache capacity SCIENCE. No speed measurements.

Never use -cs=1: pinned GPMC allocates 900001 hash-bucket pointers and
can enter deleteEntries with zero eligible entries on first cache insertion.
The only studied controls are 16, 64, 4000 MiB, already above static floor.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from gpmc_td_ablation import COUNT, COMPLEX
from gpmc_vs_td_factorial import close_enough

CASES = ("grover4_eq", "qft16_eq")
CAP_MIB = (16, 64, 4000)
CAPTURE = ("conflicts", "decisions", "propagations", "Components",
           "Split", "Cache lookup", "Cache hit", "Cache reduce")
METRICS = re.compile(r"(?m)^c o (.+?)\s+=\s+(\d+)\b")


def inspect(binary: Path, cnf: Path, cache_mib: int, td: bool) -> dict:
    if cache_mib not in CAP_MIB:
        raise ValueError("unqualified cache capacity")
    cmd = [str(binary), "-mode=1", "-prec=38", "-vs=1",
           "-cs=" + str(cache_mib), "-td" if td else "-no-td",
           str(cnf)]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        return {"status": "CENSORED_TIMEOUT", "timeout_seconds": 40}
    if cp.returncode != 0:
        return {"status": "CENSORED_NATIVE_FAILURE",
                "exit_code": cp.returncode,
                "stderr_excerpt": cp.stderr[-300:],
                "stdout_sha256": sha256(cp.stdout.encode()).hexdigest()}
    tokens = COUNT.findall(cp.stdout)
    if len(tokens) != 1:
        return {"status": "CENSORED_MISSING_COUNT",
                "stdout_sha256": sha256(cp.stdout.encode()).hexdigest()}
    v = COMPLEX.fullmatch(tokens[0].strip())
    if not v:
        return {"status": "CENSORED_MALFORMED_COMPLEX_COUNT"}
    number = tuple(Decimal(x) for x in v.groups())
    if not all(x.is_finite() for x in number):
        return {"status": "CENSORED_NONFINITE_COUNT"}
    raw = {k: int(x) for k, x in METRICS.findall(cp.stdout)}
    if any(k not in raw for k in CAPTURE):
        return {"status": "CENSORED_MISSING_NATIVE_STATS",
                "keys": sorted(raw)}
    if ("FlowCutter is running..." in cp.stdout) != td:
        return {"status": "CENSORED_TD_NOT_APPLIED"}
    return {"status": "NATIVE_COUNT_PRESENT", "count": number,
            "counters": {k: raw[k] for k in CAPTURE},
            "stdout_sha256": sha256(cp.stdout.encode()).hexdigest()}


def main(binary: Path, cnfs: Path, archived: Path, dest: Path) -> None:
    reference = json.loads(archived.read_text())
    if reference.get("complete") is not True:
        raise ValueError("source science archive not admitted")
    data = {
        "status": "INCOMPLETE",
        "scope": "cache-capacity-native-structure-and-complex-WMC-no-timing",
        "gpmc_gitlink": "a1bda3489e959d3695b6798d327c5a1fc1bed305",
        "binary_sha256": sha256(binary.read_bytes()).hexdigest(),
        "cache_cap_mib": list(CAP_MIB),
        "excluded_unsafe_cache_cap_mib": [1],
        "original_cnf_artifact_run": 41822549728,
        "official_codspeed_measurements": False,
        "cases": {},
    }
    failures = []
    dest.parent.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        cnf = cnfs / (case + ".cnf")
        source_info = reference["cases"][case]
        digest = sha256(cnf.read_bytes()).hexdigest()
        if digest != source_info["same_cnf_sha256"]:
            raise ValueError("original source CNF SHA mismatch " + case)
        ref = source_info["precision_pairs"]["38"]["observations"]["gpmc-38"]
        with localcontext() as ctx:
            ctx.prec = 110
            oracle = tuple(Decimal(Fraction(ref[k]).numerator) /
                Decimal(Fraction(ref[k]).denominator) for k in ("real", "imag"))
        variants = {}
        for td in (True, False):
            for cap in CAP_MIB:
                key = ("td_on" if td else "td_off") + "_cap_" + str(cap)
                v = inspect(binary, cnf, cap, td)
                if v["status"] == "NATIVE_COUNT_PRESENT":
                    ok, delta, bound = close_enough(v.pop("count"), oracle)
                    v["count_scale_delta"] = delta
                    v["count_scale_bound"] = bound
                    v["count_status"] = ("COUNT_CONCORDANT_UNCERTIFIED" if ok else
                                         "CENSORED_NUMERICAL_MISMATCH")
                    v["status"] = ("PASS" if ok else "CENSORED_NUMERICAL_MISMATCH")
                if v["status"] != "PASS":
                    failures.append((case, key, v["status"]))
                variants[key] = v
                data["cases"][case] = {
                    "source_cnf_sha256": digest,
                    "variants": variants,
                }
                dest.write_text(json.dumps(data, indent=2) + "\n")
            # The same-source same-TD 4000 MB path must not trigger eviction
            # (matches source-pinned earlier P2; otherwise fail closed).
            big = variants[("td_on" if td else "td_off") + "_cap_4000"]
            if big["status"] == "PASS" and big["counters"]["Cache reduce"] != 0:
                failures.append((case, "td_" + str(td), "BASELINE_UNEXPECTED_EVICTION"))
    data["failure_or_censoring"] = failures
    data["status"] = ("CACHE_CAPACITY_SCIENCE_PASS_12_OF_12" if not failures else
                      "CACHE_CAPACITY_SCIENCE_CENSORED_NOT_ADMITTED")
    # This table describes *structural* changes only, not relative performance.
    data["changed_reduction_behaviour"] = {
        case: {
            "td_" + ("on" if td else "off"): {
                "cap_16_reductions": row["variants"][("td_on" if td else "td_off")+"_cap_16"].get("counters", {}).get("Cache reduce"),
                "cap_64_reductions": row["variants"][("td_on" if td else "td_off")+"_cap_64"].get("counters", {}).get("Cache reduce"),
                "cap_4000_reductions": row["variants"][("td_on" if td else "td_off")+"_cap_4000"].get("counters", {}).get("Cache reduce"),
            } for td in (True, False)
        } for case, row in data["cases"].items()
    }
    dest.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"status": data["status"],
                      "failure_or_censoring": failures,
                      "changed_reduction_behaviour": data["changed_reduction_behaviour"]}))
    if failures:
        raise ValueError("Not all cache-capacity science settings admitted")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("binary", "cnfs", "archived", "out"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    main(a.binary, a.cnfs, a.archived, a.out)
