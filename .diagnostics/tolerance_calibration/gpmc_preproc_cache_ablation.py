"""Phase12 research-only structural ablations of unchanged pinned GPMC.

Ablate *only* preprocessing main-loop (--varlim=0) and cache-size
budget (--cs=1) on identical sealed real CNFs. Run once per variant
under a finite timeout; preserve stdout/stderr/time/RSS. Compare
final 90-digit weighted counts as exact decimal rationals, not floats.
These are behavioral controls, NOT a proof of preprocessing or caching
correctness for general WMC and NOT production benchmark evidence.
"""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,statistics,subprocess,tempfile
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
CASES={
"qpeexact8-baseline":("34d38d1718f1796d6af46cfa079aa2093aa00e5997f5b428e8af4b1672a35ee7",22),
"qpeexact8-self_negative":("b965d82a7bf4900350a2cbef028ff51506b9bb0f426859c1be9432207872d2d7",16),
"qft16-baseline":("20ee9e55eb1fc644d08daf130d180ded46f06f67897fa46f57b4f4ef4ef7f8f1",102),
"qft16-self_negative":("8e65b1d5cfdc99c4d980bc4fea24162afc4f9583e0ebf17686fc8a9f1bc6555c",96)}
VARIANTS={
"default":[],
"preprocess_mainloop_skipped":["-varlim=0"],
"cache_one_megabyte":["-cs=1"],
"both_ablation":["-varlim=0","-cs=1"]}
MARKER="c s exact double prec-sci "
METRIC=re.compile(r"ABLATEMETRIC wall=([0-9.]+) rss_kb=([0-9]+)")

def weighted_pair(text):
    fields=[x[len(MARKER):].strip().replace(" ","")
            for x in text.splitlines() if x.startswith(MARKER)]
    if len(fields)!=1:
        raise ValueError(("missing or duplicated weighted output",len(fields)))
    s=fields[0]
    if s=="0":return Fraction(0),Fraction(0)
    if not s.endswith("i"):raise ValueError(("missing complex output",s))
    body=s[:-1]
    cuts=[i for i in range(1,len(body)) if body[i] in "+-" and body[i-1] not in "eE"]
    if len(cuts)!=1:raise ValueError(("ambiguous complex output",s))
    return Fraction(Decimal(body[:cuts[0]])),Fraction(Decimal(body[cuts[0]:]))
def sci(v):
    if not v:return "0"
    with localcontext() as p:
        p.prec=43
        return format(Decimal(v.numerator)/Decimal(v.denominator),".20E")

def main(args):
    output=args.output;output.mkdir(parents=True,exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix="gpmc-ablation-",dir=str(output.parent)))/"build"
    samples=[];results=[]
    try:
        for command in (["cmake","-S",str(args.gpmc_source),"-B",str(scratch),"-DCMAKE_BUILD_TYPE=Release"],
                       ["cmake","--build",str(scratch),"-j","4"]):
            p=subprocess.run(command,capture_output=True,text=True,timeout=170)
            if p.returncode:raise RuntimeError(("GPMC exact pinned build failed",p.stderr[-1800:]))
        binary=scratch/"gpmc"
        exe_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
        for case,(expected_hash,twice) in CASES.items():
            cnf=args.artifact_folder/(case+".cnf")
            actual_hash=hashlib.sha256(cnf.read_bytes()).hexdigest()
            if actual_hash!=expected_hash:raise AssertionError(("CNF identity mismatch",case))
            base=None
            for flavor,flags in VARIANTS.items():
                name=case+"-"+flavor
                command=["/usr/bin/time","-f","ABLATEMETRIC wall=%e rss_kb=%M",
                         str(binary),"-mode=1","-prec=90",*flags,str(cnf)]
                try:
                    p=subprocess.run(command,capture_output=True,text=True,timeout=35)
                    (output/(name+".stdout")).write_text(p.stdout)
                    (output/(name+".stderr")).write_text(p.stderr)
                    if p.returncode:raise RuntimeError(("nonzero exit",p.returncode))
                    pair=weighted_pair(p.stdout)
                    metric=METRIC.search(p.stderr)
                    if not metric:raise ValueError("time metrics absent")
                    row={"case":case,"flavor":flavor,"flags":flags,"outcome":"success",
                         "cnf_sha256":actual_hash,"binary_sha256":exe_sha,
                         "wall_seconds":float(metric.group(1)),
                         "peak_rss_kb":int(metric.group(2)),
                         "complex_count":[str(pair[0]),str(pair[1])]}
                    if base is None:base=pair
                    if base is None:raise AssertionError("default failed")
                    gap=sum(abs(x-y) for x,y in zip(pair,base))/Fraction(2)**(twice//2)
                    row["normalized_l1_count_gap_from_default"]=sci(gap)
                    # Tolerance here is a research *alarm threshold* only,
                    # NOT a certified GPMC error bound or classifier epsilon.
                    row["below_research_alarm_1e_minus70"]=gap<Fraction(1,10**70)
                    if not row["below_research_alarm_1e_minus70"]:
                        raise AssertionError(("structural variation changed WMC materially",name,sci(gap)))
                except (subprocess.TimeoutExpired,RuntimeError,ValueError) as exc:
                    if flavor=="default":raise
                    row={"case":case,"flavor":flavor,"flags":flags,
                         "outcome":"unverified","failure_type":type(exc).__name__,
                         "not_a_count_equivalence_pass":True}
                samples.append(row)
                print("GPMC_STRUCTURE_ABLATION "+json.dumps(row,sort_keys=True),flush=True)
            results.append({"case":case,"all_four_modes_succeeded":
                            all(x["outcome"]=="success" for x in samples if x["case"]==case)})
        (output/"structural-gpmc-ablation.json").write_text(
            json.dumps({"results":results,"samples":samples,
                        "structural_boolean_or_weighted_semantics_proven":False,
                        "preprocess_varlim_zero_still_runs_initial_SAT_FLE":True,
                        "cache_cs_one_is_low_budget_not_cache_disabled":True,
                        "research_only_gpmc_solver_calls":len(samples),
                        "production_solver_extra_calls":0},indent=2,sort_keys=True)+"\n")
        print("GPMC_STRUCTURE_ABLATIONS_FINISHED",flush=True)
    finally:shutil.rmtree(scratch.parent,ignore_errors=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--gpmc-source",required=True,type=Path)
    p.add_argument("--artifact-folder",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    main(p.parse_args())
