"""Fail closed unless Cargo resolves the exact published RC with registry checksum."""
import json, sys, tomllib
from pathlib import Path
lock, output = map(Path, sys.argv[1:])
p=tomllib.loads(lock.read_text())["package"]
r=[x for x in p if x["name"]=="rawmocs"]
assert len(r)==1, r
a=r[0]
assert a["version"]=="0.4.0-rc.1", a
assert a["source"]=="registry+https://github.com/rust-lang/crates.io-index", a
assert a["checksum"]=="b61a1361b6a9578b3edc2d08a20cea9195ad403a18628aa9f95af365e7b503f5",a
assert not any(x["name"] in ("rawmocs-cli","rawmocs-core","rawmocs-python") for x in p),p
output.write_text(json.dumps({"status":"REGISTRY_LOCK_PASS","name":a["name"],"version":a["version"],"source":a["source"],"checksum":a["checksum"]},indent=2)+"\n")
print("REGISTRY_LOCK_PASS rawmocs 0.4.0-rc.1",a["checksum"])
