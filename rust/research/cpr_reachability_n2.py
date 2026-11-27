"""N2: compare actual native gate-built receipts to independent gate matrices.
All amplitudes are integers over sqrt(2)^h; no floats, WMC or native evaluator.
A PASS reproduces the defect, not correctness of the current RR.
"""
import json
import sys
from cpr_normalization_n1 import matrix, equal

GATES = (("h",1),("h",2),("h",0),("ccx",0,1,2),("ccx",1,2,0),("h",0),("h",1),("h",2))

def source():
    # Numerators of ordinary H and CCX matrices composed directly.
    out = {}
    for x in range(8):
        v = {x:1}
        for gate in GATES:
            w = {}
            for y,c in v.items():
                if gate[0]=="h":
                    bit=1<<gate[1]
                    for z in (y&~bit,y|bit):
                        w[z]=w.get(z,0)+c*(-1 if y&z&bit else 1)
                else:
                    _,a,b,t=gate
                    z=y^(1<<t) if y&(1<<a) and y&(1<<b) else y
                    w[z]=w.get(z,0)+c
            v={k:c for k,c in w.items() if c}
        for y,c in v.items():
            out[tuple((x>>i)&1 for i in range(3)),tuple((y>>i)&1 for i in range(3))]=(c,0,0,0)
    return out,6

def trace_numerator(m):
    return tuple(sum(v[i] for (x,y),v in m[0].items() if x==y) for i in range(4))

def main(path):
    rows=[json.loads(l.split("CPR_N2_RECEIPT ",1)[1]) for l in open(path) if l.startswith("CPR_N2_RECEIPT ")]
    assert len(rows)==4
    states={r["case"]:matrix(r["state"],[],0) for r in rows}
    assert set(states)=={"raw","first_external_hh","auto_reduced","difference_empty"}
    expected=source()
    assert equal(states["raw"],expected)
    assert (len(expected[0]),trace_numerator(expected),expected[1])==(26,(40,0,0,0),6)
    for name,h,support,tr in [("first_external_hh",5,40,24),("auto_reduced",3,40,12),("difference_empty",3,40,12)]:
        actual=states[name]
        assert (len(actual[0]),trace_numerator(actual),actual[1])==(support,(tr,0,0,0),h),name
        assert not equal(actual,expected),name
        assert set(actual[0])!=set(expected[0]),name
        print("CPR_N2_ORACLE",json.dumps({"case":name,"hidden":h,"support":support,"trace_numerator":tr,"matches_source":False,"status":"DEFECT_REPRODUCED"}))
    assert equal(states["auto_reduced"],states["difference_empty"])
    print("CPR_N2_GATE",json.dumps({"raw_source_match":True,"external_hh_reachable":True,"auto_reduce_mismatch":True,"difference_empty_mismatch":True,"diagnostic_only":True,"status":"PASS"}))

if __name__=="__main__":
    main(sys.argv[1])
