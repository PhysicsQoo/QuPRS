#!/usr/bin/env python3
"""Research-only native GPMC arithmetic-DAG rounding-amplification exponent.

Tracks q at EVERY Complex result on a disposable source copy:
  q(a+b) = 1 + max(q(a), q(b))
  q(a*b) = 1 + q(a) + q(b)
  q(exact power-of-two shift) = q(a)
Under a faithful exact sum/product DAG and nonexceptional MPFR primitives,
the output arithmetic radius is S * ((1+eta)^q-1), eta <= 16*2^-p,
where S is the exact positive-envelope polynomial over quantized weights.

Unlike plain K = distinct executed ops, q accounts for reuse/duplication
in multiplications. No production solver source or submodule is changed.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from gpmc_cache_phase15_probe import count, patch

CASES = {
    "qpeexact8-baseline": ("34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7", 14, 17, 22),
    "qpeexact8-self_negative": ("b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7", 8, 2, 16),
    "qft16-baseline": ("20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1", 86, 400, 102),
    "qft16-self_negative": ("8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c", 80, 385, 96),
}
MAX_WEIGHT_MAG = Fraction(1) + Fraction(1, 2**40)
PROBE = re.compile(r"P17_DAG q=(\d+) prec_bits=(\d+) uf=(\d+) of=(\d+) nan=(\d+) erange=(\d+)")


def annotate(source: Path, dest: Path):
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git", "build"))
    head = dest / "c-mpfr/ComplexMPFR.h"
    cpp = dest / "c-mpfr/ComplexMPFR.cc"
    main = dest / "core/Main.cc"

    patch(head, "#define ComplexMPFR_h\n",
          "#define ComplexMPFR_h\n#include <cstdint>\n")
    patch(head, "mpfr::mpreal imag;   ",
          "mpfr::mpreal imag;\n"
          "    std::uint64_t p17_rounding_exponent = 0;")
    patch(cpp, '#include "ComplexMPFR.h"\n',
          '#include "ComplexMPFR.h"\n'
          '#include <algorithm>\n#include <cstdint>\n#include <cstdlib>\n'
          'namespace {\n'
          'std::uint64_t p17_add(std::uint64_t a, std::uint64_t b) {\n'
          '    if (UINT64_MAX - a < b) std::abort();\n'
          '    return a + b;\n'
          '}\n'
          '}\n')
    patch(cpp,
          "Complex &Complex::operator=(const int v)\n{\n"
          "    // mpc_set_d_d(value, v, 0, MPC_RNDNN);\n"
          "    // return *this;\n"
          "    this->real = mpfr::mpreal(v);\n"
          "    this->imag = mpfr::mpreal(0);\n"
          "    return *this;\n}",
          "Complex &Complex::operator=(const int v)\n{\n"
          "    // mpc_set_d_d(value, v, 0, MPC_RNDNN);\n"
          "    // return *this;\n"
          "    this->real = mpfr::mpreal(v);\n"
          "    this->imag = mpfr::mpreal(0);\n"
          "    this->p17_rounding_exponent = 0;\n"
          "    return *this;\n}")
    patch(cpp,
          "Complex &Complex::operator=(const std::string &s)\n{\n"
          "    // mpc_set_str(value, s.c_str(), 0, MPC_RNDNN);\n"
          "    // return *this;\n"
          "    this->real = mpfr::mpreal(s);\n"
          "    this->imag = mpfr::mpreal(0);\n"
          "    return *this;\n}",
          "Complex &Complex::operator=(const std::string &s)\n{\n"
          "    // mpc_set_str(value, s.c_str(), 0, MPC_RNDNN);\n"
          "    // return *this;\n"
          "    this->real = mpfr::mpreal(s);\n"
          "    this->imag = mpfr::mpreal(0);\n"
          "    this->p17_rounding_exponent = 0;\n"
          "    return *this;\n}")
    patch(cpp,
          "Complex Complex::operator+(const Complex &v) const\n{\n"
          "    return Complex(real + v.real, imag + v.imag);\n}",
          "Complex Complex::operator+(const Complex &v) const\n{\n"
          "    Complex r(real + v.real, imag + v.imag);\n"
          "    r.p17_rounding_exponent = p17_add(1,"
          " std::max(p17_rounding_exponent,v.p17_rounding_exponent));\n"
          "    return r;\n}")
    patch(cpp,
          "    this->imag = imag + v.imag;\n    return *this;\n}",
          "    this->imag = imag + v.imag;\n"
          "    p17_rounding_exponent = p17_add(1,"
          " std::max(p17_rounding_exponent,v.p17_rounding_exponent));\n"
          "    return *this;\n}")
    patch(cpp,
          "Complex Complex::operator*(const Complex &v) const\n{\n"
          "    return Complex(real * v.real - imag * v.imag, real * v.imag + imag * v.real);\n}",
          "Complex Complex::operator*(const Complex &v) const\n{\n"
          "    Complex r(real * v.real - imag * v.imag, real * v.imag + imag * v.real);\n"
          "    r.p17_rounding_exponent = p17_add(1,"
          "p17_add(p17_rounding_exponent,v.p17_rounding_exponent));\n"
          "    return r;\n}")
    patch(cpp,
          "    this->imag = im;\n    return *this;\n}",
          "    this->imag = im;\n"
          "    p17_rounding_exponent = p17_add(1,"
          "p17_add(p17_rounding_exponent,v.p17_rounding_exponent));\n"
          "    return *this;\n}")
    # Both non-const and const left-shift overloads are exact on ordinary finite MPFR values.
    patch(cpp,
          "Complex Complex::operator<<(const int u)\n{\n"
          "    return Complex(real << u, imag << u);\n}",
          "Complex Complex::operator<<(const int u)\n{\n"
          "    Complex r(real << u, imag << u);\n"
          "    r.p17_rounding_exponent=p17_rounding_exponent;\n"
          "    return r;\n}")
    patch(cpp,
          "Complex Complex::operator<<(const int u) const\n{\n"
          "    return Complex(real << u, imag << u);\n}",
          "Complex Complex::operator<<(const int u) const\n{\n"
          "    Complex r(real << u, imag << u);\n"
          "    r.p17_rounding_exponent=p17_rounding_exponent;\n"
          "    return r;\n}")
    # Capture root result BEFORE diagnostics such as PrintLog10 change MPFR flags.
    patch(main,
          "static void printResult(bool sat, Mode mode, const Complex& result) {",
          "static void printResult(bool sat, Mode mode, const Complex& result) {\n"
          "    std::fprintf(stderr,"
          " \"P17_DAG q=%llu prec_bits=%ld uf=%d of=%d nan=%d erange=%d\\n\","
          " (unsigned long long) result.p17_rounding_exponent,"
          " (long)mpfr::mpreal::get_default_prec(),"
          " (int)mpfr_underflow_p(),(int)mpfr_overflow_p(),"
          " (int)mpfr_nanflag_p(),(int)mpfr_erangeflag_p());")
    return {
        "complex_header_sha256":sha256(head.read_bytes()).hexdigest(),
        "complex_source_sha256":sha256(cpp.read_bytes()).hexdigest(),
        "main_source_sha256":sha256(main.read_bytes()).hexdigest(),
    }


def fmt(x: Fraction):
    if not x: return "0"
    with localcontext() as c:
        c.prec=40
        return f"{Decimal(x.numerator)/Decimal(x.denominator):.15E}"


def bound(q, p, n_minus_m, m, twice):
    # Quantized-input WMC only. Source-to-binary, printed-output and
    # circuit-to-CNF transport must be added separately.
    eta = Fraction(16,2**p)
    t = eta*q
    if not t < 1:
        return {"status":"unsupported","reason":"roundoff_amplification_exceeds_bound"}
    N = 2**n_minus_m
    S = N*MAX_WEIGHT_MAG**m
    normalized = S*(t/(1-t))/Fraction(2)**(twice//2)
    return {"status":"conditional",
            "arithmetic_exponent_q":q,
            "normalized_count_radius":fmt(normalized),
            "scope":"quantized input WMC; source parse/print/error separate",
            "solver_semantics_certified":False,
            "amplification_formula":"S*(16*q*2^-p)/(1-16*q*2^-p)"}


def run(binary:Path, cnf:Path, output:Path, mode:str):
    cmd=[str(binary),"-mode=1","-prec=90","-cs=16"]
    if mode=="preproc-mainloop-skipped":cmd.append("-varlim=0")
    cmd.append(str(cnf))
    cp=subprocess.run(cmd,capture_output=True,text=True,timeout=50)
    (output/(binary.name+"-"+mode+".stdout")).write_text(cp.stdout)
    (output/(binary.name+"-"+mode+".stderr")).write_text(cp.stderr)
    if cp.returncode:raise RuntimeError(f"run failed exit {cp.returncode}")
    fields=PROBE.findall(cp.stderr)
    return {"count":count(cp.stdout),"sat":re.findall(r"^s (SATISFIABLE|UNSATISFIABLE)$",cp.stdout,re.M),
            "probe":fields, "stdout_sha256":sha256(cp.stdout.encode()).hexdigest()}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--baseline",type=Path,required=True)
    ap.add_argument("--artifact-folder",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    records=[]
    with tempfile.TemporaryDirectory(prefix="gpmc-dag-q-") as scratch:
        scratch=Path(scratch)
        src=scratch/"src"
        pins=annotate(args.source.resolve(),src)
        (out/"source-sha256.json").write_text(json.dumps(pins,indent=2)+"\n")
        for name,cmd in (
            ("configure",["cmake","-S",str(src),"-B",str(scratch/"build"),
                          "-DCMAKE_BUILD_TYPE=Release"]),
            ("build",["cmake","--build",str(scratch/"build"),"-j","4"])
        ):
            cp=subprocess.run(cmd,capture_output=True,text=True,timeout=250)
            (out/(name+".stdout")).write_text(cp.stdout)
            (out/(name+".stderr")).write_text(cp.stderr)
            if cp.returncode:raise RuntimeError(name+" error: "+cp.stderr[-3000:])
        probe=scratch/"build/gpmc"
        # Avoid clobbering files when baseline binary has the same filename.
        for label,(cnfhash,n_minus_m,m,twice) in CASES.items():
            cnf=args.artifact_folder/(label+".cnf")
            if not cnf.is_file():
                continue
            if sha256(cnf.read_bytes()).hexdigest()!=cnfhash:
                raise AssertionError("source CNF hash mismatch: "+label)
            for mode in ["default","preproc-mainloop-skipped"]:
                o=out/label
                o.mkdir(exist_ok=True)
                base=run(args.baseline.resolve(),cnf,o/"baseline",mode) if False else None
                # Dedicated per-executable folders preserve both raw streams.
                (o/"baseline").mkdir(exist_ok=True)
                (o/"probe").mkdir(exist_ok=True)
                original=run(args.baseline.resolve(),cnf,o/"baseline",mode)
                measured=run(probe,cnf,o/"probe",mode)
                if original["sat"]!=measured["sat"] or original["count"]!=measured["count"]:
                    raise AssertionError("instrumentation changed native count or SAT "+label+"/"+mode)
                if len(measured["probe"])!=1:
                    raise AssertionError("missing DAG q and MPFR flags")
                q,p,uf,of,nan,erange=map(int,measured["probe"][0])
                row={"label":label,"mode":mode,"q":q,"p":p,
                     "mpfr_flags":{"underflow":uf,"overflow":of,"nan":nan,"erange":erange},
                     "same_count":True,"same_boolean_sat":True,
                     "baseline_count":[str(x) for x in original["count"]],
                     "printed_cnf_sha256":cnfhash,
                     **bound(q,p,n_minus_m,m,twice)}
                records.append(row)
                print("P17_NATIVE_DAG "+json.dumps(row,sort_keys=True),flush=True)
    if not records:
        raise AssertionError("no verified source-pinned CNF files found")
    out.joinpath("summary.json").write_text(json.dumps({"records":records,
         "native_DAG_exponent_instrumented":True,
         "unmodified_gpmc_submodule":True,
         "general_solver_forward_error_certified":False},indent=2)+"\n")


if __name__=="__main__":
    main()
