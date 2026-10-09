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
