"""Every collected test runs once and expensive module fixtures stay on one runner."""

import pytest
from scripts.run_test_shard import partition_nodes


def test_partition_is_complete_disjoint_and_preserves_module_scope() -> None:
    nodes = [f"tests/{module}.py::test_case[{case}]" for module in range(9) for case in range(module + 1)]
    partitions = partition_nodes(nodes, 4)
    flattened = [node for partition in partitions for node in partition]
    assert sorted(flattened) == sorted(nodes)
    assert len(flattened) == len(set(flattened))
    owners = {}
    for index, partition in enumerate(partitions):
        for node in partition:
            module = node.split("::", 1)[0]
            assert owners.setdefault(module, index) == index
    assert partitions == partition_nodes(list(reversed(nodes)), 4)


@pytest.mark.parametrize("nodes,count", [([], 4), (["tests/a.py::test_a"] * 2, 4), (["tests/a.py::test_a"], 0)])
def test_ambiguous_or_invalid_inventory_is_refused(nodes: list[str], count: int) -> None:
    with pytest.raises(ValueError):
        partition_nodes(nodes, count)


def test_real_acceptance_receipt_is_shared_on_one_dedicated_runner() -> None:
    shared = [
        "tests/contract/v1_0_acceptance/test_gate22_rederivation.py::test_full_bundle",
        "tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py::test_nc8",
        "tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py::test_nc11",
    ]
    other = [f"tests/other_{index}.py::test_case" for index in range(6)]
    partitions = partition_nodes(shared + other, 4)
    assert sorted(partitions[-1]) == sorted(shared)
    assert sorted(node for group in partitions[:-1] for node in group) == sorted(other)
    assert partitions == partition_nodes(list(reversed(shared + other)), 4)
    assert sorted(partition_nodes(shared + other, 1)[0]) == sorted(shared + other)


def test_long_running_tiers_and_acceptance_have_separate_dedicated_runners() -> None:
    tiers = [
        f"tests/long_running_proof/test_long_running_proof_gate_20.py::test_tier[{tier}]"
        for tier in (10, 30, 50, 100)
    ]
    acceptance = [
        "tests/contract/v1_0_acceptance/test_gate22_rederivation.py::test_full_bundle",
        "tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py::test_nc8",
    ]
    other = [f"tests/other_{index}.py::test_case" for index in range(9)]
    nodes = tiers + acceptance + other
    partitions = partition_nodes(nodes, 5)
    assert sorted(partitions[-2]) == sorted(tiers)
    assert sorted(partitions[-1]) == sorted(acceptance)
    assert sorted(node for group in partitions[:-2] for node in group) == sorted(other)
    assert partitions == partition_nodes(list(reversed(nodes)), 5)
    assert sorted(partition_nodes(nodes, 1)[0]) == sorted(nodes)
