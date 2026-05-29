"""Unit tests for Kademlia implementation."""

import pytest
from src.kademlia import xor_distance, KademliaNode


def test_xor_distance_identity():
    """Test that XOR distance from a node to itself is 0."""
    assert xor_distance(5, 5) == 0
    assert xor_distance(100, 100) == 0


def test_xor_distance_symmetry():
    """Test that XOR distance is symmetric."""
    assert xor_distance(5, 10) == xor_distance(10, 5)
    assert xor_distance(100, 200) == xor_distance(200, 100)


def test_xor_distance_calculation():
    """Test XOR distance calculation with known values."""
    # 5 XOR 10 = 0101 XOR 1010 = 1111 = 15
    assert xor_distance(5, 10) == 15

    # 8 XOR 12 = 1000 XOR 1100 = 0100 = 4
    assert xor_distance(8, 12) == 4


def test_kademlia_node_creation():
    """Test KademliaNode creation."""
    node = KademliaNode(node_id=42, id_bits=8)

    assert node.node_id == 42
    assert node.id_bits == 8
    assert len(node.finger_table) == 0


def test_kademlia_node_distance():
    """Test distance calculation from KademliaNode."""
    node = KademliaNode(node_id=5, id_bits=8)

    assert node.distance_to(5) == 0
    assert node.distance_to(10) == 15


def test_kademlia_node_routing_table():
    """Test adding nodes to routing table."""
    node1 = KademliaNode(node_id=5, id_bits=8)
    node2 = KademliaNode(node_id=10, id_bits=8)
    node3 = KademliaNode(node_id=20, id_bits=8)

    node1.add_to_routing_table(node2)
    node1.add_to_routing_table(node3)

    # Should have entries for distances to node2 and node3
    assert len(node1.finger_table) >= 1


def test_kademlia_node_get_closest():
    """Test getting closest nodes to a target."""
    node1 = KademliaNode(node_id=0, id_bits=8)
    node2 = KademliaNode(node_id=10, id_bits=8)
    node3 = KademliaNode(node_id=20, id_bits=8)
    node4 = KademliaNode(node_id=30, id_bits=8)

    # Add nodes to routing table
    node1.add_to_routing_table(node2)
    node1.add_to_routing_table(node3)
    node1.add_to_routing_table(node4)

    # Find closest to target=15
    # Distances: node2(10)->15 is 5, node3(20)->15 is 27, node4(30)->15 is 17
    closest = node1.get_closest_nodes(target_id=15, k=2)

    assert len(closest) <= 2
    # node2 should be closest
    if len(closest) > 0:
        assert closest[0].node_id == 10
