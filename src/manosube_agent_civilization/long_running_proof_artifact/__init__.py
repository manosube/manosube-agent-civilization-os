"""The Long-Running Proof Artifact Bundle (Issue #86 section 10, P87-R1-F8): one durable,
versioned, content-addressed record gathering a Phase 20 long-running proof run's own raw
events, derived metrics, lineage refs, session-loss/failure/recovery receipts, Agent-swap refs,
runtime-observation refs, environment manifest, corpus manifest, and reproduction procedure.

Public entrypoints (:mod:`~manosube_agent_civilization.long_running_proof_artifact.route`):

- :func:`~manosube_agent_civilization.long_running_proof_artifact.route.commit_artifact_bundle`
- :func:`~manosube_agent_civilization.long_running_proof_artifact.route.resolve_artifact_bundle`

See ``route.py``'s own module docstring for why this package structurally cannot become a new
owner of Canonical State, Authority, Evidence, Reflow, or Completion.
"""

from __future__ import annotations

from .route import commit_artifact_bundle, resolve_artifact_bundle

__all__ = ["commit_artifact_bundle", "resolve_artifact_bundle"]
