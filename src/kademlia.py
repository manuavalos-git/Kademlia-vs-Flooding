"""Kademlia DHT implementation (structured P2P).

This module implements a simplified Kademlia distributed hash table with:
- XOR distance metric
- Finger table routing (simplified k-buckets)
- Iterative lookup protocol
"""

from typing import List, Optional
import logging

from .node import Node
from .network import Network
from .metrics import SearchMetrics

logger = logging.getLogger(__name__)


def xor_distance(a: int, b: int) -> int:
    """Calculate XOR distance between two node IDs.

    XOR distance has important properties:
    - d(x, x) = 0 (identity)
    - d(x, y) = d(y, x) (symmetry)
    - d(x, y) + d(y, z) >= d(x, z) (triangle inequality)

    Args:
        a: First node ID
        b: Second node ID

    Returns:
        XOR distance between a and b
    """
    return a ^ b


class KademliaNode(Node):
    """Node in Kademlia network with routing table.

    Extends base Node with Kademlia-specific routing information.

    Attributes:
        finger_table: Simplified routing table mapping distances to closest known nodes
        id_bits: Number of bits in node ID
    """

    def __init__(self, node_id: int, id_bits: int):
        """Initialize Kademlia node.

        Args:
            node_id: Unique identifier (0 to 2^id_bits - 1)
            id_bits: Number of bits in ID space (B)
        """
        super().__init__(node_id)
        self.id_bits = id_bits
        self.finger_table: dict[int, Node] = {}  # distance -> closest known node

    def distance_to(self, other_id: int) -> int:
        """Calculate XOR distance to another node ID.

        Args:
            other_id: ID of the other node

        Returns:
            XOR distance
        """
        return xor_distance(self.node_id, other_id)

    def add_to_routing_table(self, node: Node) -> None:
        """Add a node to the routing table.

        Simplified version: just store the closest node for each power-of-2 distance.

        Args:
            node: Node to add to routing table
        """
        if node.node_id == self.node_id:
            return

        distance = self.distance_to(node.node_id)
        # Store this node if we don't have a better one for this distance range
        if distance not in self.finger_table:
            self.finger_table[distance] = node

    def get_closest_nodes(self, target_id: int, k: int) -> List[Node]:
        """Get k closest known nodes to target_id.

        Args:
            target_id: ID to find nodes close to
            k: Number of nodes to return

        Returns:
            List of up to k closest known nodes
        """
        # Combine finger table and neighbors
        known_nodes = set(self.finger_table.values()) | self.neighbors

        # Sort by distance to target
        sorted_nodes = sorted(
            known_nodes,
            key=lambda n: xor_distance(n.node_id, target_id)
        )

        return sorted_nodes[:k]


