"""Statistical analysis: comparative table, Tcs/Tp2p formulas, and scaling fits.

Usage:
    python analysis/statistical_analysis.py
    python analysis/statistical_analysis.py --input data/
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Theoretical distribution time formulas (from course Unit 9)
# ---------------------------------------------------------------------------

def calculate_tcs(N: int, F: float, Us: float, dmin: float) -> float:
    """Minimum distribution time for client-server model.

    Tcs = max(NF/Us, F/dmin)

    Args:
        N: Number of peers receiving the file
        F: File size in Mbits
        Us: Server upload rate in Mbps
        dmin: Minimum download rate among all peers in Mbps
    """
    return max(N * F / Us, F / dmin)


def calculate_tp2p(N: int, F: float, Us: float, dmin: float, sum_Ui: float) -> float:
    """Minimum distribution time for P2P model.

    Tp2p = max(F/Us, F/dmin, NF/(Us + sum_Ui))

    Args:
        N: Number of peers
        F: File size in Mbits
        Us: Server upload rate in Mbps
        dmin: Minimum download rate among all peers in Mbps
        sum_Ui: Sum of upload rates of all N peers in Mbps
    """
    return max(F / Us, F / dmin, N * F / (Us + sum_Ui))


# ---------------------------------------------------------------------------
# CSV loading (mirrors plot_results.py but returns raw per-search DataFrames)
# ---------------------------------------------------------------------------

def _load_all_flooding(data_dir: Path) -> pd.DataFrame:
    """Load all flooding CSVs into a single DataFrame with N and K columns."""
    import re
    frames = []
    for p in sorted((data_dir / "flooding").glob("results_N*_K*.csv")):
        m = re.match(r"results_N(\d+)_K(\d+)\.csv", p.name)
        if not m:
            continue
        df = pd.read_csv(p)
        df["N"] = int(m.group(1))
        df["K"] = int(m.group(2))
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _load_all_kademlia(data_dir: Path) -> pd.DataFrame:
    """Load all Kademlia CSVs into a single DataFrame with N and B columns."""
    import re
    frames = []
    for p in sorted((data_dir / "kademlia").glob("results_N*_B*.csv")):
        m = re.match(r"results_N(\d+)_B(\d+)\.csv", p.name)
        if not m:
            continue
        df = pd.read_csv(p)
        df["N"] = int(m.group(1))
        df["B"] = int(m.group(2))
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _load_all_churn(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load churn CSVs for both architectures.

    Returns (flood_churn_df, kad_churn_df), each with columns from the CSV plus
    N, K (flooding) or B (kademlia), and churn_pct parsed from the filename.
    """
    import re
    flood_rows: list[pd.DataFrame] = []
    kad_rows: list[pd.DataFrame] = []
    churn_dir = data_dir / "churn"
    if not churn_dir.exists():
        return pd.DataFrame(), pd.DataFrame()
    for p in sorted(churn_dir.glob("flooding_*.csv")):
        m = re.match(r"flooding_N(\d+)_K(\d+)_churn(\d+)\.csv", p.name)
        if not m:
            continue
        df = pd.read_csv(p)
        df["N"] = int(m.group(1))
        df["K"] = int(m.group(2))
        df["churn_pct"] = int(m.group(3))
        flood_rows.append(df)
    for p in sorted(churn_dir.glob("kademlia_*.csv")):
        m = re.match(r"kademlia_N(\d+)_B(\d+)_churn(\d+)\.csv", p.name)
        if not m:
            continue
        df = pd.read_csv(p)
        df["N"] = int(m.group(1))
        df["B"] = int(m.group(2))
        df["churn_pct"] = int(m.group(3))
        kad_rows.append(df)
    flood = pd.concat(flood_rows, ignore_index=True) if flood_rows else pd.DataFrame()
    kad = pd.concat(kad_rows, ignore_index=True) if kad_rows else pd.DataFrame()
    return flood, kad


# ---------------------------------------------------------------------------
# Table 1: Comparative table (full experimental series)
# ---------------------------------------------------------------------------

