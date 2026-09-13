"""Closed vocabularies for FD-0004 (Issue #80) -- the acceptance-policy lineage kernel.

Every enum here is declared once, as a plain tuple/frozenset, and is the single source of
truth both the JSON Schemas (``01_SCHEMA/acceptance_policy/*.schema.json``) and this package's
own Python validation read from -- never restated independently in two places that could drift.
"""

from __future__ import annotations

#: FD4-C3/FD4-C4: Authority (who may decide) and required Evidence (what proof is needed) are
#: separate dimensions. A clause is exactly one of these, never both, and the incident this
#: Issue regresses against is precisely the conflation of the two.
POLICY_CLASSES: tuple[str, ...] = ("AUTHORITY", "REQUIRED_EVIDENCE")

#: The six closed FD4-C1/FD4-C5 operations. Every transition declares exactly one, and this
#: package's own semantic-diff gate independently recomputes which of these six actually
#: describes the transition's own before/after clause bodies -- the declared value must agree.
POLICY_OPERATIONS: tuple[str, ...] = ("ADD", "REMOVE", "REPLACE", "NARROW", "BROADEN", "RECLASSIFY")

#: Who may *propose* a transition. Only the Human Authority may *adopt* one (see
#: :data:`HUMAN_AUTHORITY` below) -- FD4-C3's Agent/Human split. Kernel-schema-safe generic
#: role labels only (never a specific provider/participant name -- ``01_SCHEMA/`` must stay
#: neutral to any named AI tool or Human, per the existing repository-development Binding's
#: own Issue #34 discipline); ``"EXECUTOR"`` and ``"HUMAN_AUTHORITY"`` are the same generic
#: labels ``development_binding.policy`` already uses for this repository's own real
#: participants, reused here by value.
PROPOSER_ROLES: tuple[str, ...] = (
    "HUMAN_AUTHORITY",
    "STRUCTURAL_ADVISOR",
    "EXECUTOR",
    "OTHER_AGENT",
)

#: The five fields ``blocking_effect`` always carries -- one boolean per gate this Issue's own
#: "Required canonical model" names explicitly: implementation, structural review, merge, Issue
#: closure, phase completion.
BLOCKING_EFFECT_FIELDS: tuple[str, ...] = (
    "implementation",
    "structural_review",
    "merge",
    "issue_closure",
    "phase_completion",
)

#: The two record kinds a transition's ``prior_clause_binding`` -- or an adoption's
#: ``adopted_ref`` -- may point at. A hash-linked chain root is always a baseline; every other
#: node is a transition.
LINEAGE_SOURCE_KINDS: tuple[str, ...] = ("BASELINE", "TRANSITION")

#: The provenance classes a ``source_reference`` may declare. ``ORIGINAL_ISSUE`` is reserved
#: for the one genesis baseline; a transition's own source is one of the other three.
SOURCE_KINDS: tuple[str, ...] = (
    "ORIGINAL_ISSUE",
    "STRUCTURAL_REVIEW",
    "AUTHORITY_ADOPTION",
    "OTHER",
)

#: FD4-C3: the sole Human Authority this package ever admits an adoption on behalf of. Matches
#: ``development_binding.adoption_record.HUMAN_AUTHORITY`` by value, not by import -- this
#: package is a self-contained extension of the same real-world owner, not a second one.
HUMAN_AUTHORITY = "SHUKOU"

#: The sole comment-author association this package treats as a genuine SHUKOU/OWNER record.
REQUIRED_COMMENT_AUTHOR_ASSOCIATION = "OWNER"
