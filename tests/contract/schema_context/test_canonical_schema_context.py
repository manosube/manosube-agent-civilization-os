"""Issue #75 (``D-KERNEL-VERIFIED-SCHEMA-BYTE-INJECTION``) KSI-C1/C4/C5: the one Kernel-owned
immutable canonical schema validation context, proved at its own boundary.

The whole-transaction proof lives next door in ``tests/integration/binding/
test_verified_schema_context_genesis.py``; this module proves the properties the context
itself must carry before any transaction can rely on them:

- it is constructed from a closed mapping of relative path to captured *bytes*, and computes
  and exposes the canonical digest of exactly those bytes (KSI-C1);
- it validates the expected digest, count and ``$id`` set when supplied, and refuses -- before
  any validator exists, therefore before any validation, Store construction, or write -- when
  they do not reproduce (KSI-C5);
- it exposes validation *operations* only: no schema document, no validator, no mutable
  mapping, and no reload/cache-clear/fall-back-to-filesystem path of any kind (KSI-C1);
- it retains no caller alias, so mutating the input mapping (or the directory it came from)
  after construction changes no validation outcome (KSI-C4/C5);
- its own attributes cannot be rebound or deleted (KSI-C5).

Every refusal is proved against a *real* canonical ``01_SCHEMA`` capture, and every claim that
something is "still rejected" is paired with a positive control proving the weakened schema
would genuinely have accepted it -- refusal here is never vacuous.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from tests.state_helpers import SCHEMA_ROOT

import manosube_agent_civilization.schema_context as schema_context_module
from manosube_agent_civilization.schema_context import (
    ADOPTED_SCHEMA_SET_DIGEST,
    CANONICAL_SCHEMA_SUFFIX,
    SCHEMA_SET_DIGEST_PROFILE,
    CanonicalSchemaContext,
    SchemaContextError,
    capture_canonical_schema_bytes,
    schema_set_digest,
)

pytestmark = [pytest.mark.contract, pytest.mark.security]

SOURCE_SNAPSHOT_SCHEMA_ID = "https://schemas.manosube.org/agent-civilization-os/v0.1/observation/source_snapshot.schema.json"
SOURCE_SNAPSHOT_RELATIVE_PATH = "observation/source_snapshot.schema.json"

#: The one public surface a caller may reach on a context. Stated exactly, so a future
#: accidental exposure of a schema document, a validator, a mutable mapping, or a reload path
#: fails this test structurally rather than being noticed by review.
EXPECTED_PUBLIC_SURFACE = frozenset(
    {
        "digest",
        "from_schema_root",
        "knows_schema",
        "relative_paths",
        "schema_count",
        "schema_ids",
        "validation_errors",
        "verified",
    }
)


def _captured() -> dict[str, bytes]:
    return capture_canonical_schema_bytes(SCHEMA_ROOT)


def _valid_source_snapshot() -> dict[str, Any]:
    """A real, schema-valid Source Snapshot body -- built by Observation's own producer, so
    this fixture can never drift from the schema it is used to exercise."""

    from tests.state_helpers import real_kernel_source_snapshot

    return real_kernel_source_snapshot()


def _schema_invalid_source_snapshot() -> dict[str, Any]:
    """The identical body with a ``schema_version`` the canonical schema's own ``const``
    forbids.

    Deliberately a field *outside* the Source Snapshot's own content-addressed identity
    payload (``source_locator``/``content_digest``/``captured_at``/``git_provenance``), so
    this body remains identity-valid: what a weakened schema would then accept is a genuinely
    schema-invalid record, not one that some later identity check would have caught anyway.
    """

    record = dict(_valid_source_snapshot())
    record["schema_version"] = "0.2"
    return record


def _weakened_source_snapshot_schema() -> bytes:
    """The canonical Source Snapshot schema with its ``schema_version`` ``const`` relaxed to
    any string -- a real, minimal weakening, not a wholesale replacement."""

    document = json.loads((SCHEMA_ROOT / SOURCE_SNAPSHOT_RELATIVE_PATH).read_bytes())
    document["properties"]["schema_version"] = {"type": "string"}
    return json.dumps(document).encode("utf-8")


def _mutable_schema_root(tmp_path: Path) -> Path:
    """A complete, real copy of the canonical schema tree the test may then mutate freely."""

    destination = tmp_path / "01_SCHEMA"
    shutil.copytree(SCHEMA_ROOT, destination)
    return destination


# --- KSI-C1: capture, digest, and closed-set adoption ------------------------------------- #


def test_a_context_adopts_the_whole_canonical_schema_set_from_captured_bytes() -> None:
    captured = _captured()
    on_disk = sorted(
        path.relative_to(SCHEMA_ROOT).as_posix()
        for path in SCHEMA_ROOT.rglob("*" + CANONICAL_SCHEMA_SUFFIX)
    )
    assert sorted(captured) == on_disk
    assert all(isinstance(content, bytes) for content in captured.values())

    context = CanonicalSchemaContext(captured)
    assert context.schema_count == len(on_disk)
    assert context.relative_paths == tuple(on_disk)
    assert context.schema_ids == tuple(
        sorted(json.loads(captured[path])["$id"] for path in captured)
    )
    assert context.knows_schema(SOURCE_SNAPSHOT_SCHEMA_ID)


def test_the_digest_commits_to_the_exact_bytes_and_to_nothing_else() -> None:
    captured = _captured()
    digest = schema_set_digest(captured)
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
    assert SCHEMA_SET_DIGEST_PROFILE == "MANOSUBE-SCHEMA-SET-SHA256-0.1"

    # Order-independent: the same set, inserted in the opposite order, is the same set.
    reversed_insertion = {path: captured[path] for path in sorted(captured, reverse=True)}
    assert schema_set_digest(reversed_insertion) == digest

    # Content-sensitive: one byte changed, one schema removed, one schema added.
    changed = dict(captured)
    changed[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    assert schema_set_digest(changed) != digest

    removed = dict(captured)
    del removed[SOURCE_SNAPSHOT_RELATIVE_PATH]
    assert schema_set_digest(removed) != digest

    added = dict(captured)
    added["observation/extra.schema.json"] = captured[SOURCE_SNAPSHOT_RELATIVE_PATH]
    assert schema_set_digest(added) != digest

    # Path-sensitive: identical bytes filed under a different relative path is a different
    # set, and the length-prefixed framing leaves no way for a path/content boundary to be
    # shifted into an identical preimage.
    renamed = dict(captured)
    renamed["observation/renamed.schema.json"] = renamed.pop(SOURCE_SNAPSHOT_RELATIVE_PATH)
    assert schema_set_digest(renamed) != digest


def test_the_context_reproduces_its_own_captured_digest() -> None:
    captured = _captured()
    context = CanonicalSchemaContext(captured)
    assert context.digest == schema_set_digest(captured)
    assert context.digest in repr(context)


# --- KSI-C5: a set that does not reproduce the adopted digest/count/id-set is refused ------ #


def test_an_unexpected_digest_count_or_id_set_is_refused_before_any_validator_exists() -> None:
    captured = _captured()
    adopted = schema_set_digest(captured)

    with pytest.raises(SchemaContextError, match="digest"):
        CanonicalSchemaContext(captured, expected_digest="sha256:" + "0" * 64)

    with pytest.raises(SchemaContextError, match="not the expected"):
        CanonicalSchemaContext(captured, expected_schema_count=len(captured) + 1)

    with pytest.raises(SchemaContextError, match=r"\$id set"):
        CanonicalSchemaContext(
            captured, expected_schema_ids=[*json_ids(captured), "https://example.invalid/x"]
        )

    # The positive control: the very same expectations, correctly stated, do construct.
    context = CanonicalSchemaContext(
        captured,
        expected_digest=adopted,
        expected_schema_count=len(captured),
        expected_schema_ids=json_ids(captured),
    )
    assert context.digest == adopted


def json_ids(captured: dict[str, bytes]) -> list[str]:
    return [json.loads(content)["$id"] for content in captured.values()]


# --- P79-R1-F2: adopted-identity verification is explicit and durable -------------------- #


def test_verified_reflects_only_whether_the_adopted_digest_actually_matches() -> None:
    """P79-R1-F2 Round 2 -- ``verified`` cannot be manufactured by any caller-supplied value.

    A real canonical capture is ``verified`` regardless of what (if anything) is passed as
    ``expected_digest``: adoption is a fact about the bytes, not a caller's own declaration.
    A weakened capture stays unverified even when its own self-computed digest is passed
    back in as its own ``expected_digest`` -- the exact Round 1 counterexample Round 2
    review reproduced, where a caller declaration alone had been accepted as if it were an
    independently adopted identity.
    """

    captured = _captured()
    assert CanonicalSchemaContext(captured).verified is True
    assert CanonicalSchemaContext(captured, expected_schema_count=len(captured)).verified is True
    assert (
        CanonicalSchemaContext(captured, expected_digest=schema_set_digest(captured)).verified
        is True
    )

    weakened = dict(captured)
    weakened[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    weakened_digest = schema_set_digest(weakened)
    assert CanonicalSchemaContext(weakened).verified is False
    assert CanonicalSchemaContext(weakened, expected_digest=weakened_digest).verified is False, (
        "a self-computed digest passed back as its own expected_digest must not manufacture "
        "verified=True"
    )


def test_verified_agrees_on_every_read() -> None:
    """``verified`` is a computed property (Round 2), recomputed from ``self._digest`` on
    every access rather than stored as a separate flag -- but ``self._digest`` itself never
    changes after construction, so every read agrees for the lifetime of the context."""

    captured = _captured()
    context = CanonicalSchemaContext(captured, expected_digest=schema_set_digest(captured))
    assert context.verified is True
    assert context.verified is True  # a second read agrees


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("remove", "digest"),
        ("add", "digest"),
        ("change", "digest"),
    ],
)
def test_a_removed_added_or_changed_schema_is_refused_against_a_pinned_digest(
    mutation: str, match: str
) -> None:
    captured = _captured()
    adopted = schema_set_digest(captured)
    tampered = dict(captured)
    if mutation == "remove":
        del tampered[SOURCE_SNAPSHOT_RELATIVE_PATH]
    elif mutation == "add":
        tampered["observation/extra.schema.json"] = tampered[SOURCE_SNAPSHOT_RELATIVE_PATH]
    else:
        tampered[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    with pytest.raises(SchemaContextError, match=match):
        CanonicalSchemaContext(tampered, expected_digest=adopted)


def test_a_duplicated_id_is_refused_even_with_no_expectation_supplied() -> None:
    """Two captured paths claiming one ``$id`` is refused on its own terms -- a caller who
    pins nothing still cannot end up with a context whose ``$id`` -> validator mapping
    silently dropped one of two competing documents."""

    captured = _captured()
    captured["observation/source_snapshot_copy.schema.json"] = captured[
        SOURCE_SNAPSHOT_RELATIVE_PATH
    ]
    with pytest.raises(SchemaContextError, match="more than once"):
        CanonicalSchemaContext(captured)


@pytest.mark.parametrize(
    ("path", "content", "match"),
    [
        ("", b"{}", "empty"),
        ("/absolute/x.schema.json", b"{}", "must be relative"),
        ("~/x.schema.json", b"{}", "must be relative"),
        ("C:/x.schema.json", b"{}", "must be relative"),
        ("../escape/x.schema.json", b"{}", "traversal"),
        ("a//b.schema.json", b"{}", "traversal"),
        ("observation/not_a_schema.json", b"{}", "canonical"),
        ("observation/x.schema.json", b"{not json", "UTF-8 JSON"),
        ("observation/x.schema.json", b"\xff\xfe", "UTF-8 JSON"),
        ("observation/x.schema.json", b"[]", "not a JSON object"),
        ("observation/x.schema.json", b'{"title": "no id"}', r"no stable \$id"),
        ("observation/x.schema.json", b'{"$id": ""}', r"no stable \$id"),
        ("observation/x.schema.json", b'{"$id": 7}', r"no stable \$id"),
    ],
)
def test_a_malformed_capture_entry_is_refused(path: str, content: bytes, match: str) -> None:
    with pytest.raises(SchemaContextError, match=match):
        CanonicalSchemaContext({path: content})


@pytest.mark.parametrize("content", ["a string, not bytes", bytearray(b"{}"), None, 7])
def test_a_non_bytes_capture_value_is_refused(content: object) -> None:
    """``bytes`` or nothing: a ``str`` has no single byte representation until an encoding is
    chosen and a ``bytearray`` is mutable -- silently coercing either would reintroduce the
    byte-identity ambiguity this context exists to remove."""

    with pytest.raises(SchemaContextError, match="must be bytes"):
        CanonicalSchemaContext({"observation/x.schema.json": content})  # type: ignore[dict-item]


def test_an_empty_capture_is_refused() -> None:
    with pytest.raises(SchemaContextError, match="empty"):
        CanonicalSchemaContext({})


def test_capture_refuses_a_missing_or_schema_free_directory(tmp_path: Path) -> None:
    with pytest.raises(SchemaContextError, match="unavailable"):
        capture_canonical_schema_bytes(tmp_path / "does-not-exist")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SchemaContextError, match="carries no schema"):
        capture_canonical_schema_bytes(empty)


# --- KSI-C1: validation operations only, no document and no reload path ------------------- #


def test_the_context_exposes_validation_operations_and_nothing_else() -> None:
    context = CanonicalSchemaContext(_captured())
    public = {name for name in dir(context) if not name.startswith("_")}
    assert public == set(EXPECTED_PUBLIC_SURFACE)
    for forbidden in (
        "cache_clear",
        "documents",
        "reload",
        "registry",
        "schema_root",
        "schemas",
        "validators",
        "with_schema_root",
    ):
        assert not hasattr(context, forbidden), forbidden


def test_validation_errors_returns_a_fresh_list_the_caller_cannot_retain() -> None:
    context = CanonicalSchemaContext(_captured())
    first = context.validation_errors(_schema_invalid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID)
    assert first
    first.clear()
    second = context.validation_errors(_schema_invalid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID)
    assert second
    assert context.validation_errors(_valid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID) == []


def test_validation_errors_fails_closed_on_a_schema_outside_the_adopted_set() -> None:
    context = CanonicalSchemaContext(_captured())
    assert not context.knows_schema("https://example.invalid/not-adopted.schema.json")
    with pytest.raises(SchemaContextError, match="unavailable in this validation context"):
        context.validation_errors({}, "https://example.invalid/not-adopted.schema.json")


def test_cross_schema_references_resolve_inside_the_adopted_set() -> None:
    """``source_snapshot.schema.json`` ``$ref``s ``../common/identity.schema.json`` and
    ``../common/timestamp.schema.json``: the context must resolve those against its own
    captured documents, never by reaching back out to a file or the network."""

    context = CanonicalSchemaContext(_captured())
    record = dict(_valid_source_snapshot())
    record["source_snapshot_id"] = "not a canonical identity"
    assert context.validation_errors(record, SOURCE_SNAPSHOT_SCHEMA_ID)


# --- KSI-C5: attribute rebinding is refused ------------------------------------------------ #


@pytest.mark.parametrize("name", ["digest", "_validators", "_digest", "a_brand_new_attribute"])
def test_a_context_attribute_cannot_be_rebound(name: str) -> None:
    context = CanonicalSchemaContext(_captured())
    with pytest.raises(SchemaContextError, match="immutable"):
        setattr(context, name, "substituted")


@pytest.mark.parametrize("name", ["digest", "_validators"])
def test_a_context_attribute_cannot_be_deleted(name: str) -> None:
    context = CanonicalSchemaContext(_captured())
    with pytest.raises(SchemaContextError, match="immutable"):
        delattr(context, name)


def test_the_internal_validator_mapping_itself_refuses_mutation() -> None:
    """P79-R3-F1/F2 Round 3: Round 2's ``_validators`` was a ``MappingProxyType`` instance
    attribute -- read-only against reassignment of its own entries, but still a named target
    ``object.__setattr__(context, "_validators", weakened_validators)`` could replace
    wholesale, splicing in a validator mapping built from different bytes while ``verified``
    (bound to a separate ``_digest`` slot) kept reporting the original, correct answer. There
    is no such attribute any more to reach, read, or replace: the constructor retypes every
    instance to a per-construction class whose validation methods are closures with no
    backing instance attribute at all (see ``schema_context._bind_adopted_identity``)."""

    context = CanonicalSchemaContext(_captured())
    with pytest.raises(AttributeError):
        _ = context._validators  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        object.__setattr__(context, "_validators", {})


def test_a_validators_own_schema_document_refuses_direct_mutation_too() -> None:
    """P79-R1-F1 Round 2 -- the finding SHUKOU's Round 2 review actually reproduced: Round
    1's deep-copy-on-return fix only ever closed the *returned*-error alias, leaving the
    schema node any returned error's ``.schema`` points at reachable and mutable through that
    same reference. That document is now frozen (:class:`_FrozenSchemaMapping`/
    :class:`_FrozenSchemaSequence`, neither a ``dict``/``list`` subclass at all), so ordinary
    item assignment at any nesting depth a real canonical schema uses -- top-level
    ``properties``, not just a leaf value -- raises immediately instead of silently
    succeeding."""

    context = CanonicalSchemaContext(_captured())
    errors = context.validation_errors({}, SOURCE_SNAPSHOT_SCHEMA_ID)
    required_error = next(error for error in errors if error.validator == "required")
    schema = required_error.schema
    assert not isinstance(schema, dict)

    with pytest.raises(TypeError):
        schema["properties"]["schema_version"] = {"type": "string"}
    with pytest.raises(TypeError):
        schema["unevaluatedProperties"] = True

    # Unaffected: the schema still rejects exactly what it rejected before the attempt.
    invalid = _schema_invalid_source_snapshot()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)


def test_a_frozen_schema_node_refuses_the_base_type_mutator_bypass_too() -> None:
    """P79-R3-F1 -- the Round 3 Structural Review finding: Round 2's frozen documents were
    real ``dict``/``list`` *subclasses*, whose own mutating methods raised, but a ``dict``/
    ``list`` subclass's base-type mutating slots stay reachable by calling the base type
    directly (``dict.__setitem__(node, ...)``), bypassing every subclass override entirely
    (independently reproduced: exactly that call against the already-admitted top-level
    Objective Revision validator's ``.schema["unevaluatedProperties"]`` made an identical
    invalid record pass, and a real ``bind_project`` genesis transaction commit it -- see
    ``tests/integration/binding/test_verified_schema_context_genesis.py`` for that scale).

    Closed by not being a ``dict``/``list`` subclass at all any more: calling the base type's
    own mutating method against a :class:`_FrozenSchemaMapping`/:class:`_FrozenSchemaSequence`
    instance raises ``TypeError`` at the call itself, because there is no ``dict``/``list``
    in its MRO for that base-type method to operate on.
    """

    context = CanonicalSchemaContext(_captured())
    errors = context.validation_errors({}, SOURCE_SNAPSHOT_SCHEMA_ID)
    required_error = next(error for error in errors if error.validator == "required")
    schema = required_error.schema
    required_list = schema["required"]
    assert not isinstance(schema, dict)
    assert not isinstance(required_list, list)

    with pytest.raises(TypeError):
        dict.__setitem__(schema, "unevaluatedProperties", True)
    with pytest.raises(TypeError):
        list.append(required_list, "schema_version")
    with pytest.raises(TypeError):
        list.__setitem__(required_list, 0, "schema_version")

    # Unaffected: the schema still rejects exactly what it rejected before every attempt.
    invalid = _schema_invalid_source_snapshot()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    assert context.validation_errors(_valid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID) == []


def test_object_setattr_cannot_promote_an_unverified_context() -> None:
    """P79-R1-F2 Round 2 -- the other half of the reproduced counterexample:
    ``object.__setattr__`` bypasses this class's own ``__setattr__`` override by design (it
    is the same mechanism the constructor itself uses to set slots), so a Round 1-shaped
    stored boolean ``_verified`` flag could always be forced from ``False`` to ``True`` by
    any caller holding a bare reference. There is no such slot to promote any more: ``verified``
    is computed fresh from ``_digest`` on every access, so the identical attack now raises
    ``AttributeError`` instead of silently promoting an unverified, weakened context."""

    weakened = dict(_captured())
    weakened[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    context = CanonicalSchemaContext(weakened)
    assert context.verified is False

    with pytest.raises(AttributeError):
        object.__setattr__(context, "_verified", True)
    assert context.verified is False


def test_object_setattr_cannot_promote_a_weakened_context_by_replacing_its_digest() -> None:
    """P79-R3-F2 -- the Round 3 Structural Review finding: Round 2's ``verified`` property
    compared ``self._digest`` (a plain, replaceable slot) against the module constant on
    every access. ``object.__setattr__(context, "_digest", ADOPTED_SCHEMA_SET_DIGEST)``
    replaces the comparison's left side to match its right and promotes a weakened context
    (independently reproduced: this exact call made ``verified`` read ``True`` for a context
    built from schema bytes that do not reproduce the adopted set).

    Closed structurally: ``verified`` is bound, at construction, to a closure over a plain
    Python ``bool`` computed once from the digest at that moment -- it is never read back
    from ``self._digest`` at all, so replacing that slot (which still exists, for the
    informational :attr:`~CanonicalSchemaContext.digest` property) has no effect on it.
    """

    weakened = dict(_captured())
    weakened[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    context = CanonicalSchemaContext(weakened)
    assert context.verified is False

    object.__setattr__(context, "_digest", ADOPTED_SCHEMA_SET_DIGEST)
    assert context.digest == ADOPTED_SCHEMA_SET_DIGEST, "the slot itself really was replaced"
    assert context.verified is False, "but verified must not follow it"


def test_rebinding_the_module_adopted_digest_cannot_promote_an_existing_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P79-R3-F2 -- the third reproduced counterexample: ``Final`` is a static-analysis
    annotation only, not runtime enforcement, so ``schema_context.ADOPTED_SCHEMA_SET_DIGEST``
    can be rebound like any other module attribute. Round 2's ``verified`` property re-read
    that global fresh on every single access, so rebinding it to a weakened context's own
    digest, *after* that context already existed and had already reported ``verified is
    False``, made the same, already-existing context start reporting ``True``.

    Closed structurally: the comparison against the adopted digest happens exactly once, at
    construction, and the resulting ``bool`` is what the per-instance closure returns from
    then on -- an already-constructed context never re-reads the module global again.
    """

    weakened = dict(_captured())
    weakened[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    context = CanonicalSchemaContext(weakened)
    assert context.verified is False

    monkeypatch.setattr(schema_context_module, "ADOPTED_SCHEMA_SET_DIGEST", context.digest)
    assert context.verified is False, "an existing context must not be promoted by a later rebind"


# --- KSI-C4/C5: no verify/use window ------------------------------------------------------- #


def test_a_returned_validation_errors_own_schema_reference_is_immutable() -> None:
    """P79-R1-F1 Round 2 -- the independently reproduced counterexample, at this module's own
    boundary: a raw :class:`jsonschema.ValidationError`'s own ``.schema`` attribute is not a
    copy but a direct reference into the schema document node it was raised against. Round 1
    closed this by deep-copying every returned error and asserting the mutation "changed no
    outcome"; Round 2 closes it structurally instead -- the mutation itself, attempted
    exactly as the reproduced counterexample did (flipping a ``const`` check to match the
    invalid instance), now raises immediately, because the schema document is frozen (and,
    per P79-R3-F1, not a ``dict``/``list`` subclass any more, so there is no base-type
    mutator bypass either)."""

    context = CanonicalSchemaContext(_captured())
    invalid = _schema_invalid_source_snapshot()
    errors = context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    assert errors

    mutation_attempted = False
    for error in errors:
        if error.validator == "const" and not isinstance(error.schema, dict):
            mutation_attempted = True
            with pytest.raises(TypeError):
                error.schema["const"] = error.instance
    assert mutation_attempted, "the counterexample's own mutation target was not reached"

    # Unaffected: the same context, revalidating the identical invalid body, still refuses it.
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    assert context.validation_errors(_valid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID) == []


def test_two_calls_to_validation_errors_never_share_a_single_error_object() -> None:
    """Defence in depth for P79-R1-F1: the error objects themselves -- and their own mutable
    per-call state, like ``.path`` -- are never the same Python objects across two calls, so
    no cross-call aliasing of *that* state is possible either. (A returned error's own
    ``.schema`` may legitimately be the very same frozen document node on both calls: sharing
    an already-immutable value is not a threat, since neither call can mutate it.)"""

    context = CanonicalSchemaContext(_captured())
    invalid = _schema_invalid_source_snapshot()
    first = context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    second = context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    assert first and second
    assert all(a is not b for a, b in zip(first, second, strict=True))
    assert all(a.path is not b.path for a, b in zip(first, second, strict=True))


def test_mutating_the_caller_mapping_after_construction_changes_no_outcome() -> None:
    """Adversarial matrix item 5. The mapping is consumed once; every document the context
    validates against was parsed from those bytes at construction and belongs to the context
    alone."""

    captured = _captured()
    context = CanonicalSchemaContext(captured)
    adopted_digest = context.digest
    invalid = _schema_invalid_source_snapshot()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)

    # Every shape of caller-side mutation at once: replace a value with a weakened schema,
    # remove an entry, add an entry, and clear the whole mapping.
    captured[SOURCE_SNAPSHOT_RELATIVE_PATH] = _weakened_source_snapshot_schema()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    del captured[SOURCE_SNAPSHOT_RELATIVE_PATH]
    captured["observation/injected.schema.json"] = b'{"$id": "https://example.invalid/x"}'
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    captured.clear()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    assert context.validation_errors(_valid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID) == []
    assert context.digest == adopted_digest
    assert context.knows_schema(SOURCE_SNAPSHOT_SCHEMA_ID)


