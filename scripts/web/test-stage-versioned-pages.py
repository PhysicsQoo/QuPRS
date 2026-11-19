"""Fail-closed regression suite for immutable Browser Playground publication."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).with_name("stage-versioned-pages.py")
spec = importlib.util.spec_from_file_location("stage_versioned", MODULE)
stage_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_module)
stage = stage_module.stage
SHA1 = "1" * 40
SHA2 = "2" * 40
SHA3 = "3" * 40


class StageVersionedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.pages = self.base / "pages"
        self.site = self.base / "site"
        self.pages.mkdir()
        self.site.mkdir()
        subprocess.run(["git", "init", "-q", str(self.pages)], check=True)
        for name in ["index.html", "docs/stable/index.html", "pr-preview/7/index.html", ".nojekyll"]:
            p = self.pages / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("unchanged " + name)
        self.make_site(SHA1, "v1")
        self.original = {
            str(p.relative_to(self.pages)): p.read_bytes()
            for p in self.pages.rglob("*")
            if p.is_file() and ".git" not in p.parts
        }

    def make_site(self, source, label):
        for name in stage_module.MANDATORY:
            p = self.site / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(source if name == "source-sha.txt" else label + name)

    def commit(self):
        subprocess.run(["git", "-C", str(self.pages), "add", "-A"], check=True)
        subprocess.run([
            "git", "-C", str(self.pages), "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "--allow-empty",
            "-qm", "test commit",
        ], check=True)

    def test_stable_two_versions_dev_separation_and_downgrade(self):
        stage(self.site, self.pages, "dev")
        self.assertFalse((self.pages / "playground/index.html").exists())
        self.assertTrue((self.pages / "playground/dev/index.html").exists())
        stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)
        self.assertFalse((self.pages / "playground/index.html").exists())
        stage(self.site, self.pages, "promote", "v0.17.0", SHA1)
        redirect = (self.pages / "playground/index.html").read_text()
        self.assertIn('href="./v0.17.0/"', redirect)
        self.assertFalse((self.pages / "playground/app.js").exists(),
                         "Stable root should not expose cacheable unversioned JS")
        self.commit()
        self.make_site(SHA2, "v2")
        stage(self.site, self.pages, "snapshot", "v0.18.0", SHA2)
        stage(self.site, self.pages, "promote", "v0.18.0", SHA2)
        self.commit()
        self.make_site(SHA3, "future-dev")
        stage(self.site, self.pages, "dev")
        self.assertEqual((self.pages / "playground/dev/source-sha.txt").read_text(), SHA3)
        self.assertEqual((self.pages / "playground/source-sha.txt").read_text(), SHA2)
        self.make_site(SHA1, "v1")
        stage(self.site, self.pages, "promote", "v0.17.0", SHA1)
        self.assertEqual((self.pages / "playground/source-sha.txt").read_text(), SHA2)
        manifest = json.loads((self.pages / "playground/versions.json").read_text())
        self.assertEqual(manifest["stable"], "v0.18.0")
        self.assertEqual([v["version"] for v in manifest["versions"]], ["v0.18.0", "v0.17.0"])
        self.assertTrue(all(len(v["asset_sha256"]) == 64 for v in manifest["versions"]))
        self.assertIn('href="./v0.18.0/"',
                      (self.pages / "playground/index.html").read_text())
        for name, before in self.original.items():
            self.assertEqual((self.pages / name).read_bytes(), before)

    def test_immutable_snapshot_and_bad_sha(self):
        stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)
        self.commit()
        stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)
        self.make_site(SHA1, "DIFFERENT")
        with self.assertRaisesRegex(ValueError, "Immutable version"):
            stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)
        with self.assertRaisesRegex(ValueError, "admitted SHA"):
            stage(self.site, self.pages, "snapshot", "v0.18.0", SHA2)

    def test_cannot_promote_unpublished_or_untrusted_tags(self):
        with self.assertRaises(ValueError):
            stage(self.site, self.pages, "promote", "v0.17.0", SHA1)
        for tag in ["v0.18.0-rc.1", "v0.17.0/../docs", "v01.0.0"]:
            with self.assertRaisesRegex(ValueError, "canonical stable"):
                stage(self.site, self.pages, "snapshot", tag, SHA1)

    def test_broken_manifest_and_symlinks(self):
        stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)
        stage(self.site, self.pages, "promote", "v0.17.0", SHA1)
        self.commit()
        (self.pages / "playground/v0.17.0/worker.js").write_text("tampered")
        with self.assertRaises(ValueError):
            stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)
        (self.pages / "playground/v0.17.0/worker.js").write_text("v1worker.js")
        (self.site / "bad-link.js").symlink_to("app.js")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            stage(self.site, self.pages, "snapshot", "v0.18.0", SHA1)

    def test_rejects_other_staged_work(self):
        (self.pages / "docs/stable/index.html").write_text("modified")
        subprocess.run(["git", "-C", str(self.pages), "add", "docs"], check=True)
        with self.assertRaisesRegex(ValueError, "Other Pages"):
            stage(self.site, self.pages, "snapshot", "v0.17.0", SHA1)


if __name__ == "__main__":
    unittest.main()
