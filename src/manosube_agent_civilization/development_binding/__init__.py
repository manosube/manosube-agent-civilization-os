"""The ratified current-repository development Binding, as an evaluable guard.

```text
CLAUDE_CODE -> READY_FOR_STRUCTURAL_REVIEW
CHATGPT     -> STRUCTURAL_REVIEW -> MERGE_RECOMMENDED | CORRECTION_REQUIRED
                                  | MORE_EVIDENCE_REQUIRED | BLOCKED | NOT_REVIEWED
SHUKOU      -> FINAL_ACCEPTANCE -> MERGE_OPERATION
```

Three things Decision 0001 collapsed into one ambiguous `MERGE_DECISION` are separate here:
`MERGE_READINESS_RECOMMENDATION` (the Advisor may say a change looks ready),
`FINAL_ACCEPTANCE_DECISION` and `MERGE_OPERATION` (only the Human decides that it is, and
only the Human merges).

This selects the four concrete participants building *this* repository. It is **not** a
Kernel element: `KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md` §6 defines the observation,
acceptance and execution capabilities without naming a provider, and that neutrality is
preserved and proven by test.
"""

from .adoption_record import (
    ADOPTION_RECORD_ADMITTED,
    ADOPTION_RECORD_REFUSED,
    evaluate_adoption_record,
)
from .errors import AdoptionRecordError, DevelopmentBindingError, PolicyIntegrityError
from .evaluation import (
    PERMITTED,
    REFUSED,
    evaluate,
    prohibited_trigger_in,
)
from .policy import EXECUTOR_TERMINAL_STATE, HUMAN_AUTHORITY, ROLES, load_policy

__all__ = [
    "ADOPTION_RECORD_ADMITTED",
    "ADOPTION_RECORD_REFUSED",
    "EXECUTOR_TERMINAL_STATE",
    "HUMAN_AUTHORITY",
    "PERMITTED",
    "REFUSED",
    "ROLES",
    "AdoptionRecordError",
    "DevelopmentBindingError",
    "PolicyIntegrityError",
    "evaluate",
    "evaluate_adoption_record",
    "load_policy",
    "prohibited_trigger_in",
]
