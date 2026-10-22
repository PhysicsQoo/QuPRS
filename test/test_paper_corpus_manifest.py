"""Read-only provenance gate for paper fixtures; no solver invocation."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'scripts/paper_corpus_audit.py'
SPEC = importlib.util.spec_from_file_location('paper_corpus_audit', AUDIT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_table2_manifest_has_exact_paper_rows_and_existing_ci_selection():
    manifest = audit.load_manifest(ROOT)
    counts = audit.check_declarations(manifest, ROOT)
    assert counts == {
        'mqt_table2_cases': 36, 'mqt_ci_cases': 6,
        'feynman_ci_cases': 4, 'mqt_families': 11,
    }
    assert manifest['paper']['table2_prose_count'] == 35
    assert manifest['paper']['table2_listed_rows'] == 36


def test_all_paper_qasm_pairs_match_pinned_git_blobs():
    report = audit.audit_corpus(ROOT)
    assert len(report['cases']) == 40
    assert all(row['execution_status'] == 'not_run' for row in report['cases'])
    for row in report['cases']:
        for key in ('source', 'transpiled'):
            assert len(row[key]['sha256']) == 64
            assert row[key]['bytes'] > 0
    assert report['additional_mqt_pair']['table2_row'] is False


def test_tampering_must_fail_before_reporting_provenance(tmp_path):
    f = tmp_path / 'tampered.qasm'
    f.write_bytes(b'OPENQASM 2.0;\n')
    with pytest.raises(audit.CorpusError, match='integrity mismatch'):
        audit.verify_blob(tmp_path, {'path': f.name, 'git_blob_sha1': '0' * 40})


def test_report_never_claims_circuit_equivalence():
    report = audit.audit_corpus(ROOT)
    assert 'no circuit equivalence' in report['claim']
    assert {c['execution_status'] for c in report['cases']} == {'not_run'}