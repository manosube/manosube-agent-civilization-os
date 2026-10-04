# Runtime observation transports (Issue #105)

This is an operator-facing guide, not a canonical design document. The load-bearing design
lives in `10_RUNTIME/RUNTIME_CONTRACT.md` §17 (read that first if you are changing behavior,
not just operating it); this file only explains how to actually use what that section
describes.

Issue #64 shipped one way to observe a running deployment: `HTTP_GET_BOUNDED`, a bounded HTTP
GET. Issue #105 adds a second, `SSH_EXEC_BOUNDED`, for a target reachable only over SSH, plus
two ways to run it:

- **Capability A -- manual.** A Human operator is shown an exact, copy/paste-able `ssh`
  command, runs it themselves, and feeds the result back in. No grant is strictly required for
  a Human to simply run a command this package rendered; a grant is required before this
  package's own CLI will *render* one, because rendering is itself part of what Issue #105's
  adoption gates.
- **Capability B -- grant-gated unattended.** This package runs the identical `ssh` command
  itself, with no Human present at the moment of execution, but only when a Human-ratified
  grant explicitly says so, for that exact target, right now.

Neither capability connects to anything by merely existing. Nothing in this delivery holds a
credential, provisions a key, or is wired into a real target -- every example below runs
against a local fixture or is marked as not yet executed against anything real.

## 1. Prerequisites

- This package installed (editable is fine): `pip install -e .`
- An `ssh` client available wherever Capability A's command is actually run (a Human's own
  machine, or a GitHub Actions runner -- `ubuntu-latest` ships one).
- For Capability B only: a **bounded-SSH-observation grant**, ratified by SHUKOU (see §2).
- `scripts/runtime_observation_probe.py` deployed, read-only, to the target -- the one script
  the rendered/executed command actually runs there. Deploying it is an operational step this
  delivery does not perform; see §5.

Nothing here requires or assumes a VPS or cloud provider exists yet. Every command in this
guide can be exercised against `127.0.0.1` with the probe script copied onto the same machine.

## 2. The grant

A grant is a plain JSON object -- not a canonical Store record, not a new Kernel element, and
not resolved through Boot. It is checked entirely offline, by
`manosube_agent_civilization.runtime.transport_control.require_valid_grant` and its siblings,
exactly the way `development_binding`'s own executor-eligibility grants are checked in a
different part of this Kernel. Its *fields* name a target, a probe artifact, and a window; what
makes it a grant at all is its own `signature` -- a genuine Ed25519 signature by the exact
Project Binding's own Human Authority, verified against a fresh Boot restoration for the exact
`project_id`/`project_binding_id` the attempt is actually using (PR #108 Structural Review
Round 1, F1) -- never a self-asserted `decision_status` string alone.

```jsonc
{
  "schema_version": "0.1",
  "grant_id": "GRANT-2026-EXAMPLE-1",
  "project_id": "PRJ-EXAMPLE",
  "project_binding_id": "PROJBIND-EXAMPLE",
  "provider": "local",
  "deployment_id": "widget-service",
  "instance_identity": "widget-service-1",
  "deployment_fingerprint": "sha256:<64 hex chars -- the target's own current claimed identity>",
  "host": "127.0.0.1",
  "port": 22,
  "user": "probe",
  "probe_identity": "OS_HEALTH_SNAPSHOT_BOUNDED",
  "probe_script_sha256": "<the real, current SHA-256 of scripts/runtime_observation_probe.py>",
  "permitted_fields": ["hostname"],
  "max_output_bytes": 1048576,
  "max_lines": 200,
  "max_timeout_seconds": 30,
  "permitted_transports": ["MANUAL_SSH"],
  "issued_at": "2026-01-01T00:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z",
  "decision_status": "RATIFIED",
  "signature": {
    "algorithm": "ed25519",
    "key_id": "<the Project Binding's own human_authority_signing_key.key_id>",
    "value": "<128 hex chars -- signed over every field above except signature itself>"
  }
}
```

