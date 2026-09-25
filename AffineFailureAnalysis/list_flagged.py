#!/usr/bin/env python3
"""List every (ECC, scan_type, category, Event, PL) directory that the
det_dev > threshold criterion (see README.md) would judge FAIL, applied
directly to records.csv (directory level - so every Event sharing a
flagged (PL, Zone) scan is listed, not just one representative).

Also marks whether the actual human judgment (from records.csv's
"judgment" column) agrees (true positive) or not (false positive: human
said OK, criterion says FAIL).

Usage:
    python list_flagged.py [--records records.csv] [--threshold 0.00252129] [--out flagged.csv]
"""
import argparse
import os

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--records", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.csv"))
    parser.add_argument("--threshold", type=float, default=0.00252129,
                         help="det_dev cut from analyze.py's threshold_scan.csv (default: its best cut)")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "flagged.csv"))
    args = parser.parse_args()

    df = pd.read_csv(args.records)
    a, b, c, d = df["AffineParam_a"], df["AffineParam_b"], df["AffineParam_c"], df["AffineParam_d"]
    df["det"] = a * d - b * c
    df["det_dev"] = (df["det"] - 1).abs()

    flagged = df[df["det_dev"] > args.threshold].copy()
    flagged["actual_judgment"] = flagged["judgment"]
    flagged["agrees_with_human"] = flagged["judgment"].isin(["k:Retake", "l:?"])
    flagged = flagged[["ecc", "scan_type", "category", "event", "pl", "det_dev",
                        "actual_judgment", "agrees_with_human", "source_dir"]]
    flagged = flagged.sort_values(["ecc", "scan_type", "category", "pl", "event"])
    flagged.to_csv(args.out, index=False)

    n = len(flagged)
    n_tp = flagged["agrees_with_human"].sum()
    print(f"threshold: det_dev > {args.threshold}")
    print(f"flagged directories: {n}  (true positive / actual FAIL: {n_tp}, false positive / actual OK: {n - n_tp})")
    print(f"wrote: {args.out}")


if __name__ == "__main__":
    main()
