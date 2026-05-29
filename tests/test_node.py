"""Unit tests for Node class."""

import pytest
from src.node import Node


def test_node_creation():
    """Test basic node creation."""
    node = Node(node_id=42)
    assert node.node_id == 42
    assert len(node.resources) == 0
    assert len(node.neighbors) == 0


def test_node_has_resource():
    """Test resource checking."""
    node = Node(node_id=1)
    node.resources.add(100)
    node.resources.add(200)

    assert node.has_resource(100)
    assert node.has_resource(200)
    assert not node.has_resource(300)


def test_node_add_neighbor():
    """Test adding neighbors."""
    node1 = Node(node_id=1)
    node2 = Node(node_id=2)

    node1.add_neighbor(node2)

    assert node2 in node1.neighbors
    assert len(node1.neighbors) == 1


def test_node_remove_neighbor():
    """Test removing neighbors."""
    node1 = Node(node_id=1)
    node2 = Node(node_id=2)

    node1.add_neighbor(node2)
    assert node2 in node1.neighbors

    node1.remove_neighbor(node2)
    assert node2 not in node1.neighbors


def test_node_equality():
    """Test node equality based on node_id."""
    node1 = Node(node_id=5)
    node2 = Node(node_id=5)
    node3 = Node(node_id=10)

    assert node1 == node2
    assert node1 != node3


def test_node_hash():
    """Test that nodes can be used in sets."""
    node1 = Node(node_id=1)
    node2 = Node(node_id=2)
    node3 = Node(node_id=1)  # Same ID as node1

    node_set = {node1, node2, node3}
    # node1 and node3 should be considered the same
    assert len(node_set) == 2
