"""A controlled, offline canonical cycle over explicit, shipped JSON inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.store import FileStateStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--schema-root", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(Path(__file__).with_name("cycle.json").read_text(encoding="utf-8"))
    store = FileStateStore(args.store_root, schema_root=args.schema_root)
    for step in payload["preparation"]:
        if step["kind"] == "initialize":
            store.initialize(step["project_id"], step["state"], records=step["records"])
        else:
            store.commit(step["project_id"], step["revision"], step["fingerprint"], step["state"], step["event"])
    before = store.load_current(payload["reflow"]["project_id"])
    result = reflow(store, **payload["reflow"])
    after = store.load_current(payload["reflow"]["project_id"])
    if result["decision"]["to_status"] != "CLOSED" or after["state_revision"] != before["state_revision"] + 1:
        raise RuntimeError("controlled cycle did not reach the expected committed state")
    print(json.dumps({"example_kind": "CONTROLLED_OFFLINE_INPUT", "decision": result["decision"],  # noqa: T201 -- example receipt on stdout
                      "before_revision": before["state_revision"], "after_revision": after["state_revision"],
                      "state_transition_ref": result["state_transition_ref"],
                      "real_agent_effect_measured": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
