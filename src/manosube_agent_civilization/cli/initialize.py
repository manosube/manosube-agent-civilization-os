"""Explicit genesis manifest adapter; Binding remains the only genesis owner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore

from .errors import CLIArgumentError


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CLIArgumentError(f"duplicate manifest key: {key}")
        result[key] = value
    return result


def initialize_project(
    *, store_root: Path, schema_root: Path, manifest_path: Path
) -> dict[str, Any]:
    """Validate explicit input and delegate atomic initialization to bind_project."""
    if manifest_path.stat().st_size > 1_048_576:
        raise CLIArgumentError("genesis manifest exceeds 1 MiB")
    with manifest_path.open("rb") as stream:
        raw = stream.read(1_048_577)
    if len(raw) > 1_048_576:
        raise CLIArgumentError("genesis manifest exceeds 1 MiB")
    try:
        manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CLIArgumentError("genesis manifest must be valid UTF-8 JSON") from exc
    if type(manifest) is not dict or set(manifest) != {"binding", "additional_genesis_records"}:
        raise CLIArgumentError("manifest requires exactly binding and additional_genesis_records")
    binding = manifest["binding"]
    required = {
        "project_id",
        "objective_revision",
        "boundary",
        "authority_policy_ref",
        "authority_rule",
        "source_registrations",
        "command_policy",
        "secret_exclusion_policy",
        "human_authority_ref",
        "human_authority_signing_key",
        "bound_at",
        "genesis_state",
    }
    if type(binding) is not dict or set(binding) != required:
        raise CLIArgumentError("binding fields do not match the explicit genesis contract")
    records = manifest["additional_genesis_records"]
    if type(records) is not list or any(
        type(item) is not list or len(item) != 3 for item in records
    ):
        raise CLIArgumentError("additional_genesis_records must contain [kind, id, body] triples")
    if not schema_root.is_dir():
        raise CLIArgumentError("schema root must be an existing directory")
    store = FileStateStore(store_root, schema_root=schema_root)
    result = bind_project(
        store,
        **binding,
        additional_genesis_records=records,
        schema_root=schema_root,
    )
    return {
        "project_id": binding["project_id"],
        "project_binding_id": result["project_binding_id"],
        "state_revision": result["committed_state"]["state_revision"],
        "store_root": str(store.root),
    }
