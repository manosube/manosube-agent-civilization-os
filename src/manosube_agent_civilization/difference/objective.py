"""The Objective revision chain conformance authority.

An Objective revision is Human Authority input this phase consumes and re-emits. Its
individual schema says nothing about its *position*: revision numbering, the immediate
predecessor it binds, and the base fingerprint that ties it to that predecessor's semantics
are relations between records, so every revision of a discontinuous history is individually
valid and the history is not.

The independent contract validator already computed this — and then used the result only to
decide whether to *trust* an Objective head, never reporting it. So an invalid chain did not
fail; it silently changed what other rules concluded, and the error that surfaced named an
evaluation head rather than the chain. The Engine, meanwhile, merged and emitted the
revisions and derived a Difference from an invalid Human Objective history.

The rule lives here once and both read it, so a discontinuity is stated as itself.

Chain completeness is not assumed: it is guaranteed upstream. ``previous_objective_ref`` is
a declared reference edge over a resolvable kind, so a carried revision N drags in N-1
transitively down to revision 0, whose predecessor is ``null``. This rule therefore reads a
group as the whole history of that Objective.
"""

from __future__ import annotations

from typing import Any

from .identity import objective_semantic_fingerprint

#: The only kind an Objective revision's predecessor may carry. A reference is a *typed*
#: reference: reading its ``id`` and discarding its ``kind`` accepts a well-formed pointer
#: at the wrong thing that happens to share an identifier.
PREDECESSOR_KIND = "objective_revision"


def _predecessor_id(reference: Any) -> str | None:
    """Return the predecessor identity, and only where the reference is of the right kind."""

    if not isinstance(reference, dict) or reference.get("kind") != PREDECESSOR_KIND:
        return None
    identity = reference.get("id")
    return identity if isinstance(identity, str) else None


def _base_digest(revision: dict[str, Any]) -> str | None:
    fingerprint = revision.get("base_semantic_fingerprint")
    if not isinstance(fingerprint, dict):
        return None
    digest = fingerprint.get("digest")
    return "sha256:" + digest if isinstance(digest, str) else None


def objective_chain_errors(revisions: dict[str, dict[str, Any]]) -> tuple[list[str], set[str]]:
    """Return every chain violation, and the Objective ids whose chain is intact.

    The second element is what consumers used the old boolean for: a rule that may only read
    a *trusted* Objective head needs to know which histories are sound. Returning it beside
    the errors keeps that decision on the same reading, rather than on a second traversal
    that could disagree with the one that reported.
    """

    groups: dict[str, list[dict[str, Any]]] = {}
    for revision in revisions.values():
        identity = revision.get("objective_id")
        if isinstance(identity, str):
            groups.setdefault(identity, []).append(revision)

    errors: list[str] = []
    intact: set[str] = set()
    for objective_id, chain in sorted(groups.items()):
        chain.sort(key=lambda item: item.get("revision", 0))
        sound = True
        for position, revision in enumerate(chain):
            where = f"{objective_id}.{revision.get('objective_revision_id')}"
            if revision.get("revision") != position:
                errors.append(
                    f"Objective revision numbering is discontinuous: {where} "
                    f"declares revision {revision.get('revision')} at position {position}"
                )
                sound = False
                continue
            reference = revision.get("previous_objective_ref")
            if position == 0:
                if reference is not None:
                    errors.append(
                        f"Objective revision zero declares a predecessor: {where}"
                    )
                    sound = False
                continue
            if _predecessor_id(reference) != chain[position - 1].get("objective_revision_id"):
                errors.append(
                    f"Objective revision does not bind its immediate predecessor: {where}"
                )
                sound = False
            # Total: this rule also runs over records the auditor indexed before deciding
            # they were schema-valid, so an incomplete predecessor is reported rather than
            # raised out of the digest.
            try:
                expected_digest = objective_semantic_fingerprint(chain[position - 1])
            except (KeyError, TypeError):
                errors.append(
                    f"Objective predecessor is not complete enough to recompute: {where}"
                )
                sound = False
                continue
            if _base_digest(revision) != expected_digest:
                errors.append(
                    f"Objective base fingerprint does not match its predecessor: {where}"
                )
                sound = False
        if sound:
            intact.add(objective_id)
    return errors, intact
