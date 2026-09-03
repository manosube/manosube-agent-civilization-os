"""Change describes an authorized mutation. It never performs one.

```text
AUTHORIZED != EXECUTED
CHANGE_DESCRIBES != CHANGE_DOES
```

There is exactly one deriver, and it is :func:`derive_change`. It reads no clock, no
filesystem, no network, no environment and no agent state; it does not mutate State, create
Evidence, close a Difference or declare completion (``COMPLETION_SEMANTICS.md`` §6).
"""

from .engine import AUTHORIZED, derive_change
from .errors import (
    AuthorityProvenanceError,
    ChangeError,
    ChangeValidationError,
    StaleChangeError,
    UnauthorizedChangeError,
)

__all__ = [
    "AUTHORIZED",
    "AuthorityProvenanceError",
    "ChangeError",
    "ChangeValidationError",
    "StaleChangeError",
    "UnauthorizedChangeError",
    "derive_change",
]