def test_a_mapping_that_answers_differently_on_a_second_read_cannot_split_digest_from_parse() -> (
    None
):
    """The closure must not contain the very window it closes.

    A caller-supplied ``Mapping`` is an arbitrary object, not necessarily a ``dict``: one
    whose ``__getitem__`` answers with the real canonical schema the first time and a
    weakened one the second would, under a naive constructor, be *digested* as canonical and
    then *parsed* as weakened. Each key is therefore read exactly once, into the
    constructor's own private snapshot, before anything is checked or parsed.
    """

    captured = _captured()
    weakened = _weakened_source_snapshot_schema()
    reads: dict[str, int] = {}

    class TwoFacedCapture(dict[str, bytes]):
        def __getitem__(self, key: str) -> bytes:
            reads[key] = reads.get(key, 0) + 1
            if key == SOURCE_SNAPSHOT_RELATIVE_PATH and reads[key] > 1:
                return weakened
            return super().__getitem__(key)

    two_faced = TwoFacedCapture(captured)
    context = CanonicalSchemaContext(two_faced)

    assert reads[SOURCE_SNAPSHOT_RELATIVE_PATH] == 1
    assert context.digest == schema_set_digest(captured)
    assert context.validation_errors(_schema_invalid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID)


def test_mutating_the_original_schema_root_after_capture_changes_no_outcome(
    tmp_path: Path,
) -> None:
    """Adversarial matrix items 1/2 at this module's own boundary, and KSI-C4: after
    construction, the directory the bytes came from is irrelevant -- weakened, emptied, or
    deleted outright."""

    root = _mutable_schema_root(tmp_path)
    context = CanonicalSchemaContext.from_schema_root(root)
    adopted_digest = context.digest
    invalid = _schema_invalid_source_snapshot()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)

    (root / SOURCE_SNAPSHOT_RELATIVE_PATH).write_bytes(_weakened_source_snapshot_schema())
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)

    shutil.rmtree(root)
    assert not root.exists()
    assert context.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID)
    assert context.validation_errors(_valid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID) == []
    assert context.digest == adopted_digest


