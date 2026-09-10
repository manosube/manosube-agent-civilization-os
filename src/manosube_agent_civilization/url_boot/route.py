"""The one public URL Boot route (Phase 17, Issue #69).

``URL_BOOT_OWNER_COUNT=1``, ``PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=1`` (this module) ``+1``
(:mod:`~manosube_agent_civilization.url_boot.evidence_handoff`'s own single hand-off route).

``observe_url_source`` re-verifies Project/Human Authority identity through the existing Boot
owner (:func:`~manosube_agent_civilization.boot.boot_project`), independently fingerprints an
explicit, fully decomposed source identity and a closed fetch Boundary (never trusting either
from a caller beyond their declared shape), refuses a source whose own hostname falls outside the
Boundary's own declared ``network_scope`` before Boot or any adapter is ever reached, calls the
one replaceable :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` exactly
once, and derives and commits one canonical URL Source Observation Envelope through the existing
Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition`). Read-only, so no
create-once-reuse-after side effect exists to protect -- observing the identical source under the
identical Boundary twice is two independent facts, not a duplicate external artifact, the
identical discipline :mod:`~manosube_agent_civilization.runtime.route` already established.

**Deliberately simpler authority model than Runtime (disclosed, P17 non-claim).** Runtime's own
route additionally resolves, authority-binds, and cryptographically verifies a Store-committed
``runtime_deployment_declaration`` before trusting a target's own claimed identity, because a
runtime target is a live, potentially adversarial system a caller could otherwise impersonate by
mere assertion. A URL Source Observation makes no such trust claim about the fetched content at
all: :data:`~manosube_agent_civilization.url_boot.types.URL_FETCH_OUTCOMES`'s own
``IDENTITY_MISMATCH``/``BOUNDARY_REFUSED`` members are the *adapter's own* honest, per-hop
classification (P17-C4/P17-C7 -- see ``types.py``'s own module docstring for why this route
performs no second, route-level semantic reinterpretation of them), never a route-computed
verdict this route derives from a signed declaration. What this route *does* independently
re-verify, itself, is Authority freshness and network-scope containment -- never the content.

**Deliberate departure from Runtime's own ``network.py`` precedent (P17-C5), applied here.**
Because a URL source is reached by real DNS resolution rather than a Boundary-declared literal
endpoint, this route re-checks *both* the requested source identity (before Boot, zero-call) and
whatever *effective* source identity the adapter reports it actually reached after following any
redirects (immediately after the adapter call, before persistence) against the Boundary's own
``network_scope`` -- neither site trusts the other, alone, to be the one place that check runs,
the identical "defense in depth, not exclusive ownership" discipline
``runtime/route.py``'s own P15-R1-F1 correction established for its own ``network.py``.

Canonical route (``12_URL_BOOT/URL_BOOT_CONTRACT.md`` §5):

```text
complete schema validation of the declared source identity and closed fetch Boundary
→ network-scope check on the requested source -- zero-call, before Boot or any adapter
→ real-instant time-window check -- refuses before any adapter call
→ real Project/Human Authority (Boot re-verification)
→ explicit source identity, fingerprinted (never trusted from a caller)
→ closed fetch Boundary, fingerprinted (never trusted from a caller)
→ deterministic source_request_identity (source + Boundary + issued_at)
→ authority-freshness re-check -- refuses before the adapter
→ replaceable URL Source Adapter -- one bounded, per-hop-reauthorized transport call, handed
  deep-frozen copies it cannot mutate
→ independent field-boundary projection (any field outside permitted_fields is a refusal, never
  silently kept), redaction, and a defense-in-depth network-scope re-check of whatever effective
  source identity the adapter reports it actually reached
→ canonical URL Source Observation Envelope
→ authority-freshness re-check on every commit attempt
→ existing canonical persistence boundary (commit_state_transition)
→ bounded URL Source Observation Receipt
```
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    URL_BOOT_SCHEMA_BASE,
    derive_url_source_observation_envelope,
    parse_utc_instant,
    require_valid_boundary,
    require_valid_source_identity,
    require_valid_timestamp,
)
from .errors import (
    UrlBootAdapterError,
    UrlBootAuthorityFreshnessError,
    UrlBootEnvelopeIntegrityError,
    UrlBootRequirementError,
)
from .identity import (
    url_boundary_fingerprint,
    url_observed_content_fingerprint,
    url_source_fingerprint,
    url_source_observation_envelope_semantic_fingerprint,
    url_source_request_identity,
)
from .network import require_source_within_network_scope
from .types import (
    RECEIPT_STATUSES,
    URL_FETCH_OUTCOMES,
    URL_OUTCOME_TO_RECEIPT_STATUS,
    UrlSourceAdapter,
    UrlSourceObservationReceipt,
    deep_freeze,
)

_ENVELOPE_RECORD_KIND = "url_source_observation_envelope"
#: The identical Compare-And-Swap retry bound Runtime's own ``_commit_envelope`` uses -- bounded
#: protection against genuine, ordinary contention from an unrelated commit landing on this
#: project between this route's own ``load_current`` and its own ``commit``.
_MAX_COMMIT_RETRIES = 8


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise UrlBootRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise UrlBootRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_within_time_window(boundary: dict[str, Any], observed_at: str) -> None:
    """Refuse before any adapter call unless *observed_at* falls within the Boundary's own
    declared, genuinely ordered, closed time window -- compared as real UTC instants, the
    identical discipline ``runtime/route.py``'s own ``_require_within_time_window`` applies."""

    issued_at = parse_utc_instant(
        boundary["time_window"]["issued_at"], "boundary.time_window.issued_at"
    )
    expires_at = parse_utc_instant(
        boundary["time_window"]["expires_at"], "boundary.time_window.expires_at"
    )
    observed = parse_utc_instant(observed_at, "observed_at")
    if not issued_at < expires_at:
        raise UrlBootRequirementError(
            "boundary.time_window is not a genuinely ordered window "
            f"({boundary['time_window']['issued_at']!r} .. "
            f"{boundary['time_window']['expires_at']!r}) -- refusing before any adapter call"
        )
    if not (issued_at <= observed <= expires_at):
        raise UrlBootRequirementError(
            f"retrieved_at {observed_at!r} falls outside the Boundary's own declared time "
            f"window [{boundary['time_window']['issued_at']!r}, "
            f"{boundary['time_window']['expires_at']!r}] -- refusing before any adapter call"
        )


