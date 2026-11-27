"""Exact source comparison for a nonempty Myers Difference gate stream."""
import json
import sys
from cpr_normalization_n1 import matrix, equal
from cpr_hh_pivot_n3 import source, trace_numerator

def main(path):
    rows=[json.loads(l.split(" ",1)[1]) for l in open(path) if l.startswith("CPR_N5B_RECEIPT ")]
    assert len(rows)==2
    states={r["case"]:matrix(r["state"],[],0) for r in rows}
    assert set(states)=={"raw","fixed"}
    # The common X prefix cancels; source() independently composes N2 H/CCX.
    expected=source()
    for name,h in [("raw",6),("fixed",2)]:
        actual=states[name]
        assert actual[1]==h and equal(actual,expected),name
        print("CPR_N5B_ORACLE",json.dumps({"case":name,"hidden":h,"support":len(actual[0]),"trace_numerator":trace_numerator(actual),"source_equal":True}))
    print("CPR_N5B_SOURCE_GATE",json.dumps({"checked":2,"matched":2,"nonempty_myers":True,"status":"PASS"}))
if __name__=="__main__":main(sys.argv[1])
