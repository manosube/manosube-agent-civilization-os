"""Collect every test before selecting a stable, disjoint CI partition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


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
    selected = [
        node
        for node in nodes
        if int(hashlib.sha256(node.encode()).hexdigest(), 16) % args.count == args.index
    ]
    if not selected:
        raise RuntimeError("empty shard")
    receipt = {
        "index": args.index,
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
            "--cov=manosube_agent_civilization",
            "--cov-report=",
            "--cov-fail-under=0",
            "--junitxml=" + str(output / f"junit-{args.index}.xml"),
        ],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
