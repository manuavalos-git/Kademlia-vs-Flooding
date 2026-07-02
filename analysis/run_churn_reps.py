"""Batch script: regenerate all churn CSVs with 30 independent repetitions.

Usage (from repo root):
    python analysis/run_churn_reps.py
    python analysis/run_churn_reps.py --reps 10   # quick test

Writes _reps{N}.csv files alongside the existing single-run CSVs.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

FLOODING_CONFIGS = [
    {"nodes": 1000,  "neighbors": 10, "churn": rate} for rate in [0.05, 0.10, 0.20]
] + [
    {"nodes": 5000,  "neighbors": 10, "churn": rate} for rate in [0.05, 0.10, 0.20]
] + [
    {"nodes": 15000, "neighbors": 10, "churn": rate} for rate in [0.05, 0.10, 0.20]
]

KADEMLIA_CONFIGS = [
    {"nodes": 1000,  "bits": 16, "churn": rate} for rate in [0.05, 0.10, 0.20]
] + [
    {"nodes": 5000,  "bits": 16, "churn": rate} for rate in [0.05, 0.10, 0.20]
] + [
    {"nodes": 15000, "bits": 16, "churn": rate} for rate in [0.05, 0.10, 0.20]
]

PYTHON = sys.executable


def run(cmd: list[str], label: str) -> float:
    print(f"\n[{label}] Running...")
    t0 = time.time()
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"  ERROR (exit code {result.returncode})")
    else:
        print(f"  Done in {elapsed:.1f}s")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=30)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--searches", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    total_configs = len(FLOODING_CONFIGS) + len(KADEMLIA_CONFIGS)
    print(f"Running {total_configs} configurations × {args.reps} reps each")
    total_elapsed = 0.0

    for cfg in FLOODING_CONFIGS:
        churn_pct = int(cfg["churn"] * 100)
        label = f"flooding N={cfg['nodes']} K={cfg['neighbors']} churn={churn_pct}%"
        cmd = [
            PYTHON, "-m", "src.simulation",
            "--mode", "churn",
            "--architecture", "flooding",
            "--nodes", str(cfg["nodes"]),
            "--neighbors", str(cfg["neighbors"]),
            "--churn-rate", str(cfg["churn"]),
            "--rounds", str(args.rounds),
            "--runs", str(args.searches),
            "--churn-reps", str(args.reps),
            "--seed", str(args.seed),
            "--output-dir", args.output_dir,
        ]
        total_elapsed += run(cmd, label)

    for cfg in KADEMLIA_CONFIGS:
        churn_pct = int(cfg["churn"] * 100)
        label = f"kademlia N={cfg['nodes']} B={cfg['bits']} churn={churn_pct}%"
        cmd = [
            PYTHON, "-m", "src.simulation",
            "--mode", "churn",
            "--architecture", "kademlia",
            "--nodes", str(cfg["nodes"]),
            "--bits", str(cfg["bits"]),
            "--churn-rate", str(cfg["churn"]),
            "--rounds", str(args.rounds),
            "--runs", str(args.searches),
            "--churn-reps", str(args.reps),
            "--seed", str(args.seed),
            "--output-dir", args.output_dir,
        ]
        total_elapsed += run(cmd, label)

    print(f"\n=== All done in {total_elapsed:.1f}s ({total_elapsed/60:.1f}min) ===")
    print(f"Output files: data/churn/*_reps{args.reps}.csv")


if __name__ == "__main__":
    main()
