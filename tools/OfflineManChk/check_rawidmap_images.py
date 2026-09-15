#!/usr/bin/env python3
"""Check that every track in a *_rawidmap.txt has its scan image directory.

Usage:
    python check_rawidmap_images.py <btrklist<n>_rawidmap.txt> [--scan-data-root DIR]

<*_rawidmap.txt> is one line per track:
    PL eventid rawid1 zone rawid2 ax ay x y ph1 ph2 trk_type
(the format RawidMapChecker.py reads/writes). trk_type is 0 (real track),
1 (extrapolated), or -1 (reference track).

For each (PL, eventid, trk_type):
  - trk_type 0 or 1 (real/extrapolated) -> looked up under
        <ScanData>/<UTS|FTS>/ECC<n>/IMG/Event?????/PL???
  - trk_type -1 (reference)             -> looked up under
        <ScanData>/<UTS|FTS>/ECC<n>/Ref/IMG/Event?????/PL???
(<n> is read from the input filename, e.g. "btrklist6_rawidmap.txt" -> ECC6.)
Existence is judged purely by whether the Event?????/PL??? directory exists
under either of those two candidate roots - file contents are not checked.

Missing entries are grouped by Event and printed (and also written to
"<rawidmap stem>_missing.txt" next to the input file) as:
    Event:????? PL???
    IMG:PL???,PL???
    Ref:PL???
(the PL??? after "Event:?????" is that Event's real track (trk_type 0) PL,
included as a reference PL that is known to exist; the IMG:/Ref: line is
omitted for an Event with nothing missing in that category.)
"""
import argparse
import os
import re
import sys
from collections import defaultdict

SCAN_TYPES = ["UTS", "FTS"]
FILENAME_PATTERN = re.compile(r"btrklist(\d+)_rawidmap", re.IGNORECASE)


def parse_ecc_num(rawidmap_path):
    m = FILENAME_PATTERN.search(os.path.basename(rawidmap_path))
    if not m:
        raise ValueError(
            f"ECC番号がファイル名から読み取れません(btrklist<n>_rawidmap.txt の形式ではない): {rawidmap_path}"
        )
    return m.group(1)


def candidate_roots(scan_data_root, ecc_num, is_ref):
    sub = os.path.join(f"ECC{ecc_num}", "Ref", "IMG") if is_ref else os.path.join(f"ECC{ecc_num}", "IMG")
    return [os.path.join(scan_data_root, scan_type, sub) for scan_type in SCAN_TYPES]


def find_dir(roots, event_pl):
    for root in roots:
        candidate = os.path.join(root, *event_pl.split("/"))
        if os.path.isdir(candidate):
            return candidate
    return None


def format_missing_report(missing, real_pl_by_event):
    """missing: list of (event_pl, category). real_pl_by_event: Event?????->PL??? of
    that event's real (trk_type 0) track. Returns the grouped-by-Event report text."""
    by_event = defaultdict(lambda: defaultdict(list))
    for event_pl, category in missing:
        event, pl = event_pl.split("/")
        by_event[event][category].append(pl)

    lines = []
    for event in sorted(by_event):
        header = "Event:" + event[len("Event"):]
        real_pl = real_pl_by_event.get(event)
        if real_pl:
            header += " " + real_pl
        lines.append(header)
        for category, prefix in (("IMG", "IMG"), ("Ref/IMG", "Ref")):
            pls = by_event[event].get(category)
            if not pls:
                continue
            lines.append(f"{prefix}:" + ",".join(sorted(pls)))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rawidmap_txt", help=r"e.g. ...\btrklist6_rawidmap.txt")
    parser.add_argument(
        "--scan-data-root",
        help=r'Override the ScanData root (default: <this repo>\ScanData)',
    )
    args = parser.parse_args()

    rawidmap_path = os.path.abspath(args.rawidmap_txt)
    ecc_num = parse_ecc_num(rawidmap_path)

    if args.scan_data_root:
        scan_data_root = os.path.abspath(args.scan_data_root)
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        scan_data_root = os.path.join(repo_root, "ScanData")

    print(f"ECC{ecc_num}")
    print(f"ScanData root: {scan_data_root}")

    targets = {}  # (event_pl, is_ref) -> None, insertion order preserved (dict, py3.7+)
    real_pl_by_event = {}  # Event????? -> PL??? of that event's trk_type==0 (real) track
    with open(rawidmap_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 12:
                print(f"Skipping malformed line: {line!r}")
                continue
            pl, eventid = int(parts[0]), int(parts[1])
            trk_type = int(parts[11])
            event = f"Event{eventid:05d}"
            pl_str = f"PL{pl:03d}"
            event_pl = f"{event}/{pl_str}"
            is_ref = trk_type == -1
            targets[(event_pl, is_ref)] = None
            if trk_type == 0 and event not in real_pl_by_event:
                real_pl_by_event[event] = pl_str

    img_roots = candidate_roots(scan_data_root, ecc_num, is_ref=False)
    ref_roots = candidate_roots(scan_data_root, ecc_num, is_ref=True)

    found = 0
    missing = []
    for event_pl, is_ref in targets:
        roots = ref_roots if is_ref else img_roots
        hit = find_dir(roots, event_pl)
        category = "Ref/IMG" if is_ref else "IMG"
        if hit:
            found += 1
        else:
            missing.append((event_pl, category))

    total = len(targets)
    print(f"\n{total} 件のユニークな (Event/PL, 種別) を確認しました。")
    print(f"  見つかった: {found}")
    print(f"  見つからない: {len(missing)}")

    if missing:
        report = format_missing_report(missing, real_pl_by_event)
        print("\n見つからないディレクトリ:")
        print(report)

        stem = os.path.splitext(os.path.basename(rawidmap_path))[0]
        out_path = os.path.join(os.path.dirname(rawidmap_path), f"{stem}_missing.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n一覧を書き出しました: {out_path}")


if __name__ == "__main__":
    main()
