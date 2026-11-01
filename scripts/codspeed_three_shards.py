"""Opt-in cost-balanced THREE-shard CodSpeed Simulation trial.

Source of heuristic weights: CodSpeed v5 Simulation's own CPU cost for
QuPRS 95f8942 (2026-11-01). These weights plan work placement only; they
are NOT wall-clock performance measurements, and the trial will compare
actual CI makespan and full CodSpeed coverage before promotion.

Do not alter original test names, benchmark fixtures, simulation instrument,
or the default five-shard production job.
"""
from __future__ import annotations

import pytest

WEIGHTS = {
    "adder_8": {"python": 15.6, "rust": .034},
    "gf2^4_mult": {"python": .644, "rust": .0044},
    "tof_3": {"python": .060, "rust": .0014},
    "vbe_adder_3": {"python": .414, "rust": .0036},
    "ghz_nativegates_ibm_qiskit_opt0_32": {"python": .379, "rust": .0021},
    "graphstate_nativegates_ibm_qiskit_opt0_16": {"python": .961, "rust": .0129},
    "grover-noancilla_nativegates_ibm_qiskit_opt0_4": {"python": 1.4, "rust": .0202},
    "qaoa_nativegates_ibm_qiskit_opt0_7": {"python": 4.7, "rust": .056},
    "qft_nativegates_ibm_qiskit_opt0_16": {"python": 8.2, "rust": .074},
    "vqe_nativegates_ibm_qiskit_opt0_4": {"python": 1.0, "rust": .019},
}


def weight(nodeid: str) -> float:
    matching = [w for stem, w in WEIGHTS.items() if "[" + stem + ".qasm-" in nodeid]
    if len(matching) != 1:
        raise ValueError(f"Unrecognized or ambiguous benchmark identity: {nodeid}")
    backend = "python" if nodeid.endswith("-python]") else "rust" if nodeid.endswith("-rust]") else None
    if backend is None:
        raise ValueError(f"Missing backend in benchmark URI: {nodeid}")
    # Include identical small run overhead in all cases and avoid placing
    # subprocess-heavy Rust work all in one shard.
    return matching[0][backend] + .1


def plan(nodeids: list[str]) -> dict[str, int]:
    if len(nodeids) != len(set(nodeids)):
        raise ValueError("Duplicate benchmark node IDs")
    loads = [0.0, 0.0, 0.0]
    groups = [[], [], []]
    for nodeid in sorted(nodeids, key=lambda n: (-weight(n), n)):
        shard = min(range(3), key=lambda k: (loads[k], k))
        groups[shard].append(nodeid)
        loads[shard] += weight(nodeid)
    if not all(groups):
        raise ValueError("Trial contains an empty shard")
    return {nodeid: i for i, group in enumerate(groups) for nodeid in group}


def pytest_addoption(parser):
    group = parser.getgroup("CodSpeed weighted three-shard pilot")
    group.addoption("--weighted-shard-id", type=int, choices=(0, 1, 2), default=None)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    shard = config.getoption("--weighted-shard-id")
    if shard is None:
        return
    allocation = plan([item.nodeid for item in items])
    keep = [item for item in items if allocation[item.nodeid] == shard]
    discard = [item for item in items if allocation[item.nodeid] != shard]
    config.hook.pytest_deselected(items=discard)
    items[:] = keep
