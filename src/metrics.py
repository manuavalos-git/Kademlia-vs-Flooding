"""Metrics collection and instrumentation for P2P simulations.

This module provides utilities to measure and record simulation metrics:
- Messages exchanged during search
- Hops until resource found
- Success rate of queries
- Node load distribution
"""

from dataclasses import dataclass, field
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchMetrics:
    """Metrics collected during a single resource search.

    Attributes:
        messages: Total messages exchanged
        hops: Number of hops until resource found (0 if not found)
        success: Whether the resource was found
        nodes_reached: Number of nodes that received the query
        initiator_id: ID of the node that initiated the search
        resource_id: ID of the resource being searched
    """
    messages: int = 0
    hops: int = 0
    success: bool = False
    nodes_reached: int = 0
    initiator_id: int = -1
    resource_id: int = -1

    def to_dict(self) -> dict:
        """Convert metrics to dictionary format for CSV export."""
        return {
            'initiator_id': self.initiator_id,
            'resource_id': self.resource_id,
            'messages': self.messages,
            'hops': self.hops,
            'success': self.success,
            'nodes_reached': self.nodes_reached,
        }


@dataclass
class SimulationMetrics:
    """Aggregated metrics for a full simulation run.

    Attributes:
        search_results: List of individual search metrics
        network_size: Number of nodes in the network
        architecture: 'flooding' or 'kademlia'
        config_params: Configuration parameters used (K, B, etc.)
    """
    search_results: List[SearchMetrics] = field(default_factory=list)
    network_size: int = 0
    architecture: str = ""
    config_params: dict = field(default_factory=dict)

    def add_search(self, metrics: SearchMetrics) -> None:
        """Add results from a single search to the aggregated metrics."""
        self.search_results.append(metrics)

    def avg_messages(self) -> float:
        """Calculate average messages per search."""
        if not self.search_results:
            return 0.0
        return sum(m.messages for m in self.search_results) / len(self.search_results)

    def avg_hops(self) -> float:
        """Calculate average hops per search (only successful searches)."""
        successful = [m for m in self.search_results if m.success]
        if not successful:
            return 0.0
        return sum(m.hops for m in successful) / len(successful)

    def success_rate(self) -> float:
        """Calculate success rate (percentage of successful searches)."""
        if not self.search_results:
            return 0.0
        successful_count = sum(1 for m in self.search_results if m.success)
        return successful_count / len(self.search_results)

    def summary(self) -> dict:
        """Generate summary statistics for this simulation run."""
        return {
            'network_size': self.network_size,
            'architecture': self.architecture,
            'total_searches': len(self.search_results),
            'avg_messages': self.avg_messages(),
            'avg_hops': self.avg_hops(),
            'success_rate': self.success_rate(),
            **self.config_params
        }


class MetricsCollector:
    """Utility class to collect and export metrics during simulation."""

    def __init__(self, architecture: str, network_size: int, config: dict):
        """Initialize metrics collector.

        Args:
            architecture: 'flooding' or 'kademlia'
            network_size: Number of nodes in network
            config: Configuration parameters
        """
        self.metrics = SimulationMetrics(
            network_size=network_size,
            architecture=architecture,
            config_params=config
        )
        logger.info(f"MetricsCollector initialized for {architecture} with N={network_size}")

    def record_search(self, metrics: SearchMetrics) -> None:
        """Record metrics from a single search."""
        self.metrics.add_search(metrics)
        logger.debug(f"Recorded search: {metrics.to_dict()}")

    def get_summary(self) -> dict:
        """Get summary statistics."""
        return self.metrics.summary()

    def export_to_csv(self, filepath: str) -> None:
        """Export individual search results to CSV.

        Args:
            filepath: Path to output CSV file
        """
        import csv

        if not self.metrics.search_results:
            logger.warning("No search results to export")
            return

        with open(filepath, 'w', newline='') as f:
            fieldnames = ['initiator_id', 'resource_id', 'messages', 'hops', 'success', 'nodes_reached']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for search in self.metrics.search_results:
                writer.writerow(search.to_dict())

        logger.info(f"Exported {len(self.metrics.search_results)} search results to {filepath}")
