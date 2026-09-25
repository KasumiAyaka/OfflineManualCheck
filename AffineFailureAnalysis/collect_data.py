#!/usr/bin/env python3
"""Collect AffineParam (and other tomographic_images.json fields) for two
populations, for later comparison:

  FAIL : every (ecc, scan_type, is_ref, event, pl) whose LATEST
         check_quality.py judgment (from ScanData\\ChkRes\\*.txt) is
         "k:Retake" or "l:?", located wherever it currently physically
         sits - either already moved to ScanData\\PatternMatchFailed\\...
         (via move_retake_dirs.py), or still in its original
         ScanData\\<UTS|FTS>\\... location pending that move. PLUS any
         directory physically present under ScanData\\PatternMatchFailed
         that has no matching ChkRes record at all (a handful of older
         entries predate consistent ChkRes tracking).
  OK   : every Event?????/PL??? directory whose LATEST judgment is
         "j:OK", located under ScanData\\<UTS|FTS>\\... (or the
         chk_<UTS|FTS> variant).

Usage:
    python collect_data.py [--scandata-root DIR] [--out records.csv]

Output: one row per (ecc, scan_type, category, event, pl) directory, with
the raw AffineParam and other json fields. See analyze.py for how this is
turned into per-unique-scan statistics and plots.
"""
import argparse
import glob
import json
import os
import re
import sys

FILENAME_PATTERN = re.compile(r"ECC(\d+)(UTS|FTS)")
EVENT_PL_PATTERN = re.compile(r"^Event(\d+)/PL(\d+)(_chk)?$")

FIELDS = [
    "ecc", "scan_type", "category", "event", "pl", "judgment", "source_dir",
    "AffineParam_a", "AffineParam_b", "AffineParam_c", "AffineParam_d",
    "AffineParam_e", "AffineParam_f",
    "NumOfPics", "Gap", "PxLen", "ThickOfBase", "ThickOfEmul",
    "lens_StagePos_x", "lens_StagePos_y", "lens_SurfacePos",
    "stage_StagePos_x", "stage_StagePos_y", "stage_SurfacePos",
    "Track_ax", "Track_ay", "Track_x", "Track_y",
]


