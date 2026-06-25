"""Kademlia DHT implementation (structured P2P).

This module implements a simplified Kademlia distributed hash table with:
- XOR distance metric
- Finger table routing (simplified k-buckets)
- Iterative lookup protocol
"""

from typing import List, Optional, Dict
from heapq import nsmallest
import logging

from .node import Node
from .network import Network
from .metrics import SearchMetrics

logger = logging.getLogger(__name__)


def xor_distance(a: int, b: int) -> int:
    """XOR distance between two node IDs (Kademlia metric).

    Args:
        a: First node ID
        b: Second node ID

    Returns:
        Bitwise XOR of a and b
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

        Fills the exact-match slot for this node's XOR distance, always
        overwriting any previous entry (used during churn bootstrap).

        Args:
            node: Node to add to routing table
        """
        if node.node_id == self.node_id:
            return

        distance = self.distance_to(node.node_id)
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


def _fill_kbuckets(node: KademliaNode, peers: list, k: int, id_bits: int) -> None:
    """Populate node's finger_table using k-bucket rules.

    Groups each peer into bucket i = floor(log2(XOR distance)) and keeps the k
    closest peers per bucket. Total entries: at most id_bits * k.

    Args:
        node: Node whose routing table will be populated.
        peers: Candidate peers (must not include node itself).
        k: Maximum peers per bucket.
        id_bits: Number of ID bits (B), defines number of buckets.
    """
    buckets: list[list] = [[] for _ in range(id_bits)]
    for peer in peers:
        d = xor_distance(node.node_id, peer.node_id)
        if d == 0:
            continue  # skip self
        b = min(d.bit_length() - 1, id_bits - 1)
        buckets[b].append(peer)

    for candidates in buckets:
        if not candidates:
            continue
        selected = (
            candidates if len(candidates) <= k
            else nsmallest(k, candidates,
                           key=lambda n, nid=node.node_id: xor_distance(nid, n.node_id))
        )
        for peer in selected:
            node.finger_table[xor_distance(node.node_id, peer.node_id)] = peer


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
        """Populate each node's k-bucket routing table.

        Bucket i covers XOR distances in [2^i, 2^(i+1)). Each node keeps at most
        k peers per bucket, capping total table size at B*k entries.
        """
        for node in self.nodes:
            others = [n for n in self.nodes if n.node_id != node.node_id]
            if not others:
                continue
            _fill_kbuckets(node, others, self.k, self.id_bits)

        logger.debug("Built k-bucket routing tables for all nodes")

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

        # Maintain alpha*k=9 candidates instead of k=3: larger shortlist compensates
        # for partial routing table knowledge without changing convergence semantics.
        shortlist_size = self.k * self.alpha

        closest = initiator.get_closest_nodes(resource_id, shortlist_size)
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
                new_closest = next_node.get_closest_nodes(resource_id, shortlist_size)
                all_candidates = set(closest) | set(new_closest)
                closest = sorted(
                    all_candidates,
                    key=lambda n: xor_distance(n.node_id, resource_id)
                )[:shortlist_size]

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
        initiator_node = random.choice(net.nodes)
        resource = random.randint(0, network_size - 1)

        metrics = net.search(initiator_node.node_id, resource)
        results.append(metrics)

        if (i + 1) % 10 == 0:
            logger.info(f"Completed {i + 1}/{num_searches} searches")

    return results


def _apply_kademlia_churn(net: KademliaNetwork, num_churn: int, next_node_id: int) -> int:
    """Remove and replace num_churn nodes in Kademlia network.

    Departed nodes are removed from all finger tables. Arriving nodes
    bootstrap their routing tables from a random sample of existing nodes.
    Resources of departed nodes are lost permanently.

    Args:
        net: The Kademlia network to mutate
        num_churn: Number of nodes to remove/add
        next_node_id: Starting value to derive new node IDs (mod 2^B)

    Returns:
        Number of resources lost due to departing nodes
    """
    import random

    departing = random.sample(net.nodes, min(num_churn, len(net.nodes)))
    resources_lost = 0
    departing_ids = {n.node_id for n in departing}

    for node in departing:
        resources_lost += len(node.resources)
        net.nodes.remove(node)

    # Purge departed nodes from all remaining finger tables
    for node in net.nodes:
        if isinstance(node, KademliaNode):
            node.finger_table = {
                d: v for d, v in node.finger_table.items()
                if v.node_id not in departing_ids
            }

    net.size = len(net.nodes)

    max_id = 2 ** net.id_bits
    for i in range(num_churn):
        if not net.nodes:
            break
        new_id = (next_node_id + i) % max_id
        new_node = KademliaNode(new_id, net.id_bits)

        # Bootstrap: build k-bucket routing table from all surviving nodes (O(N)).
        _fill_kbuckets(new_node, net.nodes, net.k, net.id_bits)

        # Reciprocal update: add new_node to each peer's bucket if there is room.
        for peer in new_node.finger_table.values():
            if not isinstance(peer, KademliaNode):
                continue
            d_back = xor_distance(peer.node_id, new_node.node_id)
            if d_back == 0:
                continue
            b_back = min(d_back.bit_length() - 1, net.id_bits - 1)
            lo, hi = 2 ** b_back, 2 ** (b_back + 1)
            bucket_count = sum(1 for d in peer.finger_table if lo <= d < hi)
            if bucket_count < net.k:
                peer.finger_table[d_back] = new_node

        net.nodes.append(new_node)

    net.size = len(net.nodes)
    return resources_lost


def run_kademlia_churn_experiment(
    network_size: int,
    id_bits: int,
    churn_rate: float,
    num_rounds: int = 20,
    searches_per_round: int = 50,
    k: int = 3,
    alpha: int = 3,
    seed: Optional[int] = None
) -> List[dict]:
    """Run Kademlia experiment with churn over multiple rounds.

    Each round: perform searches on the current network, then apply churn.
    Resources of departed nodes are lost permanently (no replication),
    which intentionally measures the worst-case degradation.

    Args:
        network_size: Initial number of nodes (N)
        id_bits: Bits in ID space (B)
        churn_rate: Fraction of nodes that leave/join each round
        num_rounds: Number of churn rounds
        searches_per_round: Searches performed each round before churn
        k: k-bucket size
        alpha: Lookup concurrency
        seed: Random seed

    Returns:
        List of per-round summary dicts
    """
    import random

    if seed is not None:
        random.seed(seed)

    net = KademliaNetwork(network_size, id_bits, k, alpha, seed)

    for resource_id in range(network_size):
        responsible = net.find_responsible_node(resource_id)
        if responsible:
            responsible.resources.add(resource_id)

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
        resources_lost = _apply_kademlia_churn(net, num_churn, next_node_id)
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