def test_the_weakened_schema_really_would_have_accepted_the_invalid_record(
    tmp_path: Path,
) -> None:
    """Adversarial matrix item 9 -- the positive control that makes every refusal above
    non-vacuous.

    A context captured *after* the identical weakening accepts the identical invalid record.
    So the earlier refusals are not an artefact of a fixture that was never really invalid,
    nor of a weakening that never really landed: the only difference is *when* the bytes were
    captured.
    """

    root = _mutable_schema_root(tmp_path)
    (root / SOURCE_SNAPSHOT_RELATIVE_PATH).write_bytes(_weakened_source_snapshot_schema())
    weakened = CanonicalSchemaContext.from_schema_root(root)

    invalid = _schema_invalid_source_snapshot()
    assert weakened.validation_errors(invalid, SOURCE_SNAPSHOT_SCHEMA_ID) == []
    assert weakened.digest != CanonicalSchemaContext(_captured()).digest


def test_changing_the_working_directory_after_construction_changes_no_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KSI-C4: a cwd-relative ``01_SCHEMA`` is one of the fall-backs the legacy resolvers
    consult. A context consults none of them, so even a hostile ``01_SCHEMA`` planted in a
    new working directory cannot reach it."""

    context = CanonicalSchemaContext(_captured())
    hostile = tmp_path / "01_SCHEMA" / "observation"
    hostile.mkdir(parents=True)
    (hostile / "source_snapshot.schema.json").write_bytes(_weakened_source_snapshot_schema())
    monkeypatch.chdir(tmp_path)
    assert context.validation_errors(_schema_invalid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID)


def test_no_schema_file_is_read_after_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    """KSI-C4 measured directly at this boundary: ``Path.read_text``/``Path.read_bytes`` are
    instrumented after the context exists, and no ``*.schema.json`` read occurs for any
    number of validations."""

    context = CanonicalSchemaContext(_captured())
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
    for _ in range(5):
        context.validation_errors(_valid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID)
        context.validation_errors(_schema_invalid_source_snapshot(), SOURCE_SNAPSHOT_SCHEMA_ID)
    assert reads == []


def test_capture_reads_each_schema_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The one filesystem read the secure route performs is bounded and accounted for: one
    read per canonical schema, and never a second pass."""

    reads: list[str] = []
    original_read_bytes = Path.read_bytes

    def read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if str(self).endswith(CANONICAL_SCHEMA_SUFFIX):
            reads.append(str(self))
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    captured = capture_canonical_schema_bytes(SCHEMA_ROOT)
    assert len(reads) == len(captured)
    assert len(set(reads)) == len(reads)


