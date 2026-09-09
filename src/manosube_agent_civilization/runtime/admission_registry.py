"""The canonical current-root-admission pointer, and the one sanctioned way to move it (Phase 15
Structural Review Round 4, Issue #64, P15-R4-F1, item 5).

**The defect this module closes.** Round 3 made
:func:`~manosube_agent_civilization.runtime.bootstrap.
bootstrap_projection_execution_capability` require a canonical, Store-committed, ACTIVE
``runtime_root_admission`` genuinely signed by an externally supplied deployment trust anchor --
a real control, and still required. But it asked only *does a matching ACTIVE admission record
exist and resolve?*, which is exactly the question Round 3 itself had already rejected one level
down, for deployment declarations, as the ineffective-revocation defect:

```text
admission A committed, ACTIVE, anchor-signed        composition succeeds -- correct
deployment revokes the boundary: mints B(REVOKED)   A keeps its own unchanged content address,
                                                    stays resolvable, stays signature-valid, and
                                                    stays ACTIVE forever
composition presented with A again                  ACCEPTED under Round 3 -- and wrong
```

The review named this explicitly ("must not repeat the declaration-currency defect below"), so
the correction is the *identical class* of fix rather than a second scheme of its own: a root
admission now carries signed ``generation``/``predecessor_ref`` fields, its own chain has a
current-admission pointer in Project State, and this module is the one sanctioned way to move it
-- through the identical shared mechanism the declaration chain uses
(:mod:`~manosube_agent_civilization.runtime.transition_chain`), so the two lifecycles cannot
drift apart into two different meanings of "current".

```text
semantic_state.runtime.claims["ROOT-ADMISSION:<project_binding_id>"] -> runtime_root_admission_id
```

**Why that key shape.** Both chains record their pointers in the identical
``semantic_state.runtime.claims`` map Round 3 established -- still with no State schema change of
any kind -- so their key spaces must be *provably* disjoint rather than merely observed not to
collide. A deployment target key is exactly ``RUNTIME-DEPLOYMENT-TARGET-`` plus 64 uppercase hex
characters; an admission chain key always contains a ``":"``, which that alphabet cannot produce
at any position. See :data:`~manosube_agent_civilization.runtime.identity.
ROOT_ADMISSION_TARGET_KEY_PREFIX` and the structural proof in
``tests/unit/runtime/test_runtime_transition_chain.py``.

**Who calls this, and why it takes a trust anchor when the request path never may.** Issuing,
rotating, or revoking a root admission *is* the deployment/composition boundary acting -- it is
the act of deciding which world is canonical at all. That is precisely the one place Contract 1
admits the raw anchor: this committer and
:func:`~manosube_agent_civilization.runtime.bootstrap.
compose_trusted_runtime_deployment_authority` are the only shipped functions that name a trust
anchor parameter outside the pure verification wrapper itself, and neither of them is
request-facing. The request-facing bootstrap's own signature carries no anchor, no admission
reference, no Store, no Project, and no Binding -- proved by introspection in
``tests/contract/runtime/test_runtime_static_conformance.py``.

This module holds no private key and mints no signature. It only ever verifies (see
:mod:`~manosube_agent_civilization.runtime.root_admission`), and it is not a second State owner:
the shared mechanism hands one transition plan to the Store's own single sanctioned committer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project

from .engine import require_valid_root_admission
from .errors import RuntimeRequirementError
from .identity import (
    runtime_root_admission_id,
    runtime_root_admission_semantic_fingerprint,
    runtime_root_admission_target_key,
)
from .root_admission import verify_runtime_root_admission_signature
from .transition_chain import (
    MonotonicChainSpec,
    commit_chain_transition,
    current_chain_record_id,
)

#: The canonical Store record kind this module commits, and the one
#: :mod:`~manosube_agent_civilization.runtime.bootstrap`'s own composition entry point resolves.
ROOT_ADMISSION_RECORD_KIND = "runtime_root_admission"

#: Everything about a ``runtime_root_admission`` the shared monotonic-chain mechanism needs, and
#: nothing else. The chain *rules* live there; only these bindings live here -- deliberately the
#: identical shape :data:`~manosube_agent_civilization.runtime.deployment_registry.
#: DEPLOYMENT_DECLARATION_CHAIN` has, because the lifecycle genuinely is the same one.
ROOT_ADMISSION_CHAIN = MonotonicChainSpec(
    record_kind=ROOT_ADMISSION_RECORD_KIND,
    id_field="runtime_root_admission_id",
    semantic_fingerprint_field="runtime_root_admission_semantic_fingerprint",
    require_valid=require_valid_root_admission,
    recompute_id=runtime_root_admission_id,
    recompute_semantic_fingerprint=runtime_root_admission_semantic_fingerprint,
    chain_key_of=runtime_root_admission_target_key,
)


def current_root_admission_id(current_state: Mapping[str, Any], chain_key: str) -> str | None:
    """Return the ``runtime_root_admission_id`` *current_state*'s own canonical pointer names for
    *chain_key*, or ``None`` when no admission has ever been made current for that Project Binding
    through :func:`commit_runtime_root_admission`.

    A pure read over the shared pointer mechanism -- no Store I/O, no resolution, no verification.
    ``None`` means *this deployment boundary has admitted nothing here*, which the composition
    entry point treats as a refusal, exactly as a missing declaration pointer is a refusal on the
    observation route.
    """

    return current_chain_record_id(current_state, chain_key)


def commit_runtime_root_admission(
    store: Any,
    project_id: str,
    admission: Mapping[str, Any],
    *,
    trust_anchor_public_key_hex: str,
    committed_at: str,
) -> dict[str, Any]:
    """Commit *admission* **and** make it this Project Binding's own current root admission, in
    one atomic :func:`~manosube_agent_civilization.store.commit.commit_state_transition` call --
    if, and only if, it is a legal monotonic transition from whatever is current right now.

    ```text
    A(ACTIVE, g=0)  -> B(ACTIVE, g=1, pred=A)     anchor rotation / re-admission
    A(ACTIVE, g=0)  -> B(REVOKED, g=1, pred=A)    the deployment withdraws this boundary;
                                                  TERMINAL for this Project Binding's chain
    replay A after either                          refused; the pointer stays at B, so a fresh
                                                   composition that still references A's own
                                                   individually-valid, individually-resolvable,
                                                   individually-anchor-signed record is refused
    ```

    *trust_anchor_public_key_hex* is a raw 32-byte Ed25519 **public** key, hex-encoded, supplied
    by the deployment/composition boundary from its own configuration -- never read from the Store
    being admitted, never derived from anything on a request path, and never a constant baked into
    shipped source. It is required here for the same reason the declaration committer requires a
    Boot-restored Human Authority key: a committer that cannot tell a genuine statement from a
    forged one cannot honestly decide whether that statement may move a chain, and ``generation``
    and ``predecessor_ref`` are part of exactly what this signature covers.

    Returns ``{"runtime_root_admission_ref", "runtime_root_admission_chain_key", "generation",
    "transition", "committed_state"}``.

    *committed_at* is required and caller-supplied: this module reads no clock.
    """

    if not isinstance(trust_anchor_public_key_hex, str) or not trust_anchor_public_key_hex:
        raise RuntimeRequirementError(
            "trust_anchor_public_key_hex must be a non-empty hex-encoded Ed25519 public key, "
            "supplied by the deployment/composition boundary itself -- never read from the Store "
            "being admitted, and never derived from anything on the request path"
        )

    def verify(checked: dict[str, Any], _current_state: Mapping[str, Any]) -> None:
        binding_ref = checked.get("project_binding_ref")
        binding_id = binding_ref.get("id") if isinstance(binding_ref, Mapping) else None
        if not isinstance(binding_id, str) or not binding_id:
            raise RuntimeRequirementError(
                "runtime_root_admission carries no readable project_binding_ref.id -- refusing "
                f"to commit it: {binding_ref!r}"
            )
        # Boot proves the Project Binding this admission names is genuinely restorable for this
        # project -- an admission cannot be committed against a Binding this project never
        # adopted. Nothing Boot restores is used to decide the admission's own trust: that is the
        # anchor's job, deliberately, and the anchor is not resolvable from inside this Store.
        boot_project(store, project_id=project_id, project_binding_id=binding_id)
        if not verify_runtime_root_admission_signature(
            checked, trust_anchor_public_key_hex=trust_anchor_public_key_hex
        ):
            raise RuntimeRequirementError(
                "runtime_root_admission carries no genuine signature over its own adopted "
                "semantic fields by the externally supplied trust anchor -- an unsigned, "
                "self-authored, or foreign-world-signed admission may never open, rotate, or "
                "revoke a deployment's own admission chain, and this is the one check an "
                "internally self-consistent alternate world cannot satisfy"
            )

    result = commit_chain_transition(
        store,
        project_id,
        admission,
        spec=ROOT_ADMISSION_CHAIN,
        committed_at=committed_at,
        verify=verify,
    )
    return {
        "runtime_root_admission_ref": result["record_ref"],
        "runtime_root_admission_chain_key": result["chain_key"],
        "generation": result["generation"],
        "transition": result["transition"],
        "committed_state": result["committed_state"],
    }


__all__ = [
    "ROOT_ADMISSION_CHAIN",
    "ROOT_ADMISSION_RECORD_KIND",
    "commit_runtime_root_admission",
    "current_root_admission_id",
]
