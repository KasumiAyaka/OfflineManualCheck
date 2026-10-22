#!/usr/bin/env python3
"""Compress the raw f<pl><1,2>_{thick,thin}_{0,1}.vxx files under every
Area<N>\\PL<nnn> directory, and remove duplicates that are already archived.

Usage:
    python compress_vxx.py <path> [options]

Example:
    python compress_vxx.py I:\\NINJA\\E71a\\ECC6
    python compress_vxx.py I:\\NINJA\\E71a\\ECC6 --dry-run
    python compress_vxx.py I:\\NINJA\\E71a\\ECC6 --area-start 1 --area-end 6 --pl-start 1 --pl-end 133

For every <path>\\Area<area>\\PL<pl> directory (area/PL range configurable via
--area-start/--area-end/--pl-start/--pl-end, default 1-6 / 1-133), checks the
following 8 files, where <pl> is that directory's own zero-padded plate
number (e.g. for PL097: f0971_thick_0.vxx, f0972_thin_1.vxx, ...):
    f<pl>1_thick_0.vxx, f<pl>1_thick_1.vxx, f<pl>1_thin_0.vxx, f<pl>1_thin_1.vxx
    f<pl>2_thick_0.vxx, f<pl>2_thick_1.vxx, f<pl>2_thin_0.vxx, f<pl>2_thin_1.vxx

For each one that is found:
  - if no "<name>.7z" archive exists yet, it is compressed (the raw file is
    removed once the archive is written successfully).
  - if a "<name>.7z" archive already exists, its CRC32 is checked against the
    raw file and, once they match, only the raw file is deleted (the archive
    is kept as-is).

After a full run, each of the 8 names should exist only as "<name>.7z";
the raw ".vxx" file should no longer be present.

Compression/verification is delegated to file_7z_compress.py (the same
helper decompress_fvxx_for_crosscheck.py uses for the reverse operation),
which wraps py_compress.compress_7z().
"""
import argparse
import os
import subprocess
import sys

def filenames_for_pl(pl):
    names = []
    for cls in (1, 2):
        for kind in ("thick", "thin"):
            for side in (0, 1):
                names.append(f"f{pl:03d}{cls}_{kind}_{side}.vxx")
    return names


COMPRESS_SCRIPT = r"I:\prg\python\python_app\python_app\file_7z_compress.py"


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
    args = parser.parse_args()

    base = args.path
    if not os.path.isdir(base):
        print(f"Error: {base} is not a directory", file=sys.stderr)
        sys.exit(1)

    n_compressed = 0
    n_duplicate_removed = 0
    n_already_ok = 0
    n_not_found = 0
    n_failed = 0
    n_missing_dir = 0

    for area in range(args.area_start, args.area_end + 1):
        for pl in range(args.pl_start, args.pl_end + 1):
            pl_dir = os.path.join(base, f"Area{area}", f"PL{pl:03d}")

            if not os.path.isdir(pl_dir):
                print(f"[skip] no such directory: {pl_dir}")
                n_missing_dir += 1
                continue

            for filename in filenames_for_pl(pl):
                vxx_path = os.path.join(pl_dir, filename)
                archive_path = vxx_path + ".7z"
                vxx_exists = os.path.isfile(vxx_path)
                archive_exists = os.path.isfile(archive_path)

                if not vxx_exists and not archive_exists:
                    print(f"[not found] {vxx_path}")
                    n_not_found += 1
                    continue

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
    print(
        f"\nDone. {n_compressed} file(s) {action}, "
        f"{n_duplicate_removed} duplicate(s) removed, "
        f"{n_already_ok} already archived-only, "
        f"{n_not_found} not found, "
        f"{n_missing_dir} directory(ies) missing, "
        f"{n_failed} failed."
    )


if __name__ == "__main__":
    main()
