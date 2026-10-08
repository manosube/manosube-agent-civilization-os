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
PACKAGED_MEMBER = "manosube_agent_civilization/development_binding/DEVELOPMENT_BINDING_POLICY.json"


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
    packaged = (
        installed
        / "manosube_agent_civilization"
        / "development_binding"
        / ("DEVELOPMENT_BINDING_POLICY.json")
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
    assert answer["decision"].endswith("0004")
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


# --------------------------------------------------------------------------- #
# SR9-F1 (PR #112 comment 6053084718): the installed ``review_adapter`` module
# itself carries no effectful controlled-mechanics launch fixture, under any
# name, and no alternate token-minting/callable local-launch bypass -- proven
# against the real installed wheel, from outside the repository, never merely
# by this delivery's own "no current CLI caller reaches it" claim or by
# checking the one specific removed name and nothing else.
# --------------------------------------------------------------------------- #

#: Named explicitly in the SR9-F1 finding (PR #112 comment 6053084718) -- the
#: three functions this correction removed from ``review_adapter.py`` entirely.
_REMOVED_SR9_F1_FIXTURE_NAMES = (
    "mint_review_launch_admission_for_controlled_mechanics_test",
    "spawn_review_process_for_controlled_mechanics_test",
    "launch_review_process_for_controlled_mechanics_test",
)


def test_the_installed_review_adapter_has_no_public_name_naming_itself_a_test_fixture(
    installed: Path,
) -> None:
    """The SR9-F1 gap was never specific to those three literal names -- the independent
    review's own point was that *any* name calling itself a "mechanics test" fixture while
    remaining shipped and callable is the same bypass under new spelling. This scans every
    public attribute the installed module actually carries (never a fixed guess list) and
    refuses the whole class of rename, not just the one instance already found."""

    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import review_adapter
        import json
        public_names = [name for name in dir(review_adapter) if not name.startswith("_")]
        test_named = [name for name in public_names if "test" in name.lower()]
        print(json.dumps({"public_names": public_names, "test_named": test_named}))
        """,
    )
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout.strip().splitlines()[-1])
    assert answer["test_named"] == [], answer["test_named"]
    for removed_name in _REMOVED_SR9_F1_FIXTURE_NAMES:
        assert removed_name not in answer["public_names"], removed_name


def test_the_installed_review_adapter_has_no_module_level_admission_token_store(
    installed: Path,
) -> None:
    """The removed fixtures' own mechanics depended on a module-level mutable token store
    (``_ADMISSION_TOKENS``) and a fingerprint/ceiling helper pair
    (``_operation_fingerprint``/``_require_within_ratified_ceiling``) -- proof that the
    fixtures themselves are gone is not proof that nothing a caller could still populate or
    invoke to mint a token survives under a different name. This checks the installed
    module's *entire* attribute surface (public and private) for any of those names, or any
    name that still says what they said, rather than only the three fixture names above."""

    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import review_adapter
        import json
        all_names = dir(review_adapter)
        suspect = [
            name for name in all_names
            if "admission_token" in name.lower()
            or "fingerprint" in name.lower()
            or name in ("_ADMISSION_TOKENS", "_operation_fingerprint",
                        "_require_within_ratified_ceiling")
        ]
        print(json.dumps(suspect))
        """,
    )
    assert result.returncode == 0, result.stderr
    suspect = json.loads(result.stdout.strip().splitlines()[-1])
    assert suspect == [], suspect


def test_the_installed_spawn_review_process_refuses_a_real_argv_unconditionally(
    installed: Path, tmp_path: Path
) -> None:
    """The one real ``Popen`` call site any admitted caller could reach before SR8-F1 --
    called here, from the installed package, with a genuine, directly-executable argv and no
    monkeypatching of any kind. If this ever again minted a token or started the process, the
    harmless marker file this writes would exist; it must not."""

    marker = tmp_path / "sr9_f1_marker.txt"
    result = _run_installed(
        installed,
        f"""
        from manosube_agent_civilization.development_binding import review_adapter
        from manosube_agent_civilization.development_binding.errors import ReviewAdapterError
        from pathlib import Path
        import json, sys

        marker = Path({str(marker)!r})
        argv = [
            sys.executable, "-c",
            "from pathlib import Path; Path(" + repr(str(marker)) + ").write_text('STARTED')",
        ]
        try:
            review_adapter.spawn_review_process(
                argv, cwd=marker.parent, env={{}}, admission_token="anything-at-all",
            )
            raised = False
        except ReviewAdapterError:
            raised = True
        print(json.dumps({{"raised": raised, "marker_exists": marker.exists()}}))
        """,
    )
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout.strip().splitlines()[-1])
    assert answer["raised"] is True, answer
    assert answer["marker_exists"] is False, answer


def test_the_installed_launch_review_process_refuses_unconditionally(installed: Path) -> None:
    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import review_adapter
        from manosube_agent_civilization.development_binding.errors import ReviewAdapterError
        from pathlib import Path
        import json, sys

        try:
            review_adapter.launch_review_process(
                [sys.executable, "-c", "pass"],
                cwd=Path.cwd(), env={}, max_seconds=5, max_output_bytes=4096,
                clock=lambda: "2026-10-08T00:00:00Z",
                authentication_decision={"decision": "REVIEW_SELECTION_ADMITTED"},
                claim_decision={"decision": "REVIEW_CLAIM_ADMITTED"},
            )
            raised = False
        except ReviewAdapterError:
            raised = True
        print(json.dumps({"raised": raised}))
        """,
    )
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout.strip().splitlines()[-1])
    assert answer["raised"] is True, answer


def test_the_installed_require_authenticated_review_launch_admission_never_returns_a_token(
    installed: Path,
) -> None:
    """The exact SR6-F1/SR7-F1 reproduction -- a hand-typed, non-genuine *store*/ledger context
    -- run against the installed wheel: this function either raises outright (refusing before
    any genuine grant/claim is even checked, or because SR8-F1/SR9-F1's own unconditional
    refusal is reached below them) or propagates a Boot/Authority error for the fabricated
    Project this test never created -- see this function's own docstring: "Every Boot
    failure... propagates completely unchanged." Either outcome is a pass: what this test
    rules out is the one specific regression -- this call returning an admission token
    string at all, the one thing that would let a caller reach :func:`spawn_review_process`
    with a real admission."""

    result = _run_installed(
        installed,
        """
        from manosube_agent_civilization.development_binding import review_adapter
        from pathlib import Path
        import json, sys

        try:
            token = review_adapter.require_authenticated_review_launch_admission(
                argv=[sys.executable, "-c", "pass"],
                cwd=Path.cwd(),
                max_seconds=5,
                max_output_bytes=4096,
                mask_paths=(),
                require_isolation=False,
                store=None,
                project_id="PROJ",
                project_binding_id="BIND",
                requirement_id="REQ",
                selection_id="SEL",
                verifier_identity={"kind": "bounded_codex_technical_reviewer", "id": "X"},
                permitted_boundary={},
                verifier_selection_grant_refs=[],
                human_grant_declaration_refs=[],
                ledger_path=Path.cwd() / "nonexistent-ledger.json",
                identity_key="deadbeef",
                repository="owner/repo",
            )
            print(json.dumps({"raised": False, "token": token}))
        except Exception as error:
            print(json.dumps({"raised": True, "error_type": type(error).__name__}))
        """,
    )
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout.strip().splitlines()[-1])
    assert answer["raised"] is True, answer
