#!/usr/bin/env python3
"""QOO-13 local evidence triage and read-only macOS environment observations.

No benchmark, CodSpeed upload, network request, process termination, sudo,
or operating-system setting changes. Existing evidence is never modified.
Output excerpts are best-effort redacted and still require human review before sharing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time

# Evidence is host-local and must be supplied explicitly; don't embed personal paths.
MAX_FILES = 60
MAX_MATCHES = 40
MAX_FILE_WINDOW = 768 * 1024  # inspect head and tail; avoid entire huge logs
SCAN_SUFFIXES = {'.log', '.txt', '.md', '.json', '.jsonl', '.out', '.err'}
WARN_RE = re.compile(
    r'\b(?:warn(?:ing)?|error|fail(?:ed|ure)?|denied|flamegraph|callgraph)\b'
    r'|(?:environment|metadata).{0,70}(?:write|save|fail|warn|error)'
    r'|(?:write|save|fail).{0,70}(?:environment|metadata)', re.I
)
METADATA_RE = re.compile(r'metadata|environment|provenance|context|\.codspeed', re.I)
FLAME_RE = re.compile(r'flamegraph|callgraph|profiling trace|language frames', re.I)
REDACT = [
    (re.compile(r'(?i)\b(bearer\s+)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)((?:access[_ -]?token|api[_ -]?key|authorization|password|secret|token)\s*[=:]\s*["\']?)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)([?&](?:token|key|secret|auth|signature|code)=)[^\s&]+'), r'\1[REDACTED]'),
    (re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{10,}|github_pat_[A-Za-z0-9_]{10,})\b'), '[REDACTED]'),
    (re.compile(r'(?i)(?:https?://)[^/@\s]+:[^/@\s]+@'), 'https://[CREDENTIALS_REDACTED]@'),
]


def scrub(value: str, limit: int = 320) -> str:
    """Reduce accidental disclosure; this is not a security-grade sanitizer."""
    value = value.replace(str(Path.home()), '~')
    value = value.replace('\x00', '')
    for pat, replacement in REDACT:
        value = pat.sub(replacement, value)
    return value[:limit]


def parse_vm_stat(raw: str) -> dict:
    """Parse cumulative macOS vm_stat page counts, not byte amounts or rates."""
    match = re.search(r'page size of\s+(\d+)\s+bytes', raw, re.I)
    page_size = int(match.group(1)) if match else None
    counts: dict[str, int] = {}
    for line in raw.splitlines():
        m = re.match(r'\s*([^:]+):\s*([\d,.]+)\.?\s*$', line)
        if not m:
            continue
        key = re.sub(r'\s+', '_', m.group(1).strip().lower())
        try:
            counts[key] = int(m.group(2).replace(',', '').replace('.', ''))
        except ValueError:
            continue
    return {
        'page_size_bytes': page_size,
        'swapins_pages': counts.get('swapins'),
        'swapouts_pages': counts.get('swapouts'),
        'pageins': counts.get('pageins'),
        'pageouts': counts.get('pageouts'),
    }


def parse_processes(raw: str) -> list[dict]:
    processes = []
    for line in raw.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) != 3:
            continue
        try:
            pid, cpu = int(fields[0]), float(fields[1].replace(',', '.'))
        except ValueError:
            continue
        command = os.path.basename(fields[2].split()[0])
        processes.append({'pid': pid, 'cpu_pct': round(cpu, 2),
                          'command_name': scrub(command, limit=80)})
    return sorted(processes, key=lambda item: item['cpu_pct'], reverse=True)


def extract_cpu_idle(raw: str) -> float | None:
    match = re.search(r'CPU usage:.*?(\d+(?:\.\d+)?)%\s+idle', raw, re.I)
    return float(match.group(1)) if match else None


def command(*argv: str, timeout: int = 9) -> dict:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           check=False, errors='replace')
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'status': 'unavailable', 'reason': type(exc).__name__}
    return {'status': 'ok' if r.returncode == 0 else 'failed',
            'exit_code': r.returncode, 'output': r.stdout[:16_000],
            'error': scrub(r.stderr)}


def snapshot() -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    vm = command('vm_stat')
    ps = command('ps', '-A', '-o', 'pid=,pcpu=,comm=')
    top = command('top', '-l', '1', '-n', '0', timeout=12)
    swap = command('sysctl', '-n', 'vm.swapusage')
    pressure = command('memory_pressure', '-Q')
    thermal = command('pmset', '-g', 'therm')
    parsed = parse_processes(ps.get('output', ''))
    return {
        'timestamp_utc': now.isoformat(),
        'monotonic_elapsed_s': time.monotonic(),
        'load_average_1_5_15': [round(v, 3) for v in os.getloadavg()],
        'vm_stat': parse_vm_stat(vm.get('output', '')) if vm['status'] == 'ok'
                   else {'status': vm['status']},
        'cpu_idle_pct': extract_cpu_idle(top.get('output', '')),
        'top_processes': parsed[:8],
        'backupd_cpu_pct': round(sum(p['cpu_pct'] for p in parsed
                                     if p['command_name'] == 'backupd'), 2),
        'swap_usage_cumulative': scrub(swap.get('output', '').strip())
                                 if swap['status'] == 'ok' else None,
        'memory_pressure': scrub(pressure.get('output', '').strip(), 650)
                           if pressure['status'] == 'ok' else None,
        'thermal_signal': scrub(thermal.get('output', '').strip(), 650)
                          if thermal['status'] == 'ok' else None,
        'thermal_signal_available': thermal['status'] == 'ok' and bool(thermal.get('output', '').strip()),
        'command_status': {k: v['status'] for k, v in [
            ('vm_stat', vm), ('ps', ps), ('top', top),
            ('swap_usage', swap), ('memory_pressure', pressure), ('thermal', thermal)]},
    }


def warning_type(line: str) -> str:
    if METADATA_RE.search(line):
        return 'metadata_or_environment'
    if FLAME_RE.search(line):
        return 'flamegraph_only'
    if re.search(r'permission|denied|read.?only', line, re.I):
        return 'filesystem_or_permissions'
    return 'other_warning_or_error'


def bounded_text_windows(path: Path) -> list[tuple[str, str, int | None]]:
    """Read at most two file windows. Tail line numbers are intentionally unknown."""
    size = path.stat().st_size
    with path.open('rb') as stream:
        head = stream.read(MAX_FILE_WINDOW)
        result = [('head', head.decode('utf-8', errors='replace'), 1)]
        if size > MAX_FILE_WINDOW:
            stream.seek(max(MAX_FILE_WINDOW, size - MAX_FILE_WINDOW))
            tail = stream.read(MAX_FILE_WINDOW)
            # Discard possibly incomplete first line of tail.
            cut = tail.find(b'\n')
            result.append(('tail', tail[cut + 1:].decode('utf-8', errors='replace')
                           if cut >= 0 else '', None))
        return result


def scan_evidence(folder: Path) -> dict:
    report: dict = {
        'directory': scrub(str(folder)), 'exists': folder.is_dir(),
        'files_scanned': 0, 'warnings': [], 'warnings_by_type': {},
        'json_top_level_keys': {}, 'partial_scan': False,
        'warning_excerpt_redaction_requires_review': True,
    }
    if not folder.is_dir():
        report['status'] = 'EVIDENCE_MISSING'
        return report
    # Avoid following file symlinks; never evaluate file contents as code.
    candidates = sorted((f for f in folder.rglob('*') if f.suffix.lower() in SCAN_SUFFIXES),
                        key=lambda f: (0 if f.suffix.lower() in {'.log', '.out', '.err'} else 1,
                                       str(f)))
    if len(candidates) > MAX_FILES:
        report['partial_scan'] = True
    for path in candidates[:MAX_FILES]:
        try:
            if path.is_symlink() or not path.is_file():
                continue
            report['files_scanned'] += 1
            relative = scrub(str(path.relative_to(folder)), 180)
            size = path.stat().st_size
            if size > 2 * MAX_FILE_WINDOW:
                report['partial_scan'] = True
            if path.suffix.lower() == '.json' and size <= MAX_FILE_WINDOW:
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    report['json_top_level_keys'][relative] = sorted(data.keys()) if isinstance(data, dict) else ['[not-object]']
                except (OSError, ValueError):
                    report['json_top_level_keys'][relative] = ['[not-parseable]']
            if len(report['warnings']) >= MAX_MATCHES:
                report['partial_scan'] = True
                continue
            for window, text, initial_line in bounded_text_windows(path):
                for idx, raw in enumerate(text.splitlines(), 0):
                    if not WARN_RE.search(raw):
                        continue
                    kind = warning_type(raw)
                    report['warnings_by_type'][kind] = report['warnings_by_type'].get(kind, 0) + 1
                    report['warnings'].append({
                        'file': relative, 'window': window,
                        'line': initial_line + idx if initial_line is not None else None,
                        'kind': kind, 'redacted_excerpt': scrub(raw.strip()),
                    })
                    if len(report['warnings']) >= MAX_MATCHES:
                        report['partial_scan'] = True
                        break
                if len(report['warnings']) >= MAX_MATCHES:
                    break
        except (OSError, UnicodeError):
            continue
    report['status'] = 'WARNINGS_FOUND' if report['warnings'] else 'NO_MATCHES_WITHIN_SCAN_LIMITS'
    report['scope_note'] = ('Only warnings visible in bounded windows are reported. '
                            'This is not a proof that metadata warnings are absent.')
    return report


def summarize_window(samples: list[dict]) -> dict:
    if not samples:
        return {'status': 'NOT_SAMPLED'}
    result: dict = {
        'status': 'MONITOR_ONLY_NOT_PERFORMANCE_CERTIFICATION',
        'sample_count': len(samples),
        'max_backupd_cpu_pct': max(s['backupd_cpu_pct'] for s in samples),
        'max_cpu_load_1m': max(s['load_average_1_5_15'][0] for s in samples),
        'thermal_unavailable': any(not s['thermal_signal_available'] for s in samples),
        'contention_preflight': ('ABSTAIN_BACKUPD_OVER_100_PCT'
                                 if any(s['backupd_cpu_pct'] > 100 for s in samples)
                                 else 'NO_BACKUPD_LIMIT_EXCEEDED_NOT_AN_ADMISSION_PASS'),
    }
    if len(samples) < 2:
        result['swap_delta_status'] = 'INSUFFICIENT_SAMPLES'
        return result
    left, right = samples[0]['vm_stat'], samples[-1]['vm_stat']
    page_size = right.get('page_size_bytes') or left.get('page_size_bytes')
    duration = samples[-1]['monotonic_elapsed_s'] - samples[0]['monotonic_elapsed_s']
    result['sample_window_seconds'] = round(duration, 3)
    if not page_size or duration <= 0:
        result['swap_delta_status'] = 'UNAVAILABLE'
        return result
    fields_present = False
    for field, alias in (('swapins_pages', 'swapins'), ('swapouts_pages', 'swapouts')):
        first, last = left.get(field), right.get(field)
        if not isinstance(first, int) or not isinstance(last, int) or last < first:
            result[alias + '_status'] = 'UNAVAILABLE_OR_COUNTER_RESET'
            continue
        delta = last - first
        mib = delta * page_size / 1024**2
        result[alias + '_delta_pages'] = delta
        result[alias + '_delta_mib'] = round(mib, 3)
        result[alias + '_rate_mib_s'] = round(mib / duration, 4)
        fields_present = True
    result['swap_delta_status'] = 'OBSERVED' if fields_present else 'UNAVAILABLE'
    result['interpretation_note'] = ('Swap used in sysctl is cumulative; page deltas during '
                                     'this monitoring window are more relevant. Still not '
                                     'synchronized to a CodSpeed sample.')
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True,
                   help='Existing A/A evidence directory to scan (read-only)')
    p.add_argument('--scan-only', action='store_true',
                   help='Scan existing logs without any host measurements or subprocess calls')
    p.add_argument('--duration', type=int, default=20,
                   help='Host observation duration in seconds (0..120); ignored with --scan-only')
    p.add_argument('--interval', type=int, default=5,
                   help='Host observation interval (1..60); ignored with --scan-only')
    p.add_argument('--output', type=Path, help='Write a new JSON file outside evidence directory')
    args = p.parse_args()
    if not (0 <= args.duration <= 120 and 1 <= args.interval <= 60):
        p.error('Duration must be 0..120 and interval must be 1..60')
    if args.output:
        if args.output.exists():
            p.error('Output exists; refusing to overwrite')
        if args.output.resolve().is_relative_to(args.evidence.resolve()):
            p.error('Output must be outside the preserved evidence directory')

    report: dict = {
        'kind': 'QOO13_READ_ONLY_DIAGNOSTICS_NOT_A_BENCHMARK',
        'script_version': 2,
        'evidence_scan': scan_evidence(args.evidence),
        'samples': [],
        'sample_window': {'status': 'NOT_SAMPLED'},
        'interpretation': {
            'official_a1_min_seconds': 0.576188,
            'official_a1_rounds': 1,
            'official_flamegraph_issue': 'CallgraphGenerationFailure (info)',
            'official_measurement_present': True,
            'local_metadata_warning_root_cause': 'UNVERIFIED_UNTIL_LOG_REVIEW',
            'local_gpmc_arithmetic_precision': 'PRECISION_UNVERIFIED',
            'performance': 'PERFORMANCE_UNQUALIFIED',
            'privacy': 'Redaction is best effort; review report before sharing.',
        },
    }
    if not args.scan_only:
        start = time.monotonic()
        while True:
            report['samples'].append(snapshot())
            elapsed = time.monotonic() - start
            if elapsed >= args.duration:
                break
            time.sleep(min(args.interval, max(0, args.duration - elapsed)))
        report['sample_window'] = summarize_window(report['samples'])
    out = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # 'x' also refuses races where a file appears after the existence check.
        with args.output.open('x', encoding='utf-8') as f:
            f.write(out)
        print('QOO13_REPORT_WRITTEN=' + str(args.output))
        print('SCAN_WARNINGS=' + str(len(report['evidence_scan']['warnings'])))
        print('NO_BENCHMARK / NO_UPLOAD / NO_PROCESS_CHANGES')
    else:
        print(out, end='')


if __name__ == '__main__':
    main()
