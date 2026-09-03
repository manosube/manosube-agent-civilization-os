"""Fail-closed Evidence errors.

Evidence has the same shape of refusal Change has, for the same reason: a record that
cannot be *read* is not an Evidence question, and a record that would be *false* is not a
malformed input. Both are refusals, because Evidence has no third answer. What separates
them is what a caller must do next, so each keeps its own name.
"""


class EvidenceError(ValueError):
    """Base error for a raw Evidence input that cannot be read, or Evidence that may not be."""


class EvidenceValidationError(EvidenceError):
    """A record failed its canonical schema."""


# There is deliberately no ``EvidenceProvenanceError``.
#
# The Phase 5 P1 defect -- a self-consistent record read as a produced one -- is closed here
# by construction rather than by a check: the request carries the predecessors' *requests*,
# and this package runs ``observe`` and ``derive_change`` to obtain the records. A forged
# predecessor is not refused, because there is no parameter through which one could be
# supplied.
#
# An exported error class that nothing raises would advertise a provenance *check* that does
# not exist, and would leave a reader looking for the guard instead of noticing the absence
# of a hole. See ``engine.py`` and ADR-0029 §5.


class UngroundedChangeResultEvidenceError(EvidenceError):
    """A Change Result Evidence record was requested with nothing after the Change to observe.

    ``KERNEL_CONSTITUTION.md`` 第27条 defines Change Result Evidence as the **re-observation**
    after a Change. ``KERNEL_INVARIANTS.md`` E-002 names the three things that are not one:
    an execution return code, an agent success report, and file existence. v0.1 has no
    executor, ``change.schema.json`` pins ``execution_result`` to null, and a Change that is
    AUTHORIZED is not a Change that was EXECUTED.

    So there is nothing here to convert into a result. Naming an ungrounded record
    "Change Result Evidence" would let it satisfy ``change_result_evidence_refs`` on a
    Closure Evaluation, which is exactly the substitution E-002 forbids. Evidence refuses
    instead. An UNKNOWN, BLOCKED or INCOMPLETE **Observation** Evidence record is always
    available and is the truthful record of the same situation.
    """


class UnsupportedEvidenceLevelError(EvidenceError):
    """A structured proof was offered at a level Phase 6 cannot derive.

    ``KERNEL_CONSTITUTION.md`` 第29条 names E4, E5 and E6 -- 自然経路実行, 対象Runtime実証,
    反復・独立Runtime実証 -- and defines no predicate that decides any of them. v0.1 has no
    Runtime, and ``CLOSURE_POLICY.md`` pins ``independent_verification_required`` to false
    with ``verification_independence_ref`` always null, so the independence E6 names does not
    exist to be observed.

    Inventing a predicate here would be Evidence deciding what a Runtime proof is, which is
    the defect ``E-005`` describes from the other side. The vocabulary E0..E6 stays in the
    schema; the derivation stops at E3 and says so.
    """
