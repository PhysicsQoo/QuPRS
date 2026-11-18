"""Stage only the browser subtree in an existing Pages checkout."""
from pathlib import Path
import shutil,subprocess,sys

def stage(site,checkout):
 site=Path(site).resolve();checkout=Path(checkout).resolve();target=checkout/'playground'
 if not (site/'index.html').is_file():raise ValueError('Missing validated browser entry page')
 if target.is_symlink():raise ValueError('Refusing symlinked playground destination')
 if any(p.is_symlink() or '.git' in p.relative_to(site).parts for p in site.rglob('*')):raise ValueError('Unexpected symlink or git metadata in browser artifact')
 if not (checkout/'.git').exists():raise ValueError('Pages checkout must be a git worktree')
 if target.exists():shutil.rmtree(target)
 shutil.copytree(site,target)
 subprocess.run(['git','-C',str(checkout),'add','--','playground'],check=True)
 paths=subprocess.check_output(['git','-C',str(checkout),'diff','--cached','--name-only'],text=True).splitlines()
 if any(not p.startswith('playground/') for p in paths):raise ValueError('Refusing changes outside the browser subtree')
 return paths

if __name__=='__main__':stage(*sys.argv[1:])
