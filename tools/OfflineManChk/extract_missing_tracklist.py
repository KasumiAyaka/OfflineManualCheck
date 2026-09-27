#!/usr/bin/env python3
"""Build a re-scan TrackList from a check_rawidmap_images.py "_missing.txt".

Usage:
    python extract_missing_tracklist.py <output_dir> <btrklist<n>_rawidmap_missing.txt> <tracklist_dir>
        [--add-csv FAIL.csv ...] [--compare-dir DIR] [--dry-run]

Example (ECC4, using the corrected TrackList ECC4TrkLst2):
    python tools\\OfflineManChk\\extract_missing_tracklist.py RetakeTrackList\\ECC4_missing ^
        OfflineManualChecking_LoggingTool\\TrackListForOfflineManChk\\btrklist4_rawidmap_missing.txt ^
        ECC4TrkLst2 --compare-dir TrackList\\ECC4

The missing list (output of check_rawidmap_images.py) is a repetition of
    Event:<event> PL<pl of the real track>
    IMG:PL???,PL???      (optional; real/extrapolated images not found)
    Ref:PL???,PL???      (optional; Reference images not found)
Every (Event, PL) appearing in IMG: or Ref: is a re-scan target. Since the
real/extrapolated entry and its Reference entry are one pair, ALL entries of
that Event+PL in <tracklist_dir>\\PL???.yaml are copied byte-for-byte (so an
IMG-only or Ref-only miss still re-scans the whole pair), exactly like
extract_retake_tracklist.py does. Output goes to <output_dir>\\PL???.yaml.
If the source holds more than one pair for the same Event+PL, pairs whose
values differ are all kept; only a pair that is an exact duplicate of an
earlier one (same IMG and Ref entries) is dropped.

--add-csv merges in extra targets from a failure CSV (e.g. the output of
AffineFailureAnalysis\\predict_ecc_failures.py, columns "event" and "pl";
"category" IMG / Ref/IMG is recorded like the missing list's IMG:/Ref:).
Targets from both sources are de-duplicated per (Event, PL).

<tracklist_dir> is the TrackList the values are taken from (e.g. the corrected
ECC4TrkLst2). With --compare-dir (e.g. the original TrackList\\ECC4), each
extracted entry is compared against the same Event+PL+kind entry there and
the differences are reported (expected: IMG identical, Ref changed).
"""
import argparse
import csv
import os
import re
import sys

from extract_retake_tracklist import split_entries, SAVETO_PATTERN, EVENT_PL_PATTERN

EVENT_LINE_PATTERN = re.compile(r"^Event:(\d+)\s+PL(\d+)\s*$")
KIND_LINE_PATTERN = re.compile(r"^(IMG|Ref):(.*)$")


def parse_missing(path):
    """Returns (targets, detail): targets = set of (event, pl); detail[(event, pl)] = set of kinds missing."""
    detail = {}
    event = None
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            m = EVENT_LINE_PATTERN.match(line)
            if m:
                event = int(m.group(1))
                continue
            m = KIND_LINE_PATTERN.match(line)
            if m and event is not None:
                for tok in m.group(2).split(","):
                    tok = tok.strip()
                    if not tok:
                        continue
                    m2 = re.fullmatch(r"PL(\d+)", tok)
                    if not m2:
                        raise ValueError(f"{path}:{lineno}: PL表記が不正です: {tok}")
                    detail.setdefault((event, int(m2.group(1))), set()).add(m.group(1))
                continue
            raise ValueError(f"{path}:{lineno}: 解釈できない行です: {line}")
    return detail


def parse_fail_csv(path, detail):
    """Adds (event, pl) of every row of a failure CSV into detail; returns the set of pairs read."""
    pairs = set()
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = (int(row["event"]), int(row["pl"]))
            kind = "Ref" if row.get("category", "").startswith("Ref") else "IMG"
            detail.setdefault(key, set()).add(kind)
            pairs.add(key)
    return pairs


