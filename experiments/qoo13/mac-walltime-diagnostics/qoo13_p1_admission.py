#!/usr/bin/env python3
"""QOO-13: classify SAVED Mac environment observations, without taking measurements.

A candidate is not a performance qualification or permission to run A/A.
No processes, benchmarks, CodSpeed, network, or macOS commands are invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_KIND = 'QOO13_READ_ONLY_DIAGNOSTICS_NOT_A_BENCHMARK'
MIN_SAMPLES = 7  # pilot policy; not a statistically calibrated threshold
MIN_SPAN_S = 25.0
CPU_IDLE_FLOOR = 50.0  # pilot stop rule, not a performance gate
PROCESS_CPU_CEILING = 100.0
MAX_JSON_BYTES = 8 * 1024 * 1024


def number(value):
    # bool is a subclass of int; it is not a legitimate measurement.
    return float(value) if type(value) in (int, float) else None


def assess(report: dict) -> dict:
    """Evaluate observed stop rules, coverage and uncertainty. Never emit PASS."""
    samples = report.get('samples') if isinstance(report, dict) else None
    out = {
        'kind': 'QOO13_P1_READ_ONLY_ASSESSMENT',
        'verdict': 'INCOMPLETE',
        'sample_count': len(samples) if isinstance(samples, list) else 0,
        'stop_reasons': [],
        'evidence_gaps': [],
        'observations': [],
        'thermal_certified': False,
        'performance': 'PERFORMANCE_UNQUALIFIED',
        'precision': 'PRECISION_UNVERIFIED',
        'authorizes_benchmark': False,
        'policy': {'min_samples': MIN_SAMPLES, 'min_span_seconds': MIN_SPAN_S,
                   'min_cpu_idle_pct': CPU_IDLE_FLOOR,
                   'max_single_process_cpu_pct': PROCESS_CPU_CEILING},
    }
    stop, gaps, obs = out['stop_reasons'], out['evidence_gaps'], out['observations']
    if not isinstance(report, dict) or report.get('kind') != SOURCE_KIND:
        gaps.append('NOT_A_QOO13_MONITOR_REPORT')
        return out
    if not isinstance(samples, list) or not samples or not all(isinstance(s, dict) for s in samples):
        gaps.append('NO_VALID_SAMPLES')
        return out
    if len(samples) < MIN_SAMPLES:
        gaps.append('TOO_FEW_SAMPLES')

    monotonic = [number(s.get('monotonic_elapsed_s')) for s in samples]
    if any(v is None for v in monotonic) or any(b <= a for a, b in zip(monotonic, monotonic[1:])):
        gaps.append('INVALID_MONOTONIC_TIMESTAMPS')
        span = None
    else:
        span = monotonic[-1] - monotonic[0]
        out['sample_span_seconds'] = round(span, 3)
        if span < MIN_SPAN_S:
            gaps.append('OBSERVATION_WINDOW_TOO_SHORT')

    idle = [number(s.get('cpu_idle_pct')) for s in samples]
    if any(v is None or not 0 <= v <= 100 for v in idle):
        gaps.append('CPU_IDLE_MISSING_OR_INVALID')
    valid_idle = [v for v in idle if v is not None and 0 <= v <= 100]
    if valid_idle:
        out['min_cpu_idle_pct'] = min(valid_idle)
        out['cpu_idle_below_50_count'] = sum(v < CPU_IDLE_FLOOR for v in valid_idle)
        if out['cpu_idle_below_50_count']:
            stop.append('CPU_IDLE_BELOW_50_PCT')

    backup = [number(s.get('backupd_cpu_pct')) for s in samples]
    if any(v is None or v < 0 for v in backup):
        gaps.append('BACKUPD_CPU_MISSING_OR_INVALID')
    if any(v is not None and v > PROCESS_CPU_CEILING for v in backup):
        stop.append('BACKUPD_OVER_100_PCT')
    other_busy = False
    for s in samples:
        procs = s.get('top_processes')
        if not isinstance(procs, list):
            gaps.append('TOP_PROCESSES_UNAVAILABLE')
            continue
        for p in procs:
            if isinstance(p, dict) and p.get('command_name') != 'backupd':
                cpu = number(p.get('cpu_pct'))
                if cpu is not None and cpu > PROCESS_CPU_CEILING:
                    other_busy = True
    if other_busy:
        stop.append('OTHER_SINGLE_PROCESS_OVER_100_PCT')

    thermal = [s.get('thermal_signal_available') is True for s in samples]
    if not all(thermal):
        obs.append('THERMAL_TELEMETRY_UNAVAILABLE_OR_INCOMPLETE')
    else:
        obs.append('CPU_LIMIT_TELEMETRY_NOT_THERMAL_CERTIFICATION')

    a, b = samples[0].get('vm_stat'), samples[-1].get('vm_stat')
    if not isinstance(a, dict) or not isinstance(b, dict):
        gaps.append('SWAP_COUNTERS_MISSING')
    else:
        page_size = number(b.get('page_size_bytes')) or number(a.get('page_size_bytes'))
        if page_size is None or page_size <= 0:
            gaps.append('SWAP_PAGE_SIZE_MISSING')
        for field in ('swapins_pages', 'swapouts_pages'):
            left, right = number(a.get(field)), number(b.get(field))
            if left is None or right is None or left < 0 or right < left:
                gaps.append(field.upper() + '_MISSING_OR_RESET')
                continue
            if page_size and span and span > 0:
                delta_mib = (right - left) * page_size / (1024**2)
                out[field + '_delta_mib'] = round(delta_mib, 4)
                out[field + '_rate_mib_s'] = round(delta_mib / span, 4)
                if delta_mib > 0:
                    obs.append(field.upper() + '_ACTIVITY_OBSERVED_NOT_CALIBRATED')

    out['stop_reasons'] = sorted(set(stop))
    out['evidence_gaps'] = sorted(set(gaps))
    out['observations'] = sorted(set(obs))
    out['verdict'] = ('ABSTAIN' if stop else 'INCOMPLETE' if gaps
                      else 'QUIET_CANDIDATE_ONLY_NOT_CERTIFIED')
    out['interpretation'] = (
        'Even a quiet candidate is not permission to begin A/A or ABBA. '
        'Review naturally occurring host workload and thermal uncertainty; '
        'do not mix this monitor with older performance samples.'
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True,
                        help='Existing p1-monitor.json from qoo13_mac_diagnostics.py')
    parser.add_argument('--output', type=Path, help='New independent report; never overwrite')
    args = parser.parse_args()
    source = args.input
    if source.is_symlink() or not source.is_file():
        parser.error('Input must be an existing regular file (no symlinks)')
    if source.stat().st_size > MAX_JSON_BYTES:
        parser.error('Input exceeds 8 MiB safety limit')
    if args.output is not None and args.output.resolve() == source.resolve():
        parser.error('Refusing to overwrite the source evidence')
    if args.output is not None and args.output.exists():
        parser.error('Output exists; refusing to overwrite')
    payload = source.read_bytes()
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeError):
        parser.error('Input is not valid JSON')
    result = assess(data)
    result['input_sha256'] = hashlib.sha256(payload).hexdigest()
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as file:
            file.write(rendered)
        print(f'QOO13_P1_ASSESSMENT_WRITTEN={args.output}')
        print(f"VERDICT={result['verdict']}")
        print('NO_BENCHMARK / NO_UPLOAD / NO_PROCESS_CHANGES')
    else:
        print(rendered, end='')


if __name__ == '__main__':
    main()