Every field is required; no field is optional and no unknown field is accepted. `probe_identity`
must be one of exactly `OS_HEALTH_SNAPSHOT_BOUNDED` / `SOURCE_LOG_EXCERPT_BOUNDED` -- the same
closed vocabulary a Boundary's own `endpoint.probe_identity` uses. `permitted_transports` lists
which of `GITHUB_ACTIONS` / `MANUAL_SSH` / `PREAUTHORIZED_UNATTENDED_SSH` this one grant
authorizes; a grant that should permit Capability A, a real Actions-executed observation, and
the unattended half of Capability B lists all three. `decision_status` must be exactly
`"RATIFIED"` and `signature` must genuinely verify against the real Project Binding -- there is
no default-admit path, and an unratified or unsigned grant is refused with the identical error
every other malformed field is.

**`deployment_fingerprint` and `probe_script_sha256` (PR #108 Structural Review Round 2,
SR2-F2/SR2-F4).** `deployment_fingerprint` binds the grant to the target's own *current* claimed
identity, not merely its stable provider/deployment/instance coordinates -- a grant issued
against one declared identity is refused once the real attempt's own target has rotated to a
new one, even though every other coordinate still matches. `probe_script_sha256` must equal the
real, current SHA-256 digest of `scripts/runtime_observation_probe.py` as this repository ships
it (`manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256`); because this field is
itself one of the fields the Human Authority's own signature covers, a live probe report's own
self-reported digest is compared against *this exact grant's* signed value, never against the
bare public constant directly -- a forged or substituted digest can never be made to agree with
a genuine signature. This is a disclosed, honestly bounded guarantee: no stronger remote
attestation primitive exists over plain SSH, so what is actually proved is "the Human Authority
signed off on exactly this digest being run," not an independent cryptographic attestation of
what code genuinely executed on the remote target.

**Where a grant lives.** This delivery introduces no grant store, no schema file under
`01_SCHEMA/`, and no Store record kind. A grant is an ordinary JSON file an operator keeps
(or a GitHub Actions `workflow_dispatch` input, as `grant_json` on the shipped
`.github/workflows/runtime_observation.yml` workflow) -- independent of the canonical Store on
purpose, exactly as `transport_control.py`'s own module docstring states ("this module creates
no second Runtime, Authority, Evidence, State, or Reflow owner"). Where it is kept, how many
copies exist, and who may edit the file are operational decisions for whoever deploys this,
not something this package tracks.

**Expiry and revocation.** A grant's own `expires_at` is the only revocation mechanism this
delivery ships: once `now` passes `expires_at`, every function in `transport_control.py`
refuses it, with zero exceptions and zero grace period. There is no separate revoke call,
because there is nothing stateful to revoke -- the grant is re-validated, fully, on every use.
To revoke a grant *before* its own `expires_at`, stop distributing/using that file; a grant
whose JSON no caller still holds authorizes nothing, because nothing ever looks it up by
`grant_id` alone. If a grant was already shared more broadly than intended, the only clean fix
is to treat it as compromised and have SHUKOU ratify a replacement with a different
`grant_id` and a window that starts now -- the old one still technically validates until its
own `expires_at`, so narrow that window deliberately when ratifying, not as an afterthought.

## 3. Capability A -- manual, step by step

1. Get a ratified grant naming `"MANUAL_SSH"` in `permitted_transports` (§2).
2. Render the command:

   ```bash
   python scripts/runtime_observation_transport.py render-command \
     --grant-file grant.json \
     --now "2026-06-01T00:00:00Z"
   ```

   Output: `{"ok": true, "command": "ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o
   ConnectTimeout=10 -p 22 probe@127.0.0.1 'python3 runtime_observation_probe.py
   OS_HEALTH_SNAPSHOT_BOUNDED'"}`. The exact same string, field for field, is what Capability B
   would run unattended for the identical grant -- `render_manual_ssh_command` and
   `SshRuntimeAdapter.observe` both build it through the one shared
   `network.render_ssh_command_argv`.