def test_an_import_reload_cannot_invalidate_or_redirect_an_existing_context(
    tmp_path: Path,
) -> None:
    """Adversarial matrix item 4's second half: ``importlib.reload``.

    Reloading :mod:`~manosube_agent_civilization.schema_context` re-executes the module and
    rebinds its names, and reloading
    :mod:`~manosube_agent_civilization.observation.schemas` discards the legacy
    zero-argument registry's cache entirely. Neither reaches a context that already exists:
    it holds its own already-built validators, not a module-level lookup performed later.

    Run in a real subprocess, like this repository's other fresh-process proofs, so a
    deliberate reload can never leak rebound classes into the rest of this session.
    """

    script = textwrap.dedent(
        f"""
        import importlib
        import json
        import sys

        sys.path.insert(0, {str(Path.cwd())!r})

        from manosube_agent_civilization import schema_context as schema_context_module
        from manosube_agent_civilization.observation import schemas as schemas_module

        context = schema_context_module.CanonicalSchemaContext.from_schema_root(
            __import__("pathlib").Path({str(SCHEMA_ROOT)!r})
        )
        record = json.loads({json.dumps(json.dumps(_schema_invalid_source_snapshot()))!r})
        schema_id = {SOURCE_SNAPSHOT_SCHEMA_ID!r}

        before = bool(context.validation_errors(record, schema_id))
        digest_before = context.digest

        schemas_module.validators.cache_clear()
        importlib.reload(schemas_module)
        importlib.reload(schema_context_module)

        print(json.dumps({{
            "rejected_before": before,
            "rejected_after": bool(context.validation_errors(record, schema_id)),
            "digest_before": digest_before,
            "digest_after": context.digest,
            "schema_count": context.schema_count,
        }}))
        """
    )
    script_path = tmp_path / "reload_probe.py"
    script_path.write_text(script, encoding="utf-8")
    completed = subprocess.run(  # noqa: S603
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(tmp_path),
    )
    observed = json.loads(completed.stdout)
    assert observed["rejected_before"] is True
    assert observed["rejected_after"] is True
    assert observed["digest_after"] == observed["digest_before"]
    assert observed["schema_count"] == len(_captured())


