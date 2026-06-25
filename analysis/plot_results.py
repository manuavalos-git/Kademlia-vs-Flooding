"""Generate all required comparison plots for the Flooding vs Kademlia simulation.

Usage:
    python analysis/plot_results.py                        # uses data/ and informe/figures/
    python analysis/plot_results.py --input data/ --output informe/figures/
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
FLOOD_COLOR = "#1565C0"
KAD_COLOR = "#C62828"
PALETTE_K = ["#64B5F6", "#1565C0", "#0D47A1"]   # K=5,10,20 shades
PALETTE_B = ["#EF9A9A", "#C62828"]               # B=8, B=16 shades


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _parse_flooding_filename(path: Path) -> dict | None:
    m = re.match(r"results_N(\d+)_K(\d+)\.csv", path.name)
    if m:
        return {"N": int(m.group(1)), "K": int(m.group(2))}
    return None


def _parse_kademlia_filename(path: Path) -> dict | None:
    m = re.match(r"results_N(\d+)_B(\d+)\.csv", path.name)
    if m:
        return {"N": int(m.group(1)), "B": int(m.group(2))}
    return None


def _parse_churn_flooding_filename(path: Path) -> dict | None:
    m = re.match(r"flooding_N(\d+)_K(\d+)_churn(\d+)\.csv", path.name)
    if m:
        return {"N": int(m.group(1)), "K": int(m.group(2)), "churn_pct": int(m.group(3))}
    return None


def _parse_churn_kademlia_filename(path: Path) -> dict | None:
    m = re.match(r"kademlia_N(\d+)_B(\d+)_churn(\d+)\.csv", path.name)
    if m:
        return {"N": int(m.group(1)), "B": int(m.group(2)), "churn_pct": int(m.group(3))}
    return None


def load_experiment_summaries(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load flooding and Kademlia CSVs, return per-config summary DataFrames.

    Returns:
        (flood_df, kad_df) with columns:
            flood_df: N, K, msg_mean, msg_std, hops_mean, hops_std, success_rate
            kad_df:   N, B, msg_mean, msg_std, hops_mean, hops_std, success_rate
    """
    flood_rows, kad_rows = [], []

    for csv_path in sorted((data_dir / "flooding").glob("*.csv")):
        meta = _parse_flooding_filename(csv_path)
        if not meta:
            continue
        df = pd.read_csv(csv_path)
        df["success"] = df["success"].astype(bool)
        successful = df[df["success"]]
        flood_rows.append({
            "N": meta["N"],
            "K": meta["K"],
            "msg_mean": df["messages"].mean(),
            "msg_std": df["messages"].std(),
            "hops_mean": successful["hops"].mean() if len(successful) else 0.0,
            "hops_std": successful["hops"].std() if len(successful) else 0.0,
            "success_rate": df["success"].mean(),
            "n_searches": len(df),
        })

    for csv_path in sorted((data_dir / "kademlia").glob("*.csv")):
        meta = _parse_kademlia_filename(csv_path)
        if not meta:
            continue
        df = pd.read_csv(csv_path)
        df["success"] = df["success"].astype(bool)
        successful = df[df["success"]]
        kad_rows.append({
            "N": meta["N"],
            "B": meta["B"],
            "msg_mean": df["messages"].mean(),
            "msg_std": df["messages"].std(),
            "hops_mean": successful["hops"].mean() if len(successful) else 0.0,
            "hops_std": successful["hops"].std() if len(successful) else 0.0,
            "success_rate": df["success"].mean(),
            "n_searches": len(df),
        })

    flood_df = pd.DataFrame(flood_rows).sort_values(["K", "N"]).reset_index(drop=True)
    kad_df = pd.DataFrame(kad_rows).sort_values(["B", "N"]).reset_index(drop=True)
    return flood_df, kad_df