def build_comparative_table(flood_raw: pd.DataFrame, kad_raw: pd.DataFrame) -> pd.DataFrame:
    """Build comparison table for the full experimental series N = {10, 50, 100, 500, 1000, 5000, 15000}.

    Uses flooding K=10 and Kademlia B=16 as the primary configurations.
    """
    target_ns = [10, 50, 100, 500, 1000, 5000, 15000]
    rows = []

    for n in target_ns:
        f = flood_raw[(flood_raw["N"] == n) & (flood_raw["K"] == 10)]
        k = kad_raw[(kad_raw["N"] == n) & (kad_raw["B"] == 16)]

        f_succ = f[f["success"].astype(bool)] if not f.empty else pd.DataFrame()
        k_succ = k[k["success"].astype(bool)] if not k.empty else pd.DataFrame()

        rows.append({
            "N": n,
            # Flooding columns
            "F_msg_mean": f["messages"].mean() if not f.empty else float("nan"),
            "F_msg_std": f["messages"].std() if not f.empty else float("nan"),
            "F_hops_mean": f_succ["hops"].mean() if not f_succ.empty else float("nan"),
            "F_hops_std": f_succ["hops"].std() if not f_succ.empty else float("nan"),
            "F_success_%": f["success"].astype(bool).mean() * 100 if not f.empty else float("nan"),
            "F_overhead": f["messages"].mean() * n if not f.empty else float("nan"),
            # Kademlia columns
            "K_msg_mean": k["messages"].mean() if not k.empty else float("nan"),
            "K_msg_std": k["messages"].std() if not k.empty else float("nan"),
            "K_hops_mean": k_succ["hops"].mean() if not k_succ.empty else float("nan"),
            "K_hops_std": k_succ["hops"].std() if not k_succ.empty else float("nan"),
            "K_success_%": k["success"].astype(bool).mean() * 100 if not k.empty else float("nan"),
            "K_overhead": k["messages"].mean() * n if not k.empty else float("nan"),
            # Theoretical expectations
            "T_flood_O(N)": n,
            "T_kad_O(logN)": np.log2(n),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Table 2: Tcs / Tp2p numerical validation
# ---------------------------------------------------------------------------

def build_theory_table(
    N_values: list[int],
    F_mbits: float = 800.0,
    Us_mbps: float = 10.0,
    dmin_mbps: float = 1.0,
    Ui_per_peer_mbps: float = 1.0,
) -> pd.DataFrame:
    """Build Tcs/Tp2p table for the given N values.

    Default bandwidth assumptions (realistic for a 2024 home network scenario):
        F = 100 MB = 800 Mbits
        Us = 10 Mbps  (server upload)
        dmin = 1 Mbps (slowest peer download)
        Ui = 1 Mbps per peer (peer upload contribution)

    Args:
        N_values: List of network sizes to evaluate
        F_mbits: File size in Mbits
        Us_mbps: Server upload rate in Mbps
        dmin_mbps: Minimum peer download rate in Mbps
        Ui_per_peer_mbps: Upload rate contributed by each peer in Mbps
    """
    rows = []
    for n in N_values:
        sum_Ui = n * Ui_per_peer_mbps
        tcs = calculate_tcs(n, F_mbits, Us_mbps, dmin_mbps)
        tp2p = calculate_tp2p(n, F_mbits, Us_mbps, dmin_mbps, sum_Ui)
        rows.append({
            "N": n,
            "Tcs (s)": round(tcs, 1),
            "Tp2p (s)": round(tp2p, 1),
            "Tcs/Tp2p ratio": round(tcs / tp2p, 1) if tp2p > 0 else float("nan"),
            "Bottleneck Tcs": "server" if N_mbits_server(n, F_mbits, Us_mbps) > F_mbits / dmin_mbps else "download",
            "Tp2p bottleneck": _tp2p_bottleneck(n, F_mbits, Us_mbps, dmin_mbps, sum_Ui),
        })
    return pd.DataFrame(rows)


def N_mbits_server(N: int, F: float, Us: float) -> float:
    return N * F / Us


def _tp2p_bottleneck(N: int, F: float, Us: float, dmin: float, sum_Ui: float) -> str:
    vals = {
        "F/Us": F / Us,
        "F/dmin": F / dmin,
        "NF/(Us+ΣUi)": N * F / (Us + sum_Ui),
    }
    return max(vals, key=vals.get)


# ---------------------------------------------------------------------------
# Table 2B: Theory vs simulation — unified normalized comparison
# ---------------------------------------------------------------------------

def build_theory_vs_sim_table(
    flood_raw: pd.DataFrame,
    kad_raw: pd.DataFrame,
    N_values: list[int] | None = None,
    F_mbits: float = 800.0,
    Us_mbps: float = 10.0,
    dmin_mbps: float = 1.0,
    Ui_per_peer_mbps: float = 1.0,
) -> pd.DataFrame:
    """Cross-reference Tcs/Tp2p theory with simulation metrics in a single table.

    IMPORTANT — what is being compared and why:
    Tcs/Tp2p measure file *distribution time* under bandwidth constraints (seconds).
    The simulation measures search *message overhead* (messages to find a resource).
    These are different phenomena — the comparison is a complexity-class analogy:

    - Tcs (C/S model) grows O(N): only the server uploads, bottleneck = NF/Us.
      Flooding (P2P *unstructured*) also grows O(N): unstructured search may reach
      all N nodes. Flooding IS P2P — the shared O(N) class is the analogy, not
      conceptual equivalence between C/S and flooding.
    - Tp2p (P2P ideal) saturates: each peer adds upload capacity, so distribution
      time stays bounded. Kademlia (P2P *structured*) grows O(log N) — sub-linear
      like Tp2p, but not flat because the simulation has no replication (divergence
      expected and documented).

    Flood/Tcs ratio: ~1.0 confirms both belong to the O(N) complexity class.
    """
    if N_values is None:
        N_values = [10, 50, 100, 500, 1000, 5000, 15000]

    rows = []
    for n in N_values:
        sum_Ui = n * Ui_per_peer_mbps
        tcs = calculate_tcs(n, F_mbits, Us_mbps, dmin_mbps)
        tp2p = calculate_tp2p(n, F_mbits, Us_mbps, dmin_mbps, sum_Ui)

        f = flood_raw[(flood_raw["N"] == n) & (flood_raw["K"] == 10)]
        k_succ = kad_raw[
            (kad_raw["N"] == n) & (kad_raw["B"] == 16) & (kad_raw["success"].astype(bool))
        ]

        rows.append({
            "N": n,
            "Tcs (s)": round(tcs, 1),
            "Tp2p (s)": round(tp2p, 1),
            "Flood msgs": round(f["messages"].mean(), 1) if not f.empty else float("nan"),
            "Kad hops": round(k_succ["hops"].mean(), 2) if not k_succ.empty else float("nan"),
        })

    df = pd.DataFrame(rows)

    # Normalize every numeric column to the first row that has both sim columns
    valid = df.dropna(subset=["Flood msgs", "Kad hops"])
    if valid.empty:
        return df

    base = valid.iloc[0]
    for raw_col, norm_col in [
        ("Tcs (s)", "Tcs_norm"),
        ("Tp2p (s)", "Tp2p_norm"),
        ("Flood msgs", "Flood_norm"),
        ("Kad hops", "Kad_norm"),
    ]:
        b = base[raw_col]
        df[norm_col] = (df[raw_col] / b).round(3) if (not pd.isna(b) and b != 0) else float("nan")

    # How closely does flooding track Tcs O(N) growth?  Close to 1.0 = matches theory.
    df["Flood/Tcs ratio"] = (df["Flood_norm"] / df["Tcs_norm"]).round(3)

    return df


# ---------------------------------------------------------------------------
# Scaling fits
# ---------------------------------------------------------------------------

def fit_flooding_scaling(flood_raw: pd.DataFrame, k_val: int = 10) -> dict:
    """Fit messages = a * N^b in log-log space for flooding K=k_val.

    Returns dict with slope b, intercept a, and R² value.
    """
    sub = (
        flood_raw[flood_raw["K"] == k_val]
        .groupby("N")["messages"]
        .mean()
        .reset_index()
        .sort_values("N")
    )
    if len(sub) < 2:
        return {}

    log_n = np.log10(sub["N"])
    log_m = np.log10(sub["messages"])
    slope, intercept, r, *_ = stats.linregress(log_n, log_m)
    return {
        "architecture": f"Flooding K={k_val}",
        "slope (b)": round(slope, 4),
        "constant (10^intercept)": round(10**intercept, 4),
        "R²": round(r**2, 4),
        "complexity": f"O(N^{slope:.2f})",
    }


def fit_kademlia_scaling(kad_raw: pd.DataFrame, b_val: int = 16) -> dict:
    """Fit hops = a * log2(N) + b for Kademlia B=b_val (successful searches only).

    Returns dict with slope a, intercept b, and R² value.
    """
    sub = (
        kad_raw[(kad_raw["B"] == b_val) & (kad_raw["success"].astype(bool))]
        .groupby("N")["hops"]
        .mean()
        .reset_index()
        .sort_values("N")
    )
    if len(sub) < 2:
        return {}

    log2_n = np.log2(sub["N"])
    hops = sub["hops"]

    if hops.nunique() == 1:
        # Constant hops (e.g. sequential-ID simulation always resolves in 1 hop).
        # Regression is undefined; report the divergence explicitly.
        return {
            "architecture": f"Kademlia B={b_val}",
            "slope (a)": 0.0,
            "intercept (b)": round(hops.iloc[0], 4),
            "R2": float("nan"),
            "complexity": f"hops = {hops.iloc[0]:.1f} (constant — theory predicts ~log2(N); see informe)",
        }

    slope, intercept, r, *_ = stats.linregress(log2_n, hops)
    return {
        "architecture": f"Kademlia B={b_val}",
        "slope (a)": round(slope, 4),
        "intercept (b)": round(intercept, 4),
        "R2": round(r**2, 4),
        "complexity": f"hops ~ {slope:.2f}*log2(N) + {intercept:.2f}",
    }


# ---------------------------------------------------------------------------
# Churn threshold identification
# ---------------------------------------------------------------------------

def identify_churn_threshold(
    flood_churn: pd.DataFrame,
    kad_churn: pd.DataFrame,
    failure_threshold: float = 0.10,
    target_n: int = 1000,
) -> pd.DataFrame:
    """Find when each architecture's success rate falls below (1 - failure_threshold).

    For each (architecture, churn_pct) pair:
    - Uses N=target_n if present, otherwise all available N values.
    - Reports baseline success (round 0, before any churn), final success (last round),
      and the first round where mean success_rate < (1 - failure_threshold).

    Args:
        flood_churn: DataFrame from _load_all_churn (flooding side).
        kad_churn: DataFrame from _load_all_churn (kademlia side).
        failure_threshold: Fraction of failed searches that defines "significant degradation".
            Default 0.10 means >10% failures = degraded.
        target_n: Network size to use for the analysis.

    Returns:
        DataFrame with one row per (architecture, churn_pct).
    """
    min_success = 1.0 - failure_threshold
    label_col = f"First round below {int(min_success * 100)}% success"
    rows: list[dict] = []

    def _analyze(df: pd.DataFrame, arch: str) -> None:
        if df.empty:
            return
        subset = df[df["N"] == target_n] if target_n in df["N"].values else df
        for churn_pct in sorted(subset["churn_pct"].unique()):
            per_round = (
                subset[subset["churn_pct"] == churn_pct]
                .sort_values("round")
                .groupby("round")["success_rate"]
                .mean()
            )
            if per_round.empty:
                continue
            baseline = per_round.iloc[0]
            final = per_round.iloc[-1]
            failing = per_round[per_round < min_success]
            rows.append({
                "Architecture": arch,
                "Churn %": churn_pct,
                "Baseline success %": round(baseline * 100, 1),
                "Final success %": round(final * 100, 1),
                label_col: int(failing.index[0]) if not failing.empty else "—",
                "Degrades significantly": "yes" if not failing.empty else "no",
            })

    if not flood_churn.empty and "K" in flood_churn.columns:
        _analyze(flood_churn[flood_churn["K"] == 10], "Flooding K=10")
    if not kad_churn.empty and "B" in kad_churn.columns:
        _analyze(kad_churn[kad_churn["B"] == 16], "Kademlia B=16")

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _banner(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def _fmt(df: pd.DataFrame) -> str:
    return df.to_string(index=False, float_format=lambda x: f"{x:.2f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical analysis of simulation results")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "data"),
                        help="Directory with flooding/ and kademlia/ subdirs")
    args = parser.parse_args()

    data_dir = Path(args.input)
    flood_raw = _load_all_flooding(data_dir)
    kad_raw = _load_all_kademlia(data_dir)

    if flood_raw.empty and kad_raw.empty:
        logger.error("No experiment data found in %s", data_dir)
        return

    # --- Table 1: Comparative table ---
    _banner("TABLE 1: Flooding (K=10) vs Kademlia (B=16) — N = {10, 50, 100, 500, 1000, 5000, 15000}")
    comp = build_comparative_table(flood_raw, kad_raw)
    print(_fmt(comp))
    csv_path = data_dir / "analysis_comparative.csv"
    comp.to_csv(csv_path, index=False, float_format="%.3f")
    logger.info("Saved %s", csv_path)

    # --- Table 2: Tcs / Tp2p ---
    _banner("TABLE 2: Theoretical distribution time — Tcs vs Tp2p")
    print("Parameters: F=100MB=800Mbits, Us=10Mbps, dmin=1Mbps, Ui=1Mbps/peer")
    theory = build_theory_table([10, 50, 100, 500, 1000, 5000, 15000])
    print(_fmt(theory))
    theory_path = data_dir / "analysis_theory.csv"
    theory.to_csv(theory_path, index=False)
    logger.info("Saved %s", theory_path)

    # --- Table 2B: Theory vs simulation combined ---
    _banner("TABLE 2B: Theory vs simulation — normalized scaling comparison")
    print("Parameters: F=100MB=800Mbits, Us=10Mbps, dmin=1Mbps, Ui=1Mbps/peer")
    print("Tcs = C/S distribution time; Tp2p = P2P ideal distribution time.")
    print("Flood msgs = P2P unstructured search overhead; Kad hops = P2P structured search overhead.")
    print("*_norm: normalized to N=10. Flood/Tcs ratio ~1.0 => both O(N) complexity class.")
    if not flood_raw.empty or not kad_raw.empty:
        theory_vs_sim = build_theory_vs_sim_table(flood_raw, kad_raw)
        print(_fmt(theory_vs_sim))
        tv_path = data_dir / "analysis_theory_vs_sim.csv"
        theory_vs_sim.to_csv(tv_path, index=False)
        logger.info("Saved %s", tv_path)

    # --- Scaling fits ---
    _banner("SCALING ANALYSIS")
    f_fit = fit_flooding_scaling(flood_raw, k_val=10)
    k_fit = fit_kademlia_scaling(kad_raw, b_val=16)

    if f_fit:
        print(f"\nFlooding (K=10):")
        for key, val in f_fit.items():
            print(f"  {key}: {val}")

    if k_fit:
        print(f"\nKademlia (B=16):")
        for key, val in k_fit.items():
            print(f"  {key}: {val}")

    # --- Per-N success rates ---
    _banner("SUCCESS RATES BY N (K=10 flooding, B=16 Kademlia)")
    if not flood_raw.empty:
        f_sr = (
            flood_raw[flood_raw["K"] == 10]
            .groupby("N")["success"]
            .apply(lambda x: x.astype(bool).mean() * 100)
            .reset_index()
            .rename(columns={"success": "Flooding success %"})
        )
        print(f_sr.to_string(index=False))

    if not kad_raw.empty:
        k_sr = (
            kad_raw[kad_raw["B"] == 16]
            .groupby("N")["success"]
            .apply(lambda x: x.astype(bool).mean() * 100)
            .reset_index()
            .rename(columns={"success": "Kademlia B=16 success %"})
        )
        print(k_sr.to_string(index=False))

    # --- Table 3: Churn threshold identification ---
    _banner("TABLE 3: Churn degradation threshold (>10% search failures) — N=1000")
    flood_churn, kad_churn = _load_all_churn(data_dir)
    if flood_churn.empty and kad_churn.empty:
        logger.warning("No churn data found in %s/churn/ — skipping threshold analysis", data_dir)
    else:
        thresh = identify_churn_threshold(flood_churn, kad_churn)
        if not thresh.empty:
            print(_fmt(thresh))
            thresh_path = data_dir / "analysis_churn_threshold.csv"
            thresh.to_csv(thresh_path, index=False)
            logger.info("Saved %s", thresh_path)
        else:
            logger.warning("Could not compute churn threshold (check churn CSV naming convention)")


if __name__ == "__main__":
    main()
