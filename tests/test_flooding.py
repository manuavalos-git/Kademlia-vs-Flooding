"""Unit tests for flooding P2P network implementation."""

import pytest
from src.flooding import FloodingNetwork, run_flooding_experiment
from src.metrics import SearchMetrics


def test_flooding_search_finds_resource():
    """Search for a resource that exists in the network succeeds."""
    net = FloodingNetwork(size=20, neighbors_per_node=5, ttl=20, seed=42)
    net.distribute_resources(num_resources=20, replication=1)

    # Pick a node that actually holds a resource
    resource_holder = next(n for n in net.nodes if n.resources)
    resource_id = next(iter(resource_holder.resources))

    # Search from a different node
    initiator = next(n for n in net.nodes if n.node_id != resource_holder.node_id)
    metrics = net.search(initiator.node_id, resource_id)

    assert metrics.success is True
    assert metrics.hops >= 0


def test_flooding_search_counts_messages():
    """A search in a multi-node network sends at least one message."""
    net = FloodingNetwork(size=10, neighbors_per_node=3, ttl=20, seed=42)
    net.distribute_resources(num_resources=10, replication=1)

    resource_holder = next(n for n in net.nodes if n.resources)
    resource_id = next(iter(resource_holder.resources))
    initiator = next(n for n in net.nodes if n.node_id != resource_holder.node_id)

    metrics = net.search(initiator.node_id, resource_id)

    assert metrics.messages > 0
    assert metrics.nodes_reached > 0


def test_flooding_search_initiator_has_resource():
    """When the initiator already holds the resource, search returns immediately."""
    net = FloodingNetwork(size=10, neighbors_per_node=3, ttl=20, seed=42)

    # Manually assign a resource to node 0
    net.nodes[0].resources.add(999)

    metrics = net.search(initiator_id=0, resource_id=999)

    assert metrics.success is True
    assert metrics.hops == 0
    assert metrics.messages == 0


def test_flooding_search_ttl_limits_propagation():
    """TTL=1 reaches far fewer nodes than TTL=20 on the same network."""
    net = FloodingNetwork(size=50, neighbors_per_node=5, seed=42, ttl=1)
    # Place resource at a distant node so search is needed
    net.nodes[-1].resources.add(77)

    metrics_ttl1 = FloodingNetwork(size=50, neighbors_per_node=5, seed=42, ttl=1).search
    net_short = FloodingNetwork(size=50, neighbors_per_node=5, seed=42, ttl=1)
    net_long = FloodingNetwork(size=50, neighbors_per_node=5, seed=42, ttl=20)
    net_short.nodes[-1].resources.add(77)
    net_long.nodes[-1].resources.add(77)

    m_short = net_short.search(initiator_id=0, resource_id=77)
    m_long = net_long.search(initiator_id=0, resource_id=77)

    assert m_short.nodes_reached < m_long.nodes_reached


def test_flooding_search_unknown_resource_fails():
    """Searching for a resource that does not exist in the network returns failure."""
    net = FloodingNetwork(size=20, neighbors_per_node=4, ttl=20, seed=42)
    net.distribute_resources(num_resources=20, replication=1)

    # Resource ID 9999 is never distributed
    metrics = net.search(initiator_id=0, resource_id=9999)

    assert metrics.success is False
    assert metrics.hops == 0


def test_flooding_experiment_returns_correct_count():
    """run_flooding_experiment returns exactly num_searches SearchMetrics objects."""
    results = run_flooding_experiment(
        network_size=10,
        neighbors_k=3,
        num_searches=5,
        ttl=20,
        seed=42,
    )

    assert len(results) == 5
    assert all(isinstance(m, SearchMetrics) for m in results)


def test_flooding_experiment_success_rate_high():
    """On a connected network with generous TTL, success rate is at least 90%."""
    results = run_flooding_experiment(
        network_size=50,
        neighbors_k=5,
        num_searches=50,
        ttl=20,
        seed=42,
    )

    success_rate = sum(1 for m in results if m.success) / len(results)
    assert success_rate >= 0.90, f"Success rate too low: {success_rate:.2%}"
