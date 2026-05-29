"""Flooding-based P2P network implementation (unstructured).

This module implements a Gnutella-style flooding search over a random
graph topology. Nodes propagate queries to all neighbors until TTL expires
or the resource is found.
"""

from typing import Set, Optional
import logging

from .node import Node
from .network import Network
from .metrics import SearchMetrics

logger = logging.getLogger(__name__)


class FloodingNetwork(Network):
    """P2P network using flooding search strategy.

    Extends base Network with flooding-specific search logic.
    """

    def __init__(self, size: int, neighbors_per_node: int, ttl: int = 20, seed: Optional[int] = None):
        """Initialize flooding network.

        Args:
            size: Number of nodes (N)
            neighbors_per_node: Number of neighbors per node (K)
            ttl: Time-to-live for query propagation
            seed: Random seed for reproducibility
        """
        super().__init__(size, seed)
        self.neighbors_per_node = neighbors_per_node
        self.ttl = ttl

        # Create random topology
        self.create_random_topology(neighbors_per_node)

        logger.info(f"FloodingNetwork initialized: N={size}, K={neighbors_per_node}, TTL={ttl}")

    def search(self, initiator_id: int, resource_id: int) -> SearchMetrics:
        """Perform flooding search for a resource.

        The initiator node sends query to all neighbors. Each neighbor
        forwards to its neighbors (except sender) until TTL expires or
        resource is found.

        Args:
            initiator_id: ID of node initiating the search
            resource_id: ID of resource to find

        Returns:
            SearchMetrics with results of the search
        """
        initiator = self.get_node(initiator_id)
        if initiator is None:
            logger.error(f"Invalid initiator_id: {initiator_id}")
            return SearchMetrics(initiator_id=initiator_id, resource_id=resource_id)

        metrics = SearchMetrics(
            initiator_id=initiator_id,
            resource_id=resource_id
        )

        # Track which nodes have seen the query (to prevent loops)
        visited: Set[Node] = {initiator}

        # Queue: (current_node, hops_from_initiator)
        queue: list[tuple[Node, int]] = [(initiator, 0)]

        while queue:
            current, hops = queue.pop(0)
            metrics.nodes_reached += 1

            # Check if current node has the resource
            if current.has_resource(resource_id):
                metrics.success = True
                metrics.hops = hops
                logger.debug(f"Resource {resource_id} found at node {current.node_id} after {hops} hops")
                break

            # Stop if TTL exceeded
            if hops >= self.ttl:
                continue

            # Forward to neighbors
            for neighbor in current.neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, hops + 1))
                    metrics.messages += 1  # Count message sent to neighbor

        if not metrics.success:
            logger.debug(f"Resource {resource_id} not found after searching {metrics.nodes_reached} nodes")

        return metrics


def run_flooding_experiment(
    network_size: int,
    neighbors_k: int,
    num_searches: int,
    ttl: int = 20,
    seed: Optional[int] = None
) -> list[SearchMetrics]:
    """Run a complete flooding experiment.

    Creates network, distributes resources, performs multiple searches.

    Args:
        network_size: Number of nodes (N)
        neighbors_k: Neighbors per node (K)
        num_searches: Number of random searches to perform
        ttl: Time-to-live for queries
        seed: Random seed

    Returns:
        List of SearchMetrics for all searches
    """
    import random

    if seed is not None:
        random.seed(seed)

    # Create network
    net = FloodingNetwork(network_size, neighbors_k, ttl, seed)

    # Distribute resources (one resource per node for simplicity)
    net.distribute_resources(num_resources=network_size, replication=1)

    # Verify network is connected
    if not net.is_connected():
        logger.warning("Network is not fully connected - some searches may fail")

    # Perform searches
    results: list[SearchMetrics] = []
    for i in range(num_searches):
        initiator = random.randint(0, network_size - 1)
        resource = random.randint(0, network_size - 1)

        metrics = net.search(initiator, resource)
        results.append(metrics)

        if (i + 1) % 10 == 0:
            logger.info(f"Completed {i + 1}/{num_searches} searches")

    return results
