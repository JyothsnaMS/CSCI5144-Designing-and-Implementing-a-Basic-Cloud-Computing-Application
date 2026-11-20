
import pytest

from hash_ring import ConsistentHashRing


def create_ring():
    ring = ConsistentHashRing(replicas=100)
    ring.add_node("http://store1:8080")
    ring.add_node("http://store2:8080")
    ring.add_node("http://store3:8080")
    return ring


def test_add_nodes():
    ring = ConsistentHashRing()
    ring.add_node("store1")
    ring.add_node("store2")

    assert ring.get_nodes() == ["store1", "store2"]


def test_duplicate_node():
    ring = ConsistentHashRing()
    ring.add_node("store1")
    ring.add_node("store1")

    assert ring.get_nodes() == ["store1"]


def test_remove_node():
    ring = create_ring()
    ring.remove_node("http://store2:8080")

    assert "http://store2:8080" not in ring.get_nodes()


def test_get_node():
    ring = create_ring()

    owner = ring.get_node("student-123")

    assert owner in ring.get_nodes()


def test_consistent_mapping():
    ring = create_ring()

    first_owner = ring.get_node("student-123")
    second_owner = ring.get_node("student-123")

    assert first_owner == second_owner


def test_empty_ring():
    ring = ConsistentHashRing()

    with pytest.raises(ValueError):
        ring.get_node("student-123")


def test_invalid_replicas():
    with pytest.raises(ValueError):
        ConsistentHashRing(replicas=0)


def test_distribution():
    ring = create_ring()
    counts = {node: 0 for node in ring.get_nodes()}

    for i in range(10000):
        owner = ring.get_node(f"key-{i}")
        counts[owner] += 1

    for count in counts.values():
        assert count > 0


def test_key_movement_after_adding_node():
    ring = ConsistentHashRing(replicas=100)
    ring.add_node("store1")
    ring.add_node("store2")

    keys = [f"key-{i}" for i in range(10000)]
    original_owners = {
        key: ring.get_node(key) for key in keys
    }

    ring.add_node("store3")

    moved_keys = sum(
        1 for key in keys
        if ring.get_node(key) != original_owners[key]
    )

    assert moved_keys > 0
    assert moved_keys < len(keys)
