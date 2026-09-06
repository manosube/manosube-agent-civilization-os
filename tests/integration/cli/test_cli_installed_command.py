"""Phase 11 (Issue #47) CLI Boot adapter: the installed-command proof (Structural Review
Round 1, SHUKOU adoption ``ADOPT_P11_R1_CLI_PUBLIC_SURFACE_AND_FAILURE_BOUNDARY``).

The primary positive-route and determinism proofs (frozen semantic decision 9) must run
against the real, installed ``manosube`` console-script executable -- not a source-tree
``python -m ...`` invocation, which no longer exists as an entry point at all (``CLI_CONTRACT.
md`` §2). This suite builds a real wheel from this repository, installs it into a fresh,
isolated virtual environment (never this repository's own ``.venv``, never a ``--target``
install layered onto the outer interpreter's own script directory), and invokes that venv's
own ``manosube`` executable directly, with a working directory outside the repository and
with ``PYTHONPATH`` stripped from the subprocess environment, so a passing result cannot mean
"the repository's own editable install answered instead."

The venv is built once per module (``scope="module"``) and reused across every test below, so
the whole file proves every required item from the SHUKOU adoption's own required-installed-
command-proof list against one single isolated installation, exactly as required, without
paying the wheel-build-plus-venv-creation cost once per test.
"""

from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import zipfile

import pytest
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore

