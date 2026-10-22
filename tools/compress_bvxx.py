#!/usr/bin/env python3
"""Compress the raw b<pl>*.vxx files (Beta track files) under every
Area<N>\\PL<nnn> directory, and remove duplicates that are already archived.

Usage:
    python compress_bvxx.py <path> [options]

Example:
    python compress_bvxx.py I:\\NINJA\\E71a\\ECC6
    python compress_bvxx.py I:\\NINJA\\E71a\\ECC6 --dry-run
    python compress_bvxx.py I:\\NINJA\\E71a\\ECC6 --area-start 1 --area-end 6 --pl-start 1 --pl-end 133
    python compress_bvxx.py I:\\NINJA\\E71a\\ECC6 --cor-only --dry-run

For every <path>\\Area<area>\\PL<pl> directory (area/PL range configurable via
--area-start/--area-end/--pl-start/--pl-end, default 1-6 / 1-133), finds every
file matching "b<pl>[._]*.vxx" that currently exists either raw or already
archived (<pl> is that directory's own zero-padded plate number), e.g. for
PL097: b097.sel.vxx, b097_thick.vxx, b097_thick_0.sel.vxx, b097_thin_3.vxx, ...

"b<pl>.sel.cor.vxx" is excluded and never touched (left as-is, uncompressed)
by default. Pass --cor-only to instead process ONLY "b<pl>.sel.cor.vxx"
(every other b<pl>*.vxx file is then left untouched).

For each matching file found:
  - if no "<name>.7z" archive exists yet, it is compressed (the raw file is
    removed once the archive is written successfully).
  - if a "<name>.7z" archive already exists, its CRC32 is checked against the
    raw file and, once they match, only the raw file is deleted (the archive
    is kept as-is).

Compression/verification is delegated to file_7z_compress.py (same helper
compress_vxx.py uses for the f<pl>* files), which wraps
py_compress.compress_7z().
"""
import argparse
import glob
import os
import subprocess
import sys

COMPRESS_SCRIPT = r"I:\prg\python\python_app\python_app\file_7z_compress.py"
EXCLUDE_SUFFIX = ".sel.cor.vxx"


def find_target_names(pl_dir, pl, cor_only=False):
    """Return sorted unique "<name>.vxx" basenames (raw or already-archived)
    found in pl_dir. By default excludes EXCLUDE_SUFFIX; if cor_only is
    True, returns ONLY names ending with EXCLUDE_SUFFIX."""
    pattern = os.path.join(pl_dir, f"b{pl:03d}[._]*.vxx*")
    names = set()
    for path in glob.glob(pattern):
        name = os.path.basename(path)
        if name.endswith(".7z"):
            name = name[: -len(".7z")]
        if not name.endswith(".vxx"):
            continue
        if cor_only:
            if not name.endswith(EXCLUDE_SUFFIX):
                continue
        else:
            if name.endswith(EXCLUDE_SUFFIX):
                continue
        names.add(name)
    return sorted(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help=r"Base directory, e.g. I:\NINJA\E71a\ECC6")
    parser.add_argument("--area-start", type=int, default=1)
    parser.add_argument("--area-end", type=int, default=6)
    parser.add_argument("--pl-start", type=int, default=1)
    parser.add_argument("--pl-end", type=int, default=133)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list what would be done, without compressing/deleting anything",
    )
    parser.add_argument(
        "--cor-only",
        action="store_true",
        help=f'Process ONLY "b<pl>{EXCLUDE_SUFFIX}" files, instead of excluding them',
    )
    args = parser.parse_args()

    base = args.path
    if not os.path.isdir(base):
        print(f"Error: {base} is not a directory", file=sys.stderr)
        sys.exit(1)

    n_compressed = 0
    n_duplicate_removed = 0
    n_already_ok = 0
    n_failed = 0
    n_missing_dir = 0

    for area in range(args.area_start, args.area_end + 1):
        for pl in range(args.pl_start, args.pl_end + 1):
            pl_dir = os.path.join(base, f"Area{area}", f"PL{pl:03d}")

            if not os.path.isdir(pl_dir):
                print(f"[skip] no such directory: {pl_dir}")
                n_missing_dir += 1
                continue

            for filename in find_target_names(pl_dir, pl, cor_only=args.cor_only):
                vxx_path = os.path.join(pl_dir, filename)
                archive_path = vxx_path + ".7z"
                vxx_exists = os.path.isfile(vxx_path)
                archive_exists = os.path.isfile(archive_path)

                if archive_exists and not vxx_exists:
                    n_already_ok += 1
                    continue

                if args.dry_run:
                    if archive_exists:
                        print(f"[DRY-RUN] would verify CRC32 and delete: {vxx_path}")
                        n_duplicate_removed += 1
                    else:
                        print(f"[DRY-RUN] would compress: {vxx_path}")
                        n_compressed += 1
                    continue

                was_duplicate = archive_exists
                result = subprocess.run(
                    [sys.executable, COMPRESS_SCRIPT, filename],
                    cwd=pl_dir,
                )
                if result.returncode == 0:
                    if was_duplicate:
                        print(f"[duplicate removed] {vxx_path}")
                        n_duplicate_removed += 1
                    else:
                        print(f"[compressed] {vxx_path} -> {archive_path}")
                        n_compressed += 1
                else:
                    print(f"[FAILED] {vxx_path} (exit code {result.returncode})")
                    n_failed += 1

    action = "would be compressed" if args.dry_run else "compressed"
    scope_note = (
        f'(only "*{EXCLUDE_SUFFIX}" files were processed.)'
        if args.cor_only
        else f'("*{EXCLUDE_SUFFIX}" files were left untouched.)'
    )
    print(
        f"\nDone. {n_compressed} file(s) {action}, "
        f"{n_duplicate_removed} duplicate(s) removed, "
        f"{n_already_ok} already archived-only, "
        f"{n_missing_dir} directory(ies) missing, "
        f"{n_failed} failed. "
        f"{scope_note}"
    )


if __name__ == "__main__":
    main()
