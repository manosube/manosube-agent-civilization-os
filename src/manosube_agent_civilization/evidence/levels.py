"""The Evidence Level scale, and what the canonical records have to *say* to reach one.

```text
EVIDENCE COUNT != EVIDENCE STRENGTH
TEST PASS      != RUNTIME PROVEN
DECLARATION    != OBSERVATION EVIDENCE
CALLER LABEL   != STRUCTURAL PROOF
```

Two separate things live here and must not be confused.

The **scale** is constitutional. ``KERNEL_CONSTITUTION.md`` 第29条 and
``COMPLETION_SEMANTICS.md`` chapter 3 both give the same closed ordered list, and
``CLOSURE_POLICY.md`` §5 requires the sufficiency gate to resolve it from that exact source
by content address. This module pins the scale and the source's blob identity; a repository
test resolves the live document and proves both pins equal it, so neither can drift without
a test failing. That split is deliberate: the engine reads no filesystem, and a guard that
lived in the engine could not be the thing that proves the engine right.

The **derivation** is a function of the canonical Observation record and of nothing a caller
writes. There is no method-class parameter, and there is no level parameter. A caller cannot
name a level, cannot name a method, and cannot raise a level by adding an artifact
reference: the only input is what the Observation Engine concluded about its own scope.
"""

from __future__ import annotations

from typing import Any

from .errors import UnsupportedEvidenceLevelError

#: The closed ordered scale of 第29条, weakest first. Order *is* the semantics: G12 compares
#: by position on this list and never by count, because a hundred E1 observations remain E1.
EVIDENCE_LEVEL_SCALE: tuple[str, ...] = ("E0", "E1", "E2", "E3", "E4", "E5", "E6")

#: What 第29条 calls each level, verbatim, so the pin above can be proven against the
#: document rather than against a paraphrase of it.
EVIDENCE_LEVEL_LABELS: dict[str, str] = {
    "E0": "宣言のみ",
    "E1": "静的確認",
    "E2": "単体テスト",
    "E3": "統合テスト",
    "E4": "自然経路実行",
    "E5": "対象Runtime実証",
    "E6": "反復・独立Runtime実証",
}

#: The canonical Evidence Level source, and the blob it must be. The path alone would let a
#: reference name the right file at any content; the blob identity is what makes the
#: reference an address. ``tests/contract/evidence/test_evidence_level_scale_source.py``
#: proves this pin equals ``git hash-object`` of the live document.
COMPLETION_SEMANTICS_PATH = "00_KERNEL/COMPLETION_SEMANTICS.md"
COMPLETION_SEMANTICS_BLOB_SHA = "d377a3c8a73e556b3c52c0c79a54e7b2dbd34abb"

#: The levels Phase 6 can derive. Not a subset chosen for convenience: it is exactly the
#: prefix of the scale for which the frozen Kernel defines something observable.
#:
#: ``E1 静的確認`` is what the Observation Engine produces -- normalized facts read from
#: immutable, content-addressed source snapshots, over a scope the Engine itself certifies as
#: completely observed. ``E0 宣言のみ`` is what is left when it does not.
#:
#: ``E2 単体テスト`` and ``E3 統合テスト`` are **not** here, and their absence is a finding
#: rather than a simplification. Deciding either requires knowing that a *test executed*, and
#: the frozen tree records no such thing: ``observation_method.schema.json`` pins
#: ``procedure_kind`` to the single value ``CANONICAL_OBSERVER`` and ``normalization_profile``
#: to one profile, so every canonical method is the same method. The only way to separate E1,
#: E2 and E3 today is to let a caller assert which one it was -- which is the defect this
#: module was rewritten to remove, and which ``E-005`` names from the other side.
#:
#: This is the reasoning that produced Q2-A for E4-E6, applied where the evidence actually
#: runs out rather than where it was first noticed.
DERIVABLE_LEVELS: frozenset[str] = frozenset({"E0", "E1"})

#: The levels the vocabulary keeps and this phase refuses to mint.
UNDERIVABLE_LEVELS: tuple[str, ...] = ("E2", "E3", "E4", "E5", "E6")

#: Why each is unreachable, so a refusal says what would have to exist rather than only that
#: something does not.
UNDERIVABLE_REASONS: dict[str, str] = {
    "E2": "no canonical record distinguishes a unit test from any other observation: "
    "observation_method.schema.json pins procedure_kind to CANONICAL_OBSERVER",
    "E3": "no canonical record distinguishes an integration test from any other observation: "
    "observation_method.schema.json pins procedure_kind to CANONICAL_OBSERVER",
    "E4": "v0.1 has no natural-path execution record and the Kernel defines no predicate for one",
    "E5": "v0.1 has no Runtime",
    "E6": "v0.1 has no independent verifier: CLOSURE_POLICY.md pins "
    "independent_verification_required to false and verification_independence_ref to null",
}

#: The two Observation statuses that mean the Engine certified its declared scope as
#: completely observed. Every other status -- INCOMPLETE, UNKNOWN, UNOBSERVED, BLOCKED,
#: FAILED, INVALID, CONFLICTED -- means it did not, and an unfinished confirmation is not a
#: confirmation.
CONFIRMING_STATUSES: frozenset[str] = frozenset({"COMPLETE", "EMPTY"})


def level_index(level: Any) -> int:
    """Return a level's position on the scale, or fail closed on anything else.

    The type check is not decoration. ``list.index`` and ``dict.get`` raise ``TypeError`` on
    an unhashable argument, and a ``TypeError`` crossing this boundary is not a refusal --
    it is a caller of Evidence learning about Evidence's internals. This is the same defect
    Decision 0002 named as D3 and ``difference/admissibility.py`` was written for.
    """

    if not isinstance(level, str):
        raise UnsupportedEvidenceLevelError(
            f"evidence level is not a level name: {type(level).__name__}"
        )
    try:
        return EVIDENCE_LEVEL_SCALE.index(level)
    except ValueError as error:
        raise UnsupportedEvidenceLevelError(
            f"evidence level is not on the canonical scale: {level!r}"
        ) from error


def weakest(levels: list[str]) -> str:
    """Return the weakest of several levels.

    ``CLOSURE_POLICY.md`` §5: 要求level未満のEvidenceを件数で補ってはならない. A claim rests on
    every piece of evidence it needs, so its strength is the strength of the weakest one, and
    adding more weak evidence cannot raise it.
    """

    return min(levels, key=level_index)


def unreachable_reason(level: str) -> str:
    """Return why a level cannot be reached in this phase."""

    return UNDERIVABLE_REASONS.get(level, "no proof predicate exists for this level in v0.1")


def derive_level(observation: dict[str, Any]) -> str:
    """Return the level this Evidence carries, from the canonical Observation and nothing else.

    ```text
    E1  the canonical Observation Engine certified its declared scope completely observed,
        over at least one immutable content-addressed source snapshot
    E0  otherwise
    ```

    The single input is a record ``observe`` produced. There is no method-class parameter and
    no level parameter on the Evidence request -- so a caller cannot assert a level, cannot
    assert what kind of observation it was, and cannot lift E0 to E1 by attaching an artifact
    reference to content nobody verified. All three were possible at ``6640ffd``.

    The method does not appear here because it cannot discriminate: ``procedure_kind`` is a
    schema constant, so every canonical method contributes the same value. Reading it would
    look like a second condition and be none.
    """

    if observation.get("status") not in CONFIRMING_STATUSES:
        return "E0"
    if not observation.get("source_snapshot_refs"):
        return "E0"
    return "E1"
