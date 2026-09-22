#!/usr/bin/env python3
"""Move PL directories judged "k:Retake" or "l:?" out of ScanData into PatternMatchFailed.

Usage:
    python move_retake_dirs.py <ChkRes.txt> [--src-dir DIR] [--dry-run] [--no-move-chk]

Example:
    python move_retake_dirs.py K:\\NINJA\\E71a\\ManualCheck\\ScanData\\ChkRes\\ECC4FTS_0922.txt
    python move_retake_dirs.py K:\\NINJA\\E71a\\ManualCheck\\ScanData\\ChkRes\\ECC4FTS_0922_Ref.txt

<ChkRes.txt> is check_quality.py's output: lines of
"Event?????/PL??? <choice>" (choice is one of j:OK / k:Retake / l:?).
The ECC number and UTS/FTS are read from the start of the file's own name
(e.g. "ECC4FTS_0922.txt" -> ECC4, FTS). Whether this ChkRes.txt is for the
normal (IMG) images or the Reference (Ref/IMG) images is read from whether
"_Ref" appears anywhere in the filename (e.g. "ECC4FTS_0922_Ref.txt" or the
older "ECC4FTS_Ref0922.txt" both count).

The source root is normally auto-detected as whichever of
    <ScanData>/<UTS|FTS>/ECC<n>/[Ref/]IMG
    <ScanData>/chk_<UTS|FTS>/ECC<n>/[Ref/]IMG
exists (the "Ref/" segment included only when the filename says so; which
of the two bases holds the checked images has varied between ECCs in this
dataset). If --src-dir is given instead, it is used directly as the sole
source root - but it must itself end in ".../Ref/IMG" or ".../IMG" matching
what the filename says; if it does not, this is treated as a probable
mistake: a warning is printed and the program exits without moving
anything.

For every line whose choice is "k:Retake", the corresponding directory is
moved to:
    <ScanData>/PatternMatchFailed/<UTS|FTS>/ECC<n>/[Ref/]IMG/Event?????/PL???
(<ScanData> is taken to be the parent of the ChkRes.txt's directory; the
destination's IMG-vs-Ref/IMG always matches the source's.)

A line whose choice is "l:?" is moved the same way, but the PL folder has
a "_chk" suffix appended at the destination (e.g. "PL025" -> "PL025_chk"),
so it's easy to tell "Retake" and "?" entries apart once both are sitting
in PatternMatchFailed. Pass --no-move-chk to instead leave "l:?" entries
where they are: their source directory paths are written, one per line,
to "<ChkRes.txt stem>_chk_list.txt" next to <ChkRes.txt>.
"""
import argparse
import os
import re
import shutil
import sys

RETAKE_CHOICE = "k:Retake"
CHK_CHOICE = "l:?"
CHK_SUFFIX = "_chk"
FILENAME_PATTERN = re.compile(r"ECC(\d+)(UTS|FTS)")


def parse_chkres_filename(chkres_path):
    """Returns (ecc_num, scan_type, is_ref) read from the ChkRes.txt filename."""
    name = os.path.basename(chkres_path)
    m = FILENAME_PATTERN.match(name)
    if not m:
        raise ValueError(f"ECC番号/UTS・FTSの区別がtxtファイル名から読み取れません: {name}")
    ecc_num, scan_type = m.group(1), m.group(2)
    stem = os.path.splitext(name)[0]
    is_ref = "_Ref" in stem
    return ecc_num, scan_type, is_ref


def path_is_ref(path):
    """True if path's own last two components look like ".../Ref/IMG"."""
    parts = [p for p in os.path.normpath(path).split(os.sep) if p]
    return len(parts) >= 2 and parts[-1].lower() == "img" and parts[-2].lower() == "ref"


