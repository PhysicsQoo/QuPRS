"""Public 1e-8 projective-distance boundary checks with independent analytic oracle."""
import argparse
import json
from pathlib import Path
from mpmath import mp
from QuPRS import check_equivalence
HEAD='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
ANG=("0.0000000099","0.0000000196","0.0000000199",
     "0.0000000201","0.0000000204","0.00000004")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    rows=[]
    with mp.workdps(90):
        for angle in ANG:
            distance=abs(mp.sin(mp.mpf(angle)/2))
            for backend in ("python","rust"):
                result=check_equivalence(HEAD,HEAD+"rz("+angle+") q[0];\n",
                    method="wmc_only",strategy="Naive",tool_name="gpmc",
                    backend=backend,approximate_distance_tolerance=1e-8,
                    timeout=45)
                verdict=result.equivalent
                assert verdict in ("equivalent","equivalent*","unknown","not_equivalent")
                assert result.wmc_solver_invoked is True
                # Only assert at points away from the unresolved numerical margin.
                if distance<=mp.mpf("0.75e-8"):
                    assert verdict!="not_equivalent",(angle,backend,verdict)
                if distance>=mp.mpf("1.75e-8"):
                    assert verdict not in ("equivalent","equivalent*"),(angle,backend,verdict)
                row={"angle":angle,"d_proj":str(distance),"backend":backend,
                     "verdict":verdict,"reason":getattr(result,"wmc_precision_reason",None)}
                rows.append(row)
                print("PUBLIC_BOUNDARY case={} backend={} D={} status={}".format(
                    angle,backend,distance,verdict),flush=True)
    args.out.write_text(json.dumps({"threshold":"1e-8","rows":rows},
                                    indent=2,default=str)+"\n")
    print("PUBLIC_BOUNDARY_SUMMARY rows={} passed={}".format(len(rows),len(rows)),flush=True)
if __name__=="__main__":
    main()
