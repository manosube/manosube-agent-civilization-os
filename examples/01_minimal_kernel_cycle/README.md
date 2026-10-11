# Try the kernel in 15 minutes

Use Linux with Python 3.12 or newer. On Windows, use a working Linux distribution in WSL. Native Windows Store execution is unsupported. These offline examples require no model account, network service, production credentials, or model spending after installation.

From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements-ci.txt -e .
```

Create a read-only demonstration project using the existing Binding owner:

```sh
DEMO_ROOT=$(mktemp -d)
manosube init --store-root "$DEMO_ROOT/binding" --schema-root "$PWD/01_SCHEMA" --manifest examples/01_minimal_kernel_cycle/genesis.json > "$DEMO_ROOT/init.json"
PROJECT_ID=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["project_id"])' "$DEMO_ROOT/init.json")
BINDING_ID=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["project_binding_id"])' "$DEMO_ROOT/init.json")
manosube boot --store-root "$DEMO_ROOT/binding" --schema-root "$PWD/01_SCHEMA" --project-id "$PROJECT_ID" --project-binding-id "$BINDING_ID"
```

The manifest contains a public test identity and its public verification key. Its corresponding test private key is publicly known. This identity is for this disposable demonstration only. For a real project, declare your own objective, boundary, authority rules, identity and verification key; never reuse the demonstration identity for production grants. `init` performs genesis through `bind_project`; it does not create an execution grant or run an agent.

Run a controlled canonical closure and persistent reflow in a separate Store:

```sh
python examples/01_minimal_kernel_cycle/run.py --store-root "$DEMO_ROOT/cycle" --schema-root "$PWD/01_SCHEMA"
```

Expected output includes `to_status: CLOSED`, before revision 3 and after revision 4, and a real committed state-transition reference. The JSON inputs are exported from the repository's established positive control. Source observations, evidence and environment assumptions are controlled example inputs, not independent real-world observations. Reflow recomputes and verifies the closure through the installed kernel, then commits through the real Store. The setup transactions prepare the example; they are not attributed to agent work. This example establishes an executable entry point, not improved agent reliability or runtime enforcement outside the kernel.

The controlled cycle needs a fresh Store directory and refuses to overwrite an initialized
Store. The `init` command preserves Binding's idempotent behavior for an identical genesis
manifest and rejects conflicts. Preserve the output and your environment/version when
reporting a reproduction to Issue #100. A failed run is useful evidence too.
