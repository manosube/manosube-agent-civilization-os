"""WU2 (Issue #116 / connection-method-independent test harness components).

Tracks #116. Scope: evidence recording, Store/external-side reconciliation, independent
judgment, aggregation, and case/task fixture generation -- per the WU2 scope SHUKOU
adopted on top of WU1 (``docs/validation/dots_production_acceptance/``), confirmed at
PR #117 HEAD ``538982731a496d3f97d1c7558206e222f68e9dcc``.

Deliberately excluded from this package: any dots-specific adapter (``dots_adapter.py``)
and the actual dispatch-to-dots call. Those depend on SHUKOU's still-open Reading A/B/C
decision (``docs/validation/dots_production_acceptance/OPEN_ITEMS.md`` item 1) and are
built later, against the real canonical routes this package already wires up. Nothing
in this package performs a live model launch, a dots/GitHub connection, a credential or
billing change, a production VPS change, or a merge.
"""

from __future__ import annotations
