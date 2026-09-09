"""The two :class:`~manosube_agent_civilization.model_runtime.types.ModelAdapter`
implementations Phase 16 ships (Issue #66, P16-C2).

Two genuinely distinct adapters execute the **identical** canonical, provider-neutral request
and produce normalized, provider-neutral results in the identical shape. They share no base
class, no helper, no module-level state, and no notion of a candidate's *origin*:

``FakeModelAdapter``
    A controlled, in-memory, fully deterministic adapter holding a **seeded world**: a test
    declares, per Work Unit, what a real model would have produced. It is the V1/V2/V4 proof
    backbone, and it carries the test-control surface (``seed_candidate``/``remove_candidate``/
    ``tamper_candidate``/``force_result``) ``FakeRuntimeAdapter`` already establishes as this
    repository's own convention for a controlled adapter.

``RequestDerivedModelAdapter``
    A controlled, in-memory, fully deterministic adapter holding **no world at all**. It derives
    every candidate field purely from the canonical request it was handed, by digesting the
    request's own provider-neutral identity together with the field name. It has no seeding
    surface, no per-instance dictionary, no removable target, and no way to be told what to
    answer -- so an identical canonical request always yields the identical normalized result
    from it, on any machine, with no prior setup.

**Why the second adapter is not a local HTTP one** (disclosed judgment call). Phase 15's own
second adapter opened a real, bounded HTTP GET against a disposable local server, because its
domain -- observing a running deployment -- genuinely *is* HTTP, and proving the transport
existed was part of the proof. This domain is not. A local HTTP server here would be a
*simulated provider endpoint*: it would add a real network surface to a package the adopted
proposal requires to have none, it would drift the delivery toward the shape of a live provider
call (``LIVE_PROVIDER_CREDENTIAL_USE=false`` is an adopted constraint), and it would prove
nothing P16-C2 actually asks for -- which is that two *structurally different* implementations
of one boundary produce provider-neutral results from the identical canonical request. Two
in-memory implementations with genuinely different internal models of "where a candidate comes
from" prove exactly that, and the static conformance suite additionally proves the negative
directly: no module in this package imports a provider SDK, a network surface, or a subprocess
surface at all.

**What no adapter here can reach.** This module imports exactly two of its own package's
modules and nothing else in this repository: no Store, no Boot, no Agent Runtime, no Authority,
no Evidence, no Difference, no Change, no Reflow. That is the identical discipline
``runtime/adapter.py`` already keeps, and it is what makes P16-C3's prohibition structural
rather than merely enforced at runtime: an adapter cannot commit State, mint Authority, derive
Evidence, or close a Difference here because none of those owners is importable from inside
this file's own import graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
from typing import Any

from .errors import ModelAdapterError
from .types import MODEL_ADAPTER_OUTCOMES


class FakeModelAdapter:
    """A controlled, in-memory, fully deterministic
    :class:`~manosube_agent_civilization.model_runtime.types.ModelAdapter`.

    Backs every V1/V2/V4 test in this package's own suites. Seeded candidates live only in this
    instance's own dict for the lifetime of the test that constructs it -- no filesystem write,
    no network call, no shared or global state between instances, no provider credential, and no
    model memory that survives a single ``execute`` call.
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_model_adapter", "version": "0.1"}
        )
        self._world: dict[str, dict[str, Any]] = {}
        self._forced_result: Mapping[str, Any] | None = None
        self.execute_call_count = 0

    @staticmethod
    def _key(request: Mapping[str, Any]) -> str:
        return str(request["model_work_unit_ref"]["id"])

    def seed_candidate(
        self,
        *,
        model_work_unit_ref: Mapping[str, Any],
        candidate_fields: Mapping[str, Any],
        candidate_kind: str = "OBSERVATION_CANDIDATE",
        adapter_outcome: str = "CANDIDATE",
    ) -> None:
        """Declare what a real model execution against this Work Unit would honestly report.

        *adapter_outcome* left at its default is the ordinary positive path; passing any other
        member of :data:`~manosube_agent_civilization.model_runtime.types.
        MODEL_ADAPTER_OUTCOMES` is exactly how a V4 typed-failure control is built -- the
        adapter honestly reports what happened, and only
        :mod:`~manosube_agent_civilization.model_runtime.route` ever decides what that means
        canonically.
        """

        self._world[str(model_work_unit_ref["id"])] = {
            "candidate_fields": dict(candidate_fields),
            "candidate_kind": candidate_kind,
            "adapter_outcome": adapter_outcome,
        }

    def remove_candidate(self, *, model_work_unit_ref: Mapping[str, Any]) -> None:
        """Test-only control surface: simulate the model having nothing at all to report."""

        self._world.pop(str(model_work_unit_ref["id"]), None)

    def tamper_candidate(
        self, *, model_work_unit_ref: Mapping[str, Any], candidate_fields: Mapping[str, Any]
    ) -> None:
        """Test-only control surface: simulate the model producing different content."""

        record = self._world.get(str(model_work_unit_ref["id"]))
        if record is not None:
            record["candidate_fields"] = dict(candidate_fields)

    def force_result(self, result: Mapping[str, Any] | None) -> None:
        """Test-only control surface: force the exact next ``execute()`` return value, bypassing
        seeded world state entirely -- used to prove this package's own fail-closed
        :class:`~manosube_agent_civilization.model_runtime.errors.ModelAdapterError` handling of
        a structurally unreadable adapter result, of an adapter claiming the route-only
        ``CANDIDATE_ACCEPTED`` classification, and of an adapter attempting to widen its own
        Boundary or authorize itself."""

        self._forced_result = result

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.execute_call_count += 1
        if self._forced_result is not None:
            return self._forced_result

        record = self._world.get(self._key(request))
        if record is None:
            return {
                "adapter_outcome": "INCOMPLETE_EVIDENCE",
                "candidate_kind": None,
                "candidate_fields": None,
            }

        outcome = str(record["adapter_outcome"])
        if outcome not in MODEL_ADAPTER_OUTCOMES:
            raise ModelAdapterError(
                f"seeded adapter_outcome is not an adapter-reportable outcome: {outcome!r}"
            )
        if outcome != "CANDIDATE":
            return {
                "adapter_outcome": outcome,
                "candidate_kind": None,
                "candidate_fields": None,
            }

        permitted = list(request["boundary"]["permitted_candidate_fields"])
        candidate_fields = {
            field: record["candidate_fields"].get(field)
            for field in permitted
            if field in record["candidate_fields"]
        }
        return {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": str(record["candidate_kind"]),
            "candidate_fields": deepcopy(candidate_fields),
        }


