"""Recheck measurement-only changes against a fully successful saved test run."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tomllib
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import coverage

PROBES = [
    "src/manosube_agent_civilization/_r11f2_e2e_shadow_writer_tmp.py",
    "src/manosube_agent_civilization/_r12f2_e2e_shadow_lineage_writer_tmp.py",
]
ALLOWED = {
    "pyproject.toml",
    ".github/workflows/coverage_recheck.yml",
    "scripts/recheck_saved_coverage.py",
    "docs/EXTERNAL_READINESS.md",
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def get_json(path: str) -> dict:
    repo = os.environ["GITHUB_REPOSITORY"]
    request = Request(
        f"https://api.github.com/repos/{repo}/{path}",
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Accept": "application/vnd.github+json"},
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    run = get_json(f"actions/runs/{args.run_id}")
    source = run["head_sha"]
    assert len(source) == 40 and all(c in "0123456789abcdef" for c in source)
    jobs = get_json(f"actions/runs/{args.run_id}/jobs?per_page=100")["jobs"]
    required = {f"tests ({i})" for i in range(5)} | {"static", "schemas", "examples", "distribution"}
    assert required <= {j["name"] for j in jobs}
    assert all(j["conclusion"] == "success" for j in jobs if j["name"] in required)
    changed = set(git("diff", "--name-only", source, "HEAD").splitlines())
    assert changed <= ALLOWED, f"runtime/evidence changed: {sorted(changed - ALLOWED)}"
    before = tomllib.loads(git("show", f"{source}:pyproject.toml"))
    after = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert after["tool"]["coverage"]["report"]["omit"] == PROBES
    comparable = deepcopy(after)
    comparable["tool"]["coverage"]["report"].pop("omit")
    assert comparable == before, "only the two explicit probe omissions may change"
    print(f"Validated saved runtime source {source}; report-only changes {sorted(changed)}")
    if args.validate_only:
        return
    root = Path("build/recheck")
    selected: list[str] = []
    totals = set()
    passed = skipped = 0
    for index in range(5):
        directory = root / f"test-results-{index}"
        receipt = json.loads((directory / f"shard-{index}.json").read_text())
        assert receipt["index"] == index and receipt["count"] == 5
        selected.extend(receipt["selected"])
        totals.add(receipt["total_collected"])
        suites = ET.parse(directory / f"junit-{index}.xml").getroot()
        cases = list(suites.iter("testcase"))
        assert len(cases) == len(receipt["selected"])
        assert not list(suites.iter("failure")) and not list(suites.iter("error"))
        count_skipped = len(list(suites.iter("skipped")))
        skipped += count_skipped
        passed += len(cases) - count_skipped
    assert len(totals) == 1 and len(selected) == len(set(selected)) == totals.pop()
    cov = coverage.Coverage(config_file="pyproject.toml", data_file=str(root / ".coverage"))
    cov.combine([str(root / f"test-results-{i}") for i in range(5)], keep=True)
    cov.save()
    value = cov.report()
    assert value >= 90
    cov.json_report(outfile=str(root / "coverage.json"))
    record = {"source_run_id": args.run_id, "runtime_source_commit": source,
              "report_commit": git("rev-parse", "HEAD").strip(), "passed": passed,
              "skipped": skipped, "collected": len(selected), "coverage_percent": value}
    (root / "validation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
