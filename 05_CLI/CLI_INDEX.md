# CLI Index (Phase 11, Issue #47)

```text
DOC_TYPE=CLI_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=CLI-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=PROCESS_ADAPTER
CANONICAL_KERNEL_COUNT=1
CLI_OWNER_COUNT=1
PUBLIC_CLI_COMMAND_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **CLI Boot adapter** contract set -- the two documents
under `05_CLI/` that define the explicit, read-only command-line surface over the existing
Phase 10 Boot route.

```text
1. CLI_INDEX.md      (this document)
2. CLI_CONTRACT.md   the one public command, its frozen semantics, and its negative controls
```

Read `CLI_CONTRACT.md` for the load-bearing design; this document only fixes the CLI's own
position relative to the rest of the Kernel and to Boot.

## 1. This is not a Kernel element, and not a second Boot owner

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). The CLI is not a ninth -- the same `KERNEL_ELEMENT=none`-style convention Development
Binding, Product Binding, and Boot already use (here spelled `PROCESS_ADAPTER`, since it is
specifically a process/command-line entry, not an in-process adapter). It never validates,
restores, or reverifies a Project itself -- that remains Boot's own, one-owner concern
(`manosube_agent_civilization.boot`). The CLI only invokes Boot's one public route,
`boot_project`, and serializes what it returns.

```text
CLI_IS_A_SECOND_BOOT_OWNER=false
CLI_CALLS_BOOT_PROJECT_MORE_THAN_ONCE_PER_INVOCATION=false
```

## 2. This is not initialization, discovery, recovery, or Change execution

The CLI never calls `FileStateStore.initialize`, `FileStateStore.recover`,
`FileStateStore.commit`, `FileStateStore.load_current`, or `bind_project`; never enumerates
Store projects, scans a filesystem, infers an identity from a path/URL/directory name, or
selects "the only" available project; and never executes a Change, starts an Agent, or makes
a network/GitHub call. A caller must already know the exact `project_id` and
`project_binding_id` of an already-bound Project, plus the two explicit filesystem roots
(`--store-root`, `--schema-root`); the CLI restores it through Boot, or fails closed.

```text
CLI_IS_DISCOVERY=false
CLI_IS_INITIALIZATION=false
CLI_MAY_MUTATE_STORE=false
CLI_MAY_CREATE_BINDING=false
CLI_MAY_REPAIR_STORE=false
CLI_MAY_DISCOVER_PROJECT=false
CLI_MAY_EXECUTE_CHANGE=false
CLI_MAY_ACCESS_NETWORK=false
```

## 3. Canonical owner

```text
src/manosube_agent_civilization/cli/
├── __init__.py     public exports
├── errors.py        CLIError / CLIArgumentError / CLIInvalidRootError
└── main.py          the one public command's own parser, route, and serialization
```

No second Boot, Store, Lineage, Recovery, Objective, Boundary, Authority, or Binding owner is
created anywhere in this package. Boot is invoked exclusively through its own existing public
entry point (`manosube_agent_civilization.boot.boot_project`); the Store is constructed
exclusively through the existing `FileStateStore` over the two caller-supplied roots; no new
schema and no new persisted record kind is introduced.

**Structural Review Round 1 correction (SHUKOU adoption
`ADOPT_P11_R1_CLI_PUBLIC_SURFACE_AND_FAILURE_BOUNDARY`).** The initial delivery resolved
Issue #47's "one console-script/module entry point" choice to a module entry point
(`python -m manosube_agent_civilization.cli boot ...`, via a `cli/__main__.py`), respecting
`pyproject.toml`'s own pre-existing v0.1 note that no `[project.scripts]` entry existed yet.
構造参謀 found this an unauthorized narrowing of Issue #47's own frozen semantic decision 3,
which fixes the public command's shape as exactly `manosube boot ...` -- with no
`[project.scripts]` entry, no installed environment actually exposes a `manosube` executable
at all. `pyproject.toml` now carries the one console-script entry
(`manosube = "manosube_agent_civilization.cli.main:main"`); `cli/__main__.py` is removed
entirely (its module-execution route is not merely undocumented but no longer exists), and
the trailing `if __name__ == "__main__":` guard is removed from `main.py` as well, since
`python -m manosube_agent_civilization.cli.main` would otherwise still resolve to a second,
undocumented invocation regardless of the package's own `__main__.py`. `manosube boot ...` is
now the sole external invocation of this adapter, in every sense: documented, installed, and
technically reachable.

## 4. Explicit non-claims

```text
CLI_IMPLEMENTED=true
PROJECT_DISCOVERY_IMPLEMENTED=false
FILESYSTEM_SCAN_IMPLEMENTED=false
STORE_PATH_INFERRED_FROM_CWD=false
STORE_RECOVERY_AUTO_EXECUTED=false
CHANGE_EXECUTION_IMPLEMENTED=false
COMMAND_EXECUTION_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
NETWORK_ACCESS_IMPLEMENTED=false
RUNTIME_OBSERVATION_IMPLEMENTED=false
TEMPORARY_AGENT_IMPLEMENTED=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
MODEL_ADAPTER_IMPLEMENTED=false
URL_READ_ONLY_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
CONSOLE_SCRIPT_ENTRY_ADDED=true
SECOND_PUBLIC_CLI_ENTRYPOINT=false
PHASE_11_COMPLETE=false
PHASE_12_ALLOWED=false
```
