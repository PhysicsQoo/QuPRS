"""Fail closed unless Cargo resolves the exact published stable crate with registry checksum."""
import json, sys, tomllib
from pathlib import Path
lock, output = map(Path, sys.argv[1:])
p=tomllib.loads(lock.read_text())["package"]
r=[x for x in p if x["name"]=="rawmocs"]
assert len(r)==1, r
a=r[0]
assert a["version"]=="0.4.0", a
assert a["source"]=="registry+https://github.com/rust-lang/crates.io-index", a
assert a["checksum"]=="d3e9e6ccd4a146bac19f6bd2628038cf20ae331dd12f9dc0cbcd37a4e63e955d",a
assert not any(x["name"] in ("rawmocs-cli","rawmocs-core","rawmocs-python") for x in p),p
output.write_text(json.dumps({"status":"REGISTRY_LOCK_PASS","name":a["name"],"version":a["version"],"source":a["source"],"checksum":a["checksum"]},indent=2)+"\n")
print("REGISTRY_LOCK_PASS rawmocs 0.4.0",a["checksum"])
