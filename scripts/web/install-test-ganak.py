#!/usr/bin/env python3
"""Install the exact upstream-pinned native GANAK solely for the unit suite."""
import pathlib,hashlib,tarfile,sys
archive=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2])
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='bea7150787a1e8f2b1bd658cb5a3c227d631d25054f5ff77ce23422e1c8b040c','Upstream GANAK archive mismatch'
with tarfile.open(archive) as t:
 members=[m for m in t.getmembers() if m.isfile() and pathlib.PurePosixPath(m.name).name=='ganak']
 assert len(members)==1,'Ambiguous GANAK executable'
 data=t.extractfile(members[0]).read()
assert hashlib.sha256(data).hexdigest()=='934a79a3db2f5b3928ce89edde20837f652e4679b099320ac71c198699c709dd','Upstream GANAK executable mismatch'
dest.write_bytes(data);dest.chmod(0o755)
