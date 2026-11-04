"""QOO-98 pinned Ganak 2.8.0 Mode6 *output* admission (SCIENCE ONLY).

No solver timing, no CodSpeed, no inference that 9 printed digits certify the
underlying MPFR arithmetic. Checks pinned --version and CLI bits, then several
small exact decimal/rational complex WMC fixtures and their printed ULP steps.
"""
from __future__ import annotations
from decimal import Decimal,localcontext
from hashlib import sha256
import argparse
import json
import re
import subprocess
from pathlib import Path

UPSTREAM="b4ca02f78301aadeb7fa9acb5ed1524dc3fa0281"
EXE_SHA="934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd"
MODE6=re.compile(
    r"^c s exact (?P<dtype>.+?) (?P<real>[+-]?\d\.\d{8}e[+-]\d+) "
    r"\+ (?P<imag>[+-]?\d\.\d{8}e[+-]\d+)i$",
    re.MULTILINE)
HEADER="p cnf {nvars} {nclauses}\nc t wmc\n"
FIXTURES={
    "upstream_two_variable":{
        "cnf":HEADER.format(nvars=2,nclauses=1)+
          "1 2 0\n"
          "c p weight 1 1/2+1i 0\n"
          "c p weight -1 1/2-1i 0\n"
          "c p weight 2 1+0i 0\n"
          "c p weight -2 1+0i 0\n",
        "real":"1.5","imag":"1"
    },
    "signed_complex":{
        "cnf":HEADER.format(nvars=1,nclauses=1)+
          "1 0\n"
          "c p weight 1 -1.23456789012345+0.123456789012345i 0\n"
          "c p weight -1 1+0i 0\n",
        "real":"-1.23456789012345","imag":"0.123456789012345"
    },
    "negative_imaginary":{
        "cnf":HEADER.format(nvars=1,nclauses=1)+
          "1 0\n"
          "c p weight 1 0.87654321098765-0.12345678901234i 0\n"
          "c p weight -1 1+0i 0\n",
        "real":"0.87654321098765","imag":"-0.12345678901234"
    },
    "near_cancellation":{
        "cnf":HEADER.format(nvars=1,nclauses=0)+
          "c p weight 1 1.0000000000000000000001+0.0000000000000000000002i 0\n"
          "c p weight -1 -1+0i 0\n",
        "real":"0.0000000000000000000001",
        "imag":"0.0000000000000000000002"
    },
    "exact_zero_cancellation":{
        "cnf":HEADER.format(nvars=1,nclauses=0)+
          "c p weight 1 1+0i 0\n"
          "c p weight -1 -1+0i 0\n",
        "real":"0","imag":"0"
    }
}


def run(binary:Path,fixtures_dir:Path,out:Path)->dict:
    actual=sha256(binary.read_bytes()).hexdigest()
    if actual!=EXE_SHA:raise ValueError("UNPINNED_GANAK_BINARY_SHA")
    version=subprocess.run([str(binary),"--version"],
         capture_output=True,text=True,timeout=10,check=False)
    if version.returncode or UPSTREAM not in version.stdout:
        raise ValueError("GANAK_VERSION_OR_EMBEDDED_SHA_MISMATCH")
    report={
        "status":"INCOMPLETE",
        "solver":"ganak","version":"2.8.0","upstream_sha":UPSTREAM,
        "native_executable_sha256":actual,
        "native_probes_run":True,"not_a_timing_benchmark":True,
        "internal_MPFR_operation_bits_uncertified":True,
        "printed_complex_significant_decimal_digits":9,
        "printed_rounding_interval_is_not_total_arithmetic_error":True,
        "cases":{}
    }
    fixtures_dir.mkdir(parents=True,exist_ok=True)
    for case,fixture in FIXTURES.items():
        source=fixtures_dir/(case+".cnf")
        source.write_text(fixture["cnf"])
        digest=sha256(source.read_bytes()).hexdigest()
        results={}
        for bits in (127,256):
            cp=subprocess.run([str(binary),"--mode=6",
                    f"--mpfrprec={bits}",str(source)],
                    text=True,capture_output=True,check=False,timeout=20)
            if cp.returncode:
                raise ValueError(f"{case}/{bits} nonzero exit={cp.returncode} stderr={cp.stderr[:250]}")
            matches=list(MODE6.finditer(cp.stdout))
            if len(matches)!=1:
                raise ValueError(f"{case}/{bits}: expected one precisely formatted 9-digit complex count")
            m=matches[0]
            if (bits<=128 and m["dtype"]!="quadruple float") or (
                    bits>128 and m["dtype"]!="octuple float"):
                raise ValueError("unexpected displayed MPFR precision class")
            component={}
            for name in ("real","imag"):
                actual_decimal=Decimal(m[name])
                expected=Decimal(fixture[name])
                # Scientific notation prints 8 digits after the dot.  Using
                # full one printed ULP is a *permissive output screen* only.
                exponent=int(m[name].split("e")[1])
                step=Decimal(1).scaleb(exponent-8)
                with localcontext() as ctx:
                    ctx.prec=100
                    difference=abs(actual_decimal-expected)
                if difference>step:
                    raise ValueError(f"{case}/{bits}/{name}: printed precision screen failed")
                component[name]={"printed":m[name],
                    "independent_exact_decimal_reference":str(expected),
                    "printed_decimal_step":str(step),
                    "absolute_point_delta":str(difference),
                    "within_one_printed_step":True}
            results[str(bits)]={
                "requested_mpfr_bits":bits,
                "printed_precision_class":m["dtype"],
                "printed_complex":m.group(0),
                "native_solver_status":next((line for line in cp.stdout.splitlines()
                                if line.startswith("s ")),None),
                "components":component,
                "stdout_sha256":sha256(cp.stdout.encode()).hexdigest(),
                "count_status":"PRINT_CONCORDANT_UNCERTIFIED",
                "numeric_precision_certified":False
            }
        report["cases"][case]={"source_weighted_cnf_sha256":digest,
                                 "precisions":results}
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+"\n")

    fixture=fixtures_dir/"upstream_two_variable.cnf"
    invalid=subprocess.run([str(binary),"--mode=6","--mpfrprec=512",
         str(fixture)],capture_output=True,text=True,check=False,timeout=10)
    if invalid.returncode==0 or "mpfr precision must not be more than 256 bits" not in (
            invalid.stdout+"\n"+invalid.stderr):
        raise ValueError("512-bit flag unexpectedly accepted despite pinned source")
    report["invalid_512_bit_request"]={
        "rejected":True,"exit_code":invalid.returncode,
        "diagnostic":"mpfr precision must not be more than 256 bits"
    }
    report["status"]="PINNED_GANAK_MODE6_NATIVE_PRINT_RESOLUTION_SCREEN_PASS"
    out.write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--fixtures-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=run(args.binary,args.fixtures_dir,args.out)
    print(json.dumps({"status":result["status"],
        "native_probe_rows":sum(len(c["precisions"]) for c in result["cases"].values()),
        "512_bits_rejected":result["invalid_512_bit_request"]["rejected"]}))
