#!/usr/bin/env python3
"""Export this analysis's FAIL population (records.csv, judgment in
k:Retake/l:?) as ChkRes.txt-format files that tools/OfflineManChk/
extract_retake_tracklist.py can read directly.

Since extract_retake_tracklist.py only needs (Event, PL) - it doesn't
care about scan_type (UTS/FTS) or category (IMG/Ref/IMG) - this collapses
all of that per ECC into ONE file per ECC, containing the union of every
(Event, PL) judged k:Retake/l:? anywhere in records.csv for that ECC.
The filename just needs to start with "ECC<n>UTS" or "ECC<n>FTS" for
extract_retake_tracklist.py's own filename parser; the "UTS" here is a
label of convenience, not a claim about which scan_type it came from.

Usage:
    python export_chkres.py [ecc_number] [--records records.csv] [--outdir .]

Pass an ECC number (e.g. "4") to output only that ECC's file; omit it to
output one file for every ECC found in records.csv (the previous default
behavior).

Output: <outdir>/ECC<n>_affine_fail.txt for every ECC found (renamed here
to satisfy the "ECC<n>UTS..." pattern extract_retake_tracklist.py's
filename parser expects - see below), one line per unique (Event, PL):
    Event?????/PL??? k:Retake
"""
import argparse
import os

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ecc_number", nargs="?", default=None, help="Output only this ECC (default: all ECCs found)")
    parser.add_argument("--records", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.csv"))
    parser.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()

    df = pd.read_csv(args.records)
    fail = df[df["judgment"].isin(["k:Retake", "l:?"])]

    if args.ecc_number is not None:
        ecc_number = int(args.ecc_number)
        fail = fail[fail["ecc"] == ecc_number]
        if fail.empty:
            print(f"ECC{ecc_number}: k:Retake/l:? のエントリが records.csv に見つかりません。")
            return

    written = []
    for ecc, sub in fail.groupby("ecc"):
        pairs = sorted(set(zip(sub["event"].astype(int), sub["pl"].astype(int))))
        out_path = os.path.join(args.outdir, f"ECC{ecc}UTS_affine_fail.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            for event, pl in pairs:
                f.write(f"Event{event:05d}/PL{pl:03d} k:Retake\n")
        written.append((ecc, len(pairs), out_path))

    for ecc, n, path in written:
        print(f"ECC{ecc}: {n} 件の (Event, PL) を {path} に出力しました。")
    print(
        "\n使い方の例:\n"
        f"  python ..\\tools\\OfflineManChk\\extract_retake_tracklist.py "
        f"AffineRetakeTrackList\\ECC<n> ECC<n>UTS_affine_fail.txt --dry-run"
    )


if __name__ == "__main__":
    main()