3. A Human operator copies that command, runs it themselves (from their own terminal, or
   pasted into a GitHub Actions step -- the shipped `runtime_observation.yml` workflow does
   exactly step 2 and stops there; it never runs the command itself).
4. The probe script prints one JSON line. Validate/normalize it:

   ```bash
   python scripts/runtime_observation_transport.py import-output --report-file report.json
   ```
5. Feed the result into the real canonical route the same way any other observation is fed in
   -- `observe_runtime_target(..., boundary=<SSH_EXEC_BOUNDED boundary>, adapter=...)`. This
   guide does not script that last step end to end, because it depends on the calling project's
   own Store, Project, and target identity, which this package never assumes.

Rendering a command never opens a connection. Running it is the Human's own act, over a
connection this package never opens.

## 4. Capability B -- grant-gated unattended, step by step

1. Get a ratified grant naming `"PREAUTHORIZED_UNATTENDED_SSH"` in `permitted_transports`.
2. Decide the transport for this attempt:

   ```bash
   python scripts/runtime_observation_transport.py classify-dispatch \
     --dispatched --runner-allocated
   # {"dispatch_status": "AVAILABLE"}
   ```

   `select_transport` prefers GitHub Actions whenever it reports `AVAILABLE` and no transport
   was explicitly requested -- Actions being unavailable never by itself selects
   `PREAUTHORIZED_UNATTENDED_SSH` through this function; an explicit request is always required
   for that mode here.
