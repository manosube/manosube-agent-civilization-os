"""The guard must still guard once the package is installed.

A guard that works only in a source checkout is a guard that stops existing the moment the
package is used the way packages are used. This suite builds a real wheel, installs it, and
calls ``evaluate`` from a subprocess whose working directory is **outside** the repository
and whose ``sys.path`` does not contain it.

Before the repair, that subprocess raised:

```text
PolicyIntegrityError: development binding policy is unreadable:
  [Errno 2] No such file or directory: .../03_BINDING/DEVELOPMENT_BINDING_POLICY.json
```

It failed *closed*, which is the one thing it got right -- it refused rather than permitting.
It also could not answer at all, which is its own kind of useless.

Every ``subprocess`` call below runs ``sys.executable`` on paths this module constructs, with
no shell and no caller-supplied argument, so each carries ``# noqa: S603`` rather than
widening a per-file ignore that would also cover a future call that is not safe.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import textwrap
import zipfile

import pytest

from manosube_agent_civilization.development_binding.policy import (
    PACKAGED_POLICY_PATH,
    REPOSITORY_POLICY_PATH,
    resolve_policy_path,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[3]

#: Where the build maps the canonical artifact inside the wheel.
PACKAGED_MEMBER = (
    "manosube_agent_civilization/development_binding/DEVELOPMENT_BINDING_POLICY.json"
)


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a wheel from this repository and install it into an isolated target."""

    if shutil.which("git") is None:  # pragma: no cover - environment guard
        pytest.skip("a build backend needs the working tree")

    workspace = tmp_path_factory.mktemp("wheel")
    built, target = workspace / "dist", workspace / "site"
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps", "-w", str(built)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover - environment guard
        pytest.skip(f"wheel build unavailable here: {result.stderr[-400:]}")

    wheels = sorted(built.glob("*.whl"))
    assert len(wheels) == 1, wheels
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target),
            str(wheels[0]),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return target


def _run_installed(target: Path, source: str) -> subprocess.CompletedProcess[str]:
    """Run *source* against the installed package, from outside the repository.

    Isolation here is load-bearing and easy to get wrong. The first attempt passed ``-I``
    with ``PYTHONPATH`` -- and ``-I`` *ignores* ``PYTHONPATH``, so the subprocess imported the
    editable install from the checkout and every result meant nothing. The isolation test at
    the bottom of this file is what caught it, which is why it is here.

    So: ``-I`` for a clean environment, ``-S`` so no site directory can re-introduce the
    editable install, and the target inserted explicitly at the head of ``sys.path``. The
    working directory is outside the repository as well.
    """

    program = f"import sys; sys.path.insert(0, {str(target)!r})\n" + textwrap.dedent(source)
    return subprocess.run(  # noqa: S603
        [sys.executable, "-I", "-S", "-c", program],
        capture_output=True,
        text=True,
        cwd=sysconfig.get_path("data"),
        check=False,
    )


# --------------------------------------------------------------------------- #
# One canonical copy
# --------------------------------------------------------------------------- #


def test_the_source_tree_holds_exactly_one_policy_artifact() -> None:
    """No independently-maintained duplicate. The build makes the packaged copy, not a person."""

    found = [
        path
        for path in ROOT.rglob("DEVELOPMENT_BINDING_POLICY.json")
        if ".venv" not in path.parts and "dist" not in path.parts and ".git" not in path.parts
    ]
    assert found == [REPOSITORY_POLICY_PATH], found


def test_the_canonical_artifact_stays_in_the_binding_directory() -> None:
    assert REPOSITORY_POLICY_PATH.parent.name == "03_BINDING"
    assert not (ROOT / "01_SCHEMA" / "DEVELOPMENT_BINDING_POLICY.json").exists()
    assert list((ROOT / "01_SCHEMA").rglob("DEVELOPMENT_BINDING_POLICY.json")) == []


