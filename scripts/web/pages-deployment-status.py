#!/usr/bin/env python3
"""Evaluate exact-SHA GitHub Pages Actions evidence without trusting other runs.

This helper is deliberately pure/offline-testable. A cancelled duplicate run
must never hide an already successful deployment of the same immutable commit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys


def deployment_status(payload: dict, sha: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Expected an exact 40-character commit SHA")
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("Expected GitHub Actions workflow_runs collection")
    runs = []
    for run in payload["workflow_runs"]:
        if not isinstance(run, dict):
            raise ValueError("Malformed GitHub Actions run")
        if (run.get("name") == "pages build and deployment"
                and run.get("head_branch") == "gh-pages"
                and run.get("head_sha") == sha):
            runs.append(run)
    if not runs:
        return "absent"
    conclusions = [run.get("conclusion") for run in runs]
    if any(run.get("status") == "completed" and result == "success"
           for run, result in zip(runs, conclusions)):
        return "success"
    if any(run.get("status") in {"queued", "in_progress", "requested",
                                  "waiting", "pending"} for run in runs):
        return "active"
    if any(run.get("status") != "completed" for run in runs):
        raise ValueError("Unexpected Pages run status")
    if any(result in {"failure", "timed_out", "action_required",
                       "startup_failure"} for result in conclusions):
        return "failed"
    if all(result in {"cancelled", "skipped", "neutral", "stale"}
           for result in conclusions):
        return "cancelled"
    raise ValueError("Unexpected completed Pages run conclusion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True)
    arguments = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        print(deployment_status(payload, arguments.sha))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Invalid Pages Actions response: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
