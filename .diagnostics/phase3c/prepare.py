from pathlib import Path
import shutil,subprocess,json,hashlib
import os
root=Path(os.environ.get('QUPRS_ATTR_ROOT','/work')); work=root/'work'; out=root/'results'; (out/'bin').mkdir(exist_ok=True)
for variant in ['A','B1','B3','B5','B10','B20']:
 src=work/('A' if variant=='A' else 'B'); dst=work/variant if variant!='A' else src
 if dst!=src:
  shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('target'))
 if variant not in ['A','B10']:
  p=dst/'rust/pathsum/src/strategy.rs'; s=p.read_text(); n=int(variant[1:]); old='self.run_with_interval(ps, gates1, gates2, NonZeroUsize::new(10).unwrap())'; assert s.count(old)==1
  p.write_text(s.replace(old,f'self.run_with_interval(ps, gates1, gates2, NonZeroUsize::new({n}).unwrap())'))
 examples=dst/'rust/pathsum/examples';examples.mkdir(exist_ok=True);shutil.copy(root/'harness/probe.rs',examples/'attribution_probe.rs')
print('prepared',flush=True)
