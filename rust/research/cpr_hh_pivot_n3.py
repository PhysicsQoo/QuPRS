"""N3: independent exact source-matrix regression after HH pivot fix."""
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
    rows=[json.loads(l.split("CPR_N3_RECEIPT ",1)[1]) for l in open(path) if l.startswith("CPR_N3_RECEIPT ")]
    assert len(rows)==5
    states={r["case"]:matrix(r["state"],[],0) for r in rows}
    assert set(states)=={"raw","external_rejected","first_internal_hh","auto_reduced","difference_empty"}
    expected=source()
    assert (len(expected[0]),trace_numerator(expected),expected[1])==(26,(40,0,0,0),6)
    for name,h in [("raw",6),("external_rejected",6),("first_internal_hh",4),("auto_reduced",2),("difference_empty",2)]:
        actual=states[name]
        assert actual[1]==h,name
        assert equal(actual,expected),name
        print("CPR_N3_ORACLE",json.dumps({"case":name,"hidden":h,"support":len(actual[0]),"trace_numerator":trace_numerator(actual),"matches_source":True,"status":"PASS"}))
    print("CPR_N3_GATE",json.dumps({"checked":5,"source_equal":5,"external_rejected":True,"internal_hh_preserved":True,"status":"PASS"}))

if __name__=="__main__":
    main(sys.argv[1])