def _project_to_permitted_fields(
    observed_fields: Mapping[str, Any], permitted_fields: list[str]
) -> dict[str, Any]:
    """Return *observed_fields* projected down to exactly *permitted_fields*, refusing any field
    the adapter reported that the closed Boundary never permitted -- the identical discipline
    ``runtime/route.py``'s own P15-R1-F3 correction established, applied here from the start."""

    extra = sorted(set(observed_fields) - set(permitted_fields))
    if extra:
        raise UrlBootAdapterError(
            "adapter.fetch() reported field(s) outside the Boundary's own permitted_fields: "
            f"{extra} -- refusing rather than persist anything the Boundary never admitted"
        )
    return {field: observed_fields[field] for field in permitted_fields if field in observed_fields}


def _redact(observed_fields: Mapping[str, Any], redaction_fields: list[str]) -> dict[str, Any]:
    redacted = set(redaction_fields)
    return {
        field: ("<REDACTED>" if field in redacted else value)
        for field, value in observed_fields.items()
    }


def _authority_context(boot_context: Any) -> dict[str, Any]:
    """Return the closed projection of *boot_context* that defines *whose authority* this
    observation is being made under -- the identical discipline
    ``runtime/route.py``'s own ``_authority_context`` establishes, applied here even though this
    package resolves no signed declaration: a Binding/Human Authority change between this call's
    own initial Boot and its own commit must still refuse rather than commit silently."""

    binding = boot_context.project_binding
    return {
        "project_binding_id": boot_context.project_binding_id,
        "human_authority_ref": boot_context.human_authority_ref,
        "human_authority_signing_key": binding.get("human_authority_signing_key"),
    }


def _boot_authority_context(store: Any, project_id: str, project_binding_id: str) -> Any:
    """The one literal ``boot_project`` call site in this module -- reached twice in a single
    observation (once to establish the authority this call runs under, once on every commit
    attempt), the identical discipline ``runtime/route.py`` already established."""

    return boot_project(store, project_id=project_id, project_binding_id=project_binding_id)


def _require_unchanged_authority_context(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    expected: Mapping[str, Any],
    stage: str,
) -> None:
    fresh = _authority_context(_boot_authority_context(store, project_id, project_binding_id))
    if fresh != dict(expected):
        raise UrlBootAuthorityFreshnessError(
            "the Project Binding / Human Authority verified at this observation's own initial "
            f"Boot is no longer the one this Store reports -- refusing {stage} rather than act "
            "under, or commit, stale authority"
        )