def find_dir(roots, rel_parts):
    for root in roots:
        candidate = os.path.join(root, *rel_parts)
        if os.path.isdir(candidate):
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chkres_txt", help=r"e.g. ...\ScanData\ChkRes\ECC4FTS_0922.txt")
    parser.add_argument(
        "--src-dir",
        help=(
            "Explicitly specify the source root directory directly (instead of "
            "auto-detecting it). Must itself end in Ref/IMG or IMG matching what "
            "the ChkRes.txt filename says, or the program exits with a warning."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be moved, without moving anything",
    )
    parser.add_argument(
        "--no-move-chk",
        action="store_true",
        help=(
            "For \"l:?\" entries, just print \"Event?????/PL???\" instead of "
            "renaming/moving the directory (k:Retake entries are unaffected)"
        ),
    )
    args = parser.parse_args()

    chkres_path = os.path.abspath(args.chkres_txt)
    ecc_num, scan_type, is_ref = parse_chkres_filename(chkres_path)
    category = "Ref/IMG" if is_ref else "IMG"
    sub = os.path.join("Ref", "IMG") if is_ref else "IMG"

    # <ScanData>/ChkRes/xxx.txt -> <ScanData>
    scan_data_root = os.path.dirname(os.path.dirname(chkres_path))

    if args.src_dir:
        src_dir_abs = os.path.abspath(args.src_dir)
        actual_is_ref = path_is_ref(src_dir_abs)
        if actual_is_ref != is_ref:
            actual_category = "Ref/IMG" if actual_is_ref else "IMG"
            print(
                f"警告: --src-dir で指定されたディレクトリは {actual_category} ですが、"
                f"ChkRes.txt ({os.path.basename(chkres_path)}) は {category} を示しています。"
                f"一致しないため処理を中止します。",
                file=sys.stderr,
            )
            print(f"  --src-dir: {src_dir_abs}", file=sys.stderr)
            sys.exit(1)
        src_roots = [src_dir_abs]
    else:
        src_roots = [
            os.path.join(scan_data_root, scan_type, f"ECC{ecc_num}", sub),
            os.path.join(scan_data_root, f"chk_{scan_type}", f"ECC{ecc_num}", sub),
        ]
    dst_root = os.path.join(scan_data_root, "PatternMatchFailed", scan_type, f"ECC{ecc_num}", sub)

    print(f"ECC{ecc_num} {scan_type} ({category})")
    print("  source candidates:")
    for r in src_roots:
        print(f"    {r} ({'exists' if os.path.isdir(r) else 'not found'})")
    print(f"  destination: {dst_root}")
    if not any(os.path.isdir(r) for r in src_roots):
        print("Error: none of the source directories above exist", file=sys.stderr)
        sys.exit(1)

    moved = 0
    listed = 0
    chk_log_paths = []
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
            if choice not in (RETAKE_CHOICE, CHK_CHOICE):
                continue

            rel_parts = rel_pl_dir.split("/")
            src_dir = find_dir(src_roots, rel_parts)
            if src_dir is None:
                skipped_missing.append(rel_pl_dir)
                continue

            if choice == CHK_CHOICE and args.no_move_chk:
                print(f"[?] {rel_pl_dir} -> {src_dir}")
                chk_log_paths.append(src_dir)
                listed += 1
                continue

            dst_parts = list(rel_parts)
            if choice == CHK_CHOICE:
                dst_parts[-1] = dst_parts[-1] + CHK_SUFFIX
            dst_dir = os.path.join(dst_root, *dst_parts)

            if os.path.exists(dst_dir):
                skipped_existing.append(rel_pl_dir)
                continue

            label = "/".join(dst_parts)
            if args.dry_run:
                print(f"[DRY-RUN] Would move: {rel_pl_dir} -> {label}")
            else:
                os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
                shutil.move(src_dir, dst_dir)
                print(f"Moved: {rel_pl_dir} -> {label}")
            moved += 1

    action = "would be moved" if args.dry_run else "moved"
    print(f"\nDone. {moved} director(ies) {action}.")
    if args.no_move_chk:
        print(f"{listed} \"l:?\" entries listed (not moved).")
        if chk_log_paths:
            stem = os.path.splitext(os.path.basename(chkres_path))[0]
            log_path = os.path.join(os.path.dirname(chkres_path), f"{stem}_chk_list.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                for p in chk_log_paths:
                    f.write(p + "\n")
            print(f"Wrote {len(chk_log_paths)} \"l:?\" directory path(s) to {log_path}")
    if skipped_missing:
        print(f"{len(skipped_missing)} Retake/? entries had no source directory:")
        for name in skipped_missing:
            print(" ", name)
    if skipped_existing:
        print(f"{len(skipped_existing)} Retake/? entries already exist at the destination (left untouched):")
        for name in skipped_existing:
            print(" ", name)


if __name__ == "__main__":
    main()