class RequestDerivedModelAdapter:
    """A second, structurally different controlled
    :class:`~manosube_agent_civilization.model_runtime.types.ModelAdapter` (P16-C2).

    Holds no seeded world, no per-Work-Unit dictionary, and no control surface of any kind: it
    is a pure function of the canonical request it is handed. Every permitted candidate field is
    answered with a deterministic digest over that request's own provider-neutral execution
    identity and the field's own name, so the *same canonical request always yields the same
    normalized result* -- which is what makes it usable as the second half of the two-adapter
    proof without any shared setup with the first.

    A single, deliberately narrow refusal control exists so the V4 matrix can exercise a
    *second* adapter's own typed failures too: when the canonical request names a capability
    this adapter does not implement, it returns ``REFUSED`` rather than raising, exactly as the
    Protocol requires. It is not a configuration surface -- nothing about it can be set from
    outside.
    """

    #: The capability vocabulary this particular adapter implements. Deliberately a class-level
    #: literal, never an instance attribute and never a constructor parameter: an adapter that
    #: could be *told* which capabilities it implements could be told to implement one its
    #: Boundary never permitted, which is precisely the self-widening P16-C3 forbids.
    IMPLEMENTED_CAPABILITIES: frozenset[str] = frozenset({"PROPOSE_EVIDENCE_CANDIDATE"})

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "request_derived_model_adapter", "version": "0.1"}
        )
        self.execute_call_count = 0

    @staticmethod
    def _derive_field_value(request_identity: str, field: str) -> str:
        payload = f"{request_identity}\x1f{field}".encode()
        return "derived:" + hashlib.sha256(payload).hexdigest()

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.execute_call_count += 1
        if request["required_capability"] not in self.IMPLEMENTED_CAPABILITIES:
            return {
                "adapter_outcome": "REFUSED",
                "candidate_kind": None,
                "candidate_fields": None,
            }
        request_identity = str(request["model_execution_request_identity"])
        candidate_fields = {
            field: self._derive_field_value(request_identity, field)
            for field in request["boundary"]["permitted_candidate_fields"]
        }
        return {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": candidate_fields,
        }


__all__ = ["FakeModelAdapter", "RequestDerivedModelAdapter"]
