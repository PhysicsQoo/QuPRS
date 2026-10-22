#!/usr/bin/env python3
"""Read-only integrity and CI-coverage audit of the published benchmark inputs.

No quantum simulation, transpilation, solver execution, or runtime success
claim is performed here. Git blob identifiers pin bytes to a repository
snapshot; SHA-256 digests of those same bytes are emitted for evidence.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path('docs/development/paper-corpus-manifest.json')
EXPECTED_TABLE2 = {
    'ghz': (32, 64, 128),
    'graphstate': (16, 32, 64),
    'grover-noancilla': (4, 5, 6),
    'qaoa': (7, 9, 11),
    'qft': (16, 20, 22, 24),
    'qnn': (4, 8, 12),
    'qpeexact': (8, 16, 20, 24),
    'qpeinexact': (8, 16, 20, 24),
    'qwalk-noancilla': (3, 4, 5),
    'vqe': (4, 8, 16),
    'wstate': (4, 8, 16),
}
MQT_CI = {
    'ghz_32', 'graphstate_16', 'grover-noancilla_4',
    'qaoa_7', 'qft_16', 'vqe_4',
}
FEYNMAN_CI = {'adder_8', 'gf2^4_mult', 'tof_3', 'vbe_adder_3'}


class CorpusError(ValueError):
    """The declared paper corpus or its immutable bytes are inconsistent."""


def load_manifest(root: Path = ROOT) -> dict:
    return json.loads((root / MANIFEST).read_text(encoding='utf-8'))


def verify_blob(root: Path, description: dict) -> dict:
    """Validate an actual file against the pinned Git object SHA-1."""
    rel = Path(description['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.suffix != '.qasm':
        raise CorpusError(f'Invalid QASM path: {rel}')
    filepath = (root / rel).resolve()
    if not filepath.is_relative_to(root.resolve()):
        raise CorpusError(f'QASM path escapes repository: {rel}')
    if not filepath.is_file():
        raise CorpusError(f'Missing QASM file: {rel}')
    contents = filepath.read_bytes()
    git_blob = b'blob ' + str(len(contents)).encode('ascii') + b'\x00' + contents
    actual_sha1 = hashlib.sha1(git_blob).hexdigest()
    expected_sha1 = description['git_blob_sha1']
    if actual_sha1 != expected_sha1:
        raise CorpusError(
            f'QASM integrity mismatch for {rel}: '
            f'expected Git blob {expected_sha1}, observed {actual_sha1}'
        )
    return {
        'path': rel.as_posix(),
        'git_blob_sha1': actual_sha1,
        'sha256': hashlib.sha256(contents).hexdigest(),
        'bytes': len(contents),
    }


def benchmark_filenames(path: Path) -> list[str]:
    """Inspect pytest parametrization statically (never import or run solvers)."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        target = node.func
        if not isinstance(target, ast.Attribute) or target.attr != 'parametrize':
            continue
        if not isinstance(node.args[0], ast.Constant):
            continue
        label = node.args[0].value
        if not isinstance(label, str) or not label.startswith('file_name,'):
            continue
        table = node.args[1]
        if isinstance(table, ast.Name):
            # The two benchmark files import one named constant rather than
            # duplicating identical tuple lists. Resolve *statically*; do not
            # execute test modules or import solvers in this fast audit.
            imports = [n for n in tree.body if isinstance(n, ast.ImportFrom)
                       and n.module == '_benchmark_cases']
            source_name = next(
                (spec.name for entry in imports for spec in entry.names
                 if (spec.asname or spec.name) == table.id), None
            )
            if source_name is None:
                raise CorpusError(f'Benchmark table import not found in {path}')
            catalog = ast.parse(
                (path.parents[1] / 'test/_benchmark_cases.py').read_text(encoding='utf-8')
            )
            definitions = [n.value for n in catalog.body
                           if isinstance(n, ast.Assign)
                           for target in n.targets
                           if isinstance(target, ast.Name) and target.id == source_name]
            if len(definitions) != 1:
                raise CorpusError(f'Invalid benchmark table {source_name}')
            rows = ast.literal_eval(definitions[0])
        else:
            rows = ast.literal_eval(table)
        found.extend(row[0] for row in rows)
    if not found or len(found) != len(set(found)):
        raise CorpusError(f'Missing or duplicated benchmark selection in {path}')
    return found


