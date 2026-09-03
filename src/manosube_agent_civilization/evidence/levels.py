"""The Evidence Level scale, and what a record has to *contain* to reach one.

```text
EVIDENCE COUNT != EVIDENCE STRENGTH
TEST PASS      != RUNTIME PROVEN
DECLARATION    != OBSERVATION EVIDENCE
```

Two separate things live here and must not be confused.

The **scale** is constitutional. ``KERNEL_CONSTITUTION.md`` 第29条 and
``COMPLETION_SEMANTICS.md`` chapter 3 both give the same closed ordered list, and
``CLOSURE_POLICY.md`` §5 requires the sufficiency gate to resolve it from that exact source
by content-addressed blob reference. This module pins the scale as a value; a repository
test resolves the live document and proves the pinned value equals it, so the pin cannot
drift from the constitution without a test failing. That split is deliberate: the engine
reads no filesystem, and a guard that lives in the engine could not be the thing that
proves the engine right.

The **ceiling** is not constitutional and does not claim to be. It answers one narrower
question, the one ``E-005 EVIDENCE_LEVEL_NOT_OVERSTATED`` asks: given what this record
actually contains, what is the highest level it could honestly carry? It only ever lowers.
A record whose method class says INTEGRATION_TEST but which carries no completed attempt
did not run an integration test, whatever it calls itself.
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

#: The levels Phase 6 can derive. Not a subset chosen for convenience: it is exactly the
#: prefix of the scale for which a structured predicate exists in the frozen Kernel.
DERIVABLE_LEVELS: frozenset[str] = frozenset({"E0", "E1", "E2", "E3"})

#: The levels the vocabulary keeps and this phase refuses to mint. See
#: :class:`UnsupportedEvidenceLevelError`.
UNDERIVABLE_LEVELS: tuple[str, ...] = ("E4", "E5", "E6")

#: Observation method class to the level it *claims*. One entry per level, so the mapping is
#: total over the scale and a method class cannot silently mean two things. The three
#: undecidable classes are present rather than omitted: a caller naming one gets the refusal
#: that says why, instead of a "no such method class" that says nothing.
METHOD_CLASS_LEVELS: dict[str, str] = {
    "DECLARATION": "E0",
    "STATIC_INSPECTION": "E1",
    "UNIT_TEST": "E2",
    "INTEGRATION_TEST": "E3",
    "NATURAL_PATH_EXECUTION": "E4",
    "TARGET_RUNTIME_PROOF": "E5",
    "REPEATED_INDEPENDENT_RUNTIME_PROOF": "E6",
}

#: An attempt that reached the thing it was observing. BLOCKED and FAILED did not, and
#: PARTIAL did not finish, so none of the three can raise a record above 静的確認.
COMPLETED_ATTEMPT_RESULTS: frozenset[str] = frozenset({"COMPLETE", "EMPTY"})


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


def structural_ceiling(*, artifact_reference_count: int, completed_attempt_count: int) -> str:
    """Return the highest level this record's *contents* can honestly carry.

    This is ``E-005`` expressed as a computation rather than as a prohibition. Each step
    names the thing 第29条 says the level is, and asks whether the record contains it:

    ```text
    宣言のみ    nothing is required; a declaration is a declaration
    静的確認    something must have been confirmed -- an artifact, bound by content digest
    単体テスト   something must have been run -- an attempt that reached its subject
    統合テスト   likewise; whether it was integrative is the method class's claim
    ```

    The last two share a floor because the frozen Kernel distinguishes E2 from E3 by what was
    exercised, not by how it was recorded, and Evidence has no way to observe the difference.
    So the ceiling admits both and the method class decides between them -- downward only,
    since :func:`derive_level` takes the weaker of the two.

    Evidence cannot fetch an artifact to check its digest, so a caller could inflate the
    artifact count with references to nothing. That buys them nothing: the ceiling only ever
    *lowers*, so the most an inflated count can do is fail to lower a claim the caller was
    already free to make through the method class. A rule that raised a level on the strength
    of an unverified count would be a different matter, and there is none.
    """

    if completed_attempt_count > 0:
        return "E3"
    if artifact_reference_count > 0:
        return "E1"
    return "E0"


def derive_level(
    method_class: Any, *, artifact_reference_count: int, completed_attempt_count: int
) -> str:
    """Return the level this Evidence carries, derived from structure alone.

    There is deliberately no parameter through which a caller can state a level. The claim
    comes from the method class; the ceiling comes from what the record contains; the answer
    is the weaker of the two. A caller can therefore overstate a *method*, and the record
    still cannot overstate its *level*.
    """

    if not isinstance(method_class, str):
        raise UnsupportedEvidenceLevelError(
            f"observation method class is not a method class name: {type(method_class).__name__}"
        )
    claimed = METHOD_CLASS_LEVELS.get(method_class)
    if claimed is None:
        raise UnsupportedEvidenceLevelError(
            f"observation method class is not on the canonical scale: {method_class!r}"
        )
    if claimed not in DERIVABLE_LEVELS:
        raise UnsupportedEvidenceLevelError(
            f"observation method class {method_class!r} claims {claimed} "
            f"({EVIDENCE_LEVEL_LABELS[claimed]}), which Phase 6 cannot derive: the Kernel "
            f"defines no proof predicate for {', '.join(UNDERIVABLE_LEVELS)} and v0.1 has no "
            "Runtime and no independent verifier"
        )
    ceiling = structural_ceiling(
        artifact_reference_count=artifact_reference_count,
        completed_attempt_count=completed_attempt_count,
    )
    return weakest([claimed, ceiling])


def completed_attempt_count(observation: dict[str, Any]) -> int:
    """Return how many of an Observation's attempts reached the thing they observed."""

    attempts = observation.get("attempts") or []
    return sum(
        1
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("result") in COMPLETED_ATTEMPT_RESULTS
    )
