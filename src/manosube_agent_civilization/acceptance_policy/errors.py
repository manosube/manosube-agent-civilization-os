"""Fail-closed Acceptance Policy errors (FD-0004, Issue #80).

The same distinction ``change/errors.py`` and ``multi_agent/errors.py`` draw holds here: an
input that cannot be *read* is not a policy question -- there is nothing to derive, so it
raises. A structurally well-formed but *undeclared or unauthorized* policy change is not a
malformed input either; it is a correctly-shaped request this package's own admission boundary
refuses, per FD4-C1/FD4-C3/FD4-C5. Refusal never mutates State (FD4-C9's own non-mutation
requirement): every error below is raised strictly before any Store commit is attempted.
"""

from __future__ import annotations


class AcceptancePolicyError(ValueError):
    """Base error for a raw acceptance-policy input that cannot be read, or a change refused."""


class AcceptancePolicyValidationError(AcceptancePolicyError):
    """A record failed its canonical schema, or a caller-supplied shape is unreadable."""


class UndeclaredPolicyChangeError(AcceptancePolicyError):
    """FD4-C1/FD4-C5: a semantic policy change was detected without the required declaration.

    Raised when a proposed transition's own declared ``policy_operation`` disagrees with the
    independently recomputed semantic diff between its ``proposed_clause`` and the clause body
    it replaces -- or when a policy-shaped term is found smuggled into an unrelated record
    (a code finding, ``REQUIRED_PROOFS``, an implementation handoff, return Evidence, or a
    closure sweep) without an accompanying ``policy_change: true`` marker (FD4-C4).
    """


class UnauthorizedPolicyAdoptionError(AcceptancePolicyError):
    """FD4-C3: the record does not carry an exact, identity-bound SHUKOU decision.

    Covers a wrong ``decision_owner``, a comment authored by anyone but the repository OWNER,
    or a source reference this package's own grammar cannot verify offline -- never a network
    call, exactly as ``development_binding.adoption_record`` performs none.
    """


class PolicyLineageConflictError(AcceptancePolicyError):
    """FD4-C6/FD4-C9: the transition history cannot be resolved to one clean effective policy.

    Covers a missing predecessor, a fork (two transitions claiming the same prior clause), a
    cycle, out-of-order adoption, a stale base/head, or a cross-project/cross-Issue/cross-PR
    substitution. A conflicted lineage blocks a clean view rather than silently picking one
    branch -- the required ``Conflicting, missing, cyclic, stale, cross-project or unauthorized
    transitions must remain explicit`` clause of FD4-C6.
    """


class PolicyProvenanceError(AcceptancePolicyError):
    """A record's own declared identity/fingerprint does not match its independently
    recomputed value, or a referenced predecessor record does not resolve in the Store.

    Hash consistency proves a record agrees with itself; it cannot prove who wrote it or that
    the chain it claims to extend actually exists. This is the forged/substituted-reference
    class -- distinct from :class:`PolicyLineageConflictError`, which covers a *resolvable but
    contradictory* lineage rather than a reference that does not resolve at all.
    """


class ConflictingPolicyReplayError(AcceptancePolicyError):
    """FD4-C9: an exact replay is idempotent; a *conflicting* replay -- the same identity with
    a different body -- is refused rather than silently overwriting the first commit.
    """