def check_declarations(manifest: dict, root: Path) -> dict:
    if manifest.get('schema_version') != 1:
        raise CorpusError('Unexpected manifest schema version')
    paper = manifest['paper']
    if paper['table2_prose_count'] != 35 or paper['table2_listed_rows'] != 36:
        raise CorpusError('Paper prose/table count discrepancy must be preserved')
    mqt = manifest['cohorts']['table2_mqt']
    feynman = manifest['cohorts']['feynman_ci_sample']
    if mqt['qiskit_version_reported'] != '1.4.2':
        raise CorpusError('MQT paper provenance changed')
    if feynman['qiskit_version_reported'] != '1.2.4':
        raise CorpusError('Feynman paper provenance changed')
    cases = mqt['cases']
    listed = {(case['family'], case['qubits']) for case in cases}
    expected = {(family, n) for family, sizes in EXPECTED_TABLE2.items() for n in sizes}
    if len(cases) != 36 or listed != expected:
        raise CorpusError(f'Table 2 mismatch: missing={expected-listed}, extra={listed-expected}')
    chosen = {c['id'] for c in cases if c['ci_benchmark'] is not None}
    if chosen != MQT_CI or any(
        c['ci_method'] != 'hybrid' or c['ci_benchmark'] != 'test/test_MQT.py'
        for c in cases if c['id'] in chosen
    ):
        raise CorpusError('Declared MQT CI selection differs from recorded baseline')
    if {c['id'] for c in feynman['cases']} != FEYNMAN_CI or any(
        c['ci_benchmark'] != 'test/test_Feynman.py' or c['ci_method'] != 'reduction_rules'
        for c in feynman['cases']
    ):
        raise CorpusError('Declared Feynman CI selection differs from recorded baseline')
    for group, source in ((mqt, 'test_MQT.py'), (feynman, 'test_Feynman.py')):
        basename = {Path(c['source']['path']).name for c in group['cases'] if c['ci_benchmark']}
        benchmark = set(benchmark_filenames(root / 'test' / source))
        if basename != benchmark:
            raise CorpusError(f'{source} selection drift: expected={basename}, observed={benchmark}')
    if manifest['additional_mqt_pair']['id'] in {c['id'] for c in cases}:
        raise CorpusError('Non-Table-2 supplement is being counted as a paper row')
    return {'mqt_table2_cases': len(cases), 'mqt_ci_cases': len(chosen),
            'feynman_ci_cases': len(feynman['cases']),
            'mqt_families': len(EXPECTED_TABLE2)}


def audit_corpus(root: Path = ROOT, manifest: dict | None = None) -> dict:
    root = root.resolve()
    data = manifest if manifest is not None else load_manifest(root)
    summary = check_declarations(data, root)
    records = []
    for cohort in ('table2_mqt', 'feynman_ci_sample'):
        for entry in data['cohorts'][cohort]['cases']:
            records.append({
                'cohort': cohort,
                'id': entry['id'],
                'ci_benchmark': entry['ci_benchmark'],
                'ci_method': entry['ci_method'],
                'source': verify_blob(root, entry['source']),
                'transpiled': verify_blob(root, entry['transpiled']),
                'execution_status': 'not_run',
            })
    extra = data['additional_mqt_pair']
    additional = {
        'id': extra['id'],
        'table2_row': False,
        'source': verify_blob(root, extra['source']),
        'transpiled': verify_blob(root, extra['transpiled']),
        'execution_status': 'not_run',
    }
    return {'reference_git_commit': data['reference_git_commit'],
            'paper_count_discrepancy': data['paper']['count_discrepancy'],
            'summary': summary, 'cases': records,
            'additional_mqt_pair': additional,
            'claim': 'Static file integrity and benchmark selection only; no circuit equivalence or runtime was checked.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--json', type=Path, help='Write a SHA-256 evidence report; default prints JSON')
    args = parser.parse_args()
    result = audit_corpus(args.root)
    output = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.json:
        args.json.write_text(output, encoding='utf-8')
    else:
        print(output, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())