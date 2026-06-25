"""Flooding-based P2P network implementation (unstructured).

This module implements a Gnutella-style flooding search over a random
graph topology. Nodes propagate queries to all neighbors until TTL expires
or the resource is found.
"""

from typing import Set, Optional, List
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

    # one resource per node
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


def _apply_flooding_churn(net: FloodingNetwork, num_churn: int, next_node_id: int) -> int:
    """Remove and replace num_churn nodes. Returns number of resources lost.

    Departed nodes disconnect from all neighbors. Arriving nodes connect to
    K random existing nodes. Resources of departed nodes are lost permanently.

    Args:
        net: The flooding network to mutate
        num_churn: Number of nodes to remove/add
        next_node_id: Starting ID for new nodes (ensures unique IDs)

    Returns:
        Number of resources lost due to departing nodes
    """
    import random

    departing = random.sample(net.nodes, min(num_churn, len(net.nodes)))
    resources_lost = 0

    for node in departing:
        resources_lost += len(node.resources)
        for neighbor in list(node.neighbors):
            neighbor.neighbors.discard(node)
        net.nodes.remove(node)

    net.size = len(net.nodes)

    for i in range(num_churn):
        if not net.nodes:
            break
        new_node = Node(node_id=next_node_id + i)
        candidates = random.sample(net.nodes, min(net.neighbors_per_node, len(net.nodes)))
        for neighbor in candidates:
            new_node.add_neighbor(neighbor)
            neighbor.add_neighbor(new_node)
        net.nodes.append(new_node)

    net.size = len(net.nodes)
    return resources_lost


def run_flooding_churn_experiment(
    network_size: int,
    neighbors_k: int,
    churn_rate: float,
    num_rounds: int = 20,
    searches_per_round: int = 50,
    ttl: int = 20,
    seed: Optional[int] = None
) -> List[dict]:
    """Run flooding experiment with churn over multiple rounds.

    Each round: perform searches on the current network, then apply churn
    (remove X% nodes, add X% new nodes). Resources of departed nodes are
    lost permanently to measure degradation.

    Args:
        network_size: Initial number of nodes (N)
        neighbors_k: Neighbors per node (K)
        churn_rate: Fraction of nodes that leave/join each round
        num_rounds: Number of churn rounds
        searches_per_round: Searches performed each round before churn
        ttl: Time-to-live for queries
        seed: Random seed

    Returns:
        List of per-round summary dicts
    """
    import random

    if seed is not None:
        random.seed(seed)

    net = FloodingNetwork(network_size, neighbors_k, ttl, seed)
    net.distribute_resources(num_resources=network_size, replication=1)

    next_node_id = network_size
    results = []

    for round_num in range(num_rounds):
        active_nodes = list(net.nodes)
        if not active_nodes:
            break

        round_metrics = []
        for _ in range(searches_per_round):
            initiator = random.choice(active_nodes)
            resource = random.randint(0, network_size - 1)
            metrics = net.search(initiator.node_id, resource)
            round_metrics.append(metrics)

        total = len(round_metrics)
        successful = sum(1 for m in round_metrics if m.success)
        avg_msgs = sum(m.messages for m in round_metrics) / total if total > 0 else 0.0
        avg_hops_val = (
            sum(m.hops for m in round_metrics if m.success) / successful
            if successful > 0 else 0.0
        )

        num_churn = max(1, int(len(net.nodes) * churn_rate))
        resources_lost = _apply_flooding_churn(net, num_churn, next_node_id)
        next_node_id += num_churn

        results.append({
            'round': round_num,
            'nodes_in_network': len(net.nodes),
            'nodes_churned': num_churn,
            'resources_lost': resources_lost,
            'total_searches': total,
            'successful_searches': successful,
            'success_rate': successful / total if total > 0 else 0.0,
            'avg_messages': avg_msgs,
            'avg_hops': avg_hops_val,
        })

        logger.info(
            f"Round {round_num}: success={successful/total*100:.1f}%, "
            f"resources_lost={resources_lost}, nodes={len(net.nodes)}"
        )

    return results