def test_a_source_checkout_reads_the_canonical_file_directly() -> None:
    """So an edit to the ratified record takes effect here without a rebuild."""

    assert not PACKAGED_POLICY_PATH.is_file()
    assert resolve_policy_path() == REPOSITORY_POLICY_PATH


# --------------------------------------------------------------------------- #
# The wheel carries it
# --------------------------------------------------------------------------- #


def test_the_wheel_contains_the_policy_and_it_is_byte_identical(installed: Path) -> None:
    packaged = installed / "manosube_agent_civilization" / "development_binding" / (
        "DEVELOPMENT_BINDING_POLICY.json"
    )
    assert packaged.is_file()
    assert packaged.read_bytes() == REPOSITORY_POLICY_PATH.read_bytes()


def test_the_built_wheel_declares_the_policy_member(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Read from the archive itself, so a future build change that drops it fails here."""

    workspace = tmp_path_factory.mktemp("archive")
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
        assert PACKAGED_MEMBER in archive.namelist()


# --------------------------------------------------------------------------- #
# The guard answers from the installed package
# --------------------------------------------------------------------------- #


def test_the_guard_loads_its_policy_when_installed(installed: Path) -> None:
    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding.policy import (
            load_policy, resolve_policy_path,
        )
        import json
        print(json.dumps({
            "decision": load_policy()["decision_id"],
            "path": str(resolve_policy_path()),
        }))
        """,
    )
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout.strip().splitlines()[-1])
    assert answer["decision"].endswith("0002")
    # Resolved through the installed package, not back into the checkout.
    assert str(installed) in answer["path"]
    assert str(ROOT / "03_BINDING") not in answer["path"]


def test_the_guard_refuses_the_prohibited_route_when_installed(installed: Path) -> None:
    """The incident's own record, evaluated by an installed copy of the guard."""

    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import evaluate
        import json
        print(json.dumps(evaluate({
            "record_type": "ACTOR_ACTION",
            "actor": "CLAUDE_CODE",
            "action": "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        })))
        """,
    )
    assert result.returncode == 0, result.stderr
    verdict = json.loads(result.stdout.strip().splitlines()[-1])
    assert verdict["decision"] == "REFUSED"
    assert "AUTOMATED_REVIEW_TRIGGER_PROHIBITED" in verdict["reason_codes"]


def test_the_guard_refuses_merge_authority_drift_when_installed(installed: Path) -> None:
    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import evaluate
        import json
        print(json.dumps(evaluate({
            "record_type": "HANDOFF_TRANSITION",
            "actor": "CLAUDE_CODE",
            "from_state": "SHUKOU_ACCEPTED",
            "to_state": "SHUKOU_MERGED",
        })))
        """,
    )
    assert result.returncode == 0, result.stderr
    verdict = json.loads(result.stdout.strip().splitlines()[-1])
    assert verdict["decision"] == "REFUSED"
    assert "MERGE_OPERATION_DRIFT" in verdict["reason_codes"]


def test_the_guard_still_permits_the_declared_route_when_installed(installed: Path) -> None:
    """The control: an installed guard that refuses everything is also broken."""

    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import evaluate
        import json
        print(json.dumps(evaluate({
            "record_type": "HANDOFF_TRANSITION",
            "actor": "CLAUDE_CODE",
            "from_state": "GITHUB_PR_READY",
            "to_state": "READY_FOR_STRUCTURAL_REVIEW",
        })))
        """,
    )
    assert result.returncode == 0, result.stderr
    verdict = json.loads(result.stdout.strip().splitlines()[-1])
    assert verdict["decision"] == "PERMITTED"


def test_the_installed_guard_cannot_see_the_repository(installed: Path) -> None:
    """Proves the subprocess is genuinely isolated, so the results above mean what they say."""

    result = _run_installed(
        installed,
        """
        from pathlib import Path
        import manosube_agent_civilization.development_binding.policy as policy
        print(policy.REPOSITORY_POLICY_PATH.is_file())
        """,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "False"
