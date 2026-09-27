#!/usr/bin/env python3
"""Apply the det_dev criterion (see README.md) to every Event/PL directory
found under ScanData\\UTS\\ECC<n> and ScanData\\FTS\\ECC<n> for one ECC, and
write out only the directories predicted FAIL as a CSV.

Unlike collect_data.py (which relies on existing ChkRes.txt judgments),
this scores directories directly from tomographic_images.json's
AffineParam, so it works even for data that has never been through
check_quality.py.

Usage:
    python predict_ecc_failures.py <ecc_number> --out <output.csv> [--threshold 0.00252129] [--scandata-root DIR]
"""
import argparse
import glob
import json
import os
import re

import pandas as pd

EVENT_PL_PATTERN = re.compile(r"Event(\d+)[\\/]+PL(\d+)(_chk)?")
DEFAULT_SCANDATA_ROOT = r"K:\NINJA\E71a\ManualCheck\ScanData"
DEFAULT_THRESHOLD = 0.00252129


def category_from_rel_path(rel_path):
    parts = re.split(r"[\\/]+", rel_path)
    return "Ref/IMG" if "Ref" in parts else "IMG"


def score_ecc_scan_type(scandata_root, ecc, scan_type, threshold):
    ecc_root = os.path.join(scandata_root, scan_type, f"ECC{ecc}")
    rows = []
    if not os.path.isdir(ecc_root):
        print(f"  (skip) {ecc_root} が見つかりません")
        return rows

    for json_path in glob.glob(os.path.join(ecc_root, "**", "tomographic_images.json"), recursive=True):
        rel = os.path.relpath(json_path, ecc_root)
        m = EVENT_PL_PATTERN.search(rel)
        if not m:
            print(f"  (skip) Event/PLがパスから読み取れません: {json_path}")
            continue
        event, pl = int(m.group(1)), int(m.group(2))
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        a, b, c, dd, e, f_ = d["AffineParam"]
        det = a * dd - b * c
        det_dev = abs(det - 1)
        rows.append({
            "ecc": ecc,
            "scan_type": scan_type,
            "category": category_from_rel_path(rel),
            "event": event,
            "pl": pl,
            "det_dev": det_dev,
            "judgment": "FAIL" if det_dev > threshold else "OK",
            "source_dir": os.path.dirname(json_path),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ecc_number", type=int, help="対象のECC番号")
    parser.add_argument("--out", required=True, help="失敗判定した一覧の出力先CSVパス")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                         help=f"det_devがこの値を超えたらFAIL(デフォルト {DEFAULT_THRESHOLD})")
    parser.add_argument("--scandata-root", default=DEFAULT_SCANDATA_ROOT,
                         help=f"ScanDataのルート(デフォルト {DEFAULT_SCANDATA_ROOT})")
    args = parser.parse_args()

    print(f"ECC{args.ecc_number} を {args.scandata_root} 配下の UTS/FTS から確認します(threshold={args.threshold})")

    rows = []
    for scan_type in ("UTS", "FTS"):
        rows.extend(score_ecc_scan_type(args.scandata_root, args.ecc_number, scan_type, args.threshold))

    if not rows:
        print("該当するディレクトリが見つかりませんでした。")
        return

    df = pd.DataFrame(rows).sort_values(["scan_type", "category", "pl", "event"])
    n_fail = int((df["judgment"] == "FAIL").sum())
    n_ok = len(df) - n_fail

    fail_df = df[df["judgment"] == "FAIL"].drop(columns=["judgment"])

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fail_df.to_csv(out_path, index=False)

    print(f"\n確認したディレクトリ数: {len(df)}")
    print(f"成功 (OK)  : {n_ok}")
    print(f"失敗 (FAIL): {n_fail}")
    print(f"\n失敗と判定された一覧を書き出しました: {out_path}")


if __name__ == "__main__":
    main()
