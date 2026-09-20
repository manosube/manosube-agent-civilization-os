"""Static conformance for the v1.0 Acceptance package (Issue #92,
`ADOPT_PHASE_22_V1_0_ACCEPTANCE`): module inventory and public-surface totality."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "src" / "manosube_agent_civilization" / "v1_0_acceptance"


def test_package_module_inventory_is_exactly_expected() -> None:
    modules = {p.name for p in PACKAGE_ROOT.glob("*.py")}
    assert modules == {
        "__init__.py",
        "blocking_differences.py",
        "commit_binding.py",
        "deferred_differences_register.py",
        "engine.py",
        "errors.py",
        "gate22.py",
        "identity.py",
        "release_identity.py",
        "types.py",
    }


def test_package_never_shells_out_beyond_pytest_and_git() -> None:
    """The only subprocess invocations this package performs are `pytest` (Gate 22
    rederivation) and `git ls-tree` (release identity) -- never an arbitrary shell command,
    never a network call."""
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "subprocess.run(" not in text:
            continue
        assert '"pytest"' in text or '"git"' in text, path.name


def test_package_never_imports_networking_modules() -> None:
    forbidden_modules = ("urllib", "http.client", "socket", "requests")
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for module in forbidden_modules:
            assert f"import {module}" not in text, (path.name, module)
