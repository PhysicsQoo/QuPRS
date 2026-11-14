#!/usr/bin/env python3
"""Assemble immutable validated binaries with matching corresponding sources."""
import pathlib,shutil,hashlib,json,tarfile,sys
core,counter,out=map(pathlib.Path,sys.argv[1:4]);shutil.copytree('web',out)
for name in ['LICENSE.md','NOTICE.md']:shutil.copy2(name,out/name)
shutil.copytree(core/'web/pkg',out/'pkg',dirs_exist_ok=True)
for name in ['gpmc.js','gpmc.wasm','sources','PROVENANCE.json']:
 source=counter/name;target=out/'engines'/name
 if source.is_dir():shutil.copytree(source,target,dirs_exist_ok=True)
 else:shutil.copy2(source,target)
p=out/'engines/PROVENANCE.json';d=json.loads(p.read_text())
for name,expected in d['sha256'].items():assert hashlib.sha256((counter/name).read_bytes()).hexdigest()==expected,(name,'Counter build checksum mismatch')
d['native_ci_sha256']=d['sha256'].pop('native-gpmc')
source=out/'engines/sources/gpmc-mpfr-browser-source.tar.gz';temp=source.with_suffix('.tmp')
with tarfile.open(source) as src,tarfile.open(temp,'w:gz') as dst:
 for member in src:dst.addfile(member,src.extractfile(member) if member.isfile() else None)
 for file,target in [('scripts/web/REBUILD.md','REBUILD.md'),('NOTICE.md','QuPRS-browser-NOTICE.md')]:dst.add(file,arcname='source-bundle/'+target)
source.write_bytes(temp.read_bytes());temp.unlink()
d['sha256']['sources/gpmc-mpfr-browser-source.tar.gz']=hashlib.sha256(source.read_bytes()).hexdigest()
p.write_text(json.dumps(d,indent=2)+'\n')
shutil.rmtree(out/'tests',ignore_errors=True)
