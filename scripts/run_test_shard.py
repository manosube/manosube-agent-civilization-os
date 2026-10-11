"""Collect every test before selecting a stable, disjoint CI partition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

_SHARED_ACCEPTANCE_MODULES = frozenset({
    "tests/contract/v1_0_acceptance/test_gate22_rederivation.py",
    "tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py",
})
_LONG_RUNNING_PROOF_MODULE = "tests/long_running_proof/test_long_running_proof_gate_20.py"


def partition_nodes(nodes: list[str], count: int) -> list[list[str]]:
    """Keep modules and the shared real acceptance receipt together, without dropping tests."""
    if count <= 0 or not nodes or len(nodes) != len(set(nodes)):
        raise ValueError("require a positive shard count and nonempty unique test IDs")
    modules: dict[str, list[str]] = {}
    for node in nodes:
        module = node.split("::", 1)[0]
        group = "shared_real_gate22_receipt" if module in _SHARED_ACCEPTANCE_MODULES else module
        modules.setdefault(group, []).append(node)
    partitions: list[list[str]] = [[] for _ in range(count)]
    shared = modules.pop("shared_real_gate22_receipt", [])
    regular_count = count
    if shared and count > 1:
        # The observed real rederivation alone takes about an hour. Reserve its
        # runner rather than balancing that cost as though it were two cheap nodes.
        partitions[-1] = sorted(shared)
        regular_count -= 1
    elif shared:
        modules["shared_real_gate22_receipt"] = shared
    if _LONG_RUNNING_PROOF_MODULE in modules and regular_count > 1:
        # Node count hides the cost of the four real 10/30/50/100-cycle tiers.
        # Retain all four tiers and their module together on another runner.
        regular_count -= 1
        partitions[regular_count] = sorted(modules.pop(_LONG_RUNNING_PROOF_MODULE))
    for module in sorted(modules, key=lambda name: (-len(modules[name]), name)):
        target = min(range(regular_count), key=lambda index: (len(partitions[index]), index))
        partitions[target].extend(sorted(modules[module]))
    return partitions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args()
    if not 0 <= args.index < args.count:
        parser.error("require 0 <= index < count")
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = Path("build/ci")
    output.mkdir(parents=True, exist_ok=True)
    (output / "collection.txt").write_text(collected.stdout + collected.stderr, encoding="utf-8")
    if collected.returncode:
        sys.stderr.write(collected.stdout + collected.stderr)
        return collected.returncode
    nodes = [
        line for line in collected.stdout.splitlines() if line.startswith("tests/") and "::" in line
    ]
    if not nodes or len(nodes) != len(set(nodes)):
        raise RuntimeError("collection is empty or contains duplicate node IDs")
    selected = partition_nodes(nodes, args.count)[args.index]
    if not selected:
        raise RuntimeError("empty shard")
    receipt = {
        "index": args.index,
        "partition_method": "dedicated_gate20_and_gate22_proofs_with_whole_modules_balanced_by_count",
        "count": args.count,
        "total_collected": len(nodes),
        "selected": selected,
    }
    (output / f"shard-{args.index}.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    argument_file = output / f"nodes-{args.index}.txt"
    argument_file.write_text("\n".join(selected) + "\n", encoding="utf-8")
    return subprocess.run(  # noqa: S603 -- fixed interpreter, pytest and collected node IDs
        [
            sys.executable,
            "-m",
            "pytest",
            "@" + str(argument_file),
            "-q",
            "--durations=20",
            "--maxfail=1",
            "--cov=manosube_agent_civilization",
            "--cov-report=",
            "--cov-fail-under=0",
            "--junitxml=" + str(output / f"junit-{args.index}.xml"),
        ],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