class KademliaNetwork(Network):
    """Kademlia DHT network implementation.

    Structured P2P network using XOR metric and iterative lookup.
    """

    def __init__(self, size: int, id_bits: int, k: int = 3, alpha: int = 3, seed: Optional[int] = None):
        """Initialize Kademlia network.

        Args:
            size: Number of nodes (N)
            id_bits: Bits in node ID space (B) - max 2^B nodes
            k: k-bucket size (nodes per routing entry)
            alpha: Concurrency parameter for iterative lookup
            seed: Random seed
        """
        # Don't call super().__init__ yet - we need to create KademliaNodes
        self.size = size
        self.id_bits = id_bits
        self.k = k
        self.alpha = alpha
        self.nodes: List[KademliaNode] = []

        import random
        if seed is not None:
            random.seed(seed)

        # Create Kademlia nodes with IDs in [0, 2^id_bits)
        max_id = 2 ** id_bits
        for i in range(size):
            node_id = i % max_id  # Ensure ID fits in id_bits
            self.nodes.append(KademliaNode(node_id, id_bits))

        # Build routing tables
        self._build_routing_tables()

        logger.info(f"KademliaNetwork initialized: N={size}, B={id_bits}, k={k}, alpha={alpha}")

    def _build_routing_tables(self) -> None:
        """Build routing tables for all nodes.

        Simplified: each node learns about a random subset of other nodes.
        In real Kademlia, routing tables are built through network activity.
        """
        import random

        for node in self.nodes:
            # Add random nodes to routing table
            others = [n for n in self.nodes if n.node_id != node.node_id]
            sample_size = min(len(others), self.id_bits * self.k)
            sample = random.sample(others, sample_size)

            for other in sample:
                node.add_to_routing_table(other)

        logger.debug("Built routing tables for all nodes")

    def find_responsible_node(self, key_id: int) -> Optional[Node]:
        """Find the node responsible for a given key.

        In Kademlia, the responsible node is the one with minimum XOR distance to the key.

        Args:
            key_id: ID of the key/resource

        Returns:
            Node with minimum distance to key_id
        """
        if not self.nodes:
            return None

        return min(self.nodes, key=lambda n: xor_distance(n.node_id, key_id))

    def search(self, initiator_id: int, resource_id: int) -> SearchMetrics:
        """Perform iterative Kademlia lookup for a resource.

        Iterative lookup:
        1. Start with k closest nodes the initiator knows
        2. Query those nodes for their k closest nodes to resource_id
        3. Repeat with newly discovered closer nodes
        4. Stop when we've found the responsible node or no closer nodes exist

        Args:
            initiator_id: ID of node initiating search
            resource_id: ID of resource to find

        Returns:
            SearchMetrics with search results
        """
        initiator = self.get_node(initiator_id)
        if initiator is None or not isinstance(initiator, KademliaNode):
            logger.error(f"Invalid initiator_id: {initiator_id}")
            return SearchMetrics(initiator_id=initiator_id, resource_id=resource_id)

        metrics = SearchMetrics(
            initiator_id=initiator_id,
            resource_id=resource_id
        )

        # Start with k closest nodes initiator knows
        closest = initiator.get_closest_nodes(resource_id, self.k)
        queried: set[int] = {initiator_id}
        hops = 0

        while closest:
            # Pick next closest node that we haven't queried
            next_node = None
            for node in closest:
                if node.node_id not in queried:
                    next_node = node
                    break

            if next_node is None:
                # No more nodes to query
                break

            queried.add(next_node.node_id)
            metrics.messages += 1
            metrics.nodes_reached += 1
            hops += 1

            # Check if this node has the resource
            if next_node.has_resource(resource_id):
                metrics.success = True
                metrics.hops = hops
                logger.debug(f"Resource {resource_id} found at node {next_node.node_id} after {hops} hops")
                break

            # Get closer nodes from this node (if it's a KademliaNode)
            if isinstance(next_node, KademliaNode):
                new_closest = next_node.get_closest_nodes(resource_id, self.k)
                # Merge with existing closest, keeping k closest overall
                all_candidates = set(closest) | set(new_closest)
                closest = sorted(
                    all_candidates,
                    key=lambda n: xor_distance(n.node_id, resource_id)
                )[:self.k]

        if not metrics.success:
            logger.debug(f"Resource {resource_id} not found after {hops} hops")

        return metrics


def run_kademlia_experiment(
    network_size: int,
    id_bits: int,
    num_searches: int,
    k: int = 3,
    alpha: int = 3,
    seed: Optional[int] = None
) -> list[SearchMetrics]:
    """Run a complete Kademlia experiment.

    Args:
        network_size: Number of nodes (N)
        id_bits: Bits in ID space (B)
        num_searches: Number of random searches
        k: k-bucket size
        alpha: Lookup concurrency
        seed: Random seed

    Returns:
        List of SearchMetrics for all searches
    """
    import random

    if seed is not None:
        random.seed(seed)

    # Create network
    net = KademliaNetwork(network_size, id_bits, k, alpha, seed)

    # Distribute resources (assign each resource to closest node by XOR distance)
    for resource_id in range(network_size):
        responsible = net.find_responsible_node(resource_id)
        if responsible:
            responsible.resources.add(resource_id)

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
