#!/usr/bin/env python3
# org script path:C:\Users\kasumi\AppData\Local\Temp\4\claude\D--NINJA-E71a-ECC5\4ef6bd43-888f-47f1-b43c-f596feefcffd\scratchpad\cleanup_vxx.py
"""Delete f0??2_thick_0.vxx files that already have a .7z archive.

Usage:
    python cleanup_vxx.py <path> [--dry-run]

Example:
    python cleanup_vxx.py D:\\NINJA\\E71a\\ECC5
    python cleanup_vxx.py D:\\NINJA\\E71a\\ECC5 --dry-run

For every file matching "f0??2_thick_0.vxx" found recursively under
<path> (e.g. under Area1..6/PL001..133), if a sibling archive named
"<same file>.7z" also exists in the same directory, the .vxx file is
deleted. Directories where only the .vxx file exists (no .7z) are left
untouched.
"""
import argparse
import sys
from pathlib import Path

PATTERN = "f0??2_thick_0.vxx"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help=r"Base directory, e.g. D:\NINJA\E71a\ECC5")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list the files that would be deleted, without deleting them",
    )
    args = parser.parse_args()

    base = Path(args.path)
    if not base.is_dir():
        print(f"Error: {base} is not a directory", file=sys.stderr)
        sys.exit(1)

    deleted = 0
    skipped = 0

    for vxx_path in sorted(base.rglob(PATTERN)):
        if not vxx_path.is_file():
            continue

        archive_path = vxx_path.with_name(vxx_path.name + ".7z")
        if archive_path.is_file():
            if args.dry_run:
                print(f"[DRY-RUN] Would delete: {vxx_path}")
            else:
                vxx_path.unlink()
                print(f"Deleted: {vxx_path}")
            deleted += 1
        else:
            print(f"Skipped (no .7z found): {vxx_path}")
            skipped += 1

    action = "would be deleted" if args.dry_run else "deleted"
    print(f"\nDone. {deleted} file(s) {action}, {skipped} file(s) left untouched.")


if __name__ == "__main__":
    main()
