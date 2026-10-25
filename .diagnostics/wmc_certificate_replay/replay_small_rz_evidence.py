#!/usr/bin/env python3
"""Replay raw, SHA256-sealed small-RZ CNF evidence; never trust saved verdict flags."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wmc_interval_reference"))
from import_dimacs import normalized_for_pathsum, parse_emitted_dimacs
from interval_wmc import ComplexInterval, WeightedCNF
from phase_coeff_reference import union_printed_and_ideal
from python_diagonal_source_certificate import (
    parse_diagonal_qasm, source_phase_terms, source_unit_complex)
from qasm_rz_source_reference import audit_single_rz_bra_source
from evidence_contract import source_cnf_bundle
from independent_source_oracle import independent_source_check

QASM = ('OPENQASM 2.0;\ninclude "qelib1.inc";\n'
        'qreg q[1];\nrz(0.0002) q[0];\n').encode()
HEAD = {"python": "ed72156b860dbafe750bbc0fe2d2e537253609a1",
        "rust": "1adbb067793d2bdf6ae7ff24b7cac27a1655c609"}
NAME = "rz_below_tolerance"


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def check(ok, why):
    if not ok:
        raise ValueError(why)


def verify_manifest(folder):
    lines = (folder/"SHA256SUMS").read_text().splitlines()
    check(0 < len(lines) < 1000, "Missing or oversized manifest")
    seen = set()
    for row in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  \./([^\r\n]+)", row)
        check(m is not None, "Malformed manifest")
        digest, name = m.groups()
        p = Path(name)
        check(name not in seen and name != "SHA256SUMS"
              and not p.is_absolute() and ".." not in p.parts,
              "Unsafe or duplicate artifact path")
        actual = (folder/p).resolve()
        check(actual.is_relative_to(folder.resolve()) and actual.is_file()
              and actual.stat().st_size < 10_000_000, "Missing/unsafe artifact")
        check(sha(actual.read_bytes()) == digest, "Modified evidence: "+name)
        seen.add(name)
    actual_files = {str(f.relative_to(folder)) for f in folder.rglob("*")
                    if f.is_file() and f.name != "SHA256SUMS"}
    check(seen == actual_files, "Unlisted evidence / incomplete manifest")


def witnesses(cnf, input_var):
    groups = [[], []]
    for a in range(1 << len(cnf.weights)):
        if all(any(bool(a & (1 << (abs(lit)-1))) == (lit > 0)
                   for lit in clause) for clause in cnf.clauses):
            groups[bool(a & (1 << (input_var-1)))].append(a)
    check(all(len(group) == 1 for group in groups), "Nonunique CNF extension")
    return [group[0] for group in groups]


def replay_python(cnf):
    check(3 <= len(cnf.weights) <= 12, "Unexpected source-CNF size")
    w0, w1 = witnesses(cnf, 1)
    unit = ComplexInterval.exact(1)
    roles = {}
    for i, (positive, negative) in enumerate(cnf.weights, 1):
        check(negative == unit, "Nonunit negative literal")
        if i == 1:
            check(positive == unit, "Source input has nonunit weight")
        elif positive != unit:
            pattern = (bool(w0 & (1 << (i-1))), bool(w1 & (1 << (i-1))))
            role = {(True,True):"constant", (False,True):"bit"}.get(pattern)
            check(role and role not in roles, "Invalid monomial activation")
            roles[role] = i
    check(set(roles) == {"constant","bit"}, "Missing required phase literals")
    ops = parse_diagonal_qasm(QASM.decode())
    check(ops == (("rz", F(1,5000)),), "Source angle unexpected")
    model = source_phase_terms(ops)
    source, hull = [], []
    for i, (printed, negative) in enumerate(cnf.weights, 1):
        kind = next((kind for kind, idx in roles.items() if idx == i), None)
        ideal = source_unit_complex(model[kind]) if kind else printed
        source.append((ideal, negative))
        hull.append((union_printed_and_ideal(printed,ideal) if kind else printed,
                     negative))
    exact = normalized_for_pathsum(WeightedCNF(cnf.clauses,tuple(source)).count(),
                                   num_qubits=1,num_pathvar=0)
    wide = normalized_for_pathsum(WeightedCNF(cnf.clauses,tuple(hull)).count(),
                                  num_qubits=1,num_pathvar=0)
    check(exact.upper < 1 and wide.upper < 1, "Insufficient rational proof")
    return {"upper":str(wide.upper), "source_upper":str(exact.upper),
            "phase_roles":roles, "input_witnesses":[str(w0),str(w1)]}


def parse_rust_phases(raw):
    lines = raw.decode().splitlines()
    check(len(lines) == 3 and lines[0] ==
          "weight_lit\tphase_numerator\tphase_denominator\tmonomial",
          "Invalid Rust coefficient header/count")
    records = {}
    for row in lines[1:]:
        fields = row.split("\t")
        check(len(fields) == 4, "Invalid phase TSV row")
        lit,num,den = map(int, fields[:3])
        check(lit > 0 and lit not in records and den > 0
              and 0 <= num < den and fields[3] in ("","0"), "Invalid phase fraction")
        records[lit] = (num, den, fields[3])
    check({v[2] for v in records.values()} == {"","0"}, "Missing phase monomial")
    return records


def replay_rust(cnf, raw_phase):
    phases = parse_rust_phases(raw_phase)
    # This independent verifier is based on dev, not the branch-specific
    # Boolean proof in the original Rust run. Recompute activation from the
    # archived CNF itself; NEVER trust the original JSON truth flags.
    phase_by_kind = {data[2]: lit for lit, data in phases.items()}
    check(len(cnf.weights) == 3
          and set(phase_by_kind) == {"", "0"}
          and len(set(phase_by_kind.values())) == 2,
          "Unexpected Rust one-input/two-phase CNF structure")
    inputs = set(range(1, 4)) - set(phase_by_kind.values())
    check(len(inputs) == 1, "Ambiguous CNF input variable")
    input_var = inputs.pop()
    w0, w1 = witnesses(cnf, input_var)
    constant_var = phase_by_kind[""]
    bit_var = phase_by_kind["0"]
    is_set = lambda a, index: bool(a & (1 << (index-1)))
    check(is_set(w0, constant_var) and is_set(w1, constant_var)
          and not is_set(w0, bit_var) and is_set(w1, bit_var),
          "Rust weighted literal activation disagrees with source monomials")
    proof = audit_single_rz_bra_source(
        QASM.decode(),cnf,phases,
        num_qubits=1,num_pathvar=0)
    check(proof["source_radians"] == "1/5000"
          and proof["source_reference_strictly_below_one"]
          and proof["source_represented_printed_hull_strictly_below_one"],
          "Rust phase/source/CNF proof inconclusive")
    check(proof["native_solver_interval_certified"] is False,
          "Native arithmetic is not certified")
    return {"upper":proof["source_represented_printed_hull_normalized_magnitude"]["upper"],
            "source_upper":proof["source_reference_normalized_magnitude"]["upper"],
            "boolean_witnesses":{
                "input_variable":input_var,
                "unique_extensions":[str(w0),str(w1)],
                "constant_phase_literal":constant_var,
                "input_bit_phase_literal":bit_var,
                "activation_verified":True}}


def replay(folder,backend):
    folder = Path(folder).resolve()
    verify_manifest(folder)
    check((folder/"source-sha.txt").read_text().strip() == HEAD[backend],
          "Evidence head SHA is not the pinned commit")
    check(re.fullmatch(r"[0-9a-f]{40}",(folder/"source-tree.txt").read_text().strip()),
          "Malformed source Git tree")
    summary = json.loads((folder/"summary.json").read_text())
    records = summary["observations" if backend == "python" else "cases"]
    check(summary["status"] == "PASS" and len(records) == (24 if backend=="python" else 14),
          "Original experiment controls missing")
    selected = [r for r in records
                if r.get("source_name" if backend=="python" else "case") == NAME]
    check(len(selected)==2 and {r["solver"] for r in selected}=={"gpmc","ganak"},
          "Missing or repeated solver evidence")
    qasm = (folder/(NAME+".qasm")).read_bytes()
    check(qasm == QASM, "Source QASM altered or not supported")
    findings = []
    for solver in ("gpmc","ganak"):
        row = next(r for r in selected if r["solver"]==solver)
        data = (folder/(NAME+"-"+solver+".cnf")).read_bytes()
        check(row["cnf_sha256"]==sha(data)
              and row["source_qasm_sha256" if backend=="rust" else "qasm_sha256"]==sha(qasm),
              "Raw CNF/QASM hash differs from experiment")
        key = ("native_solver_binary_sha256" if backend=="rust"
               else "native_executable_sha256")
        check(re.fullmatch(r"[0-9a-f]{64}",row[key]) is not None,
              "Invalid observed binary SHA")
        check(bool(row["native_solver_stdout" if backend=="rust" else "native_stdout"]),
              "Missing native solver output")
        check(row["native_solver_result_is_interval_certified"] is False if backend=="rust"
              else row["native_observational_only"] is True,
              "Floating solver output not labeled as observation")
        cnf = parse_emitted_dimacs(data.decode(),solver=solver)
        if backend=="python":
            claim = replay_python(cnf)
            analytic = independent_source_check(qasm,data,"python",solver)
            saved = row["source_certificate"][
                "inclusive_source_printed_normalized_magnitude"]["upper"]
        else:
            phases = (folder/(NAME+"-"+solver+"-phases.tsv")).read_bytes()
            claim = replay_rust(cnf,phases)
            analytic = independent_source_check(qasm,data,"rust",solver,phases)
            saved = row["source_decimal_radian_rz_audit"][
                "source_represented_printed_hull_normalized_magnitude"]["upper"]
        check(analytic["source_sha256"]==sha(qasm)
              and analytic["cnf_sha256"]==sha(data)
              and analytic["source_semantics_conditional"] is True
              and analytic["native_solver_certified"] is False,
              "Independent analytic/Boolean source oracle failed")
        claim["independent_analytic_source_oracle"]=analytic
        check(saved == claim["upper"], "Saved proof upper differs from raw replay")
        findings.append({
            "backend":backend,"solver":solver,"source_commit":HEAD[backend],
            "source_sha256":sha(qasm),"cnf_sha256":sha(data),
            "raw_recomputed_upper":claim["upper"],
            "restricted_source_model_not_equivalent":True,
            "native_solver_arithmetic_certified":False,
            "general_compiler_soundness_certified":False,
            "native_binary_sha256_observation":row[key],
            "replay":claim})
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--python-artifact",type=Path,required=True)
    ap.add_argument("--rust-artifact",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args = ap.parse_args()
    records = replay(args.python_artifact,"python")+replay(args.rust_artifact,"rust")
    check(len(records)==4 and len({r["source_sha256"] for r in records})==1,
          "Cross-backend source identity mismatch")
    # Typed scientific claims follow, never precede raw archive verification.
    obj = source_cnf_bundle(records, expected_source_hash=sha(QASM))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    for r in records:
        print("REPLAY",r["backend"],r["solver"],"NON_EQ_SOURCE_MODEL",
              "upper",r["raw_recomputed_upper"])

if __name__=="__main__":
    main()
