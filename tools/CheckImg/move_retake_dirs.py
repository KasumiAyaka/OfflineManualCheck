#!/usr/bin/env python3
"""Move PL directories judged "k:Retake" out of ScanData into PatternMatchFailed.

Usage:
    python move_retake_dirs.py <ChkRes.txt> [--dry-run]

Example:
    python move_retake_dirs.py K:\\NINJA\\E71a\\ManualCheck\\ScanData\\ChkRes\\ECC4UTS0911.txt

<ChkRes.txt> is check_quality.py's output: lines of
"Event?????/PL??? <choice>" (choice is one of j:OK / k:Retake / l:?).
The ECC number and UTS/FTS are read from the file's own name (e.g.
"ECC4UTS0911.txt" -> ECC4, UTS).

For every line whose choice is "k:Retake", the corresponding directory is
moved to:
    <ScanData>/PatternMatchFailed/<UTS|FTS>/ECC<n>/IMG/Event?????/PL???
(<ScanData> is taken to be the parent of the ChkRes.txt's directory.)

The source is looked up under both
    <ScanData>/<UTS|FTS>/ECC<n>/IMG/Event?????/PL???
and
    <ScanData>/chk_<UTS|FTS>/ECC<n>/IMG/Event?????/PL???
(whichever actually exists), since which of the two holds the checked
images has varied between ECCs in this dataset.
"""
import argparse
import os
import re
import shutil
import sys

RETAKE_CHOICE = "k:Retake"
FILENAME_PATTERN = re.compile(r"ECC(\d+)(UTS|FTS)")


def parse_ecc_and_type(chkres_path):
    name = os.path.basename(chkres_path)
    m = FILENAME_PATTERN.search(name)
    if not m:
        raise ValueError(f"ECC番号/UTS・FTSの区別がファイル名から読み取れません: {name}")
    return m.group(1), m.group(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chkres_txt", help=r"e.g. ...\ScanData\ChkRes\ECC4UTS0911.txt")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be moved, without moving anything",
    )
    args = parser.parse_args()

    chkres_path = os.path.abspath(args.chkres_txt)
    ecc_num, scan_type = parse_ecc_and_type(chkres_path)

    # <ScanData>/ChkRes/xxx.txt -> <ScanData>
    scan_data_root = os.path.dirname(os.path.dirname(chkres_path))

    src_roots = [
        os.path.join(scan_data_root, scan_type, f"ECC{ecc_num}", "IMG"),
        os.path.join(scan_data_root, f"chk_{scan_type}", f"ECC{ecc_num}", "IMG"),
    ]
    dst_root = os.path.join(scan_data_root, "PatternMatchFailed", scan_type, f"ECC{ecc_num}", "IMG")

    print(f"ECC{ecc_num} {scan_type}")
    print("  source candidates:")
    for r in src_roots:
        print(f"    {r} ({'exists' if os.path.isdir(r) else 'not found'})")
    print(f"  destination: {dst_root}")
    if not any(os.path.isdir(r) for r in src_roots):
        print("Error: none of the source directories above exist", file=sys.stderr)
        sys.exit(1)

    moved = 0
    skipped_missing = []
    skipped_existing = []

    with open(chkres_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                print(f"Skipping malformed line: {line!r}")
                continue
            rel_pl_dir, choice = parts
            if choice != RETAKE_CHOICE:
                continue

            rel_parts = rel_pl_dir.split("/")
            dst_dir = os.path.join(dst_root, *rel_parts)

            src_dir = next(
                (os.path.join(r, *rel_parts) for r in src_roots
                 if os.path.isdir(os.path.join(r, *rel_parts))),
                None,
            )
            if src_dir is None:
                skipped_missing.append(rel_pl_dir)
                continue
            if os.path.exists(dst_dir):
                skipped_existing.append(rel_pl_dir)
                continue

            if args.dry_run:
                print(f"[DRY-RUN] Would move: {rel_pl_dir}")
            else:
                os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
                shutil.move(src_dir, dst_dir)
                print(f"Moved: {rel_pl_dir}")
            moved += 1

    action = "would be moved" if args.dry_run else "moved"
    print(f"\nDone. {moved} director(ies) {action}.")
    if skipped_missing:
        print(f"{len(skipped_missing)} Retake entries had no source directory:")
        for name in skipped_missing:
            print(" ", name)
    if skipped_existing:
        print(f"{len(skipped_existing)} Retake entries already exist at the destination (left untouched):")
        for name in skipped_existing:
            print(" ", name)


if __name__ == "__main__":
    main()
