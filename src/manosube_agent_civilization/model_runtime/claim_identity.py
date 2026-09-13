"""Identity, semantic fingerprint and schema verification for the one Phase 19 companion
record kind this route ever commits atomically alongside its own Envelope (Structural Review
Round 5's own P19-R5-F2, narrowed by Structural Review Round 6's own P19-R6-F2).

Structural Review Round 5's own fix bound the caller-supplied claim body to *this* Envelope and
required a non-empty declared id -- but it could not independently recompute that id or the
claim's own semantic fingerprint, since that hash formula lived in ``multi_agent.identity``, and
this route may never import ``multi_agent`` (that package depends on this one, never the
reverse). Exact-head reproduction showed the gap that left open: a caller-selected non-empty
claim id, a wrong ``project_id``/``plan_ref``/``slot_index``, a missing or forged semantic
fingerprint, and an additional unregistered field all passed this route's own shallow checks.

Structural Review Round 6, P19-R6-F2 closes it by relocation, not duplication: this module --
not ``multi_agent`` -- is now the single owner of this one closed kind's own identity, semantic
fingerprint, and schema. ``multi_agent`` imports these functions from here rather than defining
its own copy (its own construction-time self-verification and its own read-time resolver both
follow this same owner), so a public caller of :func:`~manosube_agent_civilization.model_runtime.
route.execute_model_work_unit` supplying a hand-rolled ``slot_attempt_envelope_claim_factory`` can
never produce a body whose declared id, semantic fingerprint, or shape this route cannot
independently recompute and verify. This is deliberately not a general dependency on
``multi_agent``: no name from that package is read here, and every function below is generic --
the identical ``sha256(canonical_json_bytes(projection))`` recipe every other canonical kind in
this repository already uses, and the identical ``validate_against_schema_id``-style generic
schema lookup every other domain's own ``validation.py`` already performs for a schema it reads
but does not itself own the *meaning* of.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import ModelRuntimeRequirementError

#: The one closed companion-record kind this route ever commits alongside its own Envelope --
#: the identical literal :data:`~manosube_agent_civilization.model_runtime.route.
#: _SLOT_ATTEMPT_ENVELOPE_CLAIM_RECORD_KIND` already names.
SLOT_ATTEMPT_ENVELOPE_CLAIM_KIND = "multi_agent_slot_attempt_envelope_claim"

#: This kind's own registered canonical schema ``$id`` -- read, never restated, by
#: :func:`require_schema_valid_slot_attempt_envelope_claim` below.
SLOT_ATTEMPT_ENVELOPE_CLAIM_SCHEMA_ID = (
    "https://schemas.manosube.org/agent-civilization-os/v0.1/multi_agent/"
    "multi_agent_slot_attempt_envelope_claim.schema.json"
)

#: The narrow, natural-key projection one claim addresses -- one per ``(plan, slot,
#: attempt_ordinal)``, relocated verbatim from ``multi_agent.identity`` (Structural Review
#: Round 6, P19-R6-F2): the field list itself is not this route's own invention, it is the fact
#: this one companion kind's own identity has always been defined by, now with a single owner.
_KEY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "plan_ref",
    "slot_index",
    "attempt_ordinal",
)

#: The complete-content projection this kind's own semantic fingerprint is computed over --
#: the narrow key above, plus the one field the narrow key deliberately excludes.
_SEMANTIC_FIELDS: tuple[str, ...] = (*_KEY_FIELDS, "model_execution_envelope_ref")


def _projection(record: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ModelRuntimeRequirementError(
            f"the Phase 19 slot-attempt-envelope-claim this call produced is not a readable "
            f"mapping: {record!r}"
        )
    missing = [field for field in fields if field not in record]
    if missing:
        raise ModelRuntimeRequirementError(
            f"the Phase 19 slot-attempt-envelope-claim this call produced carries no readable "
            f"{', '.join(missing)} -- its own identity cannot be recomputed"
        )
    return {field: record[field] for field in fields}


def multi_agent_slot_attempt_envelope_claim_id(claim: Any) -> str:
    """The narrow, natural-key content address of one Multi-Agent Slot Attempt Envelope Claim.

    The identical formula and field list ``multi_agent.identity`` used before Structural Review
    Round 6's own relocation -- moved here so this route can independently recompute it, never
    duplicated as a second, potentially-diverging implementation.
    """

    projection = _projection(claim, _KEY_FIELDS)
    return (
        "MULTI-AGENT-ENVELOPE-CLAIM-"
        + hashlib.sha256(canonical_json_bytes(projection)).hexdigest().upper()
    )


def multi_agent_slot_attempt_envelope_claim_semantic_fingerprint(claim: Any) -> str:
    """The full-content digest of one Multi-Agent Slot Attempt Envelope Claim -- covers every
    field the narrow id above deliberately excludes (``model_execution_envelope_ref``), so a
    claim whose own binding was redirected after construction is still detectable even though
    its own narrow id would not change."""

    projection = _projection(claim, _SEMANTIC_FIELDS)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def _default_schema_root() -> Path:
    module_path = Path(__file__).resolve()
    for candidate in (
        module_path.parents[3] / "01_SCHEMA",  # source checkout
        module_path.parents[2] / "01_SCHEMA",  # installed wheel at site-packages root
        Path.cwd() / "01_SCHEMA",
    ):
        if candidate.is_dir():
            return candidate
    raise ModelRuntimeRequirementError("canonical schema root is unavailable")


@lru_cache(maxsize=4)
def _validators(schema_root: Path) -> dict[str, Draft202012Validator]:
    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(schema_root.rglob("*.schema.json"))
    ]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return {
        schema["$id"]: Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        for schema in schemas
    }


def require_schema_valid_slot_attempt_envelope_claim(
    claim: Any, *, schema_root: Path | None = None
) -> None:
    """Validate *claim* against its own registered canonical schema, raising a fail-closed
    error on any violation -- including an additional, unregistered field
    (``additionalProperties: false``), which recomputing the id/semantic fingerprint alone can
    never catch, since both are projections over a *named* field set."""

    validators = _validators(schema_root or _default_schema_root())
    validator = validators.get(SLOT_ATTEMPT_ENVELOPE_CLAIM_SCHEMA_ID)
    if validator is None:
        raise ModelRuntimeRequirementError(
            f"canonical schema is unavailable: {SLOT_ATTEMPT_ENVELOPE_CLAIM_SCHEMA_ID}"
        )
    errors = sorted(validator.iter_errors(claim), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise ModelRuntimeRequirementError(
            "the Phase 19 slot-attempt-envelope-claim this call produced is not schema-valid "
            f"against {SLOT_ATTEMPT_ENVELOPE_CLAIM_SCHEMA_ID}: {detail}"
        )
