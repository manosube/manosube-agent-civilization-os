"""Child-process execution must contribute actual line and branch evidence."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib


def test_a_real_child_process_contributes_both_branch_outcomes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert "subprocess" in configuration["tool"]["coverage"]["run"]["patch"]
    child = tmp_path / "child.py"
    child.write_text(
        "import sys\n"
        "if sys.argv[1] == 'yes':\n"
        "    print('accepted')\n"
        "else:\n"
        "    print('refused')\n",
        encoding="utf-8",
    )
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import subprocess, sys\n"
        "for flag in ('yes', 'no'):\n"
        "    subprocess.run([sys.executable, 'child.py', flag], check=True)\n",
        encoding="utf-8",
    )
    configuration_path = tmp_path / ".coveragerc"
    configuration_path.write_text(
        "[run]\nbranch = true\nparallel = true\npatch = subprocess\nsource = .\n",
        encoding="utf-8",
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COVERAGE_", "COV_CORE_", "PYTEST_"))
    }
    for arguments in (
        ["run", "parent.py"],
        ["combine"],
        ["json", "-o", "report.json", "--fail-under=0"],
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                arguments[0],
                f"--rcfile={configuration_path}",
                *arguments[1:],
            ],
            cwd=tmp_path,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        if arguments[0] == "run":
            assert "accepted" in result.stdout and "refused" in result.stdout
    files = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["files"]
    measured = next(value for name, value in files.items() if name.endswith("child.py"))
    assert {2, 3, 5} <= set(measured["executed_lines"])
    assert measured["missing_branches"] == []
    assert len(measured["executed_branches"]) == 2


def test_an_actual_abrupt_exit_keeps_its_exit_code_and_measured_lines(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert {"subprocess", "_exit"} <= set(configuration["tool"]["coverage"]["run"]["patch"])
    (tmp_path / "crash.py").write_text(
        "import os\nmarker = 'before-exit'\nos._exit(23)\nraise AssertionError('unreachable')\n",
        encoding="utf-8",
    )
    (tmp_path / "parent.py").write_text(
        "import subprocess, sys\n"
        "result = subprocess.run([sys.executable, 'crash.py'], check=False)\n"
        "assert result.returncode == 23\n",
        encoding="utf-8",
    )
    configuration_path = tmp_path / ".coveragerc"
    configuration_path.write_text(
        "[run]\nbranch = true\nparallel = true\npatch = subprocess\n    _exit\nsource = .\n",
        encoding="utf-8",
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COVERAGE_", "COV_CORE_", "PYTEST_"))
    }
    for arguments in (
        ["run", "parent.py"],
        ["combine"],
        ["json", "-o", "report.json", "--fail-under=0"],
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                arguments[0],
                f"--rcfile={configuration_path}",
                *arguments[1:],
            ],
            cwd=tmp_path,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    files = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["files"]
    measured = next(value for name, value in files.items() if name.endswith("crash.py"))
    assert {1, 2, 3} <= set(measured["executed_lines"])
    assert 4 not in measured["executed_lines"]
