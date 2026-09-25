#!/usr/bin/env python3
"""Compare AffineParam-derived quantities between the FAIL (PatternMatchFailed)
and OK (ChkRes j:OK) populations built by collect_data.py, and look for a
threshold that separates them.

Usage:
    python analyze.py [--records records.csv] [--outdir .]

IMPORTANT: AffineParam is a per-(PL, Zone) scan calibration, not a per-track
quantity - every Event that happens to pass through the same physical
(PL, Zone) during that check shares the exact same 6 numbers (verified
against this dataset: e.g. FTS ECC4 PL064 Zone5 gives the identical
AffineParam for Event00633/Event03933/Event06107/Event07277, while
Event12037 at the same PL064 but Zone2 differs). Comparing at the
directory (Event/PL) level would therefore over-count whichever
(PL, Zone) happened to have many crossing muons. This script DEDUPLICATES
to one row per unique (ecc, scan_type, category, PL, AffineParam-tuple)
scan before computing statistics; see unique_scans.csv.

Outputs (all written to --outdir):
    unique_scans.csv       - one row per unique physical scan, with derived metrics
    summary_stats.csv/.md  - FAIL vs OK descriptive statistics per metric
    threshold_scan.csv/.md - accuracy/precision/recall of a simple 1D threshold
                              rule on each metric, at its best cut point
    hist_<metric>.png      - FAIL vs OK histogram, one per metric
    scatter_scale.png      - scale_x vs scale_y scatter, colored by judgment
"""
import argparse
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# colorblind-safe categorical pair (blue = OK, orange = FAIL), used consistently
COLOR_OK = "#2a78d6"
COLOR_FAIL = "#eb6834"

METRICS = {
    "scale_x": "スケール x = sqrt(a^2+c^2)",
    "scale_y": "スケール y = sqrt(b^2+d^2)",
    "scale_dev": "スケール歪み = max(|scale_x-1|, |scale_y-1|)",
    "det": "行列式 det = a*d - b*c",
    "det_dev": "行列式のずれ = |det - 1|",
    "rotation_deg": "回転角 [deg] = atan2(c, a)",
    "nonortho": "非直交度 = (a*b + c*d) / (scale_x*scale_y)",
    "translation_mag": "並進量 sqrt(e^2+f^2) [um]",
}


def add_derived_columns(df):
    a, b, c, d = df["AffineParam_a"], df["AffineParam_b"], df["AffineParam_c"], df["AffineParam_d"]
    e, f = df["AffineParam_e"], df["AffineParam_f"]
    df["scale_x"] = np.sqrt(a**2 + c**2)
    df["scale_y"] = np.sqrt(b**2 + d**2)
    df["det"] = a * d - b * c
    df["det_dev"] = (df["det"] - 1).abs()
    df["scale_dev"] = pd.concat([(df["scale_x"] - 1).abs(), (df["scale_y"] - 1).abs()], axis=1).max(axis=1)
    df["rotation_deg"] = np.degrees(np.arctan2(c, a))
    df["nonortho"] = (a * b + c * d) / (df["scale_x"] * df["scale_y"])
    df["translation_mag"] = np.sqrt(e**2 + f**2)
    return df


def make_group(row):
    return (row["ecc"], row["scan_type"], row["category"], row["pl"],
            round(row["AffineParam_a"], 9), round(row["AffineParam_b"], 9),
            round(row["AffineParam_c"], 9), round(row["AffineParam_d"], 9),
            round(row["AffineParam_e"], 6), round(row["AffineParam_f"], 6))


def dedup_to_unique_scans(df):
    df = df.copy()
    df["_group"] = df.apply(make_group, axis=1)
    df["outcome"] = np.where(df["judgment"] == "j:OK", "OK", "FAIL")

    rows = []
    inconsistent = []
    for group_key, g in df.groupby("_group"):
        outcomes = set(g["outcome"])
        if len(outcomes) > 1:
            inconsistent.append((group_key, sorted(g["outcome"].tolist())))
        rep = g.iloc[0].copy()
        rep["n_dirs"] = len(g)
        rep["n_events"] = g["event"].nunique()
        rep["outcome"] = g["outcome"].mode().iat[0]  # majority vote if inconsistent
        rows.append(rep)

    unique_df = pd.DataFrame(rows).drop(columns=["_group"]).reset_index(drop=True)
    return unique_df, inconsistent


