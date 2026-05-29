"""Network topology management for P2P simulations.

This module handles the creation and management of network topologies:
- Random graph generation for flooding networks
- Resource distribution across nodes
- Network statistics and analysis
"""

from typing import List, Set, Optional
import random
import logging

from .node import Node

logger = logging.getLogger(__name__)


class Network:
    """Manages the P2P network topology and nodes.

    Attributes:
        nodes: List of all nodes in the network
        size: Number of nodes in the network
    """

    def __init__(self, size: int, seed: Optional[int] = None):
        """Initialize network with given size.

        Args:
            size: Number of nodes to create
            seed: Random seed for reproducibility
        """
        self.size = size
        self.nodes: List[Node] = []

        if seed is not None:
            random.seed(seed)

        # Create nodes
        for i in range(size):
            self.nodes.append(Node(node_id=i))

        logger.info(f"Created network with {size} nodes")

    def get_node(self, node_id: int) -> Optional[Node]:
        """Get node by ID.

        Args:
            node_id: ID of the node to retrieve

        Returns:
            Node with given ID, or None if not found
        """
        if 0 <= node_id < self.size:
            return self.nodes[node_id]
        return None

    def distribute_resources(self, num_resources: int, replication: int = 1) -> None:
        """Distribute resources randomly across nodes.

        Args:
            num_resources: Total number of unique resources
            replication: Number of copies of each resource (default 1)
        """
        for resource_id in range(num_resources):
            # Randomly select nodes to hold this resource
            holders = random.sample(self.nodes, min(replication, self.size))
            for node in holders:
                node.resources.add(resource_id)

        logger.info(f"Distributed {num_resources} resources with replication={replication}")

    def create_random_topology(self, neighbors_per_node: int) -> None:
        """Create random graph topology for flooding network.

        Each node gets K random neighbors (undirected edges).

        Args:
            neighbors_per_node: Number of neighbors (K) per node
        """
        for node in self.nodes:
            # Get potential neighbors (all nodes except this one)
            candidates = [n for n in self.nodes if n != node]

            # Add random neighbors
            num_to_add = min(neighbors_per_node, len(candidates))
            new_neighbors = random.sample(candidates, num_to_add)

            for neighbor in new_neighbors:
                # Create bidirectional connection
                node.add_neighbor(neighbor)
                neighbor.add_neighbor(node)

        logger.info(f"Created random topology with K={neighbors_per_node} neighbors per node")

    def is_connected(self) -> bool:
        """Check if the network is connected (BFS from node 0).

        Returns:
            True if all nodes are reachable from node 0, False otherwise
        """
        if not self.nodes:
            return False

        visited: Set[Node] = set()
        queue: List[Node] = [self.nodes[0]]
        visited.add(self.nodes[0])

        while queue:
            current = queue.pop(0)
            for neighbor in current.neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        is_conn = len(visited) == self.size
        logger.debug(f"Network connectivity check: {is_conn} ({len(visited)}/{self.size} reachable)")
        return is_conn

    def avg_degree(self) -> float:
        """Calculate average node degree in the network.

        Returns:
            Average number of neighbors per node
        """
        if not self.nodes:
            return 0.0
        total_degree = sum(len(node.neighbors) for node in self.nodes)
        return total_degree / len(self.nodes)

    def stats(self) -> dict:
        """Get network statistics.

        Returns:
            Dictionary with network statistics
        """
        return {
            'size': self.size,
            'connected': self.is_connected(),
            'avg_degree': self.avg_degree(),
            'total_resources': sum(len(node.resources) for node in self.nodes)
        }
