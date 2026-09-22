#!/usr/bin/env python3
"""Convert a RetakeTrackList\\ECC<n> directory (extract_retake_tracklist.py's
output) directly into the same LaTeX macro format that btrklist_to_pl.py
produces from btrklist.txt.

Usage:
    python retake_tracklist_to_pl.py <RetakeTrackList\\ECC<n> dir> <ecc_number> [output.tex]

Each PL???.yaml in the input directory holds a flat YAML list of entries,
alternating in (muon, reference) pairs sharing the same Event:
    - Plate: <PL>
      RawID: <n>            # or "Track: [...]" if no real match was found
      Surface: Both
      SaveTo: G:ECC<n>/IMG/Event?????/PL???
    - Plate: <PL>
      RawID: <n>            # the paired reference track's own id
      Zone: <area>
      Surface: Both
      SaveTo: G:ECC<n>/Ref/IMG/Event?????/PL???

This pairing (and the fields used below) was verified against every
existing TrackList\\ECC<n>\\PL???.yaml / TrackList\\btrklist<n>.txt pair in
this repo (thousands of rows, zero exceptions):
  - entries strictly alternate muon(IMG) / reference(Ref/IMG)
  - the reference entry always has "RawID" and "Zone"; the muon entry's
    Zone (when present) always agrees with its reference's Zone
  - in btrklist.txt terms, the muon row's own "btrackid2" is a positive
    number whenever the muon has a RawID, and exactly 0 when it only has
    "Track" - never anything else - so only *whether* the muon has a
    RawID matters, not any further value (which btrklist.txt sources from
    a separate matching step this YAML does not carry)

From each pair this script derives exactly what btrklist_to_pl.py's
event_value() would have produced:
  - muon entry:      \\Event{eventid}{o}{area}   if it has a RawID
                      \\Event{eventid}{ }{area}   if it only has "Track"
  - reference entry: \\Event{<its RawID>}{ }{area}
(area = the reference entry's Zone). The rest of the formatting (AreaList,
the 34-entry EventList limit, the overflow \\Events{} block, CRLF output)
is produced by importing and reusing btrklist_to_pl.py's own functions
unchanged.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MakeLatexScript"))
import btrklist_to_pl as ltx

ENTRY_SPLIT_PATTERN = re.compile(r"(?=^  - Plate: )", re.MULTILINE)
RAWID_PATTERN = re.compile(r"RawID:\s*(-?\d+)")
ZONE_PATTERN = re.compile(r"Zone:\s*(-?\d+)")
SAVETO_PATTERN = re.compile(r"SaveTo:\s*\"?([^\r\n\"]*)")
EVENT_PATTERN = re.compile(r"Event(\d+)")
PL_FILENAME_PATTERN = re.compile(r"PL(\d+)\.yaml$", re.IGNORECASE)


def split_entries(text):
    return [b for b in ENTRY_SPLIT_PATTERN.split(text) if b.strip()]


def parse_entry(block):
    m = SAVETO_PATTERN.search(block)
    if not m:
        raise ValueError(f"SaveTo が見つかりません: {block!r}")
    saveto = m.group(1)
    is_ref = "/Ref/" in saveto
    event_m = EVENT_PATTERN.search(saveto)
    if not event_m:
        raise ValueError(f"SaveTo から Event が読み取れません: {saveto!r}")
    eventid = int(event_m.group(1))
    rawid_m = RAWID_PATTERN.search(block)
    rawid = int(rawid_m.group(1)) if rawid_m else None
    zone_m = ZONE_PATTERN.search(block)
    zone = int(zone_m.group(1)) if zone_m else None
    return {"is_ref": is_ref, "eventid": eventid, "rawid": rawid, "zone": zone}


def pairs_to_rows(entries, pl_path):
    """entries: parsed dicts, expected to alternate (muon, reference). Returns
    a list of synthetic (area, eventid, btrackid, btrackid2) 4-tuples that
    btrklist_to_pl.event_value() maps to the same (value, flag) as the real
    btrklist.txt pipeline would."""
    if len(entries) % 2 != 0:
        raise ValueError(f"{pl_path}: エントリ数が奇数で (muon, reference) のペアになりません ({len(entries)}件)")

    rows = []
    for i in range(0, len(entries), 2):
        muon, ref = entries[i], entries[i + 1]
        if muon["is_ref"] or not ref["is_ref"]:
            raise ValueError(
                f"{pl_path}: {i+1}番目のペアが (muon, reference) の順になっていません"
            )
        if muon["eventid"] != ref["eventid"]:
            raise ValueError(
                f"{pl_path}: {i+1}番目のペアのEventが muon={muon['eventid']} "
                f"reference={ref['eventid']} で一致しません"
            )
        if ref["zone"] is None:
            raise ValueError(f"{pl_path}: reference エントリに Zone がありません (Event{ref['eventid']:05d})")
        area = ref["zone"]
        eventid = ref["eventid"]

        if muon["rawid"] is not None:
            rows.append((area, eventid, muon["rawid"], 1))  # btrackid2=1 (>0の代表値): 実在→フラグ'o'
        else:
            rows.append((area, eventid, -1, 0))  # muonが Track のみ(実在なし)→フラグ' '

        rows.append((area, eventid, ref["rawid"], -1))  # reference行: btrackid2=-1で常にrefのRawIDを出力
    return rows


def convert(input_dir, ecc_num, output_path):
    pl_files = sorted(glob.glob(os.path.join(input_dir, "PL*.yaml")))
    if not pl_files:
        raise ValueError(f"PL???.yaml が見つかりません: {input_dir}")

    block_texts = []
    for pl_path in pl_files:
        m = PL_FILENAME_PATTERN.search(os.path.basename(pl_path))
        if not m:
            print(f"Skipping (PL番号が読み取れないファイル名): {pl_path}")
            continue
        pl = int(m.group(1))

        with open(pl_path, "r", encoding="utf-8") as f:
            text = f.read()
        entries = [parse_entry(b) for b in split_entries(text)]
        rows = pairs_to_rows(entries, pl_path)

        block_texts.append("\n".join(ltx.format_block(pl, rows, ecc_num)))
        print(f"  PL{pl:03d}.yaml: {len(entries)} エントリ ({len(entries)//2} ペア)")

    with open(output_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(block_texts))

    return len(pl_files)


def main():
    if len(sys.argv) < 3:
        print("Usage: python retake_tracklist_to_pl.py <RetakeTrackList\\ECC<n> dir> <ecc_number> [output.tex]")
        sys.exit(1)

    input_dir = os.path.abspath(sys.argv[1])
    ecc_num = int(sys.argv[2])
    if len(sys.argv) >= 4:
        output_path = os.path.abspath(sys.argv[3])
    else:
        base = os.path.basename(os.path.normpath(input_dir))
        output_path = os.path.join(os.path.dirname(os.path.normpath(input_dir)), f"{base}_conv.tex")

    print(f"ECC{ecc_num}")
    print(f"input : {input_dir}")
    print(f"output: {output_path}")

    n = convert(input_dir, ecc_num, output_path)
    print(f"\n{n} 個の PL ブロックを出力しました。")


if __name__ == "__main__":
    main()
