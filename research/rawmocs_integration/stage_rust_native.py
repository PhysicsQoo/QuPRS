"""R3b isolated registry feature rehearsal; never modifies production manifests."""
from pathlib import Path
import json
import subprocess
import sys

stage, evidence = map(lambda s: Path(s).resolve(), sys.argv[1:])
evidence.mkdir(parents=True,exist_ok=True)
def replace(path,old,new):
    f=stage/path
    s=f.read_text()
    assert s.count(old)==1,(path,old)
    f.write_text(s.replace(old,new))
# The exact same adapter code already admitted by R3a; no duplicate solve logic.
probe=(stage/"research/rawmocs_integration/rust_native_eq.rs").read_text()
body=probe[probe.index("fn solve("):probe.index("\nfn main()")]
prefix="""use anyhow::{ensure, Result};
use crate::{NativeCounterError, precision_count::{rawmocs_count_from_parts, PrintedCount}};
use rawmocs_mpfr::{solve_text, FailureKind, SolveOptions, Precision};
use std::time::Duration;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Signed;
"""
(stage/"rust/quprs/src/rawmocs_native.rs").write_text(prefix+body.replace("fn solve(","pub(crate) fn solve(",1)+"\n")
replace("rust/quprs/src/lib.rs","    check_equivalence_with_counter_impl(num_qubits, gates1, gates2, options, None)\n}", """    #[cfg(all(feature = "rawmocs-native", not(target_arch = "wasm32")))]
    if options.tool_name == "rawmocs_rust_native" {
        return check_equivalence_with_counter_impl(num_qubits, gates1, gates2, options, Some(&rawmocs_native::solve));
    }
    check_equivalence_with_counter_impl(num_qubits, gates1, gates2, options, None)
}
#[cfg(all(feature = "rawmocs-native", not(target_arch = "wasm32")))]
mod rawmocs_native;""")
p=stage/"rust/quprs/Cargo.toml"
s=p.read_text()
assert "[features]" in s
s=s.replace("[features]",'[features]\nrawmocs-native = ["dep:rawmocs_mpfr"]',1)
s+='\n[target.\'cfg(not(target_arch = "wasm32"))\'.dependencies]\nrawmocs_mpfr = { package = "rawmocs", version = "=0.4.0", optional = true }\n'
p.write_text(s)
replace("rust/python_ffi/Cargo.toml","[features]",'[features]\nrawmocs-native = ["pathsum/rawmocs-native"]')
for name in ("quprs","python_ffi"):
    (evidence/f"{name}.Cargo.toml").write_text((stage/f"rust/{name}/Cargo.toml").read_text())
(evidence/"rawmocs_native.rs").write_text((stage/"rust/quprs/src/rawmocs_native.rs").read_text())
