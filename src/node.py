"""Base Node class for P2P network simulation.

This module defines the fundamental Node abstraction used by both
flooding and Kademlia implementations.
"""

from typing import Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Node:
    """Represents a node in the P2P network.

    Attributes:
        node_id: Unique identifier for the node
        resources: Set of resource IDs this node holds
        neighbors: Set of connected peer nodes
        metadata: Additional node-specific data (e.g., for Kademlia routing tables)
    """
    node_id: int
    resources: Set[int] = field(default_factory=set)
    neighbors: Set['Node'] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_resource(self, resource_id: int) -> bool:
        """Check if this node holds a specific resource.

        Args:
            resource_id: ID of the resource to check

        Returns:
            True if this node holds the resource, False otherwise
        """
        return resource_id in self.resources

    def add_neighbor(self, neighbor: 'Node') -> None:
        """Add a peer to this node's neighbor set.

        Args:
            neighbor: Node to add as neighbor
        """
        self.neighbors.add(neighbor)

    def remove_neighbor(self, neighbor: 'Node') -> None:
        """Remove a peer from this node's neighbor set.

        Args:
            neighbor: Node to remove from neighbors
        """
        self.neighbors.discard(neighbor)

    def __hash__(self) -> int:
        """Hash based on node_id to allow nodes in sets."""
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        """Equality based on node_id."""
        if not isinstance(other, Node):
            return NotImplemented
        return self.node_id == other.node_id

    def __repr__(self) -> str:
        return f"Node(id={self.node_id}, neighbors={len(self.neighbors)}, resources={len(self.resources)})"
