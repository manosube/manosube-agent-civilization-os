"""The canonical current-deployment-declaration pointer, and the one sanctioned way to move it
(Phase 15 Structural Review Round 3, Issue #64, P15-R3-F2).

**The defect this module closes.** Round 2 made a ``runtime_deployment_declaration`` signed,
status-bound, and cross-checked against the Human Authority the observing call's own Boot
restored. But the record is immutable and content-addressed, so minting a *new* record carrying
``status="REVOKED"`` never invalidated the original ``ACTIVE`` one: that record keeps its own
unchanged id and stays individually resolvable, individually signature-valid, and individually
schema-valid forever. A target already referencing the old ``ACTIVE`` record's id could keep
presenting that exact reference indefinitely, and Round 2's own "revoked" regression test proved
only that a *separately constructed* ``REVOKED`` record is refused -- never that an
*already-issued* ``ACTIVE`` declaration could actually be revoked at all.

**What replaces it.** "Current" stops meaning *whatever the caller happens to reference* and
starts meaning *whatever Project State's own pointer currently names*:

```text
semantic_state.runtime.claims[<target_key>]  ->  runtime_deployment_declaration_id
```

``<target_key>`` is :func:`~manosube_agent_civilization.runtime.identity.
runtime_deployment_target_key` over the four fields that decide *which target* a declaration is
about. Issuing **any** new declaration for that target through
:func:`commit_runtime_deployment_declaration` -- whether its own ``status`` is ``ACTIVE``
(a rotation) or ``REVOKED`` (a revocation) -- atomically moves the pointer, in the identical
``commit_state_transition`` call that commits the record itself. The superseded record remains
exactly as resolvable, as signed, and as within-window as it always was; it is simply no longer
what the pointer names, and :func:`~manosube_agent_civilization.runtime.route.
observe_runtime_target` refuses it on that basis alone.

**Why the pointer lives in ``semantic_state.runtime.claims``.** That property is already part of
the canonical, adopted ``01_SCHEMA/state/semantic_state.schema.json`` -- a ``$defs/domain`` whose
``claims`` is an open ``{string: scalar}`` map -- and Phase 15 had, until this round, never
written to the ``runtime`` domain at all (``route.py``'s own ``_commit_envelope`` bumps
``state_revision``/``lineage_head_ref``/``semantic_fingerprint`` and touches ``semantic_state``
nowhere). Recording a ``{target_key: declaration_id}`` mapping there needs **no schema change of
any kind**, keeps this layer from inventing a second State shape of its own, and leaves every
other field of that domain (``status``, ``identity_refs``, ``evidence_refs``, ``blind_spots``)
exactly as whoever owns them last left it -- this module merges into ``claims`` and never
replaces the domain. See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §12.2.

**This module is still not a second State owner.** It builds a transition plan and hands it to
the Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
primitive Reflow, Binding, Projection, and this package's own ``route.py`` already share),
exactly as every other domain owner in this repository does. It evaluates no Closure, mints no
Authority, and derives no Difference/Change/Evidence content; it persists one already-issued,
already-signed Human Authority statement and the pointer that says which one is current.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import require_valid_deployment_declaration
from .errors import RuntimeEnvelopeIntegrityError, RuntimeRequirementError
from .identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_target_key,
)

#: The canonical Store record kind this module commits, and the one
#: :mod:`~manosube_agent_civilization.runtime.route` resolves -- stated once, here, so the two
#: sites can never drift.
DEPLOYMENT_DECLARATION_RECORD_KIND = "runtime_deployment_declaration"

#: Where the current-declaration pointer lives inside Project State. ``semantic_state`` ->
#: this domain -> ``claims`` -> ``{target_key: declaration_id}``.
DEPLOYMENT_POINTER_SEMANTIC_DOMAIN = "runtime"
DEPLOYMENT_POINTER_CLAIMS_FIELD = "claims"

#: The identical bounded Compare-And-Swap retry ``route.py``'s own ``_commit_envelope`` uses --
#: not a timeout, not a backoff, bounded protection against genuine, ordinary contention from an
#: unrelated commit landing on this project between this call's own ``load_current`` and its own
#: ``commit``.
_MAX_COMMIT_RETRIES = 8


def current_deployment_declaration_id(
    current_state: Mapping[str, Any], target_key: str
) -> str | None:
    """Return the ``runtime_deployment_declaration_id`` *current_state*'s own canonical pointer
    names for *target_key*, or ``None`` when no declaration has ever been made current for that
    target through :func:`commit_runtime_deployment_declaration`.

    A pure read: no Store I/O, no resolution, no verification. *current_state* is whatever the
    caller already holds -- Boot's own deep-frozen ``current_state`` at resolution time, and a
    freshly loaded one at each commit attempt (P15-R3-F2's own post-check-substitution barrier).

    ``None`` is returned for every shape that cannot carry a pointer at all -- an absent or
    non-mapping ``semantic_state``/domain/``claims``, or a non-string value -- rather than
    raising: a missing pointer is a perfectly ordinary state of the world (nothing has been made
    current yet), and it is the *caller's* job to decide that "no current declaration" means a
    refusal. It always does, in this package's own only caller.
    """

    semantic_state = current_state.get("semantic_state")
    if not isinstance(semantic_state, Mapping):
        return None
    domain = semantic_state.get(DEPLOYMENT_POINTER_SEMANTIC_DOMAIN)
    if not isinstance(domain, Mapping):
        return None
    claims = domain.get(DEPLOYMENT_POINTER_CLAIMS_FIELD)
    if not isinstance(claims, Mapping):
        return None
    value = claims.get(target_key)
    return value if isinstance(value, str) else None


def _next_semantic_state(
    current_state: Mapping[str, Any], target_key: str, declaration_id: str
) -> dict[str, Any]:
    """Return a deep copy of *current_state*'s own ``semantic_state`` with exactly one claim
    added or replaced -- never a rebuilt domain, never a replaced ``semantic_state``.

    The scope is deliberately as narrow as ``reflow/bookkeeping.py``'s own single sanctioned
    ``semantic_state`` mutation: every other field of the ``runtime`` domain (its ``status``, its
    ``identity_refs``/``evidence_refs``, its ``blind_spots``) and every other domain is carried
    through byte-identical, so this Phase's own pointer can never silently redefine a domain
    whose semantics another owner holds.
    """

    semantic_state = current_state.get("semantic_state")
    if not isinstance(semantic_state, Mapping):
        raise RuntimeRequirementError(
            "the current Project State carries no readable semantic_state -- refusing to "
            "commit a runtime_deployment_declaration into a State this module cannot read"
        )
    next_semantic_state = deepcopy(dict(semantic_state))
    domain = next_semantic_state.get(DEPLOYMENT_POINTER_SEMANTIC_DOMAIN)
    if not isinstance(domain, dict):
        raise RuntimeRequirementError(
            "the current Project State carries no readable "
            f"semantic_state.{DEPLOYMENT_POINTER_SEMANTIC_DOMAIN} domain"
        )
    claims = domain.get(DEPLOYMENT_POINTER_CLAIMS_FIELD)
    if not isinstance(claims, dict):
        raise RuntimeRequirementError(
            "the current Project State carries no readable "
            f"semantic_state.{DEPLOYMENT_POINTER_SEMANTIC_DOMAIN}."
            f"{DEPLOYMENT_POINTER_CLAIMS_FIELD} map"
        )
    claims[target_key] = declaration_id
    return next_semantic_state


def commit_runtime_deployment_declaration(
    store: Any,
    project_id: str,
    declaration: Mapping[str, Any],
    *,
    committed_at: str,
) -> dict[str, Any]:
    """Commit *declaration* **and** make it the current declaration for its own target, in one
    atomic :func:`~manosube_agent_civilization.store.commit.commit_state_transition` call
    (P15-R3-F2).

    The two halves are inseparable by construction -- there is no call shape through which a
    caller could commit the record without moving the pointer, or move the pointer without
    committing the record:

    ```text
    records=[(runtime_deployment_declaration, <id>, <the record itself>)]   immutable, as always
    semantic_state.runtime.claims[<target_key>] = <id>                      the current pointer
    ```

    *declaration* must already be a real, complete, Human-Authority-signed record: this function
    proves it schema-valid and independently recomputes its own content address and semantic
    fingerprint, refusing on any mismatch, but it **never signs, mints, or repairs anything** --
    it holds no key and adds no field. It also deliberately does **not** re-verify the signature
    or the Boot-restored Authority binding: those are
    :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`'s own checks, run
    fresh against *that call's own* Boot at the moment an observation is actually made, and
    duplicating them here would create a second, drifting notion of "an acceptable declaration"
    that could disagree with the route's.

    Returns ``{"runtime_deployment_declaration_ref", "runtime_deployment_target_key",
    "committed_state"}``.

    *committed_at* is required and caller-supplied: this module reads no clock, the identical
    discipline every other route and committer in this repository already keeps.
    """

    checked = require_valid_deployment_declaration(declaration)
    declaration_id = checked["runtime_deployment_declaration_id"]
    if runtime_deployment_declaration_id(checked) != declaration_id:
        raise RuntimeRequirementError(
            "runtime_deployment_declaration own recomputed identity does not equal its own "
            "declared value -- refusing to commit it or to make it current"
        )
    if runtime_deployment_declaration_semantic_fingerprint(checked) != checked.get(
        "runtime_deployment_declaration_semantic_fingerprint"
    ):
        raise RuntimeRequirementError(
            "runtime_deployment_declaration own recomputed semantic fingerprint does not equal "
            "its own declared value -- refusing to commit it or to make it current"
        )
    if checked.get("project_id") != project_id:
        raise RuntimeRequirementError(
            "runtime_deployment_declaration names a different project than the one being "
            f"committed into: {checked.get('project_id')!r} != {project_id!r}"
        )
    target_key = runtime_deployment_target_key(checked)

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"TX-{declaration_id}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["semantic_state"] = _next_semantic_state(
            current_state, target_key, declaration_id
        )
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
                records=[(DEPLOYMENT_DECLARATION_RECORD_KIND, declaration_id, dict(checked))],
            )
        except RecordConflictError as error:
            raise RuntimeEnvelopeIntegrityError(
                f"a different record already occupies {DEPLOYMENT_DECLARATION_RECORD_KIND}/"
                f"{declaration_id} with different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
        return {
            "runtime_deployment_declaration_ref": {
                "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
                "id": declaration_id,
            },
            "runtime_deployment_target_key": target_key,
            "committed_state": next_state,
        }
    raise RuntimeRequirementError(
        f"could not durably commit {DEPLOYMENT_DECLARATION_RECORD_KIND}/{declaration_id} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


__all__ = [
    "DEPLOYMENT_DECLARATION_RECORD_KIND",
    "commit_runtime_deployment_declaration",
    "current_deployment_declaration_id",
]