def write_summary_stats(unique_df, outdir):
    rows = []
    for metric in METRICS:
        for outcome in ("OK", "FAIL"):
            vals = unique_df.loc[unique_df["outcome"] == outcome, metric].dropna()
            rows.append({
                "metric": metric, "outcome": outcome, "n": len(vals),
                "mean": vals.mean(), "std": vals.std(),
                "median": vals.median(), "p05": vals.quantile(0.05), "p95": vals.quantile(0.95),
                "min": vals.min(), "max": vals.max(),
            })
    stats_df = pd.DataFrame(rows)
    stats_df.to_csv(os.path.join(outdir, "summary_stats.csv"), index=False)

    with open(os.path.join(outdir, "summary_stats.md"), "w", encoding="utf-8") as f:
        f.write("# FAIL vs OK 記述統計 (unique scan単位, n=一意な(ECC,scan_type,category,PL,AffineParam)数)\n\n")
        for metric, desc in METRICS.items():
            f.write(f"## {metric}  \n{desc}\n\n")
            sub = stats_df[stats_df["metric"] == metric]
            f.write("| outcome | n | mean | std | median | p05 | p95 | min | max |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")
            for _, r in sub.iterrows():
                f.write(
                    f"| {r['outcome']} | {r['n']:.0f} | {r['mean']:.4g} | {r['std']:.4g} | "
                    f"{r['median']:.4g} | {r['p05']:.4g} | {r['p95']:.4g} | {r['min']:.4g} | {r['max']:.4g} |\n"
                )
            f.write("\n")
    return stats_df


def best_threshold(values, outcomes, direction="above_is_fail"):
    """1D threshold scan: for each candidate cut (midpoints between sorted
    unique values), compute how well "value > cut => predict FAIL" (or the
    reverse) matches the actual outcome. Returns the cut with best accuracy."""
    values = np.asarray(values)
    is_fail = np.asarray(outcomes) == "FAIL"
    order = np.argsort(values)
    sv = values[order]
    candidates = np.unique((sv[:-1] + sv[1:]) / 2.0) if len(sv) > 1 else sv

    best = None
    for cut in candidates:
        pred_fail = values > cut if direction == "above_is_fail" else values < cut
        tp = np.sum(pred_fail & is_fail)
        fp = np.sum(pred_fail & ~is_fail)
        fn = np.sum(~pred_fail & is_fail)
        tn = np.sum(~pred_fail & ~is_fail)
        acc = (tp + tn) / len(values)
        precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
        recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
        if best is None or acc > best["accuracy"]:
            best = {"cut": cut, "accuracy": acc, "precision": precision, "recall": recall,
                    "tp": tp, "fp": fp, "fn": fn, "tn": tn}
    return best


