"""Malformed policy data must fail with a domain refusal before filesystem execution."""

from copy import deepcopy

import pytest
from tests.fixtures.change_executor_world import execution_boundary_for, git_worktree

from manosube_agent_civilization.change_executor.boundary import validate_execution_boundary
from manosube_agent_civilization.change_executor.errors import ExecutionBoundaryError


INVALID = []
for field in ("repository", "branch", "executor_identity", "executor_version", "worktree_root"):
    INVALID.extend((field, bad) for bad in (None, False, 0, [], {}, ""))
for field in ("max_files_changed", "max_bytes_changed", "max_file_bytes", "timeout_seconds"):
    INVALID.extend((field, bad) for bad in (None, False, 0, -1, "10", [], {}))
for field in (
    "permit_symlinks",
    "permit_path_traversal",
    "permit_network",
    "permit_subprocess",
    "permit_environment_mutation",
    "permit_credential_access",
):
    INVALID.extend((field, bad) for bad in (None, True, 0, "false", [], {}))
INVALID.extend(
    ("permitted_action_kinds", bad)
    for bad in (
        None,
        {},
        [],
        [[]],
        [{}],
        [None],
        ["WRITE_DOCUMENTATION_FILE", "WRITE_DOCUMENTATION_FILE"],
        ["EXECUTE_ARBITRARY_COMMAND"],
    )
)
INVALID.extend(
    ("admitted_paths", bad)
    for bad in (
        None,
        {},
        [],
        [None],
        ["/outside"],
        ["../outside"],
        ["docs", "docs"],
        ["docs//nested"],
        ["docs/./nested"],
    )
)
INVALID.extend(("rollback_policy", bad) for bad in (None, False, 0, [], {}, "UNRESTRICTED"))
INVALID.extend(
    ("validity_window", bad)
    for bad in (
        None,
        [],
        {},
        {"issued_at": "malformed", "expires_at": "2026-09-12T00:00:00Z"},
        {"issued_at": "2026-09-12T00:00:00Z", "expires_at": "2026-09-10T00:00:00Z"},
        {"issued_at": "2026-09-10T00:00:00", "expires_at": "2026-09-12T00:00:00Z"},
    )
)


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    checkout = git_worktree(tmp_path_factory.mktemp("execution-boundary"))
    candidate = execution_boundary_for(worktree_root=str(checkout))
    assert validate_execution_boundary(candidate) == candidate
    return candidate


@pytest.mark.parametrize("field,bad", INVALID)
def test_malformed_policy_has_a_typed_refusal(baseline, field, bad):
    candidate = deepcopy(baseline)
    candidate[field] = bad
    with pytest.raises(ExecutionBoundaryError):
        validate_execution_boundary(candidate)
