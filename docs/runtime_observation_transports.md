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
different part of this Kernel. Its *fields* name a target and a window; what makes it a grant at
all is `decision_authority`/`decision_status` -- SHUKOU's own ratification, recorded in the
object itself, never inferred from who is running the CLI.

```jsonc
{
  "schema_version": "0.1",
  "grant_id": "GRANT-2026-EXAMPLE-1",
  "project_id": "PRJ-EXAMPLE",
  "host": "127.0.0.1",
  "port": 22,
  "user": "probe",
  "probe_identity": "OS_HEALTH_SNAPSHOT_BOUNDED",
  "permitted_transports": ["MANUAL_SSH"],
  "issued_at": "2026-01-01T00:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z",
  "decision_authority": "SHUKOU",
  "decision_status": "RATIFIED"
}
```

Every field is required; no field is optional and no unknown field is accepted. `probe_identity`
must be one of exactly `OS_HEALTH_SNAPSHOT_BOUNDED` / `SOURCE_LOG_EXCERPT_BOUNDED` --
the same closed vocabulary a Boundary's own `endpoint.probe_identity` uses.
`permitted_transports` lists which of `GITHUB_ACTIONS` / `MANUAL_SSH` /
`PREAUTHORIZED_UNATTENDED_SSH` this one grant authorizes; a grant that should permit both
Capability A and the unattended half of Capability B lists both `MANUAL_SSH` and
`PREAUTHORIZED_UNATTENDED_SSH`. `decision_authority` must be exactly `"SHUKOU"` and
`decision_status` must be exactly `"RATIFIED"` -- there is no default-admit path, and an
unratified or differently-authored grant is refused with the identical error every other
malformed field is.

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
   `PREAUTHORIZED_UNATTENDED_SSH`; an explicit request is always required for that mode.
3. Run the observation:

   ```bash
   python scripts/runtime_observation_transport.py observe \
     --grant-file grant.json \
     --target-identity-file target_identity.json \
     --store-root ./store \
     --project-id PRJ-EXAMPLE \
     --project-binding-id PROJBIND-EXAMPLE \
     --permitted-fields hostname,uptime_seconds \
     --now "2026-06-01T00:00:00Z" \
     --actions-status UNAVAILABLE \
     --requested-transport PREAUTHORIZED_UNATTENDED_SSH
   ```

   This refuses, with zero SSH process ever spawned, unless the grant is valid, current, and
   actually names `PREAUTHORIZED_UNATTENDED_SSH` -- there is no path through this command that
   skips `transport_control.select_transport`.

This delivery does not wire capability B into any scheduler, cron, or always-on controller; it
ships the gate and the CLI that exercises it, so a downstream project can invoke it from
whatever unattended controller it already has, under its own separate decision to actually run
one continuously.

## 5. Deploying the probe script to a real target

`scripts/runtime_observation_probe.py` is the one file that needs to exist on a target at all --
copy it there, read-only, and run it once by hand to confirm `python3
runtime_observation_probe.py OS_HEALTH_SNAPSHOT_BOUNDED` prints a JSON line. It takes no
installation step (stdlib only, Python 3.8+), reads no argument beyond the one closed
`probe_identity` positional, and never writes anything. For `SOURCE_LOG_EXCERPT_BOUNDED`, edit
the one `LOG_EXCERPT_PATH` constant at the top of the file to the real log path on that target
*before* deploying it there -- that edit is the only per-target configuration this script has,
and it is never read from an argument, an environment variable, or any other caller-reachable
input.

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