pytestmark = [pytest.mark.integration, pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[3]


def _bound(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Build a real Phase-9-bound Project on disk, using this test's own (repository-source)
    environment -- the installed venv only ever *reads* this Store, through its own copy of
    the package; it never needs to be able to construct one."""

    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store_root, kwargs, result


def _argv(
    store_root: Path, schema_root: Path, project_id: str, project_binding_id: str
) -> list[str]:
    return [
        "boot",
        "--store-root",
        str(store_root),
        "--schema-root",
        str(schema_root),
        "--project-id",
        project_id,
        "--project-binding-id",
        project_binding_id,
    ]


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a wheel from this repository and install it into a fresh, isolated venv. Returns
    the venv's own root directory."""

    if shutil.which("git") is None:  # pragma: no cover - environment guard
        pytest.skip("a build backend needs the working tree")

    workspace = tmp_path_factory.mktemp("cli-installed")
    built = workspace / "dist"
    venv_dir = workspace / "venv"

    wheel_result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps", "-w", str(built)],
        capture_output=True,
        text=True,
        check=False,
    )
    if wheel_result.returncode != 0:  # pragma: no cover - environment guard
        pytest.skip(f"wheel build unavailable here: {wheel_result.stderr[-400:]}")

    wheels = sorted(built.glob("*.whl"))
    assert len(wheels) == 1, wheels

    venv_result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if venv_result.returncode != 0:  # pragma: no cover - environment guard
        pytest.skip(f"venv creation unavailable here: {venv_result.stderr[-400:]}")

    # Not --no-deps here: unlike the development-binding guard's own installed-wheel test
    # (which never touches Boot/Store), this suite exercises the real Boot->Store->schema
    # route, which needs this package's own declared runtime dependency (`jsonschema`)
    # actually installed -- exactly what a real `pip install manosube-agent-civilization-os`
    # would resolve too.
    venv_python = venv_dir / "bin" / "python"
    install_result = subprocess.run(  # noqa: S603
        [str(venv_python), "-m", "pip", "install", str(wheels[0])],
        capture_output=True,
        text=True,
        check=False,
    )
    if install_result.returncode != 0:  # pragma: no cover - environment guard
        pytest.skip(f"dependency install unavailable here: {install_result.stderr[-400:]}")
    return venv_dir


@pytest.fixture
def outside_cwd(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A working directory that is genuinely outside the repository *and* is not an ancestor
    of any test's own ``store_root`` -- ``FileStateStore`` itself refuses a backend root that
    is inside its own construction-time current working directory (``BoundaryError``), so a
    naive ``tmp_path.parent`` (an ancestor of ``tmp_path / "backend"``) would trip that same
    check for the wrong reason and mask what this suite actually proves."""

    return tmp_path_factory.mktemp("outside-cwd")


def _manosube_executable(installed: Path) -> Path:
    executable = installed / "bin" / "manosube"
    assert executable.is_file(), "the venv install did not produce a `manosube` script"
    return executable


def _clean_env() -> dict[str, str]:
    """A copy of the current environment with ``PYTHONPATH`` removed -- the installed venv's
    own script must resolve the CLI package through its own site-packages alone, never through
    a repository path injected via this test process's own environment
    (``PYTHONPATH_REPOSITORY_INJECTION=false``)."""

    return {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}


def _run_installed(
    installed: Path, argv: list[str], cwd: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603
        [str(_manosube_executable(installed)), *argv],
        capture_output=True,
        cwd=cwd,
        env=_clean_env(),
        check=False,
    )


# --------------------------------------------------------------------------- #
# Fresh-process success, and determinism, against the real installed command
# --------------------------------------------------------------------------- #


def test_installed_manosube_boots_a_real_bound_project_in_a_fresh_process(
    installed: Path, tmp_path: Path, outside_cwd: Path
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    assert ROOT not in outside_cwd.parents and outside_cwd != ROOT

    proc = _run_installed(
        installed,
        _argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"]),
        cwd=outside_cwd,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == b""
    assert proc.stdout.endswith(b"\n")
    document = json.loads(proc.stdout)
    assert document["project_id"] == project_id
    assert document["project_binding_id"] == result["project_binding_id"]
    assert document["current_state"] == result["committed_state"]


def test_installed_manosube_success_is_deterministic_across_repeated_invocations(
    installed: Path, tmp_path: Path, outside_cwd: Path
) -> None:
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    argv = _argv(store_root, SCHEMA_ROOT, project_id, result["project_binding_id"])

    first = _run_installed(installed, argv, cwd=outside_cwd)
    second = _run_installed(installed, argv, cwd=outside_cwd)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout


# --------------------------------------------------------------------------- #
# Required rejection proofs against the same installed executable
# --------------------------------------------------------------------------- #


def test_installed_manosube_rejects_a_malformed_command_line(
    installed: Path, tmp_path: Path, outside_cwd: Path
) -> None:
    proc = _run_installed(installed, ["boot", "--store-root", str(tmp_path)], cwd=outside_cwd)

    assert proc.returncode != 0
    assert proc.stdout == b""
    document = json.loads(proc.stderr)
    assert document["error"] == "CLIArgumentError"
    assert b"Traceback" not in proc.stderr


def test_installed_manosube_rejects_a_missing_binding_with_zero_mutation(
    installed: Path, tmp_path: Path, outside_cwd: Path
) -> None:
    store_root, kwargs, _result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    project_dir = store_root / "projects" / project_id
    before = sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*"))

    proc = _run_installed(
        installed,
        _argv(store_root, SCHEMA_ROOT, project_id, "PROJBIND-DOES-NOT-EXIST"),
        cwd=outside_cwd,
    )

    assert proc.returncode != 0
    assert proc.stdout == b""
    document = json.loads(proc.stderr)
    assert document["error"] == "BootNotFoundError"
    after = sorted(str(path.relative_to(project_dir)) for path in project_dir.rglob("*"))
    assert after == before


# --------------------------------------------------------------------------- #
# The console script is the sole registered, and the sole reachable, public command
# --------------------------------------------------------------------------- #


def test_the_built_wheel_declares_exactly_one_console_script_named_manosube(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Read from the built wheel's own ``entry_points.txt`` archive member -- a real
    distribution artifact, not merely ``pyproject.toml``'s own declared intent (that static
    proof lives in ``tests/contract/cli/test_cli_static_conformance.py``)."""

    workspace = tmp_path_factory.mktemp("cli-wheel-entry-points")
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps", "-w", str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover - environment guard
        pytest.skip("wheel build unavailable here")
    wheel = sorted(workspace.glob("*.whl"))[0]

    with zipfile.ZipFile(wheel) as archive:
        entry_points_member = next(
            name for name in archive.namelist() if name.endswith("entry_points.txt")
        )
        content = archive.read(entry_points_member).decode("utf-8")

    parser = configparser.ConfigParser()
    parser.read_string(content)
    assert set(parser["console_scripts"]) == {"manosube"}
    assert parser["console_scripts"]["manosube"] == "manosube_agent_civilization.cli.main:main"


def test_installed_python_dash_m_cannot_invoke_the_cli_package(installed: Path) -> None:
    """``python -m manosube_agent_civilization.cli`` fails against the real installed package
    too, not only in a source checkout -- there is no ``cli/__main__.py`` in the wheel, so
    this is not a second, undocumented public entry point (P11-R1-F1)."""

    venv_python = installed / "bin" / "python"
    proc = subprocess.run(  # noqa: S603
        [str(venv_python), "-m", "manosube_agent_civilization.cli", "boot"],
        capture_output=True,
        cwd=installed.parent,
        env=_clean_env(),
        check=False,
    )

    assert proc.returncode != 0
    assert b"__main__" in proc.stderr or b"cannot be directly executed" in proc.stderr


def test_installed_python_dash_m_cli_main_cannot_invoke_the_cli_package_either(
    installed: Path,
) -> None:
    """The second half of the same proof: ``python -m
    manosube_agent_civilization.cli.main`` -- which *would* work despite ``__main__.py``'s own
    absence if ``main.py`` still carried a trailing ``if __name__ == "__main__":`` guard --
    also fails to invoke Boot at all, because that guard was removed (P11-R1-F1). Nothing in
    the module executes beyond function/class definitions, so the process exits cleanly with
    empty stdout; Python's own runpy still emits its standard, harmless "found in sys.modules"
    RuntimeWarning here (because ``cli/__init__.py``'s own ``from .main import ...`` already
    imported this exact submodule before ``-m`` re-executed it as ``__main__``) -- that
    warning is not a rejection, a traceback, or any sign Boot was ever reached."""

    venv_python = installed / "bin" / "python"
    proc = subprocess.run(  # noqa: S603
        [str(venv_python), "-m", "manosube_agent_civilization.cli.main", "boot"],
        capture_output=True,
        cwd=installed.parent,
        env=_clean_env(),
        check=False,
    )

    assert proc.returncode == 0
    assert proc.stdout == b""
    assert b"Traceback" not in proc.stderr
    assert b"error" not in proc.stderr.lower() or b"runtimewarning" in proc.stderr.lower()
