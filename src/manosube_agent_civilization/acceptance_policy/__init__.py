"""Acceptance Policy Lineage (FD-0004, Issue #80).

Kernel-enforced structured semantics for acceptance/merge/completion policy lineage: a canonical
distinction between the original contract, Human-adopted supplements, proposals, superseded
clauses and the current effective policy (FD4-C1..C10), so an Agent or Structural Advisor can
never silently add, remove, broaden, narrow, or reclassify a merge/acceptance/completion
condition inside an implementation finding, review round, handoff, or evidence request.

This is not a second Human Authority, State, Evidence, Reflow or Store owner (FD4-C10): it
reuses the existing Store commit path (``store.commit`` via ``commit_state_transition``) and the
existing single Human Authority (``SHUKOU``), and introduces no parallel canonical ownership.
"""

from __future__ import annotations

from .engine import (
    assert_no_undeclared_policy_change,
    assert_transition_operation_matches_diff,
    build_adoption,
    build_baseline,
    build_impact_preview,
    build_transition,
    classify_operation,
    derive_effective_policy,
    require_valid_clause,
)
from .errors import (
    AcceptancePolicyError,
    AcceptancePolicyValidationError,
    ConflictingPolicyReplayError,
    PolicyLineageConflictError,
    PolicyProvenanceError,
    UnauthorizedPolicyAdoptionError,
    UndeclaredPolicyChangeError,
)
from .route import (
    adopt_acceptance_policy_transition,
    assert_no_undeclared_policy_change_in_payload,
    open_acceptance_policy_baseline,
    preview_acceptance_policy_transition,
    propose_acceptance_policy_transition,
    resolve_and_verify_adoption,
    resolve_and_verify_baseline,
    resolve_and_verify_effective_policy,
    resolve_and_verify_transition,
)
from .types import (
    BLOCKING_EFFECT_FIELDS,
    HUMAN_AUTHORITY,
    LINEAGE_SOURCE_KINDS,
    POLICY_CLASSES,
    POLICY_OPERATIONS,
    PROPOSER_ROLES,
    REQUIRED_COMMENT_AUTHOR_ASSOCIATION,
    SOURCE_KINDS,
)

__all__ = [
    "BLOCKING_EFFECT_FIELDS",
    "HUMAN_AUTHORITY",
    "LINEAGE_SOURCE_KINDS",
    "POLICY_CLASSES",
    "POLICY_OPERATIONS",
    "PROPOSER_ROLES",
    "REQUIRED_COMMENT_AUTHOR_ASSOCIATION",
    "SOURCE_KINDS",
    "AcceptancePolicyError",
    "AcceptancePolicyValidationError",
    "ConflictingPolicyReplayError",
    "PolicyLineageConflictError",
    "PolicyProvenanceError",
    "UnauthorizedPolicyAdoptionError",
    "UndeclaredPolicyChangeError",
    "adopt_acceptance_policy_transition",
    "assert_no_undeclared_policy_change",
    "assert_no_undeclared_policy_change_in_payload",
    "assert_transition_operation_matches_diff",
    "build_adoption",
    "build_baseline",
    "build_impact_preview",
    "build_transition",
    "classify_operation",
    "derive_effective_policy",
    "open_acceptance_policy_baseline",
    "preview_acceptance_policy_transition",
    "propose_acceptance_policy_transition",
    "require_valid_clause",
    "resolve_and_verify_adoption",
    "resolve_and_verify_baseline",
    "resolve_and_verify_effective_policy",
    "resolve_and_verify_transition",
]
