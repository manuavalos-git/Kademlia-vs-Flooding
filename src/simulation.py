"""Main simulation orchestrator for P2P experiments.

This script runs flooding and Kademlia simulations with configurable parameters
and exports results to CSV files.
"""

import argparse
import logging
import sys
from pathlib import Path

from .flooding import run_flooding_experiment, run_flooding_churn_experiment
from .kademlia import run_kademlia_experiment, run_kademlia_churn_experiment
from .metrics import MetricsCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_flooding_simulation(args) -> None:
    """Run flooding simulation with given parameters.

    Args:
        args: Command-line arguments
    """
    logger.info(f"Starting FLOODING simulation: N={args.nodes}, K={args.neighbors}, runs={args.runs}")

    collector = MetricsCollector(
        architecture="flooding",
        network_size=args.nodes,
        config={'K': args.neighbors, 'TTL': args.ttl}
    )

    # Run experiment
    results = run_flooding_experiment(
        network_size=args.nodes,
        neighbors_k=args.neighbors,
        num_searches=args.runs,
        ttl=args.ttl,
        seed=args.seed
    )

    # Collect metrics
    for metrics in results:
        collector.record_search(metrics)

    # Print summary
    summary = collector.get_summary()
    logger.info(f"Simulation complete: {summary}")
    print(f"\n=== Flooding Simulation Results ===")
    print(f"Network size (N): {summary['network_size']}")
    print(f"Neighbors per node (K): {summary['K']}")
    print(f"Total searches: {summary['total_searches']}")
    print(f"Avg messages per search: {summary['avg_messages']:.2f}")
    print(f"Avg hops per search: {summary['avg_hops']:.2f}")
    print(f"Success rate: {summary['success_rate']*100:.1f}%")

    # Export to CSV
    output_dir = Path(args.output_dir) / "flooding"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"results_N{args.nodes}_K{args.neighbors}.csv"

    collector.export_to_csv(str(output_file))
    logger.info(f"Results exported to {output_file}")


def run_kademlia_simulation(args) -> None:
    """Run Kademlia simulation with given parameters.

    Args:
        args: Command-line arguments
    """
    logger.info(f"Starting KADEMLIA simulation: N={args.nodes}, B={args.bits}, runs={args.runs}")

    collector = MetricsCollector(
        architecture="kademlia",
        network_size=args.nodes,
        config={'B': args.bits, 'k': args.k_bucket, 'alpha': args.alpha}
    )

    # Run experiment
    results = run_kademlia_experiment(
        network_size=args.nodes,
        id_bits=args.bits,
        num_searches=args.runs,
        k=args.k_bucket,
        alpha=args.alpha,
        seed=args.seed
    )

    # Collect metrics
    for metrics in results:
        collector.record_search(metrics)

    # Print summary
    summary = collector.get_summary()
    logger.info(f"Simulation complete: {summary}")
    print(f"\n=== Kademlia Simulation Results ===")
    print(f"Network size (N): {summary['network_size']}")
    print(f"ID bits (B): {summary['B']}")
    print(f"Total searches: {summary['total_searches']}")
    print(f"Avg messages per search: {summary['avg_messages']:.2f}")
    print(f"Avg hops per search: {summary['avg_hops']:.2f}")
    print(f"Success rate: {summary['success_rate']*100:.1f}%")

    # Export to CSV
    output_dir = Path(args.output_dir) / "kademlia"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"results_N{args.nodes}_B{args.bits}.csv"

    collector.export_to_csv(str(output_file))
    logger.info(f"Results exported to {output_file}")