3. Run the observation, with an explicit request:

   ```bash
   python scripts/runtime_observation_transport.py observe \
     --grant-file grant.json \
     --target-identity-file target_identity.json \
     --store-root ./store \
     --schema-root 01_SCHEMA \
     --project-id PRJ-EXAMPLE \
     --project-binding-id PROJBIND-EXAMPLE \
     --permitted-fields hostname,uptime_seconds \
     --now "2026-06-01T00:00:00Z" \
     --actions-status UNAVAILABLE \
     --requested-transport PREAUTHORIZED_UNATTENDED_SSH
   ```

   This refuses, with zero SSH process ever spawned, unless the grant is valid, current, and
   actually names `PREAUTHORIZED_UNATTENDED_SSH` -- there is no path through this command that
   skips `transport_control.select_transport`. `GITHUB_ACTIONS` executes through this identical
   command too (PR #108 Structural Review Round 2, SR2-F1) -- the CLI no longer refuses every
   transport except the unattended one; only `MANUAL_SSH` is still never executed by this
   subcommand, since that mode's whole authorization act is a Human running the rendered
   command themselves.

**Automatic unattended fallback (SR2-F1), an explicit opt-in.** A caller that does not want to
make a per-attempt Human selection may instead pass `--allow-automatic-fallback`, with no
`--requested-transport` at all:

```bash
python scripts/runtime_observation_transport.py observe \
  --grant-file grant.json \
  --target-identity-file target_identity.json \
  --store-root ./store \
  --schema-root 01_SCHEMA \
  --project-id PRJ-EXAMPLE \
  --project-binding-id PROJBIND-EXAMPLE \
  --permitted-fields hostname,uptime_seconds \
  --now "2026-06-01T00:00:00Z" \
  --actions-status UNAVAILABLE \
  --allow-automatic-fallback
```

This resolves to `PREAUTHORIZED_UNATTENDED_SSH` automatically only once `--actions-status` is
exactly `UNAVAILABLE` (never the ambiguous `UNKNOWN`) and the grant already, explicitly permits
that transport -- the authority already fully pre-exists in the signed grant; this flag only
automates the mechanical trigger, never the authorization itself
(`select_transport`'s own existing, unchanged behavior is untouched; this is a separate,
narrowly scoped function, `select_transport_with_automatic_fallback`). Pass
`--attempt-already-satisfied` on a retry of an attempt a caller's own bounded, local
record already knows reached a transport, to refuse a second, duplicate unattended execution;
this package keeps no attempt ledger of its own, so that correlation is the caller's own
responsibility (`compute_runtime_observation_attempt_id`, surfaced in every `observe` output as
`attempt_id`, is the pure, deterministic identity a caller correlates against).

This delivery does not wire capability B into any scheduler, cron, or always-on controller; it
ships the gate and the CLI that exercises it, so a downstream project can invoke it from
whatever unattended controller it already has, under its own separate decision to actually run
one continuously.

## 5. Deploying the probe script to a real target

`scripts/runtime_observation_probe.py` is the one file that needs to exist on a target at all --
copy it there, read-only, and run it once by hand to confirm `python3
runtime_observation_probe.py OS_HEALTH_SNAPSHOT_BOUNDED` prints a JSON line. It takes no
installation step (stdlib only, Python 3.8+), reads no argument beyond the one closed
`probe_identity` positional, and never writes anything.

**Per-target path configuration is a sibling file, never an edit to this reviewed script
(PR #108 Structural Review Round 2, SR2-F4).** For `SOURCE_LOG_EXCERPT_BOUNDED`, place a
`runtime_observation_probe.config.json` file next to the deployed script (same directory,
resolved only relative to the script's own real location -- never a caller-supplied path):

```json
{
  "source_excerpt_path": "/opt/widget-service/source_excerpt.txt",
  "log_excerpt_path": "/var/log/widget-service/observed.log"
}
```

Either key, or the whole file, may be omitted -- an omitted key or an absent/unreadable/
malformed file falls back to this script's own shipped default for that path. **Do not edit
`SOURCE_EXCERPT_PATH`/`LOG_EXCERPT_PATH` directly in the script file itself** -- editing the
reviewed script changes its own SHA-256 content digest, which breaks the exact digest pin a
grant's own signed `probe_script_sha256` field is supposed to bind to a specific, reviewed
artifact (the earlier version of this guide instructed exactly that edit; it is withdrawn,
because it directly contradicted the very digest pin this delivery relies on). If this
repository's own probe script is ever genuinely revised, its new digest must be recomputed
(`manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256`) and a new grant issued
naming it -- never silently carried forward from an old approval.

## 6. What this delivery has, and has not, proven against a real target

- Every HTTP-transport claim in this repository's own tests runs against a real, disposable,
  local HTTP server (unchanged from Issue #64).
- Every SSH-transport test in this delivery's own suite runs the real
  `observe_runtime_target`/`SshRuntimeAdapter` pipeline with `subprocess.run` mocked to return
  exactly the JSON line the real probe script emits -- proving this package's own handling of
  that exact contract, never a real network/SSH round trip.
- No `ssh`/`sshd`/`ssh-keygen` binary exists in this delivery's own build/test environment, and
  installing one was out of scope for this delivery (a machine/service modification the
  adoption and handoff both explicitly prohibit). **The real local-SSH-fixture vertical proof,
  and the real unattended-dispatch-against-a-real-target proof, are both pending** -- not
  claimed by this delivery, and tracked for a future, separately authorized step once a real
  disposable SSH target (or a sandbox that can install `openssh-server`) is available.
- No production SSH connection, no credential, and no key of any kind was created, requested,
  or used anywhere in this delivery.

**PR #108 Structural Review Round 2 adds one further disclosed gap.** Neither
`scripts/runtime_observation_transport.py` (the CLI) nor `scripts/runtime_observation_probe.py`
(the probe) is part of the installed `manosube_agent_civilization` package, and this round's own
permitted-file inventory authorizes no new test file for either (`ADDITIONAL_PATH_AUTHORIZATION_
BY_THIS_RECORD=false`). This round's CLI-level corrections (real `GITHUB_ACTIONS`/automatic-
fallback execution, `import-output`'s own bound and grant-bound digest check) and the probe
script's own corrections (ancestor-symlink-safe paths, sibling configuration loading) were
verified by direct manual invocation against a real, Boot-bound fixture world during this
round's own correction work -- not by a permanent automated test, which a future round with
authorization to add one should supply. The security-critical logic both scripts call
(`transport_control.py`, `adapter.py`) is fully covered by this delivery's own automated suite
either way -- the scripts themselves are documented as "thin CLI wrappers" around exactly that
logic, and remain so.
