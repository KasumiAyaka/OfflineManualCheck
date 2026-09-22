#!/usr/bin/env python3
"""Build a new TrackList containing only the "k:Retake"/"l:?" Event/PL entries.

Usage:
    python extract_retake_tracklist.py <output_dir> <ChkRes.txt> [<ChkRes.txt> ...] [--tracklist-root DIR]

Example (all 4 ChkRes.txt for one ECC - UTS/FTS x normal/Ref):
    python extract_retake_tracklist.py TrackList_Retake\ECC4 ^
        ScanData\ChkRes\ECC4UTS_0922.txt ScanData\ChkRes\ECC4UTS_0922_Ref.txt ^
        ScanData\ChkRes\ECC4FTS_0922.txt ScanData\ChkRes\ECC4FTS_0922_Ref.txt

Pass any number of ChkRes.txt for the same ECC - typically the 4 combinations
of UTS/FTS x normal(IMG)/"_Ref", but 1 or 2 also work (order does not
matter; each file is identified by its own filename, same rule as
move_retake_dirs.py: "ECC<n><UTS|FTS>..." prefix, "_Ref" substring marks
the Reference file - UTS vs FTS makes no difference here since the source
TrackList below isn't split by scan type). If an (Event, PL) is judged
"k:Retake" or "l:?" in ANY of the given files, it is extracted.

The source is <repo>\\TrackList\\ECC<n>\\PL???.yaml (one file per PL, each
holding a flat YAML list of entries; every entry's "SaveTo:" field encodes
its Event and PL, and whether it is a real/extrapolated entry
(".../IMG/...") or its paired Reference entry (".../Ref/IMG/...")).
--tracklist-root overrides the "<repo>\\TrackList" base.

For every flagged (Event, PL), ALL of its entries in the source PL???.yaml
are copied to <output_dir>\\PL???.yaml, byte-for-byte - since the real/
extrapolated entry and its Reference entry share the same Event+PL, this
naturally keeps the pair together (never just one half of it) without any
extra logic. Entries for other, non-flagged Events in the same source file
are left out. PL numbers with nothing flagged produce no output file.
"""
import argparse
import os
import re
import sys

RETAKE_CHOICE = "k:Retake"
CHK_CHOICE = "l:?"
FLAGGED_CHOICES = (RETAKE_CHOICE, CHK_CHOICE)

CHKRES_FILENAME_PATTERN = re.compile(r"ECC(\d+)(UTS|FTS)")
ENTRY_SPLIT_PATTERN = re.compile(r"(?=^  - Plate: )", re.MULTILINE)
SAVETO_PATTERN = re.compile(r"SaveTo:\s*\"?([^\r\n\"]*)")
EVENT_PL_PATTERN = re.compile(r"Event(\d+)[\\/]PL(\d+)")


def parse_ecc_num(chkres_path):
    m = CHKRES_FILENAME_PATTERN.match(os.path.basename(chkres_path))
    if not m:
        raise ValueError(f"ECC番号がファイル名から読み取れません: {chkres_path}")
    return m.group(1)


def collect_flagged(chkres_paths):
    """Returns set of (event:int, pl:int) flagged k:Retake/l:? in any of the given files."""
    flagged = set()
    for path in chkres_paths:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 2:
                    continue
                rel_pl_dir, choice = parts
                if choice not in FLAGGED_CHOICES:
                    continue
                m = re.match(r"Event(\d+)/PL(\d+)$", rel_pl_dir)
                if not m:
                    continue
                flagged.add((int(m.group(1)), int(m.group(2))))
    return flagged


def split_entries(text):
    return [b for b in ENTRY_SPLIT_PATTERN.split(text) if b.strip()]


def entry_event_pl(block):
    m = SAVETO_PATTERN.search(block)
    if not m:
        return None
    m2 = EVENT_PL_PATTERN.search(m.group(1))
    if not m2:
        return None
    return int(m2.group(1)), int(m2.group(2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_dir", help=r"e.g. TrackList_Retake\ECC4")
    parser.add_argument(
        "chkres_txt", nargs="+",
        help="ChkRes.txt file(s) for this ECC - typically all 4 of UTS/FTS x normal/_Ref",
    )
    parser.add_argument(
        "--tracklist-root",
        help=r'Override the source TrackList root (default: <this repo>\TrackList)',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be extracted, without writing any output files",
    )
    args = parser.parse_args()

    chkres_paths = [os.path.abspath(p) for p in args.chkres_txt]
    ecc_nums = {parse_ecc_num(p) for p in chkres_paths}
    if len(ecc_nums) != 1:
        print(f"Error: the given ChkRes.txt files don't agree on the ECC number: {ecc_nums}", file=sys.stderr)
        sys.exit(1)
    ecc_num = ecc_nums.pop()

    if args.tracklist_root:
        tracklist_root = os.path.abspath(args.tracklist_root)
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tracklist_root = os.path.join(repo_root, "TrackList")
    src_dir = os.path.join(tracklist_root, f"ECC{ecc_num}")
    output_dir = os.path.abspath(args.output_dir)

    print(f"ECC{ecc_num}")
    print(f"source TrackList : {src_dir}")
    print(f"output TrackList : {output_dir}")

    flagged = collect_flagged(chkres_paths)
    print(f"\n{len(flagged)} 件の (Event, PL) が k:Retake または l:? と判定されています。")

    by_pl = {}
    for event, pl in flagged:
        by_pl.setdefault(pl, set()).add(event)

    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)
    total_entries = 0
    not_found = []

    for pl in sorted(by_pl):
        events_wanted = by_pl[pl]
        src_path = os.path.join(src_dir, f"PL{pl:03d}.yaml")
        if not os.path.isfile(src_path):
            for event in sorted(events_wanted):
                not_found.append((event, pl))
            continue

        with open(src_path, "r", encoding="utf-8", newline="") as f:
            text = f.read()

        matched_blocks = []
        found_events = set()
        for block in split_entries(text):
            ep = entry_event_pl(block)
            if ep is None:
                continue
            event, block_pl = ep
            if block_pl == pl and event in events_wanted:
                matched_blocks.append(block)
                found_events.add(event)

        for event in sorted(events_wanted - found_events):
            not_found.append((event, pl))

        if matched_blocks:
            tag = "[DRY-RUN] " if args.dry_run else ""
            if not args.dry_run:
                out_path = os.path.join(output_dir, f"PL{pl:03d}.yaml")
                with open(out_path, "w", encoding="utf-8", newline="") as f:
                    f.write("".join(matched_blocks))
            print(f"  {tag}PL{pl:03d}.yaml: {len(matched_blocks)} エントリ ({len(found_events)} Event)")
            total_entries += len(matched_blocks)

    action = "出力する予定です(--dry-run)" if args.dry_run else f"を {output_dir} に出力しました"
    print(f"\nDone. {total_entries} エントリ{action}。")
    if not_found:
        print(f"{len(not_found)} 件の (Event, PL) がソースのTrackListに見つかりませんでした:")
        for event, pl in sorted(not_found):
            print(f"  Event{event:05d}/PL{pl:03d}")


if __name__ == "__main__":
    main()