def run_churn_simulation(args) -> None:
    """Run churn simulation for flooding or Kademlia.

    Args:
        args: Command-line arguments
    """
    if not args.architecture:
        logger.error("--architecture is required for churn mode (flooding or kademlia)")
        sys.exit(1)

    churn_pct = int(args.churn_rate * 100)
    output_dir = Path(args.output_dir) / "churn"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.architecture == 'flooding':
        logger.info(
            f"Starting CHURN simulation: flooding, N={args.nodes}, K={args.neighbors}, "
            f"churn={args.churn_rate}, rounds={args.rounds}, searches/round={args.runs}"
        )
        results = run_flooding_churn_experiment(
            network_size=args.nodes,
            neighbors_k=args.neighbors,
            churn_rate=args.churn_rate,
            num_rounds=args.rounds,
            searches_per_round=args.runs,
            ttl=args.ttl,
            seed=args.seed
        )
        output_file = output_dir / f"flooding_N{args.nodes}_K{args.neighbors}_churn{churn_pct}.csv"

    else:  # kademlia
        logger.info(
            f"Starting CHURN simulation: kademlia, N={args.nodes}, B={args.bits}, "
            f"churn={args.churn_rate}, rounds={args.rounds}, searches/round={args.runs}"
        )
        results = run_kademlia_churn_experiment(
            network_size=args.nodes,
            id_bits=args.bits,
            churn_rate=args.churn_rate,
            num_rounds=args.rounds,
            searches_per_round=args.runs,
            k=args.k_bucket,
            alpha=args.alpha,
            seed=args.seed
        )
        output_file = output_dir / f"kademlia_N{args.nodes}_B{args.bits}_churn{churn_pct}.csv"

    # Export CSV
    import csv
    fieldnames = [
        'round', 'nodes_in_network', 'nodes_churned', 'resources_lost',
        'total_searches', 'successful_searches', 'success_rate',
        'avg_messages', 'avg_hops'
    ]
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Print summary
    final = results[-1] if results else {}
    print(f"\n=== Churn Simulation Results ({args.architecture}) ===")
    print(f"Network size (N): {args.nodes}")
    print(f"Churn rate: {args.churn_rate*100:.0f}% per round")
    print(f"Rounds: {args.rounds}")
    print(f"Final round success rate: {final.get('success_rate', 0)*100:.1f}%")
    print(f"Total resources lost: {sum(r['resources_lost'] for r in results)}")
    logger.info(f"Results exported to {output_file}")


def main():
    """Main entry point for simulation script."""
    parser = argparse.ArgumentParser(
        description="P2P Network Simulation: Kademlia vs Flooding"
    )

    # Common arguments
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['flooding', 'kademlia', 'churn'],
        help='Simulation mode'
    )
    parser.add_argument(
        '--nodes',
        type=int,
        default=100,
        help='Number of nodes in network (N)'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=100,
        help='Number of search queries to perform'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data',
        help='Output directory for results'
    )

    # Flooding-specific arguments
    parser.add_argument(
        '--neighbors',
        type=int,
        default=10,
        help='[Flooding] Number of neighbors per node (K)'
    )
    parser.add_argument(
        '--ttl',
        type=int,
        default=20,
        help='[Flooding] Time-to-live for query propagation'
    )

    # Kademlia-specific arguments
    parser.add_argument(
        '--bits',
        type=int,
        default=8,
        help='[Kademlia] Number of bits in node ID (B)'
    )
    parser.add_argument(
        '--k-bucket',
        type=int,
        default=3,
        help='[Kademlia] k-bucket size'
    )
    parser.add_argument(
        '--alpha',
        type=int,
        default=3,
        help='[Kademlia] Concurrency parameter for iterative lookup'
    )

    # Churn-specific arguments
    parser.add_argument(
        '--architecture',
        type=str,
        choices=['flooding', 'kademlia'],
        help='[Churn] Architecture to test under churn'
    )
    parser.add_argument(
        '--churn-rate',
        type=float,
        default=0.05,
        help='[Churn] Fraction of nodes that leave/join per round (e.g. 0.05 = 5%%)'
    )
    parser.add_argument(
        '--rounds',
        type=int,
        default=20,
        help='[Churn] Number of churn rounds'
    )

    args = parser.parse_args()

    # Route to appropriate simulation
    if args.mode == 'flooding':
        run_flooding_simulation(args)
    elif args.mode == 'kademlia':
        run_kademlia_simulation(args)
    elif args.mode == 'churn':
        run_churn_simulation(args)


if __name__ == '__main__':
    main()
