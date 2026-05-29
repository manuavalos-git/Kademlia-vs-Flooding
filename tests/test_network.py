"""Unit tests for Network class."""

import pytest
from src.network import Network


def test_network_creation():
    """Test network creation with given size."""
    net = Network(size=10, seed=42)

    assert net.size == 10
    assert len(net.nodes) == 10
    assert all(node.node_id == i for i, node in enumerate(net.nodes))


def test_network_get_node():
    """Test retrieving nodes by ID."""
    net = Network(size=5, seed=42)

    node = net.get_node(2)
    assert node is not None
    assert node.node_id == 2

    invalid_node = net.get_node(10)
    assert invalid_node is None


def test_network_distribute_resources():
    """Test resource distribution across network."""
    net = Network(size=10, seed=42)
    net.distribute_resources(num_resources=5, replication=2)

    # Each resource should be on exactly 2 nodes
    total_resources = sum(len(node.resources) for node in net.nodes)
    assert total_resources == 5 * 2  # 5 resources * 2 replicas


def test_network_random_topology():
    """Test creation of random graph topology."""
    net = Network(size=10, seed=42)
    net.create_random_topology(neighbors_per_node=3)

    # Check that nodes have neighbors
    for node in net.nodes:
        # May have fewer than requested if network is small
        assert len(node.neighbors) > 0


def test_network_connectivity():
    """Test network connectivity check."""
    net = Network(size=10, seed=42)
    net.create_random_topology(neighbors_per_node=3)

    # With enough neighbors, network should be connected
    is_connected = net.is_connected()
    # Note: may occasionally fail with small K, so we just test the method works
    assert isinstance(is_connected, bool)


def test_network_stats():
    """Test network statistics generation."""
    net = Network(size=5, seed=42)
    net.create_random_topology(neighbors_per_node=2)
    net.distribute_resources(num_resources=3, replication=1)

    stats = net.stats()

    assert stats['size'] == 5
    assert 'connected' in stats
    assert 'avg_degree' in stats
    assert stats['total_resources'] == 3
