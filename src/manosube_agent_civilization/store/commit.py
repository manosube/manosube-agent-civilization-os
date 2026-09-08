"""The one place in this package that ever calls ``FileStateStore.commit`` (Structural
Review Round 5-R1, Issue #51, P13-R5-R1: ``SINGLE_COMMITTER_REQUIRED``).

Neither Reflow nor Binding owns the atomic State-transition commit itself -- each owns only
its own reason for wanting one (Closure semantics for Reflow, Human declaration semantics
for Binding) and the transition plan (successor State + transition event + records) that
reason produces. This module owns nothing about *why* a commit is happening; it is a thin,
domain-agnostic pass-through to the Store's own already-atomic, already-idempotent
``commit`` method, so ``topology.py``'s own K-003/R-001 static scan has exactly one module to
sanction (:data:`~manosube_agent_civilization.topology._SANCTIONED_COMMIT_CALL_MODULES`)
regardless of how many domain owners build transition plans that end up here.
"""

from __future__ import annotations

from typing import Any, cast


def commit_state_transition(
    store: Any,
    project_id: str,
    expected_revision: int,
    expected_fingerprint: dict[str, Any],
    next_state: dict[str, Any],
    transition: dict[str, Any],
    *,
    records: list[tuple[str, str, dict[str, Any]]] | None = None,
    fault: Any | None = None,
) -> dict[str, Any]:
    """Call the Store's own ``commit`` exactly as given -- no domain interpretation, no
    validation beyond what ``FileStateStore.commit`` itself already performs (Compare-And-
    Swap, idempotent replay, transaction-conflict rejection, staged atomic commit). Every
    domain caller (``reflow.commit.commit_reflow``, ``binding.route.declare_human_grant``)
    builds its own *next_state*/*transition*/*records* first; this function never builds
    them itself."""

    # *store* is typed ``Any`` (the same convention ``reflow.commit.commit_reflow`` and
    # ``binding.route.declare_human_grant`` already use for their own *store* parameter) to
    # avoid importing the concrete ``FileStateStore`` type here; ``FileStateStore.commit``
    # itself is already fully typed to return ``dict[str, Any]``, so the cast only restores
    # the annotation the ``Any`` parameter erased -- it asserts nothing new.
    return cast(
        "dict[str, Any]",
        store.commit(
            project_id,
            expected_revision,
            expected_fingerprint,
            next_state,
            transition,
            records=records,
            fault=fault,
        ),
    )
