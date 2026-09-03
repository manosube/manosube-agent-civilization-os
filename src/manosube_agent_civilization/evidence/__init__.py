"""Evidence records what was observed. It never observes, and it never closes a Difference.

```text
OBSERVATION EVIDENCE      = before state と Difference を裏付ける証拠
CHANGE RESULT EVIDENCE    = Change 後の再観測結果を裏付ける証拠

AUTHORIZED  != EXECUTED
POST_CHANGE_OBSERVATION != EXECUTION_RECEIPT != CAUSALITY_PROOF
DECLARATION != OBSERVATION EVIDENCE
EVIDENCE COUNT != EVIDENCE STRENGTH
```

There is exactly one deriver, :func:`derive_evidence`, and exactly one producer of the
Difference-owned sufficiency result, :func:`evaluate_sufficiency`. Neither reads a clock, a
filesystem, a network, an environment or any agent state.
"""

from .engine import (
    CHANGE_RESULT_EVIDENCE,
    EVIDENCE_REFERENCE_KIND,
    OBSERVATION_EVIDENCE,
    derive_evidence,
)
from .errors import (
    EvidenceError,
    EvidenceValidationError,
    UngroundedChangeResultEvidenceError,
    UnsupportedEvidenceLevelError,
)
from .levels import DERIVABLE_LEVELS, EVIDENCE_LEVEL_SCALE, UNDERIVABLE_LEVELS
from .sufficiency import NOT_EVALUATED_HERE, REASON_CODES, evaluate_sufficiency

__all__ = [
    "CHANGE_RESULT_EVIDENCE",
    "DERIVABLE_LEVELS",
    "EVIDENCE_LEVEL_SCALE",
    "EVIDENCE_REFERENCE_KIND",
    "NOT_EVALUATED_HERE",
    "OBSERVATION_EVIDENCE",
    "REASON_CODES",
    "UNDERIVABLE_LEVELS",
    "EvidenceError",
    "EvidenceValidationError",
    "UngroundedChangeResultEvidenceError",
    "UnsupportedEvidenceLevelError",
    "derive_evidence",
    "evaluate_sufficiency",
]
