"""Resource-monitor unit checks that do not execute quantum simulations."""
import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/profile_benchmark_resources.py'
SPEC = importlib.util.spec_from_file_location('profile_benchmark_resources', SCRIPT)
resource = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resource)


def test_resource_case_catalog_matches_current_ci_selection():
    for name in ('grover4', 'qaoa7', 'vqe4', 'tof3'):
        case = resource.resolve_case(name)
        assert case['method'] in ('hybrid', 'reduction_rules')
        assert case['source'] != case['transpiled']


def test_memory_sampler_observes_live_process():
    assert resource.sample_tree_rss(__import__('os').getpid()) > 0


def test_walltime_limit_stops_long_running_worker():
    report = resource.run_limited(
        [sys.executable, '-c', 'import time; time.sleep(4)'],
        deadline=0.12, rss_cap=1024**3, sample_seconds=0.03,
    )
    assert report['resource_limit_status'] == 'walltime_limit_exceeded'
    assert report['elapsed_seconds'] < 2
    assert report['sampled_peak_tree_rss_bytes'] > 0


def test_completed_worker_reports_measured_peak():
    report = resource.run_limited(
        [sys.executable, '-c', 'a=bytearray(4*1024*1024); print(len(a))'],
        deadline=5, rss_cap=1024**3, sample_seconds=0.03,
    )
    assert report['exit_code'] == 0
    assert report['resource_limit_status'] is None
    assert report['sampled_peak_tree_rss_bytes'] > 0