def read_json_record(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    a, b, c, dd, e, f_ = d["AffineParam"]
    surf = {s["Layer"]: s for s in d.get("Surfaces", [])}
    lens = surf.get("lens", {})
    stage = surf.get("stage", {})
    track = d.get("Track", [None, None, None, None])
    lens_pos = lens.get("StagePos", [None, None])
    stage_pos = stage.get("StagePos", [None, None])
    return {
        "AffineParam_a": a, "AffineParam_b": b, "AffineParam_c": c,
        "AffineParam_d": dd, "AffineParam_e": e, "AffineParam_f": f_,
        "NumOfPics": d.get("NumOfPics"), "Gap": d.get("Gap"), "PxLen": d.get("PxLen"),
        "ThickOfBase": d.get("ThickOfBase"), "ThickOfEmul": d.get("ThickOfEmul"),
        "lens_StagePos_x": lens_pos[0], "lens_StagePos_y": lens_pos[1],
        "lens_SurfacePos": lens.get("SurfacePos"),
        "stage_StagePos_x": stage_pos[0], "stage_StagePos_y": stage_pos[1],
        "stage_SurfacePos": stage.get("SurfacePos"),
        "Track_ax": track[0], "Track_ay": track[1], "Track_x": track[2], "Track_y": track[3],
    }


def scan_pattern_match_failed(scandata_root):
    """Every tomographic_images.json physically under ScanData/PatternMatchFailed.
    Returns {(ecc, scan_type, is_ref, event, pl): (judgment, dir_path)}."""
    found = {}
    base = os.path.join(scandata_root, "PatternMatchFailed")
    for json_path in glob.glob(os.path.join(base, "**", "tomographic_images.json"), recursive=True):
        rel = os.path.relpath(json_path, base)
        parts = rel.split(os.sep)
        # <scan_type>/ECC<n>/[Ref/]IMG/Event?????/PL???[_chk]/tomographic_images.json
        scan_type = parts[0]
        ecc = parts[1].replace("ECC", "")
        is_ref = parts[2].lower() == "ref"
        event_dir = parts[3 + (1 if is_ref else 0)]
        pl_dir = parts[4 + (1 if is_ref else 0)]
        event = int(re.sub(r"\D", "", event_dir))
        m = re.match(r"PL(\d+)(_chk)?$", pl_dir, re.IGNORECASE)
        pl = int(m.group(1))
        judgment = "l:?" if (m and m.group(2)) else "k:Retake"
        found[(ecc, scan_type, is_ref, event, pl)] = (judgment, os.path.dirname(json_path))
    return found


def find_fail_source_dir(scandata_root, ecc, scan_type, is_ref, event, pl, judgment):
    """Search for this entry's directory, wherever it currently sits:
    already moved to PatternMatchFailed (with the "_chk" suffix that
    move_retake_dirs.py adds for "l:?"), or still in its original
    ScanData/<UTS|FTS>/... location pending that move."""
    sub = os.path.join("Ref", "IMG") if is_ref else "IMG"
    pl_name = f"PL{pl:03d}" + ("_chk" if judgment == "l:?" else "")
    rel_leaf = os.path.join(f"Event{event:05d}", pl_name)

    candidate_bases = [os.path.join(scandata_root, "PatternMatchFailed", scan_type, f"ECC{ecc}")]
    for base in [
        os.path.join(scandata_root, scan_type, f"ECC{ecc}"),
        *sorted(glob.glob(os.path.join(scandata_root, f"chk_{scan_type}", f"ECC{ecc}*"))),
    ]:
        candidate_bases.append(base)

    for base in candidate_bases:
        candidate = os.path.join(base, sub, rel_leaf)
        if os.path.isfile(os.path.join(candidate, "tomographic_images.json")):
            return candidate
        if judgment == "l:?":
            # not-yet-moved originals never get the "_chk" suffix
            plain = os.path.join(base, sub, f"Event{event:05d}", f"PL{pl:03d}")
            if os.path.isfile(os.path.join(plain, "tomographic_images.json")):
                return plain
    return None


def collect_fail_rows(scandata_root, judgments):
    """Union of: (a) every ChkRes entry whose latest judgment is
    "k:Retake"/"l:?", located wherever it currently sits, and (b) every
    directory physically in PatternMatchFailed regardless of ChkRes
    coverage (a few older entries predate ChkRes tracking)."""
    on_disk = scan_pattern_match_failed(scandata_root)
    rows_by_key = {}
    not_found = []

    for (ecc, scan_type, is_ref, event, pl), (judgment, mtime, path) in judgments.items():
        if judgment not in ("k:Retake", "l:?"):
            continue
        src_dir = find_fail_source_dir(scandata_root, ecc, scan_type, is_ref, event, pl, judgment)
        if src_dir is None:
            not_found.append((ecc, scan_type, is_ref, event, pl, path))
            continue
        rows_by_key[(ecc, scan_type, is_ref, event, pl)] = (judgment, src_dir)

    # entries physically in PatternMatchFailed but with no ChkRes coverage at all
    for key, (judgment, src_dir) in on_disk.items():
        rows_by_key.setdefault(key, (judgment, src_dir))

    rows = []
    for (ecc, scan_type, is_ref, event, pl), (judgment, src_dir) in rows_by_key.items():
        json_path = os.path.join(src_dir, "tomographic_images.json")
        try:
            rec = read_json_record(json_path)
        except Exception as e:
            print(f"Skipping (parse error): {json_path}: {e}")
            continue
        category = "Ref/IMG" if is_ref else "IMG"
        row = {"ecc": ecc, "scan_type": scan_type, "category": category,
               "event": event, "pl": pl, "judgment": judgment, "source_dir": src_dir}
        row.update(rec)
        rows.append(row)

    if not_found:
        print(f"\n{len(not_found)} 件の k:Retake/l:? 判定について、現在の場所にディレクトリが見つかりませんでした:")
        for ecc, scan_type, is_ref, event, pl, path in not_found:
            cat = "Ref/IMG" if is_ref else "IMG"
            print(f"  ECC{ecc} {scan_type} {cat} Event{event:05d}/PL{pl:03d}  (from {os.path.basename(path)})")
    return rows


def load_chkres_judgments(scandata_root):
    """Returns {(ecc, scan_type, is_ref, event, pl): (judgment, mtime)} using
    the LATEST (by file mtime) verdict across all ChkRes/**/*.txt files
    (recursive - e.g. ChkRes/ECC6/*.txt archived-but-still-authoritative
    files, for a category with no newer top-level replacement, still get
    picked up; "latest mtime wins per key" makes this safe even when both
    an archived and a newer top-level file exist for the same entry)."""
    chkres_dir = os.path.join(scandata_root, "ChkRes")
    result = {}
    paths = sorted(glob.glob(os.path.join(chkres_dir, "**", "*.txt"), recursive=True))
    # process oldest -> newest so later files win ties naturally via dict overwrite,
    # but we still track mtime explicitly to be robust to filesystem mtime granularity
    paths_with_mtime = sorted((os.path.getmtime(p), p) for p in paths)
    for mtime, path in paths_with_mtime:
        name = os.path.basename(path)
        if "_chk_list" in name or "_missing" in name:
            continue
        m = FILENAME_PATTERN.match(name)
        if not m:
            continue
        ecc, scan_type = m.group(1), m.group(2)
        stem = os.path.splitext(name)[0]
        is_ref = "_Ref" in stem
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 2:
                    continue
                rel_pl_dir, judgment = parts
                em = re.match(r"^Event(\d+)/PL(\d+)$", rel_pl_dir)
                if not em:
                    continue
                event, pl = int(em.group(1)), int(em.group(2))
                key = (ecc, scan_type, is_ref, event, pl)
                prev = result.get(key)
                if prev is None or mtime >= prev[1]:
                    result[key] = (judgment, mtime, path)
    return result


def find_ok_source_dir(scandata_root, ecc, scan_type, is_ref, event, pl):
    """Search plausible source roots for this (ecc, scan_type) and return the
    directory path if a tomographic_images.json is found there, else None."""
    sub = os.path.join("Ref", "IMG") if is_ref else "IMG"
    rel_leaf = os.path.join(f"Event{event:05d}", f"PL{pl:03d}")

    candidate_bases = [os.path.join(scandata_root, scan_type, f"ECC{ecc}")]
    # also try chk_<scan_type>/ECC<n>* (date-suffixed variants such as ECC4_0918)
    candidate_bases += sorted(glob.glob(os.path.join(scandata_root, f"chk_{scan_type}", f"ECC{ecc}*")))

    for base in candidate_bases:
        candidate = os.path.join(base, sub, rel_leaf)
        json_path = os.path.join(candidate, "tomographic_images.json")
        if os.path.isfile(json_path):
            return candidate
    return None


def collect_ok_rows(scandata_root, judgments):
    rows = []
    not_found = []
    for (ecc, scan_type, is_ref, event, pl), (judgment, mtime, path) in judgments.items():
        if judgment != "j:OK":
            continue
        src_dir = find_ok_source_dir(scandata_root, ecc, scan_type, is_ref, event, pl)
        if src_dir is None:
            not_found.append((ecc, scan_type, is_ref, event, pl, path))
            continue
        json_path = os.path.join(src_dir, "tomographic_images.json")
        try:
            rec = read_json_record(json_path)
        except Exception as e:
            print(f"Skipping (parse error): {json_path}: {e}")
            continue
        category = "Ref/IMG" if is_ref else "IMG"
        row = {"ecc": ecc, "scan_type": scan_type, "category": category,
               "event": event, "pl": pl, "judgment": judgment, "source_dir": src_dir}
        row.update(rec)
        rows.append(row)

    if not_found:
        print(f"\n{len(not_found)} 件の j:OK 判定について、現在の場所にディレクトリが見つかりませんでした:")
        for ecc, scan_type, is_ref, event, pl, path in not_found:
            cat = "Ref/IMG" if is_ref else "IMG"
            print(f"  ECC{ecc} {scan_type} {cat} Event{event:05d}/PL{pl:03d}  (from {os.path.basename(path)})")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--scandata-root",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ScanData"),
        help=r"Default: <this repo>\ScanData",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.csv"),
    )
    args = parser.parse_args()

    scandata_root = os.path.abspath(args.scandata_root)
    print(f"ScanData root: {scandata_root}")

    judgments = load_chkres_judgments(scandata_root)

    fail_rows = collect_fail_rows(scandata_root, judgments)
    print(f"\nFAIL (ChkRes k:Retake/l:?、および PatternMatchFailed 直置き): {len(fail_rows)} 件のディレクトリ")

    ok_rows = collect_ok_rows(scandata_root, judgments)
    print(f"\nOK (ChkRes j:OK, 現存): {len(ok_rows)} 件のディレクトリ")

    all_rows = fail_rows + ok_rows
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})

    print(f"\n合計 {len(all_rows)} 行を {args.out} に出力しました。")


if __name__ == "__main__":
    main()
