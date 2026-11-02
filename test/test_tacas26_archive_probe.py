"""Structural and failure-mode checks for the read-only archived probe."""
import importlib.util
from pathlib import Path


def _probe():
    root=Path(__file__).resolve().parents[1]
    path=root/"scripts/tacas26_archive_qpe20_probe.py"
    spec=importlib.util.spec_from_file_location("tacas26_archive_probe",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_archived_reproducer_pins_qpe20_files_and_sha():
    x=_probe()
    assert x.HISTORICAL_SHA=="e928abc47dd15926364ec77905eb0d5dc92ce8cc"
    assert set(x.INPUTS)=={"original","transpiled"}
    assert all(len(hash_value)==64 for _,hash_value in x.INPUTS.values())

def test_archived_reproducer_has_explicit_artifact_fail_closed_contract():
    x=_probe()
    # The archived runner cannot manufacture a phase verdict from an empty
    # source tree: without /app artifact it writes an explicit failure report.
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        data=x.run(Path(folder)/"result.json")
        assert data["science_certification"]=="ARCHIVE_QPE20_NOT_CERTIFIED"
        assert data["error"] is not None
        assert (Path(folder)/"result.json").is_file()