def observe_url_source(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    source_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: UrlSourceAdapter,
    observed_at: str,
) -> dict[str, Any]:
    """Bounded-observe one explicit URL source and return ``{"envelope": ..., "receipt":
    UrlSourceObservationReceipt}``.

    *source_identity* and *boundary* must already be real, explicit, closed shapes -- this
    function proves each completely valid against its own canonical schema before Boot or any
    adapter is reached, and fingerprints them itself (never trusting a caller-declared
    fingerprint). *observed_at* is a required, caller-supplied instant (this route reads no
    clock) that must fall within *boundary*'s own declared, closed time window, compared as real
    UTC instants.

    Zero-call refusals (before any adapter is ever reached, and before Boot for the first):

    - *source_identity*'s own hostname must be inside *boundary*'s own declared
      ``network_scope`` (P17-C1/P17-C5);
    - the Project Binding / Human Authority verified at this call's own initial Boot must still
      be the ones the Store reports -- re-proved again on every commit attempt.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(observed_at, "observed_at")

    checked_source_identity = require_valid_source_identity(source_identity)
    checked_boundary = require_valid_boundary(boundary)
    require_source_within_network_scope(checked_source_identity, checked_boundary["network_scope"])
    _require_within_time_window(checked_boundary, observed_at)

    boot_context = _boot_authority_context(store, project_id, project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)
    authority_context = _authority_context(boot_context)

    requested_source_fingerprint = url_source_fingerprint(checked_source_identity)
    boundary_fingerprint = url_boundary_fingerprint(checked_boundary)
    source_request_identity = url_source_request_identity(
        requested_source_fingerprint,
        boundary_fingerprint,
        checked_boundary["time_window"]["issued_at"],
    )

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise UrlBootAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated or "
            "unverifiable identity may never observe on this route's behalf"
        )

    _require_unchanged_authority_context(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        expected=authority_context,
        stage="before the adapter is reached",
    )

    raw = adapter.fetch(
        source_identity=deep_freeze(checked_source_identity),
        boundary=deep_freeze(checked_boundary),
    )
    if not isinstance(raw, Mapping):
        raise UrlBootAdapterError(f"adapter.fetch() returned {raw!r}, not a mapping")
    fetch_outcome = raw.get("fetch_outcome")
    if fetch_outcome not in URL_FETCH_OUTCOMES:
        raise UrlBootAdapterError(
            f"adapter.fetch()'s own fetch_outcome is not recognized: {fetch_outcome!r}"
        )

    raw_effective_identity = raw.get("effective_source_identity")
    effective_source_identity: dict[str, Any] | None = None
    effective_source_fingerprint: str | None = None
    if raw_effective_identity is not None:
        # Independent re-validation of whatever the adapter reports it actually reached
        # (defense in depth, P17-C5 -- neither this route nor the adapter's own per-hop check
        # is trusted to be the only place a redirect escape is caught).
        effective_source_identity = require_valid_source_identity(raw_effective_identity)
        require_source_within_network_scope(
            effective_source_identity, checked_boundary["network_scope"]
        )
        effective_source_fingerprint = url_source_fingerprint(effective_source_identity)

    response_status = raw.get("response_status")
    if response_status is not None and not isinstance(response_status, int):
        raise UrlBootAdapterError(
            f"adapter.fetch()'s own response_status is unreadable: {response_status!r}"
        )
    redirect_hop_count = raw.get("redirect_hop_count")
    if not isinstance(redirect_hop_count, int) or redirect_hop_count < 0:
        raise UrlBootAdapterError(
            f"adapter.fetch()'s own redirect_hop_count is unreadable: {redirect_hop_count!r}"
        )
    if redirect_hop_count > checked_boundary["redirect_policy"]["max_redirects"]:
        raise UrlBootAdapterError(
            f"adapter.fetch() reported redirect_hop_count={redirect_hop_count!r} exceeding the "
            f"Boundary's own max_redirects={checked_boundary['redirect_policy']['max_redirects']!r}"
        )

    if fetch_outcome == "OBSERVED":
        raw_observed_fields = raw.get("observed_fields")
        if not isinstance(raw_observed_fields, Mapping):
            raise UrlBootAdapterError(
                f"adapter.fetch() reported OBSERVED with no readable observed_fields: "
                f"{raw_observed_fields!r}"
            )
        observed_fields: dict[str, Any] | None = _redact(
            _project_to_permitted_fields(
                raw_observed_fields, list(checked_boundary["permitted_fields"])
            ),
            list(checked_boundary.get("redaction_fields", [])),
        )
        observed_content_fingerprint: str | None = url_observed_content_fingerprint(observed_fields)
    else:
        observed_fields = None
        observed_content_fingerprint = None

    envelope = derive_url_source_observation_envelope(
        project_id=project_id,
        requested_source_identity=checked_source_identity,
        requested_source_fingerprint=requested_source_fingerprint,
        effective_source_identity=effective_source_identity,
        effective_source_fingerprint=effective_source_fingerprint,
        boundary=checked_boundary,
        boundary_fingerprint=boundary_fingerprint,
        source_request_identity=source_request_identity,
        retrieved_at=observed_at,
        fetch_outcome=fetch_outcome,
        response_status=response_status,
        redirect_hop_count=redirect_hop_count,
        observed_fields=observed_fields,
        observed_content_fingerprint=observed_content_fingerprint,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
    )

    _commit_envelope(
        store,
        project_id,
        envelope,
        observed_at,
        project_binding_id=project_binding_id,
        authority_context=authority_context,
    )

    status = URL_OUTCOME_TO_RECEIPT_STATUS[fetch_outcome]
    if status not in RECEIPT_STATUSES:
        raise UrlBootAdapterError(f"unrecognized receipt status derived from outcome: {status!r}")

    receipt = UrlSourceObservationReceipt(
        status=status,
        url_source_observation_envelope_id=envelope["url_source_observation_envelope_id"],
        project_id=project_id,
        requested_source_identity=checked_source_identity,
        boundary=checked_boundary,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
        input_refs=(dict(real_human_authority_ref),),
        observations={
            "fetch_outcome": fetch_outcome,
            "observed_content_fingerprint": observed_content_fingerprint,
            "retrieved_at": observed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


def _commit_envelope(
    store: Any,
    project_id: str,
    envelope: dict[str, Any],
    committed_at: str,
    *,
    project_binding_id: str,
    authority_context: Mapping[str, Any],
) -> None:
    """Durably persist *envelope* through the Store's own single sanctioned committer, bounded
    Compare-And-Swap retry against genuine, unrelated contention only -- the identical discipline
    ``runtime/route.py``'s own ``_commit_envelope`` already establishes."""

    envelope_id = envelope["url_source_observation_envelope_id"]
    if (
        url_source_observation_envelope_semantic_fingerprint(envelope)
        != envelope["url_source_observation_semantic_fingerprint"]
    ):
        raise UrlBootEnvelopeIntegrityError(
            "newly derived envelope's own recomputed semantic fingerprint does not equal its "
            "own declared value -- refusing to commit"
        )

    for _ in range(_MAX_COMMIT_RETRIES):
        _require_unchanged_authority_context(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            expected=authority_context,
            stage="to commit this Envelope",
        )
        current_state = store.load_current(project_id)
        transaction_id = (
            f"TX-URL-SOURCE-OBSERVATION-{envelope_id}-{current_state['state_revision']}"
        )
        next_state = dict(current_state)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        transition = {
            "schema_version": "0.1",
            "transaction_id": transaction_id,
            "event_type": "TRANSITION",
            "project_id": project_id,
            "from_revision": current_state["state_revision"],
            "to_revision": next_state["state_revision"],
            "before_fingerprint": current_state["semantic_fingerprint"],
            "after_fingerprint": next_state["semantic_fingerprint"],
            "after_state": next_state,
            "evidence_refs": [],
            "committed_at": committed_at,
        }
        try:
            commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(_ENVELOPE_RECORD_KIND, envelope_id, envelope)],
            )
            return
        except RecordConflictError as error:
            raise UrlBootEnvelopeIntegrityError(
                f"a different record already occupies {_ENVELOPE_RECORD_KIND}/{envelope_id} "
                "with different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
    raise UrlBootRequirementError(
        f"could not durably commit {_ENVELOPE_RECORD_KIND}/{envelope_id} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


__all__ = ["URL_BOOT_SCHEMA_BASE", "observe_url_source"]