def entry_key(block):
    """(event, pl, kind) of a YAML entry, kind = 'Ref' or 'IMG'."""
    m = SAVETO_PATTERN.search(block)
    if not m:
        return None
    save_to = m.group(1)
    m2 = EVENT_PL_PATTERN.search(save_to)
    if not m2:
        return None
    kind = "Ref" if re.search(r"[\\/]Ref[\\/]IMG[\\/]", save_to) else "IMG"
    return int(m2.group(1)), int(m2.group(2)), kind


def read_blocks(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return split_entries(f.read())


def norm(block):
    return block.replace("\r\n", "\n").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_dir", help=r"e.g. RetakeTrackList\ECC4_missing")
    parser.add_argument("missing_txt", help="btrklist<n>_rawidmap_missing.txt")
    parser.add_argument("tracklist_dir", help=r"TrackList to take the entries from, e.g. ECC4TrkLst2")
    parser.add_argument("--add-csv", action="append", default=[],
                        help="failure CSV (columns event, pl) to merge in; can be given more than once")
    parser.add_argument("--compare-dir", help=r"TrackList to compare against, e.g. TrackList\ECC4")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing")
    args = parser.parse_args()

    src_dir = os.path.abspath(args.tracklist_dir)
    output_dir = os.path.abspath(args.output_dir)
    cmp_dir = os.path.abspath(args.compare_dir) if args.compare_dir else None
    if os.path.normcase(output_dir) == os.path.normcase(src_dir):
        print("Error: output_dir と tracklist_dir が同じです", file=sys.stderr)
        sys.exit(1)

    detail = parse_missing(args.missing_txt)
    missing_pairs = set(detail)
    csv_pairs = set()
    for path in args.add_csv:
        csv_pairs |= parse_fail_csv(path, detail)
    print(f"missing list     : {os.path.abspath(args.missing_txt)}")
    print(f"source TrackList : {src_dir}")
    if cmp_dir:
        print(f"compare TrackList: {cmp_dir}")
    print(f"output TrackList : {output_dir}")
    if args.add_csv:
        print(f"add CSV          : {', '.join(os.path.abspath(p) for p in args.add_csv)}")
        print(f"\nmissing {len(missing_pairs)} 件 + CSV {len(csv_pairs)} 件 "
              f"(重複 {len(missing_pairs & csv_pairs)} 件) -> 合計 {len(detail)} 件")
        only_csv = sorted(csv_pairs - missing_pairs)
        print(f"CSVのみの (Event, PL): {len(only_csv)} 件")
        for event, pl in only_csv:
            print(f"  Event{event:05d}/PL{pl:03d}")

    kinds_count = {}
    for kinds in detail.values():
        k = "+".join(sorted(kinds))
        kinds_count[k] = kinds_count.get(k, 0) + 1
    print(f"\n{len(set(e for e, _ in detail))} Event, {len(detail)} 件の (Event, PL) が再スキャン対象です "
          f"(内訳: " + ", ".join(f"{k}: {v}" for k, v in sorted(kinds_count.items())) + ")")

    by_pl = {}
    for event, pl in detail:
        by_pl.setdefault(pl, set()).add(event)

    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)
    total_entries = 0
    not_found = []
    incomplete = []
    multi_pair = []
    dup_pairs = []
    n_same = {"IMG": 0, "Ref": 0}
    diffs = []

    for pl in sorted(by_pl):
        events_wanted = by_pl[pl]
        src_path = os.path.join(src_dir, f"PL{pl:03d}.yaml")
        if not os.path.isfile(src_path):
            not_found.extend((e, pl) for e in sorted(events_wanted))
            continue

        cmp_entries = {}
        if cmp_dir:
            cmp_path = os.path.join(cmp_dir, f"PL{pl:03d}.yaml")
            if os.path.isfile(cmp_path):
                for b in read_blocks(cmp_path):
                    key = entry_key(b)
                    if key:
                        cmp_entries.setdefault(key, []).append(b)

        selected = []
        found_kinds = {}
        for block in read_blocks(src_path):
            key = entry_key(block)
            if key is None:
                continue
            event, block_pl, kind = key
            if block_pl != pl or event not in events_wanted:
                continue
            selected.append((key, block))
            found_kinds.setdefault(event, []).append(kind)

        # 実在・外挿(IMG)+直後のReference(Ref)を1組とし、同じEventで中身が完全に
        # 同じ組は1つだけ残す(値が違う組はすべて残す)。
        matched = []
        kept_pairs = {}
        i = 0
        while i < len(selected):
            (event, _, kind), block = selected[i]
            if kind == "IMG" and i + 1 < len(selected) and selected[i + 1][0] == (event, pl, "Ref"):
                group = selected[i:i + 2]
            else:
                group = selected[i:i + 1]
            i += len(group)
            sig = tuple(norm(b) for _, b in group)
            if sig in kept_pairs.setdefault(event, set()):
                dup_pairs.append((event, pl))
                continue
            kept_pairs[event].add(sig)
            for key, block in group:
                matched.append(block)
                if not cmp_dir:
                    continue
                kind = key[2]
                olds = cmp_entries.get(key)
                if not olds:
                    diffs.append((event, pl, kind, None, block))
                elif any(norm(o) == norm(block) for o in olds):
                    n_same[kind] += 1
                else:
                    diffs.append((event, pl, kind, olds[0], block))

        for event in sorted(events_wanted):
            n_kept = len(kept_pairs.get(event, ()))
            if n_kept > 1:
                multi_pair.append((event, pl, n_kept))

        for event in sorted(events_wanted):
            kinds = found_kinds.get(event)
            if not kinds:
                not_found.append((event, pl))
            elif kinds != ["IMG", "Ref"] * (len(kinds) // 2):
                incomplete.append((event, pl, kinds))

        if matched:
            if not args.dry_run:
                with open(os.path.join(output_dir, f"PL{pl:03d}.yaml"), "w", encoding="utf-8", newline="") as f:
                    f.write("".join(matched))
            tag = "[DRY-RUN] " if args.dry_run else ""
            print(f"  {tag}PL{pl:03d}.yaml: {len(matched)} エントリ ({len(found_kinds)} Event)")
            total_entries += len(matched)

    action = "出力する予定です(--dry-run)" if args.dry_run else f"を {output_dir} に出力しました"
    print(f"\nDone. {total_entries} エントリ{action}。")
    if not_found:
        print(f"\n{len(not_found)} 件の (Event, PL) がソースのTrackListに見つかりませんでした:")
        for event, pl in sorted(not_found):
            print(f"  Event{event:05d}/PL{pl:03d}")
    if incomplete:
        print(f"\n{len(incomplete)} 件の (Event, PL) で実在/外挿とReferenceの組が揃っていません:")
        for event, pl, kinds in sorted(incomplete):
            print(f"  Event{event:05d}/PL{pl:03d}: {kinds}")
    if multi_pair:
        print(f"\n{len(multi_pair)} 件の (Event, PL) は値の違う組が複数あります(すべて出力):")
        for event, pl, n in sorted(multi_pair):
            print(f"  Event{event:05d}/PL{pl:03d}: {n} 組")
    if dup_pairs:
        print(f"\n{len(dup_pairs)} 組は同じ (Event, PL) の中身が完全に同じ組の重複なので除きました:")
        for event, pl in sorted(dup_pairs):
            print(f"  Event{event:05d}/PL{pl:03d}")
    if cmp_dir:
        print(f"\n比較結果 (vs {cmp_dir}): 一致 IMG {n_same['IMG']} / Ref {n_same['Ref']}, 相違 {len(diffs)}")
        diff_kinds = {}
        for d in diffs:
            diff_kinds[d[2]] = diff_kinds.get(d[2], 0) + 1
        if diffs:
            print("  相違の内訳: " + ", ".join(f"{k}: {v}" for k, v in sorted(diff_kinds.items())))
        for event, pl, kind, old, new in sorted(diffs, key=lambda d: (d[2] != "IMG", d[0], d[1])):
            if kind == "IMG" or old is None:
                print(f"  [{kind}] Event{event:05d}/PL{pl:03d}")
                print("    old: " + (" | ".join(norm(old).splitlines()) if old else "(none)"))
                print("    new: " + " | ".join(norm(new).splitlines()))


if __name__ == "__main__":
    main()
