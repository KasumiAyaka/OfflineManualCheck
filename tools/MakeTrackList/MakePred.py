#!/usr/bin/env python3
"""
mkpred.awk の Python版。

使い方:
    python MakePred.py <input_directory> <ECC番号> <output_file>

例:
    python MakePred.py K:\\NINJA\\E71a\\ManualCheck\\Pred\\water 6 TrackList_ECC6.txt
"""

import os
import sys


def process_file(input_file, ecc_num, fout):
    gid = 0
    flg = 0

    with open(input_file, "r") as fin:
        for line in fin:
            fields = line.split()
            nf = len(fields)

            if nf == 4:
                # 例: "groupid:  10264, ntrk:  6" -> $2 = "10264,"
                gid = int(fields[1].rstrip(","))

            if nf == 14:
                flg = 0
                if int(fields[3]) == 0:
                    flg = 1
                if flg > 0:
                    plate = int(fields[5])
                    rawid = int(fields[6])
                    fout.write("  - Plate: %d\n" % plate)
                    fout.write("    RawID: %d\n" % rawid)
                    fout.write("    Surface: Both\n")
                    fout.write(
                        "    SaveTo: \"G:ECC%d/IMG/Event%05d/PL%03d\"\n"
                        % (ecc_num, gid, plate)
                    )

            if nf == 13:
                if flg > 0:
                    plate = int(fields[0])
                    zone = int(fields[1])
                    fout.write("  - Plate: %d\n" % plate)
                    fout.write(
                        "    Track: [%.4f,%.4f,%.1f,%.1f]\n"
                        % (
                            float(fields[3]),
                            float(fields[4]),
                            float(fields[5]),
                            float(fields[6]),
                        )
                    )
                    fout.write("    Zone: %d\n" % zone)
                    fout.write("    Surface: Both\n")
                    fout.write(
                        "    SaveTo: \"G:ECC%d/Ref/Event%05d/PL%03d\"\n"
                        % (ecc_num, gid, plate)
                    )


def main():
    if len(sys.argv) != 4:
        sys.stderr.write(
            "Usage: python MakePred.py <input_directory> <ECC_number> <output_file>\n"
        )
        sys.exit(1)

    input_dir = sys.argv[1]
    ecc_num = int(sys.argv[2])
    output_file = sys.argv[3]

    if not os.path.isdir(input_dir):
        sys.stderr.write("Error: %s is not a directory\n" % input_dir)
        sys.exit(1)

    input_files = sorted(
        f for f in os.listdir(input_dir)
        if os.path.isfile(os.path.join(input_dir, f))
    )

    with open(output_file, "w", newline="\n") as fout:
        for name in input_files:
            process_file(os.path.join(input_dir, name), ecc_num, fout)


if __name__ == "__main__":
    main()
