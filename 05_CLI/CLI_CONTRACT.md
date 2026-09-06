# CLI Contract (Phase 11, Issue #47)

```text
DOC_TYPE=CLI_CONTRACT
DOCUMENT_ID=CLI-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=PROCESS_ADAPTER
PREDECESSOR_ISSUE=#45
PREDECESSOR_PR=#46
PREDECESSOR_MERGE_COMMIT=7bc714797098ca5d74a736598f668bbb1dce58ae
```

See `CLI_INDEX.md` for this contract set's own position and reading order.

## 1. Position

The CLI exposes the existing, already-verified Phase 10 Boot route
(`manosube_agent_civilization.boot.boot_project`) as one explicit, read-only,
provider-neutral command-line command, so a human or automation process can restore an
already-bound Project's Boot Context without writing any Python. It is produced by exactly
one owner (`manosube_agent_civilization.cli`) and its one public command invokes Boot exactly
once.

```text
CLI_OWNER_COUNT=1
PUBLIC_CLI_COMMAND_COUNT=1
```

## 2. Public signature

```text
python -m manosube_agent_civilization.cli boot \
    --store-root PATH --schema-root PATH --project-id ID --project-binding-id ID
```

displayed (via the parser's own `prog`) as `manosube boot --store-root ... --schema-root ...
--project-id ... --project-binding-id ...` -- the exact command shape Issue #47 itself
illustrates. All four flags are required; there is no current-working-directory, environment
variable, filesystem scan, repository URL, directory name, or "only project" inference of any
kind (frozen semantic decision 2, below).

## 3. Frozen semantic decisions

1. **One adapter, existing owners only.** The CLI owns argument parsing, process exit
   status, and canonical-JSON serialization. Boot owns restoration; the Store owns
   persistence and corruption classification; Binding/Authority/State retain their existing
   owners. The CLI creates none of these a second time.
2. **All inputs are explicit.** A successful command requires explicit `--store-root`,
   `--schema-root`, `--project-id`, and `--project-binding-id`. No current-working-directory,
   environment, filesystem scan, repository URL, directory name, or "only project" inference
   is allowed.
3. **One public command.** The initial surface is exactly `boot`, with exactly the four
   flags above. Aliases, interactive prompts, default project selection, and future command
   placeholders are forbidden.
4. **CLI invokes Boot once.** The route calls `boot_project` exactly once and must not call
   `bind_project`, `FileStateStore.initialize`, `.commit`, `.recover`, `.load_current`, or
   read a Store-private path directly.
5. **Read-only is end-to-end.** Both the successful route and every rejection route make
   zero Store writes: no State transition, lineage append, record promotion, manifest
   creation, journal change, current-view materialization, or external operation.
6. **Deterministic output.** Success writes exactly one canonical JSON document to stdout,
   terminated by one newline, representing the verified Boot Context projection -- generated
   from the deep-frozen `BootContext` without preserving any mutable alias into it (`main.py
   ::_plain` rebuilds a fresh, plain `dict`/`list` tree; `state.canonicalize.
   canonical_json_bytes` -- the same canonicalization owner Store and State already use, never
   a second serializer -- sorts every key and normalizes every string deterministically).
   Stderr is empty on success.
7. **Typed, machine-readable failures.** Every rejection -- a CLI-owned argument/root error,
   or any typed error propagating unchanged from Boot, Binding, the Store, Authority, or
   canonical-JSON/schema/fingerprint processing, or (as a last-resort adapter-owned safety
   net) any other unclassified exception -- writes exactly one canonical JSON error object to
   stderr (`{"error": <exception's own class name>, "message": <str(exception)>}`) and exits
   non-zero. No traceback is ever emitted. Stdout remains empty. The CLI never catches and
   rewraps a domain error into a different category; the `error` field is always the already-
   raised instance's own class name, never a hand-maintained second classification that could
   drift from it.
8. **No capability escalation.** A successful result is a projection, not a grant of
   Authority or a command-execution handle. No tokens, credentials, secrets, network clients,
   or persistent CLI receipts are emitted or created (and `canonical_json_bytes` itself still
   refuses any accidental secret-bearing field name at any depth, exactly as it already does
   for Store/State's own canonical bodies).
9. **Fresh process is load-bearing.** The primary positive proof invokes the CLI as a real
   `python -m manosube_agent_civilization.cli` subprocess against a real Phase 9-bound Store,
   and proves byte-equivalent stdout across repeated invocations.
10. **Phase boundary remains strict.** Temporary Agent (12), Independent Verification (13),
    GitHub (14), Runtime (15), model adapters, URL reads, autonomous Change, and multi-agent
    execution remain out of scope; Phase 12 remains forbidden until this PR is structurally
    reviewed, accepted, and manually merged.

## 4. Canonical owner

```text
src/manosube_agent_civilization/cli/
├── __init__.py     public exports
├── __main__.py      python -m manosube_agent_civilization.cli entry point
├── errors.py        CLIError / CLIArgumentError / CLIInvalidRootError
└── main.py          the one public command's own parser, route, and serialization
```

`CLIArgumentError` and `CLIInvalidRootError` exist only for the two checks this adapter
itself owns (malformed/missing command-line arguments; a `--store-root`/`--schema-root` that
does not name an existing directory). Every other failure mode propagates the existing
owning domain's own typed error unchanged -- `manosube_agent_civilization.boot.
{BootNotFoundError,BootConsistencyError}`, `manosube_agent_civilization.binding.errors.
{BindingIdentityError,BindingValidationError}`, `manosube_agent_civilization.store.errors.
{CorruptStoreError,StateNotFoundError,BoundaryError,...}`, `manosube_agent_civilization.
authority.errors.*`, and `manosube_agent_civilization.state.errors.CanonicalizationError`
(and its subclasses, e.g. `SchemaValidationError`) -- classified only by `main.py
::_error_document` reading the already-raised instance's own class name, never rewrapped.

## 5. Canonical successful route

```text
1. Parse the command line via the parser's own error() override -- a parse failure raises
   CLIArgumentError instead of argparse's own usage-text-then-exit, so it gets the identical
   deterministic JSON-to-stderr treatment as every other rejection (§6).
2. Require --store-root and --schema-root to each name an existing directory, or raise
   CLIInvalidRootError -- a CLI-owned check; the Store itself never validates root existence.
3. Construct the existing FileStateStore(store_root, schema_root=schema_root).
4. Invoke boot_project(store, project_id=..., project_binding_id=...) exactly once.
5. Convert the returned immutable BootContext to its deterministic JSON projection
   (main.py::_projection, via _plain then canonical_json_bytes).
6. Write that one document plus one trailing newline to stdout, and exit 0. Stderr is empty.
7. Prove the identical route from a fresh python -m manosube_agent_civilization.cli
   subprocess, repeated, with byte-equal stdout each time and zero Store mutation.
```

## 6. Required rejection proofs

At minimum, the CLI fails closed, with zero Store mutation
(`STATE_TRANSITION_COUNT_DELTA=0`, `LINEAGE_APPEND_COUNT_DELTA=0`, `RECORD_COUNT_DELTA=0`,
`TRANSACTION_MANIFEST_COUNT_DELTA=0`, `EXTERNAL_OPERATION_COUNT_DELTA=0`), empty stdout
(`STDOUT_BYTES=0`), a single canonical JSON error object on stderr, and a non-zero exit, for:

```text
- missing or malformed required command-line arguments, or an unknown subcommand
  (CLIArgumentError)
- a --store-root or --schema-root that does not name an existing directory, including one
  that names an existing plain file instead (CLIInvalidRootError)
- a --schema-root that names an existing but unusable directory (no canonical schemas under
  it) -- caught by this adapter's own top-level unclassified-exception safety net, still
  typed, traceback-free, and non-zero-exit
- project-id/path/URL/directory-name substitution (Boot's own locator rejection,
  BootNotFoundError)
- missing project or Product Binding (BootNotFoundError)
- a tampered persisted Project Binding, Objective Revision, or Authority Rule -- caught by
  the Store's own generic manifest-claimant tamper detection before Boot's own identity
  reverification ever runs (CorruptStoreError, propagated unchanged)
- an interrupted transaction at a representative crash stage, a later transaction's deleted
  recovery journal, and a later transaction's recovery journal replaced by a non-directory
  entry -- all three collapse to the Store's own CorruptStoreError (P10-R2/R3/R4), propagated
  unchanged
- a malformed or lineage-divergent present current.json view (CorruptStoreError)
- an attempted CLI path to Store initialization, recovery completion, State commit, Binding
  adoption, filesystem discovery, command execution, network/GitHub access, or Agent startup
  (proven by a static AST/import scan over cli/main.py, cli/__init__.py, cli/__main__.py)
- stderr/stdout channel inversion, traceback leakage, or non-deterministic output (every
  rejection test asserts empty stdout, a parseable single-line JSON stderr document with no
  "Traceback" substring, and a non-zero exit; the positive route additionally proves
  byte-equal stdout across repeated fresh-process invocations)
```

A missing materialized `current.json` view is **not** a rejection: Boot succeeds and the CLI
still writes nothing, exactly as Boot itself already proves (P10-R1-F2); the CLI-level test
suite proves this positive route stays true through the CLI's own boundary too.

## 7. Explicit non-claims

```text
PROJECT_DISCOVERY_IMPLEMENTED=false
STORE_PATH_INFERRED_FROM_CWD=false
STORE_RECOVERY_AUTO_EXECUTED=false
CHANGE_EXECUTION_IMPLEMENTED=false
TEMPORARY_AGENT_IMPLEMENTED=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
NETWORK_ACCESS_IMPLEMENTED=false
RUNTIME_OBSERVATION_IMPLEMENTED=false
MODEL_ADAPTER_IMPLEMENTED=false
URL_READ_ONLY_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
CONSOLE_SCRIPT_ENTRY_ADDED=false
```
