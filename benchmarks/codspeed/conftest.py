"""Export the exact pytest-codspeed WallTime measurements, not new timings.

Runs as a pytest hook after the CodSpeed instrument has collected all cases.
Version pinned in CI to pytest-codspeed 5.0.3. The official instrument itself
remains the only source of numbers; this file is a report input artifact.
"""
import json
import os
from pathlib import Path

import pytest


def export_walltime_result(results, output):
    """Write only WallTime measurements. Never reject another CodSpeed instrument."""
    if results.get("instrument", {}).get("type") != "walltime":
        return False
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return True


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    if not session.config.getoption("--codspeed", default=False):
        return
    from pytest_codspeed.plugin import get_plugin

    plugin = get_plugin(session.config)
    results = plugin.instrument.get_result_dict()
    output = Path(os.environ["RUNNER_TEMP"]) / "quprs-paired-walltime-codspeed.json"
    export_walltime_result(results, output)