def test_two_captures_of_the_same_tree_agree_and_stay_distinct_objects() -> None:
    """Equality is identity, deliberately: two contexts built from identical bytes agree on
    every outcome but remain two contexts, which is exactly what lets a caller prove that
    *one* context was used end to end rather than merely that two happened to agree."""

    first = CanonicalSchemaContext(_captured())
    second = CanonicalSchemaContext(_captured())
    assert first.digest == second.digest
    assert first.schema_ids == second.schema_ids
    assert first is not second
    assert first != second


def test_the_digest_is_domain_separated_from_a_bare_content_hash() -> None:
    """The profile's own domain separator keeps this digest space from colliding with
    ``MANOSUBE-STATE-SHA256-0.1`` or the genesis manifest digest -- a bare hash of the same
    preimage is not this digest."""

    captured = {"observation/x.schema.json": b'{"$id": "https://example.invalid/x"}'}
    bare = hashlib.sha256(captured["observation/x.schema.json"]).hexdigest()
    assert schema_set_digest(captured) != "sha256:" + bare


# --- KSI-C2: every threaded owner fails closed on a context that cannot serve the schema --- #


def _source_snapshot_only_context() -> CanonicalSchemaContext:
    """A real, well-formed context that adopted only one canonical schema.

    Not a malformed context -- a *narrower* one. It exists to prove that every owner the
    validation context is threaded through asks whether the context can actually serve the
    schema it needs, and refuses when it cannot, rather than silently validating against
    nothing.
    """

    captured = _captured()
    return CanonicalSchemaContext(
        {SOURCE_SNAPSHOT_RELATIVE_PATH: captured[SOURCE_SNAPSHOT_RELATIVE_PATH]}
    )


