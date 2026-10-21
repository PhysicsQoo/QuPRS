#!/usr/bin/env python3
"""Strict family-held-out model comparison on original six-family Elim clocks.

Exploratory post-hoc work: ALL source fixtures have unsuccessful Elim only.
No scheduler / speedup / zero-overhead inference is justified.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

import numpy as np

FAMILIES = ("qaoa7", "qft16", "grover4", "vqe4", "graphstate16", "ghz32")
FEATURES = {
    "M0_constant": (),
    "M1_L_only": ("l",),
    "M2_scan_K_L": ("l", "k"),
    "M3_K_L_V_D": ("k", "l", "v", "d"),
    "M4_old_W_proxy": ("w",),
}
ALPHA = 0.02
ROUNDS = 8


def check_archive(path):
    blob = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError("ZIP CRC failure: " + bad)
        members = set(archive.namelist())
        checks = archive.read("SHA256SUMS").decode().splitlines()
        for line in checks:
            digest, stored = line.split("  ", 1)
            # Original Actions SHA256SUMS paths are artifact-root-relative
            # with an extra directory that upload-artifact removes.
            name = stored.removeprefix("rust-elim-cost-pilot-results/")
            if name not in members:
                raise ValueError("missing SHA256SUMS member: " + name)
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("SHA256 mismatch: " + name)
        if len(checks) < 110:
            raise ValueError("incomplete original artifact SHA256SUMS")
        raw = {name: json.loads(archive.read(name)) for name in members
               if name.endswith(".json") and name.startswith("individual/")}
        summary = json.loads(archive.read("summary.json"))
        env = json.loads(archive.read("environment.json"))
        if summary["status"] != "PASS_DATA_COLLECTION" or summary["errors"]:
            raise ValueError("source experimental run is not accepted")
        return raw, {
            "artifact_zip_sha256": hashlib.sha256(blob).hexdigest(),
            "sha256sum_files_verified": len(checks),
            "source_git_sha": env["git"]["stdout"].strip(),
            "gpmc_sha256": env["gpmc_binary_sha256"],
        }


def structural_data(raw):
    data = []
    for family in FAMILIES:
        stages = []
        for round_id in range(ROUNDS):
            name = f"individual/{family}_{round_id:03d}_timed.json"
            if name not in raw:
                raise ValueError("missing timed sample " + name)
            point = raw[name]
            if point["errors"] or point["case"] != family or point["mode"] != "timed":
                raise ValueError("invalid timed sample " + name)
            ledger = point["stage_ledger"]
            feat = ledger["structural_elim_attempts"]
            times = ledger["elim_attempt_timings"]
            if len(feat) != len(times):
                raise ValueError("structural/timing count mismatch")
            for i, t in enumerate(times):
                if (t["structural_index"] != i or t["success"]
                    or type(t["elapsed_ns"]) is not int or t["elapsed_ns"] <= 0):
                    raise ValueError("invalid/unsupported Elim event")
            stages.append((feat, times))
        first = stages[0][0]
        for run_feats, _ in stages[1:]:
            if first != run_feats:
                raise ValueError("structural features vary across timing repeats")
        for pos, f in enumerate(first):
            elapsed = [times[pos]["elapsed_ns"] for _,times in stages]
            data.append({
                "family":family, "event_index":pos,
                "k":f["k_r"],"l":f["l_r"],"v":f["v_r"],
                "d":f["d_r"],"w":f["w_redundant_estimated"],
                "median_elapsed_ns":statistics.median(elapsed),
                "replicates":len(elapsed),
            })
    return data


def predict(train, test, predictors):
    """Family-equal weighted ridge on log(ns), scaling train data ONLY."""
    count = collections.Counter(x["family"] for x in train)
    weights = np.asarray([1.0/count[x["family"]] for x in train], dtype=float)
    weights /= weights.sum()
    y = np.log(np.asarray([x["median_elapsed_ns"] for x in train],dtype=float))
    y_mean = float(weights @ y)
    if not predictors:
        return np.full(len(test), y_mean)
    x = np.asarray([[math.log1p(row[f]) for f in predictors] for row in train])
    x_test = np.asarray([[math.log1p(row[f]) for f in predictors] for row in test])
    mu = weights @ x
    sigma = np.sqrt(weights @ ((x - mu)**2))
    sigma[sigma < 1e-8] = 1.0
    z = (x-mu)/sigma
    z_test = (x_test-mu)/sigma
    beta = np.linalg.solve(
        z.T @ (weights[:,None]*z) + ALPHA*np.eye(len(predictors)),
        z.T @ (weights*(y-y_mean))
    )
    return y_mean + z_test @ beta


def compare(rows):
    per_family = {}
    for held in FAMILIES:
        train = [r for r in rows if r["family"] != held]
        test = [r for r in rows if r["family"] == held]
        assert train and test and {r["family"] for r in train}.isdisjoint({held})
        values = np.log([r["median_elapsed_ns"] for r in test])
        per_family[held] = {}
        for model, features in FEATURES.items():
            predicted = predict(train, test, features)
            per_family[held][model] = float(np.abs(predicted-values).mean())
    macro = {m: statistics.mean(per_family[f][m] for f in FAMILIES)
             for m in FEATURES}
    return per_family, macro


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", type=Path, required=True,
                   help="Original GitHub Actions rust-elim-six-family-cost ZIP (PR #60)")
    p.add_argument("--out", type=Path, default=Path("cost-model-lofo-results"))
    args = p.parse_args()
    raw, provenance = check_archive(args.artifact)
    rows = structural_data(raw)
    if len(rows) != 555 or any(r["replicates"] != ROUNDS for r in rows):
        raise ValueError("unexpected source event set; fail closed")
    per_family,macro = compare(rows)
    args.out.mkdir(parents=True,exist_ok=True)
    report = {
        "schema":"quprs-exploratory-family-heldout-elim-v1",
        "status":"PASS_EXPLORATORY_ANALYSIS",
        "provenance":provenance,
        "source_pilot":"https://github.com/PhysicsQoo/QuPRS/actions/runs/39528135089",
        "population":"Failed Elim only (all 555 positions success=false)",
        "independent_groups":len(FAMILIES),
        "event_positions":len(rows),
        "replicates_per_event":ROUNDS,
        "protocol":{
            "validation":"Leave one entire circuit family out; fit on other five families",
            "training_weights":"Each training family has equal total weight, positions within family share that weight",
            "target":"log(median elapsed_ns of 8 repeated observations per event)",
            "predictor_transform":"log1p(x), training-fold standardization only",
            "regularizer":"weighted ridge alpha=0.02, no held-out tuning",
            "metric":"mean absolute error in log(ns), macro-averaged over 6 held-out families",
            "models":FEATURES,
        },
        "per_family_mae_log_ns":per_family,
        "macro_mae_log_ns":macro,
        "limitations":[
            "Models chosen after prior six-family exploratory evidence, not prospective preregistration.",
            "All 555 Elim events are unsuccessful; no generalization to successful Elim.",
            "Many correlated positions are nested in only six circuit families; 8 repeats are not independent circuit groups.",
            "The held-out family GHZ32 has only three events; macro-average weights families equally.",
            "Elapsed ns is perturbed by timer overhead and CPU noise, not counterfactual cost.",
            "Feature collinearity prevents interpreting full-model coefficients causally.",
            "The best model here does not justify a new scheduler, solver choice or speedup claim.",
        ],
    }
    (args.out/"model_summary.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    (args.out/"event_medians.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows))
    cols=" | ".join(FEATURES)
    md=["# Leave-one-family-out failed-Elim cost model (exploratory)","",
        f"Original artifact SHA256: \`{provenance['artifact_zip_sha256']}\`",
        f"Source event positions: {len(rows)} over 6 circuit families; all unsuccessful.",
        "",
        "| Held-out family | " + " | ".join(FEATURES) + " |",
        "|---|" + "---:|"*len(FEATURES)]
    for family in FAMILIES:
        md.append("| "+family+" | "+" | ".join(f"{per_family[family][model]:.3f}"
                                            for model in FEATURES)+" |")
    md.append("| **Macro MAE, log ns** | "+" | ".join(f"**{macro[m]:.3f}**"
                                                  for m in FEATURES)+" |")
    md += ["","**Exploratory only.** Success branch, HH, Omega, candidate discovery and",
            "true uninstrumented walltime were not in this training population.",
            "Post-hoc model choice and only six held-out families prohibit deployment."]
    (args.out/"model_summary.md").write_text("\n".join(md)+"\n")
    print("\n".join(md))
    return 0

if __name__ == "__main__":
    sys.exit(main())