def write_threshold_scan(unique_df, outdir):
    rows = []
    for metric in METRICS:
        sub = unique_df[["outcome", metric]].dropna()
        if sub["outcome"].nunique() < 2 or len(sub) < 2:
            continue
        b = best_threshold(sub[metric].values, sub["outcome"].values, direction="above_is_fail")
        rows.append({"metric": metric, "rule": f"{metric} > {b['cut']:.6g}  =>  FAIL", **b})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(outdir, "threshold_scan.csv"), index=False)

    with open(os.path.join(outdir, "threshold_scan.md"), "w", encoding="utf-8") as f:
        f.write("# 単純な1変数しきい値ルールの性能 (unique scan単位)\n\n")
        f.write("各指標について「値 > しきい値 なら FAIL と判定する」というルールを、\n")
        f.write("全ての候補しきい値の中から正解率(accuracy)が最大になるように選んだ結果。\n\n")
        f.write("| metric | rule | accuracy | precision | recall | TP | FP | FN | TN |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for _, r in df.iterrows():
            f.write(
                f"| {r['metric']} | {r['rule']} | {r['accuracy']:.3f} | {r['precision']:.3f} | "
                f"{r['recall']:.3f} | {r['tp']:.0f} | {r['fp']:.0f} | {r['fn']:.0f} | {r['tn']:.0f} |\n"
            )
    return df


def plot_histograms(unique_df, outdir):
    for metric, desc in METRICS.items():
        ok_vals = unique_df.loc[unique_df["outcome"] == "OK", metric].dropna()
        fail_vals = unique_df.loc[unique_df["outcome"] == "FAIL", metric].dropna()
        if len(ok_vals) == 0 or len(fail_vals) == 0:
            continue

        lo = min(ok_vals.min(), fail_vals.min())
        hi = max(ok_vals.max(), fail_vals.max())
        pad = (hi - lo) * 0.05 if hi > lo else 1.0
        bins = np.linspace(lo - pad, hi + pad, 40)

        fig, ax = plt.subplots(figsize=(7, 4.2), dpi=140)
        ax.hist(ok_vals, bins=bins, density=True, alpha=0.55, color=COLOR_OK,
                label=f"OK (n={len(ok_vals)})", edgecolor="white", linewidth=0.4)
        ax.hist(fail_vals, bins=bins, density=True, alpha=0.55, color=COLOR_FAIL,
                label=f"FAIL (n={len(fail_vals)})", edgecolor="white", linewidth=0.4)
        ax.set_title(f"{metric}: {desc}", fontsize=11)
        ax.set_xlabel(metric)
        ax.set_ylabel("density")
        ax.legend(frameon=False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.25, linewidth=0.6)
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, f"hist_{metric.replace('/', '_')}.png"))
        plt.close(fig)


def plot_scale_scatter(unique_df, outdir):
    fig, ax = plt.subplots(figsize=(6.5, 6), dpi=140)
    for outcome, color, marker in (("OK", COLOR_OK, "o"), ("FAIL", COLOR_FAIL, "^")):
        sub = unique_df[unique_df["outcome"] == outcome]
        ax.scatter(sub["scale_x"], sub["scale_y"], s=22, alpha=0.6, color=color,
                   marker=marker, label=f"{outcome} (n={len(sub)})", edgecolor="none")
    ax.axhline(1.0, color="#c3c2b7", linewidth=0.8, zorder=0)
    ax.axvline(1.0, color="#c3c2b7", linewidth=0.8, zorder=0)
    ax.set_xlabel("scale_x")
    ax.set_ylabel("scale_y")
    ax.set_title("scale_x vs scale_y (1,1) = 理想的な等方スケール")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "scatter_scale.png"))
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--records", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.csv"))
    parser.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()

    df = pd.read_csv(args.records)
    df = add_derived_columns(df)

    unique_df, inconsistent = dedup_to_unique_scans(df)
    unique_df.to_csv(os.path.join(args.outdir, "unique_scans.csv"), index=False)

    print(f"directory-level rows : {len(df)}")
    print(f"unique (PL, AffineParam) scans : {len(unique_df)}")
    print(f"  OK  : {(unique_df['outcome'] == 'OK').sum()}")
    print(f"  FAIL: {(unique_df['outcome'] == 'FAIL').sum()}")
    if inconsistent:
        print(f"\n{len(inconsistent)} 個の (PL, AffineParam) グループで判定が一致していません(多数決で処理):")
        for key, outcomes in inconsistent:
            print(f"  {key}: {outcomes}")

    write_summary_stats(unique_df, args.outdir)
    write_threshold_scan(unique_df, args.outdir)
    plot_histograms(unique_df, args.outdir)
    plot_scale_scatter(unique_df, args.outdir)

    print(f"\n出力先: {args.outdir}")


if __name__ == "__main__":
    main()
