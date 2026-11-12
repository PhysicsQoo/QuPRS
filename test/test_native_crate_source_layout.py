"""Guard the native Cargo source move against stale live build wiring.

The historical source-paired CLI experiment intentionally references an old
source tree in its fixed comparison checkout, not the active checkout.
"""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def _toml(path):
    return tomllib.loads((ROOT / path).read_text(encoding="utf-8"))


def test_native_workspace_paths_match_published_crate():
    assert (ROOT / "rust/quprs/Cargo.toml").is_file()
    assert (ROOT / "rust/quprs/Cargo.lock").is_file()
    assert not (ROOT / "rust/pathsum").exists()
    manifest = _toml("rust/quprs/Cargo.toml")
    assert manifest["package"]["name"] == "quprs"
    assert manifest["lib"]["name"] == "quprs"
    assert "quprs" in _toml("rust/Cargo.toml")["workspace"]["members"]
    for manifest_path in ("rust/cli/Cargo.toml", "rust/python_ffi/Cargo.toml"):
        assert _toml(manifest_path)["dependencies"]["pathsum"]["path"] == "../quprs"
    assert _toml("benchmarks/rust_core/Cargo.toml")["dependencies"]["pathsum"]["path"] == "../../rust/quprs"


def test_live_ci_scripts_do_not_reference_deleted_crate_path():
    for directory, suffixes in (
        (ROOT / ".github/workflows", (".yml", ".yaml")),
        (ROOT / ".github/scripts", (".js", ".cjs", ".mjs")),
        (ROOT / "scripts", (".py", ".js", ".sh")),
    ):
        for file in directory.rglob("*"):
            if file.suffix not in suffixes or not file.is_file():
                continue
            lines = file.read_text(encoding="utf-8").splitlines()
            for n, line in enumerate(lines, 1):
                if "rust/pathsum" not in line:
                    continue
                historical = (
                    file.name in {
                        "qoo156-cli-hosted-abba.yml",
                        "qoo156-cli-macro-pr-admission.yml",
                    }
                    and "git -C qoo156-base rev-parse HEAD:rust/pathsum" in line
                )
                assert historical, f"stale active native source reference: {file}:{n}"
