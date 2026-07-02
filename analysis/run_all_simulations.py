"""Batch script: reproduce all flooding and Kademlia simulations (Tasks 1 & 2).

Generates every CSV under data/flooding/ and data/kademlia/ used in the report.
Run from the repo root:

    python analysis/run_all_simulations.py

Total runtime: ~10-15 minutes on a standard desktop.
"""

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PYTHON = sys.executable

FLOODING_CONFIGS = [
    # (N, K)
    (10,    5), (10,    10),
    (50,    5), (50,    10), (50,    20),
    (100,   5), (100,   10), (100,   20),
    (500,   5), (500,   10), (500,   20),
    (1000,  5), (1000,  10), (1000,  20),
    (5000,  5), (5000,  10), (5000,  20),
    (15000, 5), (15000, 10), (15000, 20),
]

KADEMLIA_CONFIGS = [
    # (N, B)
    (10,    8), (10,    16),
    (50,    8), (50,    16),
    (100,   8), (100,   16),
    (500,   8), (500,   16),
    (1000,  8), (1000,  16),
    (5000,  8), (5000,  16),
    (15000, 8), (15000, 16),
]


def run(cmd: list[str], label: str) -> None:
    print(f"  [{label}]", end=" ", flush=True)
    t0 = time.time()
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True)
    elapsed = time.time() - t0
    status = "OK" if result.returncode == 0 else f"ERROR (exit {result.returncode})"
    print(f"{status} — {elapsed:.1f}s")
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace")[-500:])


def main() -> None:
    total = len(FLOODING_CONFIGS) + len(KADEMLIA_CONFIGS)
    print(f"Running {total} simulation configurations (--runs 100 each)")
    t_start = time.time()

    print("\n--- Flooding ---")
    for n, k in FLOODING_CONFIGS:
        run([
            PYTHON, "-m", "src.simulation",
            "--mode", "flooding",
            "--nodes", str(n),
            "--neighbors", str(k),
            "--runs", "100",
            "--seed", "42",
            "--output-dir", "data",
        ], f"N={n} K={k}")

    print("\n--- Kademlia ---")
    for n, b in KADEMLIA_CONFIGS:
        run([
            PYTHON, "-m", "src.simulation",
            "--mode", "kademlia",
            "--nodes", str(n),
            "--bits", str(b),
            "--runs", "100",
            "--seed", "42",
            "--output-dir", "data",
        ], f"N={n} B={b}")

    elapsed = time.time() - t_start
    print(f"\nAll done in {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print("Next step: python analysis/run_churn_reps.py --reps 30")


if __name__ == "__main__":
    main()
