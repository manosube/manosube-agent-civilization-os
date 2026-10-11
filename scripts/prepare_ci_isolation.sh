#!/usr/bin/env bash
# Only disposable GitHub-hosted runners: allow the explicit unshare sandbox helper.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_ENVIRONMENT:-}" != github-hosted ]]; then
  echo 'This preparation is restricted to disposable GitHub-hosted CI runners.' >&2
  exit 1
fi
if [[ -e /proc/sys/kernel/apparmor_restrict_unprivileged_userns ]]; then
  policy_path="$RUNNER_TEMP/manosube-ci-unshare.apparmor"
  cat > "$policy_path" <<'POLICY'
abi <abi/4.0>,
include <tunables/global>
profile manosube-ci-unshare /usr/bin/unshare flags=(unconfined) {
  userns,
}
POLICY
  # Preserve the system-wide restriction. This profile lasts only for this runner.
  sudo apparmor_parser -r "$policy_path"
fi
python - <<'PY'
import json
from manosube_agent_civilization.development_binding.review_adapter import check_isolation_capability
capability = check_isolation_capability()
print(json.dumps({"isolation_available": capability.available, "reason": capability.reason}))
if not capability.available:
    raise SystemExit("Real isolation probe failed; refusing to substitute a mock or skip the checks")
PY
