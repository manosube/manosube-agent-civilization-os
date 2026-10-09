"""Genesis uses the real Binding/Store, with no implicit execution grant."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.cli.initialize import initialize_project
from manosube_agent_civilization.cli.errors import CLIArgumentError
from manosube_agent_civilization.store import FileStateStore


@pytest.mark.skipif(os.name != "posix", reason="real Store requires POSIX flock/fsync")
def test_explicit_genesis_can_be_restored_by_the_real_boot(tmp_path: Path) -> None:
    from manosube_agent_civilization.boot import boot_project

    manifest = tmp_path / "manifest.json"
    binding = bind_project_kwargs()
    manifest.write_text(
        json.dumps({"binding": binding, "additional_genesis_records": genesis_records()})
    )
    root = tmp_path / "backend"
    result = initialize_project(store_root=root, schema_root=SCHEMA_ROOT, manifest_path=manifest)
    store = FileStateStore(root, schema_root=SCHEMA_ROOT)
    context = boot_project(
        store, project_id=result["project_id"], project_binding_id=result["project_binding_id"]
    )
    assert context.current_state["state_revision"] == 0
    assert context.authority_rule["action_kinds"] == ["READ_ONLY_QUERY"]


@pytest.mark.parametrize(
    "body", ["{}", '{"binding":{},"binding":{},"additional_genesis_records":[]}']
)
def test_bad_manifest_does_not_create_store(tmp_path: Path, body: str) -> None:
    manifest = tmp_path / "bad.json"
    manifest.write_text(body)
    root = tmp_path / "backend"
    with pytest.raises(CLIArgumentError):
        initialize_project(store_root=root, schema_root=SCHEMA_ROOT, manifest_path=manifest)
    assert not root.exists()
