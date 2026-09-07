"""The one production reference-edge registry for Store-owned record kinds.

SHUKOU Phase 8 final-closure round 4 (P8-R4-F1/F2): Round 3's own Reference Closure gate
(``route.py``'s ``_admitted_records``) was scoped to one field on one record kind
(``observation.observation_evidence_refs``) and gated on a caller opting in. Round 4 makes
Reference Closure an unconditional ``reflow()`` invariant covering every Store-owned
reference edge this vertical persists -- which first requires exactly one place naming what
those edges *are*, so the production gate and any test proving
``UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0`` walk the identical vocabulary
(``PRODUCTION_AND_TEST_REFERENCE_VOCABULARY_MUST_MATCH=true``,
``DUPLICATE_TEST_REFERENCE_REGISTRY=false``, ``FUZZY_KEY_SUFFIX_SCAN=false``).

Round 4 completion repair 2 (P8-R4-C2-F1, adopted): widened this registry's own field
*coverage* -- ``difference_event``/``closure_evaluation`` had recognized only one field
each. Closed by walking every classification-A field every Store-owned record kind's own
canonical schema declares.

Round 4 completion repair 3 (P8-R4-C3-F1, adopted): 構造参謀's independent re-observation
found this registry's own *edge identity* incomplete even after Repair 2 -- the delivered
``_edge()`` helper (removed in this repair, replaced by :func:`_check`'s field-specific
validation) trusted a reference's own self-declared ``kind`` as the authority for what it
names, so a
right-ID, wrong-kind reference (e.g. an ``observation_evidence`` id planted in
``difference_event.observation_refs``, a field that must always name an ``observation``)
was silently accepted and, if a real record of that wrong kind happened to share the id,
resolved. SHUKOU's own semantic decision (adopted, not this module's invention):

```text
CANONICAL_REFERENCE_EDGE_IDENTITY = SOURCE_RECORD_KIND + SOURCE_FIELD_PATH
                                     + EXPECTED_TARGET_KIND + TARGET_ID
REFERENCE_BODY_SELF_DECLARED_KIND_IS_AUTHORITY = false
FIELD_SPECIFIC_TARGET_KIND_REQUIRED = true
EXPECTED_TARGET_KIND_IS_REGISTRY_OWNED = true
ACTUAL_KIND_MUST_EQUAL_EXPECTED_KIND = true
KIND_VALIDATION_PRECEDES_STORE_RESOLUTION = true
CROSS_KIND_ID_ALIASING_ALLOWED = false
CROSS_KIND_RECORD_SUBSTITUTION_ALLOWED = false
```

Closed here by :data:`FIELD_EXPECTED_TARGET_KINDS` -- a field-path-keyed table naming the
closed set of kinds each Store-owned record kind's own canonical field may actually carry
(exactly one kind for most fields, an explicit finite set for the few fields real production
code populates with more than one -- never an unbounded "any Store-owned kind"). Every
reference :func:`reference_edges` reads is checked against its own field's own expected set
*before* the caller ever resolves it against the Store, and a reference naming a kind outside
that set -- whether a real Store-owned kind belonging to a different field, or anything else
-- is refused (:class:`~manosube_agent_civilization.reflow.errors.ReflowValidationError`)
before any write, never silently accepted or narrowed to "whatever kind happened to be
there".

The kind sets themselves are not guessed: every field this module shares with
:mod:`manosube_agent_civilization.difference.graph` (``difference_lifecycle_event``'s and
``closure_evaluation``'s own reference fields -- the identical schemas, since
``difference_event`` persists exactly the ``difference_lifecycle_event`` schema shape) is
cross-checked against that module's own ``REFERENCE_EDGES`` -- an independently adopted,
schema-cross-validated typed registry for Difference's own emitted predecessor bundle,
already reviewed and merged, and the reason several fields here admit *two* kinds
(``observation_evidence`` or ``negative_evidence``) rather than one: real production code
(``evidence/engine.py``'s own ``EVIDENCE_REFERENCE_KIND`` comment, ``difference/graph.py``'s
own field-level closed sets) treats these as siblings the Observation layer and the Evidence
layer each own one of, both legitimate in the identical field. Fields this module owns that
``difference/graph.py`` does not describe (``observation_evidence``'s own ``lineage``/
``artifact_references``, which belong to the Evidence element, external to Difference's own
bundle) are instead cross-checked directly against ``evidence/engine.py``'s own producer
code (``_lineage``'s own call sites, ``EVIDENCE_REFERENCE_KIND``, the schema's own
``const``-pinned ``evidence_reference``/``artifact_reference`` shapes).

Structural Review Round 6 (P13-R6) adds one further field this registry walks:
``observation_evidence.verification_result_provenance.target_refs`` members, cross-checked
against :data:`~manosube_agent_civilization.independent_verification.types.TARGET_REF_KINDS`
-- the one closed kind contract Independent Verification's own types give this field.
``verification_result_provenance.input_refs`` is deliberately never walked: no closed kind
contract exists anywhere in this Kernel for a verifier's own freely-chosen input references,
and this registry's own kind sets are never guessed.

Round 4 completion repair 2's own kind *inventory* stands: :data:`STORE_OWNED_REFERENCE_KINDS`
is unchanged by this repair, and this repair does not walk any field the prior repair did
not already walk -- only what counts as a *valid* reference at each already-walked field is
now checked. Four additional record kinds this vertical already persists (confirmed against
``reflow/route.py``'s own admission code, never assumed) were previously missing as
recognized reference *targets* entirely -- ``closure_evaluation``, ``evidence_sufficiency_
result``, ``kernel_source_witness``, ``invariant_evaluation``,
``candidate_claim_evaluation_event`` and ``candidate_completion_record`` -- and are part of
:data:`STORE_OWNED_REFERENCE_KINDS`.

This module enumerates and validates edges; it resolves nothing, persists nothing, and is
not a second canonical owner of any record kind -- only a read of reference-bearing fields
those owners already produce, checked against the one shape those owners' own real code
actually produces. Schema-level duplicate-collapse (``uniqueItems``) is enforced by
``validate_record`` on every body this function ever receives, long before it runs, and
canonical-reference-equality re-verification for the specific ``authority_ref``/
``change_refs``/``observation_refs`` provenance fields is P8-R1-F5/P8-R2-F2's own,
already-adequate mechanism -- neither is this registry's to duplicate.

:data:`STORE_OWNED_REFERENCE_KINDS` is deliberately narrow: a reference kind this Kernel
names but gives no Store-owned producer of its own is out of this registry's scope, never
silently treated as resolved. Confirmed, not merely a fuzzy `*_ref` key-suffix guess, against
every referenced kind's actual production behavior (whether ``reflow/route.py`` ever calls
``store.commit``/``_merge_verified_record`` for it):

- ``difference`` -- Difference has no Reflow-Store-owned persistence of its own; Evidence's
  own ``difference_ref`` and Sufficiency/Invariant-Evaluation's own ``subject_ref``/
  ``difference_ref`` name it, but it is never a ``resolve_record`` target here.
- ``change`` -- Change is verified by canonical-reference equality against the caller's own
  already-verified input (P8-R1-F5/P8-R2-F2), never resolved from the Store.
- ``authority_decision`` -- identical: canonical-reference equality against caller input,
  never a Store record.
- ``negative_evidence`` -- the Observation layer's own sibling to Evidence's
  ``observation_evidence``, permitted (never required) in every field an Evidence reference
  may occupy; never persisted as a Reflow Store record.
- ``artifact``, ``material_contradiction``, ``target_predicate``, ``objective_revision``,
  ``closure_policy``, ``observation_scope``, ``observation_method``, ``normalized_fact``,
  ``kernel_invariant``, ``next_observation_request``, ``reopen_condition``,
  ``reopen_condition_evaluation``, ``completion_claim`` -- named by this Kernel's schemas,
  none ever persisted as an immutable record by this vertical's Reflow Store.
- ``state``/``state_transition`` -- resolved through the State/Store's own dedicated lineage
  and transaction mechanisms (``load_current``/``resolve_transaction``), never through
  ``resolve_record`` -- a different, already-established resolution surface, not this
  registry's to duplicate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ReflowValidationError

#: Every Store-owned record kind this registry recognizes as a reference *target*. A
#: reference naming any other ``kind`` is not this vertical's to resolve (no Store-owned
#: producer exists for it), so :func:`reference_edges` never emits an edge toward one.
STORE_OWNED_REFERENCE_KINDS: frozenset[str] = frozenset(
    {
        "observation",
        "observation_evidence",
        "source_snapshot",
        "difference_event",
        "closure_evaluation",
        "evidence_sufficiency_result",
        "kernel_source_witness",
        "invariant_evaluation",
        "candidate_claim_evaluation_event",
        "candidate_completion_record",
    }
)

#: ``(source_record_kind, source_field_path) -> the closed set of kinds that field may
#: actually carry`` -- P8-R4-C3-F1's own canonical edge identity. *source_field_path* uses
#: :mod:`manosube_agent_civilization.difference.graph`'s own dotted-locator convention
#: (``[]`` iterates a list, ``.members[]`` reads an explicit ``UNORDERED_SET`` wrapper) so a
#: field this module shares with that registry is directly, textually comparable to it.
#: Every entry is the *complete* answer for that field -- a field admitting more than one
#: kind lists all of them, never a single guessed one -- confirmed against real schema and
#: producer code (this module's own docstring records the citation for each).
FIELD_EXPECTED_TARGET_KINDS: dict[tuple[str, str], frozenset[str]] = {
    # -- observation (01_SCHEMA/observation/observation.schema.json) -----------------------
    ("observation", "source_snapshot_refs[]"): frozenset({"source_snapshot"}),
    ("observation", "observation_evidence_refs[]"): frozenset({"observation_evidence"}),
    # -- observation_evidence (01_SCHEMA/evidence/evidence.schema.json) --------------------
    # observed_result.observation_ref: evidence/engine.py's own _common(), always
    # {"kind": "observation", ...}.
    ("observation_evidence", "observed_result.observation_ref"): frozenset({"observation"}),
    # lineage.derived_from.members[]: evidence/engine.py's own _lineage() call sites name
    # observation/difference/change/authority_decision members together (exhaustively
    # confirmed by an AST walk of every literal `"kind":` value passed to `_lineage()` in
    # that module -- only observation is Store-owned here).
    ("observation_evidence", "lineage.derived_from.members[]"): frozenset(
        {"observation", "difference", "change", "authority_decision"}
    ),
    # lineage.predecessor_evidence_refs.members[]: schema-pinned
    # ($defs/evidence_reference.kind is a JSON Schema const) to "observation_evidence".
    ("observation_evidence", "lineage.predecessor_evidence_refs.members[]"): frozenset(
        {"observation_evidence"}
    ),
    # artifact_references.members[].source_snapshot_ref: the member's own optional field
    # (never populated by any producer today, but schema-legal and never silently skipped).
    ("observation_evidence", "artifact_references.members[].source_snapshot_ref"): frozenset(
        {"source_snapshot"}
    ),
    # verification_result_provenance.target_refs.members[] (Structural Review Round 6,
    # P13-R6): the closed set is independent_verification.types.TARGET_REF_KINDS, the one
    # closed kind contract Independent Verification's own VerificationRequirement/
    # VerificationResult give this field -- observation_evidence is Store-owned here, exactly
    # as lineage.derived_from.members[] above mixes one Store-owned kind with several that
    # are not. verification_result_provenance.input_refs.members[] is deliberately absent
    # from this table: no closed kind contract exists anywhere for a verifier's own freely-
    # chosen input references (unlike target_refs, IndependentVerifier.__call__'s own contract
    # names no closed vocabulary for it), and inventing one here would be exactly the guessed
    # formula this module's own docstring already refuses to write.
    ("observation_evidence", "verification_result_provenance.target_refs.members[]"): frozenset(
        {"difference", "change", "observation_evidence"}
    ),
    # -- closure_evaluation (01_SCHEMA/difference/closure_evaluation.schema.json) ----------
    ("closure_evaluation", "kernel_source_witness_ref"): frozenset({"kernel_source_witness"}),
    ("closure_evaluation", "difference_event_head_ref"): frozenset({"difference_event"}),
    ("closure_evaluation", "after_state_candidate.source_snapshot_refs.members[]"): frozenset(
        {"source_snapshot"}
    ),
    ("closure_evaluation", "after_observation_refs[]"): frozenset({"observation"}),
    ("closure_evaluation", "change_result_evidence_refs[]"): frozenset({"observation_evidence"}),
    ("closure_evaluation", "change_free_verification_evidence_refs[]"): frozenset(
        {"observation_evidence"}
    ),
    ("closure_evaluation", "evidence_sufficiency_ref"): frozenset({"evidence_sufficiency_result"}),
    ("closure_evaluation", "terminal_reason_evidence_refs[]"): frozenset({"observation_evidence"}),
    # contradiction_refs[]: neither permitted kind is Store-owned -- classified, checked, and
    # (correctly) never emits a resolvable edge.
    ("closure_evaluation", "contradiction_refs[]"): frozenset(
        {"material_contradiction", "normalized_fact"}
    ),
    (
        "closure_evaluation",
        "candidate_invariant_evaluation_bindings[].invariant_evaluation_ref",
    ): frozenset({"invariant_evaluation"}),
    (
        "closure_evaluation",
        "candidate_invariant_evaluation_bindings[].evaluation_evidence_refs.members[]",
    ): frozenset({"observation_evidence", "negative_evidence"}),
    (
        "closure_evaluation",
        "candidate_claim_evaluation_bindings[].evaluation_head_event_ref",
    ): frozenset({"candidate_claim_evaluation_event"}),
    (
        "closure_evaluation",
        "candidate_claim_evaluation_bindings[].completion_record_ref",
    ): frozenset({"candidate_completion_record"}),
    (
        "closure_evaluation",
        "candidate_claim_evaluation_bindings[].evaluation_evidence_refs.members[]",
    ): frozenset({"observation_evidence", "negative_evidence"}),
    # -- difference_event (01_SCHEMA/difference/difference_lifecycle_event.schema.json) ---
    ("difference_event", "previous_event_id"): frozenset({"difference_event"}),
    ("difference_event", "observation_refs[]"): frozenset({"observation"}),
    ("difference_event", "evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("difference_event", "closure_evaluation_ref"): frozenset({"closure_evaluation"}),
    ("difference_event", "revoked_evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("difference_event", "invalid_evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("difference_event", "contradiction_evidence_refs[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    # -- evidence_sufficiency_result --------------------------------------------------------
    ("evidence_sufficiency_result", "evidence_refs.members[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    # -- invariant_evaluation ----------------------------------------------------------------
    ("invariant_evaluation", "evidence_refs.members[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    # -- candidate_claim_evaluation_event ----------------------------------------------------
    ("candidate_claim_evaluation_event", "predecessor_event_ref"): frozenset(
        {"candidate_claim_evaluation_event"}
    ),
    ("candidate_claim_evaluation_event", "completion_record_ref"): frozenset(
        {"candidate_completion_record"}
    ),
    # -- candidate_completion_record ----------------------------------------------------------
    ("candidate_completion_record", "required_evidence_refs.members[]"): frozenset(
        {"observation_evidence", "negative_evidence"}
    ),
    ("candidate_completion_record", "invariant_evaluation_refs.members[]"): frozenset(
        {"invariant_evaluation"}
    ),
}


@dataclass(frozen=True)
class TypedReferenceEdge:
    """One Store-owned reference edge, carrying the field provenance that produced it.

    *source_kind*/*field_path* are what P8-R4-C3-F1 requires diagnostics to name: which
    record, and which exact field/path (member index included), declared this edge -- never
    merely "some (kind, id) tuple somewhere". A bare 2-tuple cannot carry this
    (``BARE_KIND_ID_TUPLE_SUFFICIENT=false``).
    """

    source_kind: str
    field_path: str
    target_kind: str
    target_id: str

    def __iter__(self):
        # Deliberately still destructures as ``(kind, id)`` for call sites that only need
        # the pair to resolve against the Store -- the diagnostic fields are named
        # attributes, not silently dropped, never a second, competing shape.
        return iter((self.target_kind, self.target_id))


def _check(
    edges: list[TypedReferenceEdge],
    *,
    source_kind: str,
    field_key: str,
    diagnostic_path: str,
    ref: Any,
) -> None:
    """Validate one reference value against its own field's expected target kind(s).

    ``NULL_REFERENCE=NO_EDGE``: an absent reference is not an edge and is not an error.
    Every other shape or kind violation fails closed with
    :class:`~manosube_agent_civilization.reflow.errors.ReflowValidationError`, before this
    function -- and therefore before any caller's Store resolution -- ever returns an edge
    for it (``KIND_VALIDATION_PRECEDES_STORE_RESOLUTION=true``,
    ``KIND_VALIDATION_PRECEDES_ANY_WRITE=true``). Only a reference whose actual kind is
    both permitted for this field *and* itself Store-owned becomes a
    :class:`TypedReferenceEdge`; a permitted-but-external kind (``material_contradiction``,
    ``negative_evidence``, ``difference``, ``change``, ...) is valid here and correctly
    produces no edge to resolve.
    """

    if ref is None:
        return
    allowed = FIELD_EXPECTED_TARGET_KINDS.get((source_kind, field_key))
    if allowed is None:
        raise ReflowValidationError(
            f"{source_kind}.{diagnostic_path}: no expected target kind is registered for "
            "this reference field -- UNKNOWN_CLASSIFICATION_A_FIELD_PATH"
        )
    if not isinstance(ref, dict):
        raise ReflowValidationError(
            f"{source_kind}.{diagnostic_path}: reference value is not an object: {ref!r}"
        )
    kind = ref.get("kind")
    ref_id = ref.get("id")
    if not isinstance(kind, str) or not kind:
        raise ReflowValidationError(
            f"{source_kind}.{diagnostic_path}: reference is missing a non-empty kind: {ref!r}"
        )
    if not isinstance(ref_id, str) or not ref_id:
        raise ReflowValidationError(
            f"{source_kind}.{diagnostic_path}: reference is missing a non-empty id: {ref!r}"
        )
    if kind not in allowed:
        raise ReflowValidationError(
            f"{source_kind}.{diagnostic_path}: reference kind {kind!r} is not permitted here "
            f"-- expected one of {sorted(allowed)}, CROSS_KIND_SUBSTITUTION_ALLOWED=false"
        )
    if kind in STORE_OWNED_REFERENCE_KINDS:
        edges.append(TypedReferenceEdge(source_kind, diagnostic_path, kind, ref_id))


def _check_list(
    edges: list[TypedReferenceEdge], *, source_kind: str, field_key: str, values: Any
) -> None:
    """*field_key* ends with ``"[]"`` -- a bare JSON array of references."""

    base = field_key[: -len("[]")]
    for index, ref in enumerate(values or []):
        _check(
            edges,
            source_kind=source_kind,
            field_key=field_key,
            diagnostic_path=f"{base}[{index}]",
            ref=ref,
        )


def _check_members(
    edges: list[TypedReferenceEdge],
    *,
    source_kind: str,
    field_key: str,
    collection: Any,
    path_prefix: str | None = None,
) -> None:
    """*field_key* ends with ``".members[]"`` -- an ``UNORDERED_SET``-wrapped collection."""

    if collection is None:
        return
    if not isinstance(collection, dict):
        raise ReflowValidationError(
            f"{source_kind}.{path_prefix or field_key}: reference collection is not an "
            f"object: {collection!r}"
        )
    base = (path_prefix if path_prefix is not None else field_key)[: -len(".members[]")]
    for index, ref in enumerate(collection.get("members") or []):
        _check(
            edges,
            source_kind=source_kind,
            field_key=field_key,
            diagnostic_path=f"{base}.members[{index}]",
            ref=ref,
        )


def reference_edges(kind: str, body: dict[str, Any]) -> list[TypedReferenceEdge]:
    """Return every :class:`TypedReferenceEdge` *body* (an admitted record of *kind*)
    declares toward another Store-owned record -- fail-closed on any reference whose shape
    is malformed or whose actual kind is not the one its own field permits
    (:data:`FIELD_EXPECTED_TARGET_KINDS`), before this function ever returns one for a
    caller to resolve.

    Covers, completely, every reference field each Store-owned record kind's own canonical
    schema declares (``00_KERNEL/VERTICAL_PROOF_CONTRACT.md``'s Reference Field
    Classification table is this function's own specification):

    - ``observation``: ``source_snapshot_refs``, ``observation_evidence_refs``.
    - ``observation_evidence``: ``observed_result.observation_ref``,
      ``lineage.derived_from``/``lineage.predecessor_evidence_refs`` members, each
      ``artifact_references`` member's own optional ``source_snapshot_ref``, and (Structural
      Review Round 6, P13-R6) ``verification_result_provenance.target_refs`` members --
      ``verification_result_provenance.input_refs`` is deliberately never walked (see
      :data:`FIELD_EXPECTED_TARGET_KINDS`'s own comment for why).
    - ``closure_evaluation``: ``kernel_source_witness_ref``, ``difference_event_head_ref``,
      the embedded ``after_state_candidate``'s own ``source_snapshot_refs`` members,
      ``after_observation_refs``, ``change_result_evidence_refs``,
      ``change_free_verification_evidence_refs``, ``evidence_sufficiency_ref``,
      ``terminal_reason_evidence_refs``, ``contradiction_refs`` (permitted kinds are both
      external, so this edge is checked but never emitted), and -- recursively, the embedded
      reference fields nested inside each ``candidate_invariant_evaluation_bindings``/
      ``candidate_claim_evaluation_bindings`` entry.
    - ``difference_event``: ``previous_event_id`` (a bare id string -- the kind is always
      ``difference_event``, its own vocabulary's one self-reference), ``observation_refs``,
      ``evidence_refs``, ``closure_evaluation_ref``, ``revoked_evidence_refs``,
      ``invalid_evidence_refs``, ``contradiction_evidence_refs``.
    - ``evidence_sufficiency_result``/``invariant_evaluation``: ``evidence_refs`` members.
    - ``candidate_claim_evaluation_event``: ``predecessor_event_ref``,
      ``completion_record_ref``.
    - ``candidate_completion_record``: ``required_evidence_refs`` members,
      ``invariant_evaluation_refs`` members.
    - ``source_snapshot``, ``kernel_source_witness``: leaf record kinds -- their own
      canonical schemas declare no reference field of any kind, so neither emits an edge.

    Raises :class:`~manosube_agent_civilization.reflow.errors.ReflowValidationError` if
    *kind* is not one of :data:`STORE_OWNED_REFERENCE_KINDS` -- an unrecognized source
    record kind fails closed rather than silently returning no edges
    (``UNKNOWN_SOURCE_RECORD_KIND`` is refused, never conflated with a genuine leaf kind's
    legitimate zero-edge result).
    """

    if kind not in STORE_OWNED_REFERENCE_KINDS:
        raise ReflowValidationError(
            f"{kind!r} is not a Store-owned record kind this registry recognizes -- "
            "UNKNOWN_SOURCE_RECORD_KIND"
        )

    edges: list[TypedReferenceEdge] = []

    if kind == "observation":
        _check_list(
            edges,
            source_kind=kind,
            field_key="source_snapshot_refs[]",
            values=body.get("source_snapshot_refs"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="observation_evidence_refs[]",
            values=body.get("observation_evidence_refs"),
        )
    elif kind == "observation_evidence":
        observed_result = body.get("observed_result") or {}
        _check(
            edges,
            source_kind=kind,
            field_key="observed_result.observation_ref",
            diagnostic_path="observed_result.observation_ref",
            ref=observed_result.get("observation_ref"),
        )
        lineage = body.get("lineage") or {}
        _check_members(
            edges,
            source_kind=kind,
            field_key="lineage.derived_from.members[]",
            collection=lineage.get("derived_from"),
        )
        _check_members(
            edges,
            source_kind=kind,
            field_key="lineage.predecessor_evidence_refs.members[]",
            collection=lineage.get("predecessor_evidence_refs"),
        )
        artifact_members = (body.get("artifact_references") or {}).get("members") or []
        for index, artifact_ref in enumerate(artifact_members):
            if not isinstance(artifact_ref, dict):
                raise ReflowValidationError(
                    f"observation_evidence.artifact_references.members[{index}] is not an "
                    f"object: {artifact_ref!r}"
                )
            _check(
                edges,
                source_kind=kind,
                field_key="artifact_references.members[].source_snapshot_ref",
                diagnostic_path=f"artifact_references.members[{index}].source_snapshot_ref",
                ref=artifact_ref.get("source_snapshot_ref"),
            )
        verification_result_provenance = body.get("verification_result_provenance")
        if isinstance(verification_result_provenance, dict):
            _check_members(
                edges,
                source_kind=kind,
                field_key="verification_result_provenance.target_refs.members[]",
                collection=verification_result_provenance.get("target_refs"),
            )
        elif verification_result_provenance is not None:
            raise ReflowValidationError(
                "observation_evidence.verification_result_provenance is not an object: "
                f"{verification_result_provenance!r}"
            )
    elif kind == "closure_evaluation":
        _check(
            edges,
            source_kind=kind,
            field_key="kernel_source_witness_ref",
            diagnostic_path="kernel_source_witness_ref",
            ref=body.get("kernel_source_witness_ref"),
        )
        _check(
            edges,
            source_kind=kind,
            field_key="difference_event_head_ref",
            diagnostic_path="difference_event_head_ref",
            ref=body.get("difference_event_head_ref"),
        )
        after_state_candidate = body.get("after_state_candidate")
        if isinstance(after_state_candidate, dict):
            _check_members(
                edges,
                source_kind=kind,
                field_key="after_state_candidate.source_snapshot_refs.members[]",
                collection=after_state_candidate.get("source_snapshot_refs"),
            )
        elif after_state_candidate is not None:
            raise ReflowValidationError(
                "closure_evaluation.after_state_candidate is not an object: "
                f"{after_state_candidate!r}"
            )
        _check_list(
            edges,
            source_kind=kind,
            field_key="after_observation_refs[]",
            values=body.get("after_observation_refs"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="change_result_evidence_refs[]",
            values=body.get("change_result_evidence_refs"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="change_free_verification_evidence_refs[]",
            values=body.get("change_free_verification_evidence_refs"),
        )
        _check(
            edges,
            source_kind=kind,
            field_key="evidence_sufficiency_ref",
            diagnostic_path="evidence_sufficiency_ref",
            ref=body.get("evidence_sufficiency_ref"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="terminal_reason_evidence_refs[]",
            values=body.get("terminal_reason_evidence_refs"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="contradiction_refs[]",
            values=body.get("contradiction_refs"),
        )
        for binding_index, binding in enumerate(
            body.get("candidate_invariant_evaluation_bindings") or []
        ):
            if not isinstance(binding, dict):
                raise ReflowValidationError(
                    "closure_evaluation.candidate_invariant_evaluation_bindings"
                    f"[{binding_index}] is not an object: {binding!r}"
                )
            _check(
                edges,
                source_kind=kind,
                field_key="candidate_invariant_evaluation_bindings[].invariant_evaluation_ref",
                diagnostic_path=(
                    f"candidate_invariant_evaluation_bindings[{binding_index}]"
                    ".invariant_evaluation_ref"
                ),
                ref=binding.get("invariant_evaluation_ref"),
            )
            _check_members(
                edges,
                source_kind=kind,
                field_key=(
                    "candidate_invariant_evaluation_bindings[].evaluation_evidence_refs.members[]"
                ),
                collection=binding.get("evaluation_evidence_refs"),
                path_prefix=(
                    f"candidate_invariant_evaluation_bindings[{binding_index}]"
                    ".evaluation_evidence_refs.members[]"
                ),
            )
        for binding_index, binding in enumerate(
            body.get("candidate_claim_evaluation_bindings") or []
        ):
            if not isinstance(binding, dict):
                raise ReflowValidationError(
                    "closure_evaluation.candidate_claim_evaluation_bindings"
                    f"[{binding_index}] is not an object: {binding!r}"
                )
            _check(
                edges,
                source_kind=kind,
                field_key="candidate_claim_evaluation_bindings[].evaluation_head_event_ref",
                diagnostic_path=(
                    f"candidate_claim_evaluation_bindings[{binding_index}]"
                    ".evaluation_head_event_ref"
                ),
                ref=binding.get("evaluation_head_event_ref"),
            )
            _check(
                edges,
                source_kind=kind,
                field_key="candidate_claim_evaluation_bindings[].completion_record_ref",
                diagnostic_path=(
                    f"candidate_claim_evaluation_bindings[{binding_index}].completion_record_ref"
                ),
                ref=binding.get("completion_record_ref"),
            )
            _check_members(
                edges,
                source_kind=kind,
                field_key=(
                    "candidate_claim_evaluation_bindings[].evaluation_evidence_refs.members[]"
                ),
                collection=binding.get("evaluation_evidence_refs"),
                path_prefix=(
                    f"candidate_claim_evaluation_bindings[{binding_index}]"
                    ".evaluation_evidence_refs.members[]"
                ),
            )
    elif kind == "difference_event":
        previous_event_id = body.get("previous_event_id")
        if previous_event_id is not None:
            if not isinstance(previous_event_id, str) or not previous_event_id:
                raise ReflowValidationError(
                    "difference_event.previous_event_id is not a non-empty string: "
                    f"{previous_event_id!r}"
                )
            edges.append(
                TypedReferenceEdge(
                    "difference_event", "previous_event_id", "difference_event", previous_event_id
                )
            )
        _check_list(
            edges,
            source_kind=kind,
            field_key="observation_refs[]",
            values=body.get("observation_refs"),
        )
        _check_list(
            edges, source_kind=kind, field_key="evidence_refs[]", values=body.get("evidence_refs")
        )
        _check(
            edges,
            source_kind=kind,
            field_key="closure_evaluation_ref",
            diagnostic_path="closure_evaluation_ref",
            ref=body.get("closure_evaluation_ref"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="revoked_evidence_refs[]",
            values=body.get("revoked_evidence_refs"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="invalid_evidence_refs[]",
            values=body.get("invalid_evidence_refs"),
        )
        _check_list(
            edges,
            source_kind=kind,
            field_key="contradiction_evidence_refs[]",
            values=body.get("contradiction_evidence_refs"),
        )
    elif kind in ("evidence_sufficiency_result", "invariant_evaluation"):
        _check_members(
            edges,
            source_kind=kind,
            field_key="evidence_refs.members[]",
            collection=body.get("evidence_refs"),
        )
    elif kind == "candidate_claim_evaluation_event":
        _check(
            edges,
            source_kind=kind,
            field_key="predecessor_event_ref",
            diagnostic_path="predecessor_event_ref",
            ref=body.get("predecessor_event_ref"),
        )
        _check(
            edges,
            source_kind=kind,
            field_key="completion_record_ref",
            diagnostic_path="completion_record_ref",
            ref=body.get("completion_record_ref"),
        )
    elif kind == "candidate_completion_record":
        _check_members(
            edges,
            source_kind=kind,
            field_key="required_evidence_refs.members[]",
            collection=body.get("required_evidence_refs"),
        )
        _check_members(
            edges,
            source_kind=kind,
            field_key="invariant_evaluation_refs.members[]",
            collection=body.get("invariant_evaluation_refs"),
        )
    return edges
