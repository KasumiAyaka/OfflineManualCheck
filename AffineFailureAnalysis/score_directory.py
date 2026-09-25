#!/usr/bin/env python3
"""Apply the det_dev criterion (see README.md) directly to any directory
tree, regardless of whether it has ever been human-reviewed via
check_quality.py. Useful for scoring data that has no ChkRes.txt /
PatternMatchFailed history yet (e.g. a Ref/IMG side that was never
checked).

Usage:
    python score_directory.py <root_dir> [--threshold 0.00252129] [--out scored.csv]

<root_dir> is walked recursively for tomographic_images.json; every
Event?????/PL??? found is scored independently (no dedup - if you want
the "one row per unique physical (PL, Zone) scan" view, dedup on
(pl, AffineParam) yourself the way analyze.py does).
"""
import argparse
import glob
import json
import os
import re

import pandas as pd

EVENT_PL_PATTERN = re.compile(r"Event(\d+)[\\/]+PL(\d+)(_chk)?")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root_dir")
    parser.add_argument("--threshold", type=float, default=0.00252129)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    root = os.path.abspath(args.root_dir)
    rows = []
    for json_path in glob.glob(os.path.join(root, "**", "tomographic_images.json"), recursive=True):
        rel = os.path.relpath(json_path, root)
        m = EVENT_PL_PATTERN.search(rel)
        if not m:
            print(f"Skipping (Event/PL not found in path): {json_path}")
            continue
        event, pl = int(m.group(1)), int(m.group(2))
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        a, b, c, dd, e, f_ = d["AffineParam"]
        det = a * dd - b * c
        det_dev = abs(det - 1)
        rows.append({
            "event": event, "pl": pl, "det_dev": det_dev,
            "predicted": "FAIL" if det_dev > args.threshold else "OK",
            "source_dir": os.path.dirname(json_path),
        })

    df = pd.DataFrame(rows).sort_values(["pl", "event"])
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    f"scored_{os.path.basename(root.rstrip(os.sep))}.csv")
    df.to_csv(out, index=False)

    n_fail = (df["predicted"] == "FAIL").sum()
    print(f"root: {root}")
    print(f"scored: {len(df)} directories  (predicted FAIL: {n_fail}, predicted OK: {len(df) - n_fail})")
    print(f"wrote: {out}")
    if n_fail:
        print("\npredicted FAIL:")
        for _, r in df[df["predicted"] == "FAIL"].iterrows():
            print(f"  Event{r['event']:05d}/PL{r['pl']:03d}  det_dev={r['det_dev']:.4f}")


if __name__ == "__main__":
    main()
