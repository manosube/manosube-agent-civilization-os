"""Operational exemptions never exempt an entire module from writer detection."""

import ast

import pytest

from manosube_agent_civilization import topology


def test_review_module_extra_writer_remains_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    module = "manosube_agent_civilization.development_binding.review_control"
    tree = ast.parse('def _write_ledger(path, data):\n    path.write_text(data)\ndef rogue(path, data):\n    path.write_text(data)\n')
    monkeypatch.setattr(topology, "_module_source_trees", lambda: [(module, tree)])
    assert topology._direct_filesystem_write_sites() == [module + ":4"]


def test_real_operational_inventory_keeps_a_single_canonical_owner() -> None:
    topology.kernel_topology_inventory.cache_clear()
    try:
        assert topology.k002_single_canonical_state_owner()
        assert topology.k003_single_authority_and_transition_owner()
        assert topology.r001_single_atomic_committer()
    finally:
        topology.kernel_topology_inventory.cache_clear()
