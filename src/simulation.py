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


def _run_single_churn(args, seed: int) -> list[dict]:
    """Run one churn experiment with the given seed; returns per-round dicts."""
    if args.architecture == 'flooding':
        return run_flooding_churn_experiment(
            network_size=args.nodes,
            neighbors_k=args.neighbors,
            churn_rate=args.churn_rate,
            num_rounds=args.rounds,
            searches_per_round=args.runs,
            ttl=args.ttl,
            seed=seed,
        )
    return run_kademlia_churn_experiment(
        network_size=args.nodes,
        id_bits=args.bits,
        churn_rate=args.churn_rate,
        num_rounds=args.rounds,
        searches_per_round=args.runs,
        k=args.k_bucket,
        alpha=args.alpha,
        seed=seed,
    )


def run_churn_simulation(args) -> None:
    """Run churn simulation for flooding or Kademlia.

    When --churn-reps > 1, runs the experiment that many times with
    different seeds and writes an aggregated CSV with mean ± std per round.

    Args:
        args: Command-line arguments
    """
    import csv
    import numpy as np

    if not args.architecture:
        logger.error("--architecture is required for churn mode (flooding or kademlia)")
        sys.exit(1)

    churn_pct = int(args.churn_rate * 100)
    reps = args.churn_reps
    output_dir = Path(args.output_dir) / "churn"
    output_dir.mkdir(parents=True, exist_ok=True)

    base_seed = args.seed if args.seed is not None else 42

    if args.architecture == 'flooding':
        logger.info(
            f"Starting CHURN simulation: flooding, N={args.nodes}, K={args.neighbors}, "
            f"churn={args.churn_rate}, rounds={args.rounds}, searches/round={args.runs}, reps={reps}"
        )
        single_file = output_dir / f"flooding_N{args.nodes}_K{args.neighbors}_churn{churn_pct}.csv"
        reps_file   = output_dir / f"flooding_N{args.nodes}_K{args.neighbors}_churn{churn_pct}_reps{reps}.csv"
    else:
        logger.info(
            f"Starting CHURN simulation: kademlia, N={args.nodes}, B={args.bits}, "
            f"churn={args.churn_rate}, rounds={args.rounds}, searches/round={args.runs}, reps={reps}"
        )
        single_file = output_dir / f"kademlia_N{args.nodes}_B{args.bits}_churn{churn_pct}.csv"
        reps_file   = output_dir / f"kademlia_N{args.nodes}_B{args.bits}_churn{churn_pct}_reps{reps}.csv"

    if reps == 1:
        results = _run_single_churn(args, base_seed)
        fieldnames = [
            'round', 'nodes_in_network', 'nodes_churned', 'resources_lost',
            'total_searches', 'successful_searches', 'success_rate',
            'avg_messages', 'avg_hops',
        ]
        with open(single_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        final = results[-1] if results else {}
        print(f"\n=== Churn Simulation Results ({args.architecture}) ===")
        print(f"Network size (N): {args.nodes}, Churn: {args.churn_rate*100:.0f}%, Rounds: {args.rounds}")
        print(f"Final round success rate: {final.get('success_rate', 0)*100:.1f}%")
        logger.info(f"Results exported to {single_file}")
        return

    # --- Multi-rep path ---
    all_runs: list[list[dict]] = []
    for i in range(reps):
        logger.info(f"  Rep {i+1}/{reps} (seed={base_seed + i})")
        all_runs.append(_run_single_churn(args, base_seed + i))

    num_rounds = len(all_runs[0])
    agg_rows = []
    for r in range(num_rounds):
        sr   = [run[r]['success_rate']  for run in all_runs]
        msgs = [run[r]['avg_messages']  for run in all_runs]
        hops = [run[r]['avg_hops']      for run in all_runs]
        agg_rows.append({
            'round':               r,
            'success_rate_mean':   round(float(np.mean(sr)),   4),
            'success_rate_std':    round(float(np.std(sr, ddof=1)), 4),
            'avg_messages_mean':   round(float(np.mean(msgs)), 3),
            'avg_messages_std':    round(float(np.std(msgs, ddof=1)), 3),
            'avg_hops_mean':       round(float(np.mean(hops)), 3),
            'avg_hops_std':        round(float(np.std(hops, ddof=1)), 3),
            'n_reps':              reps,
        })

    fieldnames = [
        'round',
        'success_rate_mean', 'success_rate_std',
        'avg_messages_mean', 'avg_messages_std',
        'avg_hops_mean',     'avg_hops_std',
        'n_reps',
    ]
    with open(reps_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(agg_rows)

    print(f"\n=== Churn Simulation Results ({args.architecture}, {reps} reps) ===")
    print(f"Network size (N): {args.nodes}, Churn: {args.churn_rate*100:.0f}%, Rounds: {args.rounds}")
    final = agg_rows[-1]
    print(f"Final round success rate: {final['success_rate_mean']*100:.1f}% ± {final['success_rate_std']*100:.1f}%")
    logger.info(f"Results exported to {reps_file}")


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
    parser.add_argument(
        '--churn-reps',
        type=int,
        default=1,
        help='[Churn] Number of independent repetitions; when >1 writes mean±std per round'
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