def test_binding_validation_fails_closed_on_a_context_missing_the_schema() -> None:
    from manosube_agent_civilization.binding.errors import BindingValidationError
    from manosube_agent_civilization.binding.validation import validate_against_schema_id

    unknown = "https://schemas.manosube.org/agent-civilization-os/v0.1/not/a.schema.json"

    with pytest.raises(BindingValidationError, match="mutually exclusive"):
        validate_against_schema_id(
            {},
            SOURCE_SNAPSHOT_SCHEMA_ID,
            schema_root=SCHEMA_ROOT,
            schema_context=_captured_context(),
        )
    with pytest.raises(BindingValidationError, match="canonical schema is unavailable"):
        validate_against_schema_id({}, unknown, schema_context=_captured_context())
    with pytest.raises(BindingValidationError, match="canonical schema is unavailable"):
        validate_against_schema_id({}, unknown, schema_root=SCHEMA_ROOT)


def test_observation_fails_closed_on_a_schema_neither_source_can_serve() -> None:
    from manosube_agent_civilization.observation.errors import ObservationValidationError
    from manosube_agent_civilization.observation.schemas import observation_schema_errors

    unknown = "https://schemas.manosube.org/agent-civilization-os/v0.1/observation/none.schema.json"

    with pytest.raises(ObservationValidationError, match="canonical schema is unavailable"):
        observation_schema_errors({}, unknown)
    with pytest.raises(SchemaContextError, match="unavailable in this validation context"):
        observation_schema_errors({}, unknown, schema_context=_captured_context())


def test_state_canonicalization_fails_closed_on_a_context_missing_project_state() -> None:
    from tests.state_helpers import initial_state

    from manosube_agent_civilization.state.canonicalize import canonical_semantic_state_bytes
    from manosube_agent_civilization.state.errors import SchemaValidationError

    state = initial_state()

    with pytest.raises(SchemaValidationError, match="mutually exclusive"):
        canonical_semantic_state_bytes(
            state, schema_root=SCHEMA_ROOT, schema_context=_captured_context()
        )
    with pytest.raises(SchemaValidationError, match="required schema is unavailable"):
        canonical_semantic_state_bytes(state, schema_context=_source_snapshot_only_context())


def _captured_context() -> CanonicalSchemaContext:
    return CanonicalSchemaContext(_captured())
