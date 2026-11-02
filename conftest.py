"""Export first-party pytest-codspeed data for exact-SHA cross-instrument audits.

No stopwatch is added. The existing CodSpeed instrument owns every measurement.
"""
import json
import os
from pathlib import Path

import pytest


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("QUPRS_CODSPEED_EXPORT")
    if (not destination or session.config.getoption("--collect-only", default=False)
            or not session.config.getoption("--codspeed", default=False)):
        return
    from pytest_codspeed.plugin import get_plugin

    results = get_plugin(session.config).instrument.get_result_dict()
    if not isinstance(results, dict) or not isinstance(results.get("benchmarks"), list):
        raise RuntimeError("CodSpeed did not produce a benchmark measurement dictionary")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
