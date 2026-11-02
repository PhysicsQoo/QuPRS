"""Exact-SHA CodSpeed case identity export without replacing its timing engine.

CPU Simulation results are measured and uploaded by the CodSpeed runner, not by
pytest-codspeed.get_result_dict(). This hook records only completed case IDs.
WallTime includes numeric instrument data and keeps its first-party records.
"""
import json
import os
from pathlib import Path

import pytest

_EXECUTED = []


@pytest.hookimpl
def pytest_runtest_logreport(report):
    if report.when == "call" and report.passed:
        _EXECUTED.append(report.nodeid)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("QUPRS_CODSPEED_EXPORT")
    if (not destination or session.config.getoption("--collect-only", default=False)
            or not session.config.getoption("--codspeed", default=False)):
        return
    from pytest_codspeed.plugin import get_plugin

    result = get_plugin(session.config).instrument.get_result_dict()
    if not isinstance(result, dict):
        raise RuntimeError("CodSpeed instrument metadata was not a dictionary")
    if not isinstance(result.get("benchmarks"), list):
        # The CodSpeed CPU/Memory runner collects the numerical results outside
        # pytest. Never manufacture CPU cost from wall time or a local stopwatch.
        result = dict(result)
        result["benchmarks"] = [
            {"uri": uri, "metric_location": "CodSpeed service",
             "measurement_provenance": "pytest_passed_case_identity_only"}
            for uri in _EXECUTED
        ]
        result["evidence_kind"] = "identity_only_no_local_cpu_metrics"
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
