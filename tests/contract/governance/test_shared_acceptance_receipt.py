"""The test-session receipt must not survive source/project substitution or mutation."""

import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest

from manosube_agent_civilization.v1_0_acceptance.errors import (
    DeliveryHeadBindingError,
    RepositoryProjectBindingError,
)


def test_shared_receipt_rechecks_real_git_binding_and_isolates_consumers(tmp_path: Path) -> None:
    fixture_path = Path(__file__).parents[1] / "v1_0_acceptance" / "conftest.py"
    spec = importlib.util.spec_from_file_location("receipt_fixture_guard_check", fixture_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executable = shutil.which("git")
    assert executable is not None

    def git(*args: str) -> str:
        return subprocess.run(  # noqa: S603 -- resolved Git executable and fixed test arguments
            [executable, *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init")
    git("config", "user.name", "Receipt check")
    git("config", "user.email", "receipt-check@example.invalid")
    git("config", "core.autocrlf", "false")
    git("remote", "add", "origin", "https://github.com/manosube/manosube-agent-civilization-os.git")
    source = tmp_path / "source.txt"
    source.write_text("one\n", encoding="utf-8")
    git("add", "source.txt")
    git("commit", "-m", "First source")
    receipt = {"delivery_head": git("rev-parse", "HEAD"), "nested": {"values": [1]}}
    module.REPO_ROOT = tmp_path
    # This small receipt tests freshness/copy plumbing, not the actual Gate 22 verdict.
    bound_copy = module.real_v1_0_acceptance_bundle.__wrapped__
    first = bound_copy(receipt)
    first["nested"]["values"].append(2)
    assert bound_copy(receipt)["nested"]["values"] == [1]

    source.write_text("two\n", encoding="utf-8")
    with pytest.raises(DeliveryHeadBindingError):
        bound_copy(receipt)
    git("add", "source.txt")
    git("commit", "-m", "Changed source")
    with pytest.raises(DeliveryHeadBindingError):
        bound_copy(receipt)
    git("remote", "set-url", "origin", "https://github.com/other/foreign.git")
    with pytest.raises(RepositoryProjectBindingError):
        bound_copy(receipt)
