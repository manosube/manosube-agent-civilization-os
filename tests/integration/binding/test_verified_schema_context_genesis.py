"""Issue #75 (``D-KERNEL-VERIFIED-SCHEMA-BYTE-INJECTION``) KSI-C2/C3/C6/C7: one real Product
Binding genesis transaction, end to end, through the public verified-byte route.

``tests/contract/schema_context/test_canonical_schema_context.py`` proves the context's own
properties. This module proves the vertical claim: that a caller who captures and
digest-verifies the canonical schema bytes *once* gets those exact bytes performing every
schema validation in a whole ``bind_project`` genesis transaction -- Objective Revision and
Authority Rule admission, the Project Binding engine's embedded structures, genesis State
canonicalization and fingerprinting, the shared pre-commit admission's Source Snapshot
reverification through Observation's own owner, and ``FileStateStore``'s own State, event and
genesis-receipt validation -- with no filesystem read of any schema after capture, and with no
way to substitute or redirect that context afterwards::

    ONE_VALIDATION_CONTEXT_USED_END_TO_END = true
    SCHEMA_FILESYSTEM_READ_COUNT_AFTER_CONTEXT_CONSTRUCTION = 0
    INVALID_RECORD_ACCEPTED_AFTER_SCHEMA_SWAP = false
    INVALID_SOURCE_SNAPSHOT_ACCEPTED_AFTER_SCHEMA_SWAP = false
    STORE_WRITE_COUNT_AFTER_REFUSAL = 0
    VALID_BINDING_AND_GENESIS_COMMIT = true
    BINDING_REPLAY_IDEMPOTENT = true

Every "still rejected after the schema was swapped" proof below is paired with a positive
control (a context captured *after* the identical weakening, which does accept the identical
record), so no refusal here can be an artefact of a fixture that was never really invalid or
a weakening that never really landed.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import pkgutil
import shutil
from typing import Any

import pytest
from tests.fixtures.product_binding import PROJECT_ID, bind_project_kwargs
from tests.state_helpers import SCHEMA_ROOT, real_kernel_git_objects

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.binding.errors import BindingValidationError
from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot
from manosube_agent_civilization.schema_context import (
    CANONICAL_SCHEMA_SUFFIX,
    CanonicalSchemaContext,
    SchemaContextError,
    capture_canonical_schema_bytes,
    schema_set_digest,
)
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import BoundaryError

pytestmark = [pytest.mark.integration, pytest.mark.security]

OBJECTIVE_REVISION_RELATIVE_PATH = "objective/objective_revision.schema.json"
OBJECTIVE_REVISION_SCHEMA_ID = "https://schemas.manosube.org/agent-civilization-os/v0.1/objective/objective_revision.schema.json"
SOURCE_SNAPSHOT_RELATIVE_PATH = "observation/source_snapshot.schema.json"


# --- real fixture material ------------------------------------------------------------------ #


def _kernel_source_snapshot(
    *, schema_context: CanonicalSchemaContext | None = None
) -> dict[str, Any]:
    """The identical real Kernel Source Snapshot ``tests/state_helpers.py`` mints, produced
    here through Observation's own producer with an explicit validation context.

    Only the ``build_source_snapshot`` call differs from the shared helper: the Git object
    witness, the pinned ``KERNEL_INVARIANTS.md`` bytes, and the captured-at instant are all
    reused from :func:`tests.state_helpers.real_kernel_git_objects`, so this cannot drift from
    the snapshot id every genesis fixture in this repository already references.
    """

    from tests.state_helpers import ROOT

    from manosube_agent_civilization.reflow.git_witness import blob_sha1
    from manosube_agent_civilization.reflow.invariant_registry import KERNEL_INVARIANTS_PATH

    kernel_source_ref, _ = real_kernel_git_objects()
    blob_content = (ROOT / KERNEL_INVARIANTS_PATH).read_bytes()
    return build_source_snapshot(
        source_locator=KERNEL_INVARIANTS_PATH,
        content_digest="sha256:" + hashlib.sha256(blob_content).hexdigest(),
        captured_at="2026-08-29T09:00:00Z",
        git_provenance={
            "repository": kernel_source_ref["repository"],
            "commit_sha": kernel_source_ref["commit_sha"],
            "tree_sha": kernel_source_ref["tree_sha"],
            "path": KERNEL_INVARIANTS_PATH,
            "blob_sha": blob_sha1(blob_content),
        },
        schema_context=schema_context,
    )


def _genesis_records(
    *, schema_context: CanonicalSchemaContext | None = None, snapshot: dict[str, Any] | None = None
) -> list[tuple[str, str, dict[str, Any]]]:
    body = (
        snapshot if snapshot is not None else _kernel_source_snapshot(schema_context=schema_context)
    )
    return [("source_snapshot", body["source_snapshot_id"], body)]


def _mutable_schema_root(tmp_path: Path) -> Path:
    destination = tmp_path / "01_SCHEMA"
    shutil.copytree(SCHEMA_ROOT, destination)
    return destination


def _verified_from_schema_root(root: Path) -> CanonicalSchemaContext:
    """A context adopted from *root* with its own captured bytes' digest passed back in as
    ``expected_digest`` -- enough to satisfy the mandatory ``verified`` gate
    :class:`FileStateStore` and :func:`bind_project` both enforce (Issue #75, P79-R1-F2) for
    every test in this module that needs the context to actually reach a Store or a genesis
    transaction. This is *not* an independently adopted expectation in the sense P79-R1-F2
    itself requires of a real caller (whose ``expected_digest`` must come from outside the
    capture being checked) -- it only satisfies the mechanical gate so this module can go on
    proving what it already proves about the whole-transaction route."""

    captured = capture_canonical_schema_bytes(root)
    return CanonicalSchemaContext(captured, expected_digest=schema_set_digest(captured))


def _verified(captured: dict[str, bytes]) -> CanonicalSchemaContext:
    """As :func:`_verified_from_schema_root`, for an already-captured mapping."""

    return CanonicalSchemaContext(captured, expected_digest=schema_set_digest(captured))


def _replace_with_anything_goes(root: Path, relative_path: str) -> None:
    """Overwrite one canonical schema with a same-``$id`` document that accepts anything --
    the real, minimal swap every "after schema swap" proof below depends on."""

    path = root / relative_path
    document = json.loads(path.read_bytes())
    path.write_bytes(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": document["$id"],
                "type": "object",
            }
        ).encode("utf-8")
    )


def _weaken_source_snapshot_schema_version(root: Path) -> None:
    """Relax only the Source Snapshot ``schema_version`` ``const`` -- everything else about
    the canonical schema, its ``$id`` and its ``$ref``s included, is left intact."""

    path = root / SOURCE_SNAPSHOT_RELATIVE_PATH
    document = json.loads(path.read_bytes())
    document["properties"]["schema_version"] = {"type": "string"}
    path.write_bytes(json.dumps(document).encode("utf-8"))


def _schema_invalid_objective_revision() -> dict[str, Any]:
    """A real Objective Revision carrying one field its own schema's
    ``unevaluatedProperties: false`` forbids. Nothing else about it changes, so every
    cross-check ``bind_project`` performs still passes: only the schema can reject it."""

    revision: dict[str, Any] = deepcopy(bind_project_kwargs()["objective_revision"])
    revision["a_field_no_canonical_schema_declares"] = "definitely not in the schema"
    return revision


def _schema_invalid_source_snapshot() -> dict[str, Any]:
    """A real Source Snapshot with a ``schema_version`` its own schema's ``const`` forbids.

    ``schema_version`` is outside the record's own content-addressed identity payload, so the
    body still recomputes its own ``source_snapshot_id`` and still closes the genesis State's
    own ``source_snapshot_refs``: schema validation is the only thing standing between this
    body and the Store.
    """

    body = dict(_kernel_source_snapshot())
    body["schema_version"] = "0.2"
    return body


def _schema_read_recorder(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Instrument ``Path.read_text``/``Path.read_bytes`` and return the live list of every
    canonical schema file read from this point on."""

    reads: list[str] = []
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes

    def read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if str(self).endswith(CANONICAL_SCHEMA_SUFFIX):
            reads.append(str(self))
        return original_read_text(self, *args, **kwargs)

    def read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if str(self).endswith(CANONICAL_SCHEMA_SUFFIX):
            reads.append(str(self))
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    return reads


def _store_write_recorder(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Instrument the Store's own one write primitive and return the live list of every
    durable write it performs from this point on."""

    from manosube_agent_civilization.store import file_store as file_store_module
    from manosube_agent_civilization.store.atomic_write import atomic_write

    writes: list[str] = []

    def recording_atomic_write(path: Path, payload: bytes) -> None:
        writes.append(str(path))
        atomic_write(path, payload)

    monkeypatch.setattr(file_store_module, "atomic_write", recording_atomic_write)
    return writes


# --- KSI-C7: the whole transaction, measured ------------------------------------------------ #


def test_a_whole_genesis_transaction_reads_no_schema_file_after_context_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``SCHEMA_FILESYSTEM_READ_COUNT_AFTER_CONTEXT_CONSTRUCTION=0`` (adversarial matrix item
    8), measured rather than asserted: every ``Path.read_text``/``read_bytes`` of a
    ``*.schema.json`` is recorded from the instant the context exists, across Source Snapshot
    production, the full ``bind_project`` genesis transaction, an identical replay, a fresh
    ``FileStateStore`` over the same backend, and a full lineage reconstruction."""

    captured = capture_canonical_schema_bytes(SCHEMA_ROOT)
    context = CanonicalSchemaContext(captured, expected_digest=schema_set_digest(captured))

    # The declaration bodies are ordinary caller-supplied data, assembled before the counter
    # is installed: `tests.fixtures.product_binding` mints its own genesis Source Snapshot
    # through the *default* registry, which is exactly the pre-capture filesystem read this
    # Difference never claimed to remove. What is measured below is the transaction.
    kwargs = bind_project_kwargs()
    replay_kwargs = bind_project_kwargs()

    reads = _schema_read_recorder(monkeypatch)

    snapshot = _kernel_source_snapshot(schema_context=context)
    records = _genesis_records(snapshot=snapshot)
    store = FileStateStore(tmp_path / "backend", schema_context=context)
    result = bind_project(
        store,
        **kwargs,
        additional_genesis_records=records,
        schema_context=context,
    )
    replay = bind_project(
        store,
        **replay_kwargs,
        additional_genesis_records=records,
        schema_context=context,
    )
    fresh = FileStateStore(store.root, schema_context=context)
    reconstructed = fresh.reconstruct(PROJECT_ID)

    assert reads == []
    assert result["committed_state"]["state_revision"] == 0
    assert replay["committed_state"] == result["committed_state"]
    assert replay["project_binding_id"] == result["project_binding_id"]
    assert reconstructed == fresh.load_current(PROJECT_ID)
    assert (
        fresh.resolve_record(PROJECT_ID, "project_binding", result["project_binding_id"])
        == result["project_binding"]
    )
    assert fresh.resolve_record(PROJECT_ID, "source_snapshot", snapshot["source_snapshot_id"]) == (
        snapshot
    )


def test_exactly_one_validation_context_object_performs_every_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ONE_VALIDATION_CONTEXT_USED_END_TO_END=true``, proved by recording the identity of
    the object every single validation in the transaction actually ran against -- never by
    trusting that two registries happened to agree."""

    context = _verified_from_schema_root(SCHEMA_ROOT)
    seen: list[int] = []
    original = CanonicalSchemaContext.validation_errors

    def recording_validation_errors(
        self: CanonicalSchemaContext, instance: Any, schema_id: str
    ) -> list[Any]:
        seen.append(id(self))
        return original(self, instance, schema_id)

    monkeypatch.setattr(CanonicalSchemaContext, "validation_errors", recording_validation_errors)

    store = FileStateStore(tmp_path / "backend", schema_context=context)
    bind_project(
        store,
        **bind_project_kwargs(),
        additional_genesis_records=_genesis_records(schema_context=context),
        schema_context=context,
    )

    assert seen, "the transaction performed no validation at all -- the proof would be vacuous"
    assert set(seen) == {id(context)}
    assert store.schema_context is context
    assert store.schema_root is None


def test_the_verified_byte_route_commits_exactly_what_the_schema_root_route_commits(
    tmp_path: Path,
) -> None:
    """Existing default behaviour is untouched: the two routes are byte-identical in what
    they mint and commit, so adopting verified-byte injection changes no identity, no
    fingerprint, and no committed body (``IDENTITY_ALGORITHM_CHANGE=false``,
    ``STATE_FINGERPRINT_CHANGE=false``, ``BINDING_ID_CHANGE=false``)."""

    context = _verified_from_schema_root(SCHEMA_ROOT)
    records = _genesis_records(schema_context=context)

    secure_store = FileStateStore(tmp_path / "secure", schema_context=context)
    secure = bind_project(
        secure_store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_context=context,
    )

    default_store = FileStateStore(tmp_path / "default", schema_root=SCHEMA_ROOT)
    default = bind_project(
        default_store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_root=SCHEMA_ROOT,
    )

    assert secure == default


# --- P79-R1-F1: no internal schema reference escapes a real bind_project transaction -------- #


def test_mutating_a_returned_validation_errors_schema_cannot_reopen_a_verified_context(
    tmp_path: Path,
) -> None:
    """P79-R1-F1 -- the independently reproduced counterexample, at real ``bind_project``
    scale: flipping a returned :class:`jsonschema.ValidationError`'s own
    ``.schema["unevaluatedProperties"]`` from ``False`` to ``True`` -- exactly the mutation the
    Structural Advisor's reproduction used to make a real ``bind_project`` genesis transaction
    incorrectly commit a schema-invalid Objective Revision -- must not change any later
    validation outcome this same context reports, nor any later genesis transaction it
    performs."""

    context = _verified_from_schema_root(SCHEMA_ROOT)
    invalid = _schema_invalid_objective_revision()

    first_errors = context.validation_errors(invalid, OBJECTIVE_REVISION_SCHEMA_ID)
    assert first_errors
    mutated_any = False
    for error in first_errors:
        if isinstance(error.schema, dict) and "unevaluatedProperties" in error.schema:
            error.schema["unevaluatedProperties"] = True
            mutated_any = True
    assert mutated_any, "the counterexample's own mutation target was not reached"

    # The same context, revalidating the identical invalid body, still refuses it.
    assert context.validation_errors(invalid, OBJECTIVE_REVISION_SCHEMA_ID)

    kwargs = bind_project_kwargs()
    kwargs["objective_revision"] = invalid
    store = FileStateStore(tmp_path / "backend", schema_context=context)
    with pytest.raises(BindingValidationError, match="schema-invalid"):
        bind_project(
            store,
            **kwargs,
            additional_genesis_records=_genesis_records(schema_context=context),
            schema_context=context,
        )
    assert not (store.root / "projects").exists()

    # The same context, immediately afterwards, still admits the real transaction.
    recovered = bind_project(
        store,
        **bind_project_kwargs(),
        additional_genesis_records=_genesis_records(schema_context=context),
        schema_context=context,
    )
    assert recovered["committed_state"]["state_revision"] == 0


# --- P79-R1-F2: an unverified context can never reach a Store or a genesis transaction ------ #


def test_an_unverified_context_is_refused_by_the_store_constructor(tmp_path: Path) -> None:
    """P79-R1-F2: a context built with no adopted ``expected_digest`` at all -- one whose own
    ``verified`` is ``False`` -- must never reach a Store, even one that would otherwise
    validate against real, byte-identical canonical schemas."""

    unverified = CanonicalSchemaContext.from_schema_root(SCHEMA_ROOT)
    assert unverified.verified is False
    with pytest.raises(BoundaryError, match="unverified validation context"):
        FileStateStore(tmp_path / "backend", schema_context=unverified)


def test_an_unverified_context_is_refused_by_bind_project_even_if_the_store_already_holds_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defence in depth for P79-R1-F2: ``FileStateStore`` does not freeze its own
    ``schema_context`` attribute, so this proves ``bind_project`` itself also refuses an
    unverified context rather than relying solely on the Store constructor's own gate."""

    context = _verified_from_schema_root(SCHEMA_ROOT)
    store = FileStateStore(tmp_path / "backend", schema_context=context)

    unverified = CanonicalSchemaContext.from_schema_root(SCHEMA_ROOT)
    assert unverified.verified is False
    store.schema_context = unverified  # simulate the one residual reassignment gap

    writes = _store_write_recorder(monkeypatch)
    with pytest.raises(BindingValidationError, match="unverified validation context"):
        bind_project(
            store,
            **bind_project_kwargs(),
            additional_genesis_records=_genesis_records(schema_context=unverified),
            schema_context=unverified,
        )
    assert writes == []
    assert not (store.root / "projects").exists()


# --- adversarial matrix items 1, 2, 3 and 9: mutate the root after capture ------------------ #


def test_a_valid_transaction_stays_byte_identical_after_the_original_root_is_destroyed(
    tmp_path: Path,
) -> None:
    """Adversarial matrix item 1. The canonical tree is captured, then weakened *and* deleted
    outright; the transaction still commits, and commits exactly what a pristine run
    commits."""

    root = _mutable_schema_root(tmp_path)
    context = _verified_from_schema_root(root)
    records = _genesis_records(schema_context=context)

    control_store = FileStateStore(tmp_path / "control", schema_context=context)
    control = bind_project(
        control_store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_context=context,
    )

    _replace_with_anything_goes(root, OBJECTIVE_REVISION_RELATIVE_PATH)
    shutil.rmtree(root)
    assert not root.exists()

    store = FileStateStore(tmp_path / "after", schema_context=context)
    after = bind_project(
        store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_context=context,
    )
    assert after == control


def test_an_invalid_objective_revision_stays_rejected_after_the_schema_is_swapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adversarial matrix item 2 -- ``INVALID_RECORD_ACCEPTED_AFTER_SCHEMA_SWAP=false`` -- with
    its own positive control (item 9) proving the swap really would have let it through."""

    root = _mutable_schema_root(tmp_path)
    context = _verified_from_schema_root(root)
    records = _genesis_records(schema_context=context)
    invalid = _schema_invalid_objective_revision()

    _replace_with_anything_goes(root, OBJECTIVE_REVISION_RELATIVE_PATH)

    kwargs = bind_project_kwargs()
    kwargs["objective_revision"] = invalid
    store = FileStateStore(tmp_path / "after", schema_context=context)
    writes = _store_write_recorder(monkeypatch)
    with pytest.raises(BindingValidationError, match="schema-invalid"):
        bind_project(store, **kwargs, additional_genesis_records=records, schema_context=context)
    assert writes == []
    assert not (store.root / "projects").exists()

    # Positive control: a context captured from the *swapped* root accepts the very same
    # body and commits it -- the earlier refusal is therefore non-vacuous, and the swap was
    # real.
    swapped = _verified_from_schema_root(root)
    assert swapped.digest != context.digest
    permissive_store = FileStateStore(tmp_path / "permissive", schema_context=swapped)
    accepted = bind_project(
        permissive_store,
        **kwargs,
        additional_genesis_records=_genesis_records(schema_context=swapped),
        schema_context=swapped,
    )
    assert accepted["objective_revision"] == invalid


def test_an_invalid_source_snapshot_stays_rejected_by_real_admission_after_the_schema_is_swapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adversarial matrix item 3 -- ``INVALID_SOURCE_SNAPSHOT_ACCEPTED_AFTER_SCHEMA_SWAP=
    false``.

    This is the seam the whole Difference exists for: ``binding.admission.
    _verify_source_snapshot_body`` previously reached Observation's zero-argument, reloadable
    registry directly, with no ``schema_root`` plumbed through from ``bind_project`` at all,
    so no caller could redirect it. The rejection below is produced by the real
    ``admit_genesis_transaction`` inside a real ``bind_project`` call, not by calling the
    verifier directly.
    """

    root = _mutable_schema_root(tmp_path)
    context = _verified_from_schema_root(root)
    invalid_snapshot = _schema_invalid_source_snapshot()
    records = _genesis_records(snapshot=invalid_snapshot)

    _weaken_source_snapshot_schema_version(root)

    store = FileStateStore(tmp_path / "after", schema_context=context)
    writes = _store_write_recorder(monkeypatch)
    with pytest.raises(BindingValidationError, match=r"source_snapshot.*schema-invalid"):
        bind_project(
            store,
            **bind_project_kwargs(),
            additional_genesis_records=records,
            schema_context=context,
        )
    assert writes == []
    assert not (store.root / "projects").exists()

    # Positive control: the weakened Source Snapshot schema genuinely accepts this body.
    swapped = _verified_from_schema_root(root)
    assert swapped.digest != context.digest
    permissive_store = FileStateStore(tmp_path / "permissive", schema_context=swapped)
    accepted = bind_project(
        permissive_store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_context=swapped,
    )
    assert accepted["committed_state"]["state_revision"] == 0
    assert (
        permissive_store.resolve_record(
            PROJECT_ID, "source_snapshot", invalid_snapshot["source_snapshot_id"]
        )
        == invalid_snapshot
    )


# --- adversarial matrix item 4: the legacy cache cannot redirect the secure route ----------- #


def test_clearing_the_legacy_zero_argument_registry_cannot_redirect_the_secure_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adversarial matrix item 4.

    ``observation.schemas.validators`` is an ``lru_cache(maxsize=1)`` whose public
    ``cache_clear()`` forces the next call to re-read the whole canonical tree from disk. The
    secure route's own read counter therefore doubles as the proof: if anything in the
    transaction still reached that registry, a cache cleared immediately beforehand would
    have produced one filesystem read per canonical schema. It produces none.
    """

    from manosube_agent_civilization.observation.schemas import validators

    context = _verified_from_schema_root(SCHEMA_ROOT)
    snapshot = _kernel_source_snapshot(schema_context=context)
    kwargs = bind_project_kwargs()

    validators.cache_clear()
    reads = _schema_read_recorder(monkeypatch)
    store = FileStateStore(tmp_path / "backend", schema_context=context)
    result = bind_project(
        store,
        **kwargs,
        additional_genesis_records=_genesis_records(snapshot=snapshot),
        schema_context=context,
    )

    assert reads == []
    assert result["committed_state"]["state_revision"] == 0


# --- adversarial matrix item 5: caller-side mutation after construction --------------------- #


def test_mutating_the_caller_mapping_after_construction_cannot_change_the_transaction(
    tmp_path: Path,
) -> None:
    """Adversarial matrix item 5, at transaction scale: the capture mapping (and the nested
    bytes in it) is rewritten between context construction and ``bind_project``; the
    committed result is byte-identical to a run where it was never touched."""

    captured = capture_canonical_schema_bytes(SCHEMA_ROOT)
    context = _verified(captured)
    records = _genesis_records(schema_context=context)

    control_store = FileStateStore(tmp_path / "control", schema_context=context)
    control = bind_project(
        control_store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_context=context,
    )

    captured[OBJECTIVE_REVISION_RELATIVE_PATH] = b'{"$id": "https://example.invalid/swapped"}'
    del captured[SOURCE_SNAPSHOT_RELATIVE_PATH]
    captured["observation/injected.schema.json"] = b'{"$id": "https://example.invalid/injected"}'

    store = FileStateStore(tmp_path / "after", schema_context=context)
    after = bind_project(
        store,
        **bind_project_kwargs(),
        additional_genesis_records=records,
        schema_context=context,
    )
    assert after == control

    kwargs = bind_project_kwargs()
    kwargs["objective_revision"] = _schema_invalid_objective_revision()
    refusing_store = FileStateStore(tmp_path / "refusing", schema_context=context)
    with pytest.raises(BindingValidationError, match="schema-invalid"):
        bind_project(
            refusing_store, **kwargs, additional_genesis_records=records, schema_context=context
        )


# --- adversarial matrix item 6: context substitution before Store construction -------------- #


def test_a_substituted_context_is_refused_before_any_validation_or_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adversarial matrix item 6, ``POST_SCHEMA_VERIFY_PRE_VALIDATION_SUBSTITUTION_ACCEPT_
    COUNT=0``: a second context -- even one built from byte-identical captures, even one built
    from a weakened capture -- is refused the moment it disagrees with the object the Store
    itself was constructed with."""

    verified = _verified_from_schema_root(SCHEMA_ROOT)
    substituted = _verified_from_schema_root(SCHEMA_ROOT)
    assert substituted.digest == verified.digest
    assert substituted is not verified

    store = FileStateStore(tmp_path / "backend", schema_context=verified)
    writes = _store_write_recorder(monkeypatch)
    with pytest.raises(BindingValidationError, match="ONE_VALIDATION_CONTEXT_USED_END_TO_END"):
        bind_project(
            store,
            **bind_project_kwargs(),
            additional_genesis_records=_genesis_records(schema_context=verified),
            schema_context=substituted,
        )
    assert writes == []
    assert not (store.root / "projects").exists()


def test_a_store_built_on_a_filesystem_root_refuses_the_verified_byte_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The secure route fails closed rather than falling back: a Store still reading a
    directory cannot be paired with a caller that has already pinned its bytes."""

    context = CanonicalSchemaContext.from_schema_root(SCHEMA_ROOT)
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    writes = _store_write_recorder(monkeypatch)
    with pytest.raises(BindingValidationError, match="the Store carries none"):
        bind_project(
            store,
            **bind_project_kwargs(),
            additional_genesis_records=_genesis_records(schema_context=context),
            schema_context=context,
        )
    assert writes == []
    assert not (store.root / "projects").exists()


def test_naming_both_a_schema_root_and_a_context_is_refused_everywhere(tmp_path: Path) -> None:
    """One schema source or the other, never both -- at the Store constructor and at the
    route, so a caller can never end up half-injected and half-reading a directory."""

    context = _verified_from_schema_root(SCHEMA_ROOT)

    with pytest.raises(BoundaryError, match="exactly one of"):
        FileStateStore(tmp_path / "both", schema_root=SCHEMA_ROOT, schema_context=context)
    with pytest.raises(BoundaryError, match="exactly one of"):
        FileStateStore(tmp_path / "neither")

    store = FileStateStore(tmp_path / "backend", schema_context=context)
    with pytest.raises(BindingValidationError, match="mutually exclusive"):
        bind_project(
            store,
            **bind_project_kwargs(),
            additional_genesis_records=_genesis_records(schema_context=context),
            schema_root=SCHEMA_ROOT,
            schema_context=context,
        )
    assert not (store.root / "projects").exists()


# --- adversarial matrix item 7: a tampered set never reaches a Store ------------------------ #


@pytest.mark.parametrize("tamper", ["remove", "add", "duplicate", "change", "change_id"])
def test_a_tampered_schema_set_is_refused_before_any_store_exists(
    tmp_path: Path, tamper: str
) -> None:
    """Adversarial matrix item 7: removing, adding, duplicating, byte-changing, or
    ``$id``-changing one schema is refused at context construction -- before a Store is ever
    built, therefore before any write is even possible."""

    root = _mutable_schema_root(tmp_path)
    adopted = schema_set_digest(capture_canonical_schema_bytes(root))
    source = root / SOURCE_SNAPSHOT_RELATIVE_PATH

    if tamper == "remove":
        source.unlink()
    elif tamper == "add":
        (root / "observation" / "extra.schema.json").write_bytes(source.read_bytes())
    elif tamper == "duplicate":
        (root / "observation" / "duplicate.schema.json").write_bytes(source.read_bytes())
    elif tamper == "change":
        _weaken_source_snapshot_schema_version(root)
    else:
        document = json.loads(source.read_bytes())
        document["$id"] = document["$id"].replace("source_snapshot", "source_snapshot_renamed")
        source.write_bytes(json.dumps(document).encode("utf-8"))

    with pytest.raises(SchemaContextError):
        CanonicalSchemaContext.from_schema_root(root, expected_digest=adopted)

    assert not (tmp_path / "backend").exists()


def test_a_duplicated_id_is_refused_even_with_no_pinned_digest(tmp_path: Path) -> None:
    """A caller who pins nothing is still protected from the one tamper that would otherwise
    silently drop a competing document: two captured paths claiming one ``$id``."""

    root = _mutable_schema_root(tmp_path)
    source = root / SOURCE_SNAPSHOT_RELATIVE_PATH
    (root / "observation" / "duplicate.schema.json").write_bytes(source.read_bytes())
    with pytest.raises(SchemaContextError, match="more than once"):
        CanonicalSchemaContext.from_schema_root(root)


# --- adversarial matrix item 10: every affected pre-commit seam leaves the Store unchanged -- #


def _kwargs_for_seam(seam: str) -> dict[str, Any]:
    kwargs = bind_project_kwargs()
    if seam == "objective_revision":
        kwargs["objective_revision"] = _schema_invalid_objective_revision()
    elif seam == "authority_rule":
        kwargs["authority_rule"] = deepcopy(kwargs["authority_rule"])
        kwargs["authority_rule"]["a_field_no_canonical_schema_declares"] = "x"
    elif seam == "boundary":
        kwargs["boundary"] = deepcopy(kwargs["boundary"])
        kwargs["boundary"]["a_field_no_canonical_schema_declares"] = "x"
    elif seam == "command_policy":
        kwargs["command_policy"] = deepcopy(kwargs["command_policy"])
        kwargs["command_policy"]["a_field_no_canonical_schema_declares"] = "x"
    elif seam == "genesis_state":
        kwargs["genesis_state"] = deepcopy(kwargs["genesis_state"])
        kwargs["genesis_state"]["a_field_no_canonical_schema_declares"] = "x"
    return kwargs


@pytest.mark.parametrize(
    "seam",
    [
        "objective_revision",
        "authority_rule",
        "boundary",
        "command_policy",
        "genesis_state",
        "source_snapshot",
    ],
)
def test_a_failure_at_any_affected_pre_commit_seam_leaves_the_store_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seam: str
) -> None:
    """Adversarial matrix item 10, over every validation seam this Difference threads the
    context through: the Objective Revision and Authority Rule admission checks, the Project
    Binding engine's own embedded-structure checks, genesis State canonicalization/
    fingerprinting, and the shared pre-commit admission's Source Snapshot reverification.
    ``STORE_WRITE_COUNT_AFTER_REFUSAL=0`` at every one of them."""

    context = _verified_from_schema_root(SCHEMA_ROOT)
    kwargs = _kwargs_for_seam(seam)
    if seam == "source_snapshot":
        records = _genesis_records(snapshot=_schema_invalid_source_snapshot())
    else:
        records = _genesis_records(schema_context=context)

    store = FileStateStore(tmp_path / "backend", schema_context=context)
    writes = _store_write_recorder(monkeypatch)
    with pytest.raises(ValueError, match="schema"):
        bind_project(store, **kwargs, additional_genesis_records=records, schema_context=context)

    assert writes == []
    assert not (store.root / "projects").exists()

    # The same Store, immediately afterwards, still admits the real transaction: the refusal
    # left nothing behind that a subsequent legitimate genesis has to work around.
    recovered = bind_project(
        store,
        **bind_project_kwargs(),
        additional_genesis_records=_genesis_records(schema_context=context),
        schema_context=context,
    )
    assert recovered["committed_state"]["state_revision"] == 0


# --- KSI-C3: Observation stays the Source Snapshot schema/identity owner -------------------- #


def _binding_module_sources() -> list[tuple[str, ast.Module]]:
    package = importlib.import_module("manosube_agent_civilization.binding")
    modules = [
        package,
        *(
            importlib.import_module(info.name)
            for info in pkgutil.walk_packages(
                package.__path__, prefix="manosube_agent_civilization.binding."
            )
        ),
    ]
    return [
        (module.__name__, ast.parse(inspect.getsource(module), filename=module.__name__))
        for module in modules
    ]


def test_binding_never_reimplements_observation_source_snapshot_validation() -> None:
    """``BINDING_INVENTED_OBSERVATION_VALIDATION=false`` / ``OBSERVATION_SCHEMA_OWNER_COUNT=1``
    (KSI-C3), by a real AST walk over every Binding module's own source rather than a grep.

    Three independent facts, each of which was false before this Difference:

    1. no Binding module imports Observation's schema *registry* at all -- Binding reaches
       Observation only through its public record owners;
    2. no Binding module names the Source Snapshot schema ``$id`` anywhere in its own source,
       so it cannot be resolving a validator of its own;
    3. no Binding module calls the zero-argument ``validators`` registry.
    """

    for module_name, tree in _binding_module_sources():
        imported: set[str] = set()
        called: set[str] = set()
        literals: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.add(node.func.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.add(node.value)

        assert not any("observation.schemas" in name for name in imported), module_name
        assert not any("source_snapshot.schema.json" in text for text in literals), module_name
        assert "validators" not in called, module_name


def test_exactly_one_module_owns_the_source_snapshot_schema_identity() -> None:
    """``SOURCE_SNAPSHOT_IDENTITY_OWNER_COUNT=1``: across the whole installed package, exactly
    one module names the canonical Source Snapshot schema ``$id`` as a validation target, and
    it is Observation's own Source Snapshot owner."""

    package = importlib.import_module("manosube_agent_civilization")
    owners: set[str] = set()
    for info in pkgutil.walk_packages(package.__path__, prefix="manosube_agent_civilization."):
        module = importlib.import_module(info.name)
        tree = ast.parse(inspect.getsource(module), filename=info.name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SOURCE_SNAPSHOT_SCHEMA_ID":
                    owners.add(info.name)
    assert owners == {"manosube_agent_civilization.observation.source_snapshot"}


def test_observations_own_producer_and_resolver_both_accept_the_context(tmp_path: Path) -> None:
    """KSI-C2/C3 at Observation's own boundary: Source Snapshot *construction* and
    *resolution* are both performed through the injected context, and both still fail closed
    against the captured bytes after the schema they were captured from is swapped."""

    from manosube_agent_civilization.observation.errors import ObservationError
    from manosube_agent_civilization.observation.source_snapshot import resolve_source_snapshot

    root = _mutable_schema_root(tmp_path)
    context = CanonicalSchemaContext.from_schema_root(root)
    snapshot = _kernel_source_snapshot(schema_context=context)
    ref = {"kind": "source_snapshot", "id": snapshot["source_snapshot_id"]}

    _weaken_source_snapshot_schema_version(root)
    shutil.rmtree(root)

    # Construction still succeeds against the captured bytes, with the root gone entirely.
    assert _kernel_source_snapshot(schema_context=context) == snapshot
    # Resolution against the captured bytes still accepts the valid record...
    assert resolve_source_snapshot(ref, [snapshot], schema_context=context) == snapshot
    # ...and still refuses the schema-invalid one, which the weakened schema would accept.
    invalid = _schema_invalid_source_snapshot()
    invalid_ref = {"kind": "source_snapshot", "id": invalid["source_snapshot_id"]}
    with pytest.raises(ObservationError, match="schema-invalid"):
        resolve_source_snapshot(invalid_ref, [invalid], schema_context=context)


def test_binding_admission_reuses_observations_own_validation_and_message(
    tmp_path: Path,
) -> None:
    """Observation owns the semantics; Binding owns only its own error taxonomy. The
    admission refusal carries Observation's own diagnostic verbatim, raised as Binding's own
    fail-closed error type -- neither a second message nor a second validation."""

    from manosube_agent_civilization.observation.errors import ObservationValidationError
    from manosube_agent_civilization.observation.source_snapshot import (
        validate_source_snapshot_body,
    )

    context = _verified_from_schema_root(SCHEMA_ROOT)
    invalid = _schema_invalid_source_snapshot()
    record_id = invalid["source_snapshot_id"]

    with pytest.raises(ObservationValidationError) as observation_refusal:
        validate_source_snapshot_body(
            invalid,
            context_label=f"additional genesis record source_snapshot/{record_id}",
            schema_context=context,
        )

    store = FileStateStore(tmp_path / "backend", schema_context=context)
    with pytest.raises(BindingValidationError) as binding_refusal:
        bind_project(
            store,
            **bind_project_kwargs(),
            additional_genesis_records=_genesis_records(snapshot=invalid),
            schema_context=context,
        )
    assert str(binding_refusal.value) == str(observation_refusal.value)


# --- KSI-C6: the documented public downstream route ----------------------------------------- #


def test_the_whole_secure_route_is_reachable_through_public_symbols_only(
    tmp_path: Path,
) -> None:
    """``KSI-C6``: the downstream integration needs no private function, no ``lru_cache``
    internal, no monkeypatch, no import hook, and no CPython-specific cache behaviour -- only
    these public symbols, imported from these public modules."""

    schema_context_module = importlib.import_module("manosube_agent_civilization.schema_context")
    for name in (
        "CanonicalSchemaContext",
        "SchemaContextError",
        "SCHEMA_SET_DIGEST_PROFILE",
        "CANONICAL_SCHEMA_SUFFIX",
        "capture_canonical_schema_bytes",
        "schema_set_digest",
    ):
        assert not name.startswith("_")
        assert hasattr(schema_context_module, name), name

    # The route itself, written exactly as a downstream caller would write it.
    captured = capture_canonical_schema_bytes(SCHEMA_ROOT)
    adopted_digest = schema_set_digest(captured)
    context = CanonicalSchemaContext(
        captured,
        expected_digest=adopted_digest,
        expected_schema_count=len(captured),
        expected_schema_ids=context_schema_ids(captured),
    )
    store = FileStateStore(tmp_path / "backend", schema_context=context)
    result = bind_project(
        store,
        **bind_project_kwargs(),
        additional_genesis_records=_genesis_records(schema_context=context),
        schema_context=context,
    )
    assert result["committed_state"]["state_revision"] == 0
    assert context.digest == adopted_digest


def context_schema_ids(captured: dict[str, bytes]) -> list[str]:
    return [json.loads(content)["$id"] for content in captured.values()]
