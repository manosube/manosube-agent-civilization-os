"""The ratified current-repository development Binding, as an evaluable guard.

```text
CHATGPT     = STRUCTURAL_ADVISOR
CLAUDE_CODE = IMPLEMENTATION_EXECUTOR
GITHUB      = HUMAN_INTENT_AND_WORK_STATE_SURFACE
SHUKOU      = ACCEPTANCE AND MERGE AUTHORITY
```

This selects the four concrete participants building *this* repository. It is **not** a
Kernel element: `KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md` §6 defines the observation,
acceptance and execution capabilities without naming a provider, and that neutrality is
preserved and proven by test.
"""

from .errors import DevelopmentBindingError, PolicyIntegrityError
from .evaluation import (
    PERMITTED,
    REFUSED,
    evaluate,
    prohibited_trigger_in,
)
from .policy import HUMAN_AUTHORITY, ROLES, load_policy

__all__ = [
    "HUMAN_AUTHORITY",
    "PERMITTED",
    "REFUSED",
    "ROLES",
    "DevelopmentBindingError",
    "PolicyIntegrityError",
    "evaluate",
    "load_policy",
    "prohibited_trigger_in",
]
