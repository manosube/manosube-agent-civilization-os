"""Measure planted closure defects; this is not a real-agent comparison."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from manosube_agent_civilization.reflow.closure import evaluate_closure
from manosube_agent_civilization.reflow.errors import ReflowValidationError


def controls(base: dict) -> list[dict]:
    cases = []
    for repetition in range(5):
        for category in (
            "complete", "missing_reobservation", "missing_sufficiency",
            "missing_source_snapshots", "stale_state", "missing_claim_bindings",
            "missing_invariant_evaluations", "wrong_project",
        ):
            request = deepcopy(base)
            if category == "missing_reobservation":
                request["reobservation"] = None
            elif category == "missing_sufficiency":
                request["evidence_sufficiency_request"] = None
            elif category == "missing_source_snapshots":
                request["source_snapshots"] = []
            elif category == "stale_state":
                request["current_state"]["revision"] += 1
            elif category == "missing_claim_bindings":
                request["candidate_claim_evaluation_bindings"] = []
            elif category == "missing_invariant_evaluations":
                request["invariant_evaluations"] = []
            elif category == "wrong_project":
                request["difference"]["project_id"] = "PRJ-WRONG"
            cases.append({"id": f"{category}-{repetition}", "category": category,
                          "expected_closed": category == "complete", "request": request})
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("examples/01_minimal_kernel_cycle/cycle.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    base = json.loads(raw)["reflow"]["closure_request"]
    results = []
    for case in controls(base):
        started = time.perf_counter()
        typed_refusal = None
        try:
            evaluation = evaluate_closure(case["request"])
            closed = evaluation["result"] == "SATISFIED" and evaluation["proposed_terminal_status"] == "CLOSED"
            error = None
        except ReflowValidationError as exc:
            closed = False
            typed_refusal = str(exc)
            error = None
        except (ValueError, RuntimeError, TypeError, KeyError) as exc:
            # An exception remains separately visible. It is not credited as a clean refusal.
            closed = False
            error = type(exc).__name__ + ": " + str(exc)
        results.append({"id": case["id"], "category": case["category"],
                        "expected_closed": case["expected_closed"], "observed_closed": closed,
                        "typed_refusal": typed_refusal, "exception": error,
                        "seconds": time.perf_counter() - started})
    false_accepts = sum(not x["expected_closed"] and x["observed_closed"] for x in results)
    false_rejects = sum(x["expected_closed"] and not x["observed_closed"] for x in results)
    report = {"kind": "CONTROLLED_CLOSURE_GATE_REGRESSION", "input_sha256": hashlib.sha256(raw).hexdigest(),
              "unique_categories": 8, "repetitions_per_category": 5,
              "independent_real_tasks": 0, "agent_comparison_run": False,
              "false_accepts": false_accepts, "false_rejects": false_rejects,
              "typed_refusal_count": sum(x["typed_refusal"] is not None for x in results),
              "exception_count": sum(x["exception"] is not None for x in results),
              "model_cost": None, "human_intervention_minutes": None, "cases": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if false_accepts or false_rejects or report["exception_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
