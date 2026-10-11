"""Share one real Gate 22 rerun between assertions about the same clean commit.

This is a test-session receipt, not a production acceptance cache. Each consumer
rechecks the live repository binding and receives its own deep copy. The canonical
rederivation test still executes every owning suite through the real subprocesses.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from manosube_agent_civilization.v1_0_acceptance.commit_binding import (
    verify_repo_root_bound_to_commit,
    verify_repository_project_binding,
)
from manosube_agent_civilization.v1_0_acceptance.engine import build_v1_0_acceptance_bundle

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def _real_v1_0_bundle_once() -> dict[str, Any]:
    return build_v1_0_acceptance_bundle(
        REPO_ROOT,
        authorized_base_main_sha="b2a5d287113d3a98e77a2212f8b89359d8e09c5d",
        delivery_head="HEAD",
        release_version_label="v1.0-candidate",
    )


@pytest.fixture
def real_v1_0_acceptance_bundle(
    _real_v1_0_bundle_once: dict[str, Any],
) -> dict[str, Any]:
    verify_repository_project_binding(REPO_ROOT)
    verify_repo_root_bound_to_commit(REPO_ROOT, _real_v1_0_bundle_once["delivery_head"])
    return deepcopy(_real_v1_0_bundle_once)
