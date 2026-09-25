#!/usr/bin/env python3
"""Zoom into det_dev <= 0.01 with a fixed bin width of 0.0002, comparing the
FAIL and OK populations at directory level (records.csv - NOT the
unique_scans.csv dedup, since human judgment can differ between two
directories that share the exact same (PL, Zone) AffineParam - see
README.md's note on this; the dedup's majority-vote representative row is
not the right unit for finding individual borderline/mislabeled entries).

Goal: find a det_dev value below which essentially no OK case sits, so a
threshold can be chosen that never misclassifies an actual success as a
failure - i.e. spot candidates where the human (eye) judgment itself may
be wrong, not just where the numeric criterion disagrees with it.

Usage:
    python plot_det_dev_zoom.py [--records records.csv] [--outdir .] [--xmax 0.01] [--binwidth 0.0002]

Outputs:
    hist_det_dev_zoom.png   - count histogram (not density) of det_dev in [0, xmax]
    det_dev_zoom_list.csv   - every directory-level row with det_dev <= xmax, sorted by det_dev
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

COLOR_OK = "#2a78d6"
COLOR_FAIL = "#eb6834"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--records", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.csv"))
    parser.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--xmax", type=float, default=0.01)
    parser.add_argument("--binwidth", type=float, default=0.0002)
    args = parser.parse_args()

    df = pd.read_csv(args.records)
    a, b, c, d = df["AffineParam_a"], df["AffineParam_b"], df["AffineParam_c"], df["AffineParam_d"]
    df["det"] = a * d - b * c
    df["det_dev"] = (df["det"] - 1).abs()
    df["outcome"] = np.where(df["judgment"] == "j:OK", "OK", "FAIL")

    zoom = df[df["det_dev"] <= args.xmax].copy()
    zoom = zoom.sort_values("det_dev")
    list_path = os.path.join(args.outdir, "det_dev_zoom_list.csv")
    zoom[["ecc", "scan_type", "category", "event", "pl", "judgment", "outcome", "det_dev", "source_dir"]].to_csv(
        list_path, index=False
    )

    ok_vals = zoom.loc[zoom["outcome"] == "OK", "det_dev"]
    fail_vals = zoom.loc[zoom["outcome"] == "FAIL", "det_dev"]

    bins = np.arange(0, args.xmax + args.binwidth, args.binwidth)

    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=140)
    ax.hist(ok_vals, bins=bins, alpha=0.6, color=COLOR_OK, label=f"OK (n={len(ok_vals)})",
            edgecolor="white", linewidth=0.4)
    ax.hist(fail_vals, bins=bins, alpha=0.6, color=COLOR_FAIL, label=f"FAIL (n={len(fail_vals)})",
            edgecolor="white", linewidth=0.4)
    # rug: individual points, since many bins have very low counts
    rng = np.random.default_rng(0)
    ax.scatter(ok_vals, -1 - rng.uniform(0, 0.6, size=len(ok_vals)), s=8, color=COLOR_OK, alpha=0.7, marker="|")
    ax.scatter(fail_vals, -2.2 - rng.uniform(0, 0.6, size=len(fail_vals)), s=8, color=COLOR_FAIL, alpha=0.7, marker="|")

    ax.set_title(f"det_dev の分布 (0〜{args.xmax}, bin幅={args.binwidth}) - directory単位")
    ax.set_xlabel("det_dev")
    ax.set_ylabel("count")
    ax.set_xlim(0, args.xmax)
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    fig.tight_layout()
    out_path = os.path.join(args.outdir, "hist_det_dev_zoom.png")
    fig.savefig(out_path)
    plt.close(fig)

    print(f"OK   in [0,{args.xmax}]: {len(ok_vals)}  (max={ok_vals.max() if len(ok_vals) else float('nan'):.5f})")
    print(f"FAIL in [0,{args.xmax}]: {len(fail_vals)}  (min={fail_vals.min() if len(fail_vals) else float('nan'):.5f})")
    print(f"wrote: {out_path}")
    print(f"wrote: {list_path}")


if __name__ == "__main__":
    main()
