"""The one canonical Product Binding engine (Phase 9, Issue #43).

``assemble_project_binding`` is the single place a declared Project Binding is validated,
cross-checked, and content-addressed. It never touches the Store -- :mod:`.route` is the
one place this engine's output is atomically persisted, alongside genesis State, through
the existing, generic :class:`~manosube_agent_civilization.store.file_store.FileStateStore`.

Reused rather than restated: the repo-wide secret scan and moving-reference rejection
already owned by :mod:`manosube_agent_civilization.difference.canonical`
(``PRODUCT_BINDING_OWNER_COUNT=1`` does not mean this engine reinvents primitives another
domain already proved).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manosube_agent_civilization.difference.canonical import (
    reject_secret_material,
    walk_references,
)

from .errors import BindingValidationError
from .identity import project_binding_id, verify_project_binding_identity
from .validation import validate_record


def _reject_unsafe_relative_path(path: str, context: str) -> None:
    """Fail closed on an absolute path, a home-relative path, a drive letter, a UNC path,
    or any ``..`` traversal segment -- Issue #43 §4.5/required negative controls."""

    if path.startswith(("/", "~")):
        raise BindingValidationError(
            f"{context}: absolute or home-relative path not permitted: {path!r}"
        )
    if path.startswith("\\\\"):
        raise BindingValidationError(f"{context}: UNC path not permitted: {path!r}")
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        raise BindingValidationError(f"{context}: drive-letter path not permitted: {path!r}")
    segments = path.replace("\\", "/").split("/")
    if any(segment == ".." for segment in segments):
        raise BindingValidationError(f"{context}: path traversal segment not permitted: {path!r}")


def _is_within_any_root(locator: str, root_paths: list[str]) -> bool:
    """Return whether *locator* falls within (or equals) one of *root_paths*, by path
    segment, never by bare string prefix -- ``root/foo`` must not match ``root/foobar``."""

    locator_segments = tuple(
        segment for segment in locator.replace("\\", "/").split("/") if segment
    )
    for root in root_paths:
        root_segments = tuple(segment for segment in root.replace("\\", "/").split("/") if segment)
        if locator_segments[: len(root_segments)] == root_segments:
            return True
    return False


def _reject_conflicting_patterns(include: list[str], exclude: list[str], context: str) -> None:
    overlap = sorted(set(include) & set(exclude))
    if overlap:
        raise BindingValidationError(
            f"{context}: conflicting include/exclude pattern(s): {overlap}"
        )


def _reject_duplicate_registrations(registrations: list[dict[str, Any]]) -> None:
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for registration in registrations:
        source_id = registration["source_id"]
        pair = (registration["source_type"], registration["locator"])
        if source_id in seen_ids:
            raise BindingValidationError(f"duplicate source_registration source_id: {source_id}")
        if pair in seen_pairs:
            raise BindingValidationError(
                f"duplicate source_registration (source_type, locator): {pair}"
            )
        seen_ids.add(source_id)
        seen_pairs.add(pair)


def assemble_project_binding(
    *,
    project_id: str,
    objective_revision_ref: dict[str, Any],
    boundary: dict[str, Any],
    authority_policy_ref: dict[str, Any],
    source_registrations: list[dict[str, Any]],
    command_policy: dict[str, Any],
    secret_exclusion_policy: dict[str, Any],
    human_authority_ref: dict[str, Any],
    bound_at: str,
    schema_root: Path | None = None,
) -> dict[str, Any]:
    """Validate a declared Project Binding, cross-check its embedded structures, mint and
    reverify its content-addressed identity, and return the full, schema-valid record.

    Never touches the Store. Raises :class:`~.errors.BindingValidationError` or
    :class:`~.errors.BindingIdentityError` before returning anything a caller could persist.
    """

    # 1. Validate each embedded structure against its own schema first, independently --
    #    a caller's malformed Boundary, Source Registration, or Command Policy is refused
    #    here with a precise field-level message, before any cross-field reasoning runs.
    validate_record(boundary, "boundary.schema.json", schema_root=schema_root)
    for registration in source_registrations:
        validate_record(registration, "source_registration.schema.json", schema_root=schema_root)
    validate_record(command_policy, "command_policy.schema.json", schema_root=schema_root)

    # 2. Boundary structural checks -- fail closed on escape, never a filesystem read.
    for root in boundary["root_paths"]:
        _reject_unsafe_relative_path(root, "boundary.root_paths")
    _reject_conflicting_patterns(
        boundary["include_patterns"], boundary["exclude_patterns"], "boundary"
    )

    # 3. Source Registration structural checks -- declares trust, never observes.
    _reject_duplicate_registrations(source_registrations)
    for registration in source_registrations:
        source_id = registration["source_id"]
        _reject_unsafe_relative_path(
            registration["locator"], f"source_registration {source_id}.locator"
        )
        if not _is_within_any_root(registration["locator"], boundary["root_paths"]):
            raise BindingValidationError(
                f"source_registration {source_id} locator is outside the declared boundary: "
                f"{registration['locator']!r}"
            )
        _reject_conflicting_patterns(
            registration["include_patterns"],
            registration["exclude_patterns"],
            f"source_registration {source_id}",
        )

    record: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "objective_revision_ref": objective_revision_ref,
        "boundary": boundary,
        "authority_policy_ref": authority_policy_ref,
        "source_registrations": source_registrations,
        "command_policy": command_policy,
        "secret_exclusion_policy": secret_exclusion_policy,
        "human_authority_ref": human_authority_ref,
    }

    # 4. Secret-value and moving-reference scan over the whole accepted declaration, before
    #    any identity is minted or anything is persisted. `secret_exclusion_policy` itself is
    #    excluded from the scan: its own schema already forecloses any actual secret value
    #    (only field-name strings and a closed reference-kind enum are accepted there), and
    #    its own field names (`allowed_secret_reference_kinds`, ...) would otherwise trip the
    #    repo-wide secret-*key*-name pattern by simply naming the concept they forbid.
    scan_target = {key: value for key, value in record.items() if key != "secret_exclusion_policy"}
    reject_secret_material(scan_target, "project_binding")
    walk_references(scan_target, "project_binding")

    # 5. Mint the content-addressed identity, assemble the full record, and reverify.
    record["project_binding_id"] = project_binding_id(record)
    record["bound_at"] = bound_at
    verify_project_binding_identity(record)

    # 6. Validate the fully assembled record against its own top-level schema.
    validate_record(record, "project_binding.schema.json", schema_root=schema_root)

    return record
