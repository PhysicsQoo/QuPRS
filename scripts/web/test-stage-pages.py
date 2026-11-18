"""Verify Pages publication preserves existing docs/root and fails closed."""
import importlib.util,pathlib,subprocess,tempfile,unittest
spec=importlib.util.spec_from_file_location('stage',pathlib.Path(__file__).with_name('stage-pages.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class StageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.pages=self.root/'pages';self.site=self.root/'site';self.pages.mkdir();self.site.mkdir();(self.site/'index.html').write_text('browser')
  subprocess.run(['git','init','-q',str(self.pages)],check=True)
  for name in ['index.html','docs/index.html','pr-preview/pr-1/index.html','robots.txt','.nojekyll']:
   p=self.pages/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('preserve:'+name)
  subprocess.run(['git','-C',str(self.pages),'add','.'],check=True)
  subprocess.run(['git','-C',str(self.pages),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','Fixture'],check=True)
 def tearDown(self):self.tmp.cleanup()
 def test_preserves_every_existing_path(self):
  old={p.relative_to(self.pages):p.read_bytes() for p in self.pages.rglob('*') if p.is_file() and '.git' not in p.parts}
  paths=module.stage(self.site,self.pages);self.assertEqual(paths,['playground/index.html'])
  for name,data in old.items():self.assertEqual((self.pages/name).read_bytes(),data)
  (self.site/'extra.txt').write_text('new');module.stage(self.site,self.pages);self.assertTrue((self.pages/'playground/extra.txt').is_file())
  (self.site/'extra.txt').unlink();module.stage(self.site,self.pages);self.assertFalse((self.pages/'playground/extra.txt').exists())
 def test_rejects_destination_symlink(self):
  (self.pages/'playground').symlink_to(self.site,target_is_directory=True)
  with self.assertRaises(ValueError):module.stage(self.site,self.pages)
 def test_rejects_unrelated_staged_changes(self):
  (self.pages/'index.html').write_text('unrelated');subprocess.run(['git','-C',str(self.pages),'add','index.html'],check=True)
  with self.assertRaises(ValueError):module.stage(self.site,self.pages)
if __name__=='__main__':unittest.main()