def load_churn_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load churn CSVs, return (flood_churn_df, kad_churn_df)."""
    churn_dir = data_dir / "churn"
    flood_rows, kad_rows = [], []

    if churn_dir.exists():
        for csv_path in sorted(churn_dir.glob("flooding_*.csv")):
            meta = _parse_churn_flooding_filename(csv_path)
            if not meta:
                continue
            df = pd.read_csv(csv_path)
            df["N"] = meta["N"]
            df["K"] = meta["K"]
            df["churn_pct"] = meta["churn_pct"]
            flood_rows.append(df)

        for csv_path in sorted(churn_dir.glob("kademlia_*.csv")):
            meta = _parse_churn_kademlia_filename(csv_path)
            if not meta:
                continue
            df = pd.read_csv(csv_path)
            df["N"] = meta["N"]
            df["B"] = meta["B"]
            df["churn_pct"] = meta["churn_pct"]
            kad_rows.append(df)

    flood_churn = pd.concat(flood_rows, ignore_index=True) if flood_rows else pd.DataFrame()
    kad_churn = pd.concat(kad_rows, ignore_index=True) if kad_rows else pd.DataFrame()
    return flood_churn, kad_churn


# ---------------------------------------------------------------------------
# Plot 1: Messages vs N (log-log) — flooding K=10 and Kademlia B=16
# ---------------------------------------------------------------------------

def plot_messages_vs_n(flood_df: pd.DataFrame, kad_df: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))

    f = flood_df[flood_df["K"] == 10].sort_values("N")
    k = kad_df[kad_df["B"] == 16].sort_values("N")

    if f.empty and k.empty:
        logger.warning("No K=10 flooding or B=16 Kademlia data — skipping plot 1")
        return

    if not f.empty:
        ax.errorbar(f["N"], f["msg_mean"], yerr=f["msg_std"],
                    fmt="o-", color=FLOOD_COLOR, label="Flooding (K=10)", capsize=4)
        # O(N) reference line
        slope_f, intercept_f, *_ = stats.linregress(np.log10(f["N"]), np.log10(f["msg_mean"]))
        n_ref = np.array([f["N"].min(), f["N"].max()])
        ax.plot(n_ref, 10**intercept_f * n_ref**slope_f,
                "--", color=FLOOD_COLOR, alpha=0.5,
                label=f"Fit: $\\propto N^{{{slope_f:.2f}}}$")

    if not k.empty:
        ax.errorbar(k["N"], k["msg_mean"], yerr=k["msg_std"],
                    fmt="s-", color=KAD_COLOR, label="Kademlia (B=16)", capsize=4)
        slope_k, intercept_k, *_ = stats.linregress(np.log10(k["N"]), np.log10(k["msg_mean"]))
        n_ref = np.array([k["N"].min(), k["N"].max()])
        ax.plot(n_ref, 10**intercept_k * n_ref**slope_k,
                "--", color=KAD_COLOR, alpha=0.5,
                label=f"Fit: $\\propto N^{{{slope_k:.2f}}}$")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Network size N")
    ax.set_ylabel("Messages per search (mean)")
    ax.set_title("Messages per search vs Network size (log-log)")
    ax.legend()
    fig.tight_layout()
    _save(fig, output_dir / "01_messages_vs_n.png")


# ---------------------------------------------------------------------------
# Plot 2: Hops vs log₂(N) — Kademlia B=16 (successful searches only)
# ---------------------------------------------------------------------------

def plot_hops_vs_logn(kad_df: pd.DataFrame, output_dir: Path) -> None:
    k = kad_df[kad_df["B"] == 16].sort_values("N").copy()
    if k.empty:
        logger.warning("No B=16 Kademlia data — skipping plot 2")
        return

    k["log2_N"] = np.log2(k["N"])

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(k["log2_N"], k["hops_mean"], yerr=k["hops_std"],
                fmt="s-", color=KAD_COLOR, capsize=4, label="Kademlia B=16")

    slope, intercept, r, *_ = stats.linregress(k["log2_N"], k["hops_mean"])
    x_ref = np.linspace(k["log2_N"].min(), k["log2_N"].max(), 50)
    r2 = r**2
    if k["hops_mean"].nunique() == 1:
        # Constant hops — annotate as divergence from theory instead of showing a flat fit
        ax.axhline(k["hops_mean"].iloc[0], linestyle="--", color=KAD_COLOR, alpha=0.6,
                   label=f"Fit: hops = {k['hops_mean'].iloc[0]:.1f} (constant; diverges from theory)")
    else:
        ax.plot(x_ref, slope * x_ref + intercept, "--", color=KAD_COLOR, alpha=0.6,
                label=f"Fit: hops = {slope:.2f}*log2(N) + {intercept:.2f}  (R2={r2:.3f})")

    # Theoretical O(log N): slope=1 line anchored at the midpoint
    mid_x = k["log2_N"].median()
    mid_y = k["hops_mean"].median()
    ax.plot(x_ref, (x_ref - mid_x) + mid_y, ":", color="gray", alpha=0.7,
            label=r"Ideal $O(\log N)$")

    ax.set_xlabel(r"$\log_2(N)$")
    ax.set_ylabel("Average hops (successful searches only)")
    ax.set_title(r"Kademlia: hops vs $\log_2(N)$")
    ax.legend()
    fig.tight_layout()
    _save(fig, output_dir / "02_hops_vs_logn.png")


# ---------------------------------------------------------------------------
# Plot 3: Flooding sensitivity to K
# ---------------------------------------------------------------------------

def plot_sensitivity_k(flood_df: pd.DataFrame, output_dir: Path) -> None:
    if flood_df.empty:
        logger.warning("No flooding data — skipping plot 3")
        return

    ks = sorted(flood_df["K"].unique())
    colors = sns.color_palette("Blues_d", len(ks))

    fig, ax = plt.subplots(figsize=(7, 5))
    for k_val, color in zip(ks, colors):
        sub = flood_df[flood_df["K"] == k_val].sort_values("N")
        ax.plot(sub["N"], sub["msg_mean"], "o-", color=color, label=f"K={k_val}")
        ax.fill_between(sub["N"],
                        sub["msg_mean"] - sub["msg_std"],
                        sub["msg_mean"] + sub["msg_std"],
                        color=color, alpha=0.15)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Network size N")
    ax.set_ylabel("Messages per search (mean)")
    ax.set_title("Flooding: sensitivity to K (neighbors per node)")
    ax.legend(title="K")
    fig.tight_layout()
    _save(fig, output_dir / "03_sensitivity_k.png")


# ---------------------------------------------------------------------------
# Plot 4: Kademlia sensitivity to B
# ---------------------------------------------------------------------------

def plot_sensitivity_b(kad_df: pd.DataFrame, output_dir: Path) -> None:
    if kad_df.empty:
        logger.warning("No Kademlia data — skipping plot 4")
        return

    bs = sorted(kad_df["B"].unique())
    colors = sns.color_palette("Reds_d", len(bs))

    fig, ax = plt.subplots(figsize=(7, 5))
    for b_val, color in zip(bs, colors):
        sub = kad_df[kad_df["B"] == b_val].sort_values("N")
        ax.plot(sub["N"], sub["hops_mean"], "s-", color=color, label=f"B={b_val}")
        ax.fill_between(sub["N"],
                        sub["hops_mean"] - sub["hops_std"],
                        sub["hops_mean"] + sub["hops_std"],
                        color=color, alpha=0.15)

    ax.set_xscale("log")
    ax.set_xlabel("Network size N")
    ax.set_ylabel("Hops per search (successful only)")
    ax.set_title("Kademlia: sensitivity to B (ID bit width)")
    ax.legend(title="B")
    fig.tight_layout()
    _save(fig, output_dir / "04_sensitivity_b.png")


# ---------------------------------------------------------------------------
# Plot 5: Churn robustness — success rate vs round
# ---------------------------------------------------------------------------

def plot_churn_robustness(flood_churn: pd.DataFrame, kad_churn: pd.DataFrame,
                          output_dir: Path) -> None:
    if flood_churn.empty and kad_churn.empty:
        logger.warning("No churn data — skipping plot 5")
        return

    # Collect all N values present across both datasets
    ns_flood = set(flood_churn["N"].unique()) if not flood_churn.empty else set()
    ns_kad = set(kad_churn["N"].unique()) if not kad_churn.empty else set()
    network_sizes = sorted(ns_flood | ns_kad)

    churn_rates = [5, 10, 20]

    for n in network_sizes:
        fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)

        for ax, pct in zip(axes, churn_rates):
            if not flood_churn.empty:
                sub_f = flood_churn[
                    (flood_churn["N"] == n) &
                    (flood_churn["churn_pct"] == pct) &
                    (flood_churn["K"] == 10)
                ].sort_values("round")
                if not sub_f.empty:
                    ax.plot(sub_f["round"], sub_f["success_rate"],
                            "o-", color=FLOOD_COLOR, label="Flooding K=10")

            if not kad_churn.empty:
                sub_k = kad_churn[
                    (kad_churn["N"] == n) &
                    (kad_churn["churn_pct"] == pct) &
                    (kad_churn["B"] == 16)
                ].sort_values("round")
                if not sub_k.empty:
                    ax.plot(sub_k["round"], sub_k["success_rate"],
                            "s-", color=KAD_COLOR, label="Kademlia B=16")

            ax.axhline(y=0.90, color="gray", linestyle=":", alpha=0.7, label="90% threshold")
            ax.set_title(f"Churn {pct}%/round")
            ax.set_xlabel("Round")
            ax.set_ylim(-0.05, 1.05)

        axes[0].set_ylabel("Success rate")
        axes[0].legend(fontsize=9)
        fig.suptitle(f"Search success rate under churn (N={n})")
        fig.tight_layout()
        _save(fig, output_dir / f"05_churn_robustness_N{n}.png")


# ---------------------------------------------------------------------------
# Plot 6: Message distribution histogram
# ---------------------------------------------------------------------------

def plot_load_histogram(flood_df: pd.DataFrame, kad_df: pd.DataFrame,
                        data_dir: Path, output_dir: Path) -> None:
    flood_msgs, kad_msgs = [], []

    for csv_path in (data_dir / "flooding").glob("results_N1000_K10.csv"):
        df = pd.read_csv(csv_path)
        flood_msgs.extend(df["messages"].tolist())

    for csv_path in (data_dir / "kademlia").glob("results_N1000_B16.csv"):
        df = pd.read_csv(csv_path)
        kad_msgs.extend(df["messages"].tolist())

    if not flood_msgs and not kad_msgs:
        logger.warning("No N=1000 data found for histogram — skipping plot 6")
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    if flood_msgs:
        axes[0].hist(flood_msgs, bins=30, color=FLOOD_COLOR, edgecolor="white", alpha=0.85)
        axes[0].set_title("Flooding (N=1000, K=10)\nMessages per search")
        axes[0].set_xlabel("Messages")
        axes[0].set_ylabel("Frequency")

    if kad_msgs:
        axes[1].hist(kad_msgs, bins=30, color=KAD_COLOR, edgecolor="white", alpha=0.85)
        axes[1].set_title("Kademlia (N=1000, B=16)\nMessages per search")
        axes[1].set_xlabel("Messages")
        axes[1].set_ylabel("Frequency")

    fig.suptitle("Distribution of messages per search (N=1000)")
    fig.tight_layout()
    _save(fig, output_dir / "06_message_histogram.png")


# ---------------------------------------------------------------------------
# Plot 8: Total cost breakdown — search (Phase 1) + transfer (Phase 2)
# ---------------------------------------------------------------------------

def plot_total_cost_comparison(
    flood_df: pd.DataFrame,
    kad_df: pd.DataFrame,
    output_dir: Path,
    F_mbits: float = 800.0,
    Us_mbps: float = 10.0,
    dmin_mbps: float = 1.0,
    Ui_per_peer_mbps: float = 1.0,
    demo_n: int = 1000,
) -> None:
    """Two-phase total cost comparison: search overhead + file transfer, both normalized.

    Normalization baseline: Tp2p(N=10) = 1 unit for transfer;
    search is expressed as multiples of the search cost at N=10.
    Both components are additive in this normalized space.

    Key story:
    - C/S:       transfer grows O(N), search is trivial (1 request to server)
    - Flooding:  transfer = Tp2p (flat — same P2P benefit as Kademlia!)
                 search   = O(N) — as costly as C/S transfer → wastes Tp2p's advantage
    - Kademlia:  transfer = Tp2p (same flat transfer as flooding)
                 search   = O(log N) → total cost stays sub-linear
    """
    f = flood_df[flood_df["K"] == 10].sort_values("N")
    k = kad_df[kad_df["B"] == 16].sort_values("N")

    if f.empty and k.empty:
        logger.warning("No K=10/B=16 data — skipping plot 8")
        return

    all_ns = sorted(set(f["N"].tolist()) | set(k["N"].tolist()))
    n0 = min(all_ns)

    tp2p_base = _tp2p(n0, F_mbits, Us_mbps, dmin_mbps, n0 * Ui_per_peer_mbps)

    f_msgs = f.set_index("N")["msg_mean"]
    k_hops = k.set_index("N")["hops_mean"]
    f_base = f_msgs.loc[n0] if n0 in f_msgs.index else f_msgs.iloc[0]
    k_base = k_hops.loc[n0] if n0 in k_hops.index else k_hops.iloc[0]

    ns_valid, cs_tot, flood_tot, kad_tot = [], [], [], []
    for n in all_ns:
        if n not in f_msgs.index or n not in k_hops.index:
            continue
        tcs_n = _tcs(n, F_mbits, Us_mbps, dmin_mbps) / tp2p_base
        tp2p_n = _tp2p(n, F_mbits, Us_mbps, dmin_mbps, n * Ui_per_peer_mbps) / tp2p_base
        f_s = f_msgs.loc[n] / f_base
        k_s = k_hops.loc[n] / k_base
        ns_valid.append(n)
        cs_tot.append(tcs_n)           # transfer only; search = 1 request (negligible)
        flood_tot.append(tp2p_n + f_s) # Tp2p transfer + O(N) search
        kad_tot.append(tp2p_n + k_s)   # Tp2p transfer + O(log N) search

    if not ns_valid:
        logger.warning("No overlapping N values across K=10 and B=16 — skipping plot 8")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # --- LEFT: total cost lines (log-log) ---
    ax1.plot(ns_valid, cs_tot, "k^-", linewidth=2,
             label="C/S: bottleneck = transfer (Tcs grows O(N))")
    ax1.plot(ns_valid, flood_tot, "o-", color=FLOOD_COLOR, linewidth=2,
             label="Flooding: bottleneck = search O(N) — wastes Tp2p advantage")
    ax1.plot(ns_valid, kad_tot, "s-", color=KAD_COLOR, linewidth=2,
             label="Kademlia: search O(log N) + same Tp2p as flooding")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Network size N")
    ax1.set_ylabel(f"Total normalized cost  (Tp2p(N={n0}) = 1)")
    ax1.set_title("Total cost per operation: Phase 1 + Phase 2\n(log-log)")
    ax1.legend(fontsize=8.5, loc="upper left")

    # --- RIGHT: stacked horizontal bars at demo_n (linear scale) ---
    n_demo = demo_n if demo_n in ns_valid else ns_valid[-1]
    tcs_demo  = _tcs(n_demo, F_mbits, Us_mbps, dmin_mbps) / tp2p_base
    tp2p_demo = _tp2p(n_demo, F_mbits, Us_mbps, dmin_mbps, n_demo * Ui_per_peer_mbps) / tp2p_base
    f_search_demo = f_msgs.loc[n_demo] / f_base if n_demo in f_msgs.index else 0.0
    k_search_demo = k_hops.loc[n_demo] / k_base if n_demo in k_hops.index else 0.0

    archs      = ["C/S", "Flooding (P2P)", "Kademlia (P2P)"]
    transfers  = [tcs_demo,  tp2p_demo,  tp2p_demo]
    searches   = [0.0,       f_search_demo, k_search_demo]
    bar_colors = ["#546E7A", FLOOD_COLOR,   KAD_COLOR]

    y = np.arange(len(archs))
    ax2.barh(y, transfers, height=0.45, color="#B0BEC5", edgecolor="white",
             label=f"Transfer cost (Phase 2)")
    for i, (t, s, c) in enumerate(zip(transfers, searches, bar_colors)):
        ax2.barh(i, s, height=0.45, left=t, color=c, edgecolor="white", alpha=0.85,
                 label=f"Search overhead (Phase 1)" if i == 0 else "_")
        total = t + s
        ax2.text(total + max(transfers) * 0.02, i,
                 f" {total:.1f}x", va="center", fontsize=9, color=c)

    ax2.set_yticks(y)
    ax2.set_yticklabels(archs, fontsize=10)
    ax2.set_xlabel(f"Normalized cost  (Tp2p(N={n0}) = 1 unit)")
    ax2.set_title(f"Cost decomposition at N={n_demo}\n"
                  f"Flooding search = C/S transfer magnitude; Kademlia search is negligible")
    ax2.legend(fontsize=9, loc="lower right")
    ax2.invert_yaxis()

    fig.suptitle(
        "Kademlia wins on both phases: O(log N) search AND same Tp2p transfer as flooding\n"
        f"Flooding 'wastes' Tp2p — its O(N) search overhead is as costly as C/S transfer"
    )
    fig.tight_layout()
    _save(fig, output_dir / "08_total_cost_comparison.png")


# ---------------------------------------------------------------------------
# Plot 7: Tcs/Tp2p theory vs simulation — normalized scaling comparison
# ---------------------------------------------------------------------------

def _tcs(n: int, F: float, Us: float, dmin: float) -> float:
    return max(n * F / Us, F / dmin)


def _tp2p(n: int, F: float, Us: float, dmin: float, sum_Ui: float) -> float:
    return max(F / Us, F / dmin, n * F / (Us + sum_Ui))


def plot_tcs_tp2p_vs_simulation(
    flood_df: pd.DataFrame,
    kad_df: pd.DataFrame,
    output_dir: Path,
    F_mbits: float = 800.0,
    Us_mbps: float = 10.0,
    dmin_mbps: float = 1.0,
    Ui_per_peer_mbps: float = 1.0,
) -> None:
    """Compare normalized Tcs/Tp2p scaling with simulation results.

    Theory (seconds) and simulation (messages / hops) are normalized to N=10 so
    they can be placed on the same axes despite different units.  The comparison
    is qualitative: matching slopes confirm that flooding is O(N) like Tcs, and
    Kademlia is sub-linear like Tp2p.
    """
    f = flood_df[flood_df["K"] == 10].sort_values("N")
    k = kad_df[kad_df["B"] == 16].sort_values("N")

    if f.empty and k.empty:
        logger.warning("No K=10 flooding or B=16 Kademlia data — skipping plot 7")
        return

    all_ns = sorted(set(f["N"].tolist()) | set(k["N"].tolist()))
    n0 = min(all_ns)

    tcs_vals = np.array([_tcs(n, F_mbits, Us_mbps, dmin_mbps) for n in all_ns])
    tp2p_vals = np.array([_tp2p(n, F_mbits, Us_mbps, dmin_mbps, n * Ui_per_peer_mbps) for n in all_ns])
    tcs_base = _tcs(n0, F_mbits, Us_mbps, dmin_mbps)
    tp2p_base = _tp2p(n0, F_mbits, Us_mbps, dmin_mbps, n0 * Ui_per_peer_mbps)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # LEFT — Tcs (C/S) and flooding messages: both exhibit O(N) scaling, but for different reasons.
    # Tcs grows O(N) because only the server uploads (NF/Us bottleneck).
    # Flooding grows O(N) because unstructured search may reach all N nodes.
    # The comparison is a complexity-class analogy, not conceptual equivalence.
    ax1.plot(all_ns, tcs_vals / tcs_base, "k--", linewidth=2,
             label="Tcs — C/S theory (O(N) bandwidth)", alpha=0.8)
    if not f.empty:
        n0_msgs = f.loc[f["N"] == n0, "msg_mean"]
        f_base = n0_msgs.values[0] if len(n0_msgs) > 0 else f["msg_mean"].iloc[0]
        ax1.errorbar(f["N"], f["msg_mean"] / f_base,
                     yerr=f["msg_std"] / f_base,
                     fmt="o-", color=FLOOD_COLOR, capsize=4,
                     label="Flooding msgs — P2P unstructured (O(N) search)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Network size N")
    ax1.set_ylabel(f"Normalized value  (N={n0} = 1)")
    ax1.set_title("O(N) scaling: Tcs (C/S) vs Flooding (P2P unstructured)\n"
                  "(both scale linearly — different bottlenecks)")
    ax1.legend(fontsize=9)

    # RIGHT — Tp2p (P2P ideal) and Kademlia hops: both sub-linear vs the O(N) left panel.
    # Tp2p saturates at F/dmin because each new peer adds upload capacity.
    # Kademlia achieves O(log N) via XOR-guided routing — better than flooding, slightly
    # worse than the theoretical Tp2p minimum (which assumes full replication).
    ax2.plot(all_ns, tp2p_vals / tp2p_base, "k--", linewidth=2,
             label="Tp2p — P2P theory (saturates at F/dmin)", alpha=0.8)
    if not k.empty:
        n0_hops = k.loc[k["N"] == n0, "hops_mean"]
        k_base = n0_hops.values[0] if len(n0_hops) > 0 else k["hops_mean"].iloc[0]
        ax2.errorbar(k["N"], k["hops_mean"] / k_base,
                     yerr=k["hops_std"] / k_base,
                     fmt="s-", color=KAD_COLOR, capsize=4,
                     label="Kademlia hops — P2P structured (O(log N) search)")
    ax2.set_xscale("log")
    ax2.set_xlabel("Network size N")
    ax2.set_ylabel(f"Normalized value  (N={n0} = 1)")
    ax2.set_title("Sub-linear scaling: Tp2p (P2P ideal) vs Kademlia (P2P structured)\n"
                  "(divergence: Tp2p flat; Kademlia O(log N) — no replication in sim)")
    ax2.legend(fontsize=9)

    fig.suptitle(
        f"Theoretical distribution time vs simulation search overhead — normalized to N={n0}\n"
        f"Complexity-class analogy: O(N) left; sub-linear right  "
        f"[F={int(F_mbits / 8)}MB, Us={Us_mbps}Mbps, dmin={dmin_mbps}Mbps]"
    )
    fig.tight_layout()
    _save(fig, output_dir / "07_theory_vs_simulation.png")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved {path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate comparison plots")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "data"),
                        help="Directory with flooding/, kademlia/, churn/ subdirs")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "informe" / "figures"),
                        help="Directory to write PNG files")
    args = parser.parse_args()

    data_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    flood_df, kad_df = load_experiment_summaries(data_dir)
    flood_churn, kad_churn = load_churn_data(data_dir)

    if flood_df.empty and kad_df.empty:
        logger.error("No experiment CSVs found in %s — run simulations first.", data_dir)
        sys.exit(1)

    logger.info("Flooding configs: %s", flood_df[["N", "K"]].drop_duplicates().to_dict("records"))
    logger.info("Kademlia configs: %s", kad_df[["N", "B"]].drop_duplicates().to_dict("records"))

    plot_messages_vs_n(flood_df, kad_df, output_dir)
    plot_hops_vs_logn(kad_df, output_dir)
    plot_sensitivity_k(flood_df, output_dir)
    plot_sensitivity_b(kad_df, output_dir)
    plot_churn_robustness(flood_churn, kad_churn, output_dir)
    plot_load_histogram(flood_df, kad_df, data_dir, output_dir)
    plot_tcs_tp2p_vs_simulation(flood_df, kad_df, output_dir)
    plot_total_cost_comparison(flood_df, kad_df, output_dir)

    logger.info("All plots written to %s", output_dir)


if __name__ == "__main__":
    main()
