import argparse
import glob
import multiprocessing as mp
import os
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

PER_DIR_PDF_NAME = "check.pdf"
FILES = ["pattern_match_0.png", "pattern_match_1.png", "pattern_match_2.png", "result.png"]

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
FONT_SIZE = 26
HEADER_PAD = 14

# Populated once per worker process by _init_worker (avoids re-loading the
# font file and avoids pickling ImageFont objects across processes).
_FONT = None


def _init_worker():
    global _FONT
    try:
        _FONT = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        _FONT = ImageFont.load_default()


def build_composite(dir_path, font):
    imgs = [Image.open(os.path.join(dir_path, f)).convert("RGB") for f in FILES]
    width = max(im.width for im in imgs)

    tmp_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = tmp_draw.textbbox((0, 0), dir_path, font=font)
    text_h = bbox[3] - bbox[1]
    header_h = text_h + HEADER_PAD * 2

    total_h = header_h + sum(im.height for im in imgs)
    canvas = Image.new("RGB", (width, total_h), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((HEADER_PAD, HEADER_PAD - bbox[1]), dir_path, fill="black", font=font)

    y = header_h
    for im in imgs:
        canvas.paste(im, (0, y))
        y += im.height
    return canvas


def _process_dir(args):
    """Runs in a worker process: builds the per-directory check.pdf and a
    composite PNG (used later by the main process to build the merged PDF)."""
    index, dir_path, composite_dir = args

    if not all(os.path.exists(os.path.join(dir_path, f)) for f in FILES):
        return index, dir_path, None, "missing files"

    try:
        canvas = build_composite(dir_path, _FONT)
    except Exception as e:
        return index, dir_path, None, f"error: {e}"

    pdf_path = os.path.join(dir_path, PER_DIR_PDF_NAME)
    canvas.save(pdf_path, "PDF", resolution=100.0)

    comp_path = os.path.join(composite_dir, f"{index:04d}.png")
    canvas.save(comp_path)
    return index, dir_path, comp_path, None


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a per-directory check.pdf (folder path + pattern_match_0/1/2.png + "
            "result.png) for every Event*/PL*/* directory under the input directory, "
            "then merge all of them into a single combined PDF. "
            "Multiprocess version of make_check_pdfs.py."
        )
    )
    parser.add_argument("input_dir", help=r'Root IMG directory, e.g. "K:\NINJA\E71a\ManualCheck\ScanData\UTS\ECC6\IMG"')
    parser.add_argument("output_pdf", help=r'Path of the merged output PDF, e.g. "K:\NINJA\E71a\ManualCheck\ScanData\UTS\ECC6\IMG\ALL_check.pdf"')
    parser.add_argument(
        "-j", "--jobs", type=int, default=os.cpu_count(),
        help="Number of worker processes (default: number of CPU cores)",
    )
    args = parser.parse_args()

    root = os.path.abspath(args.input_dir)
    output_pdf = os.path.abspath(args.output_pdf)

    dirs = sorted(
        d for d in glob.glob(os.path.join(root, "Event*", "PL*", "*")) if os.path.isdir(d)
    )
    print(f"Found {len(dirs)} target directories under {root}")
    if not dirs:
        print("No target directories found, aborting.")
        sys.exit(1)

    print(f"Using {args.jobs} worker processes")
    composite_dir = tempfile.mkdtemp(prefix="check_pdfs_mp_")

    try:
        tasks = [(i, d, composite_dir) for i, d in enumerate(dirs)]
        results = [None] * len(dirs)
        skipped = []

        with mp.Pool(processes=args.jobs, initializer=_init_worker) as pool:
            done = 0
            for index, dir_path, comp_path, err in pool.imap_unordered(_process_dir, tasks, chunksize=1):
                results[index] = comp_path
                if err:
                    skipped.append((dir_path, err))
                done += 1
                if done % 50 == 0 or done == len(dirs):
                    print(f"  processed {done}/{len(dirs)}")

        if skipped:
            print(f"Skipped {len(skipped)} directories (missing files or error):")
            for d, err in skipped:
                print(" ", d, "-", err)

        composite_paths = [p for p in results if p is not None]
        if not composite_paths:
            print("No composites created, aborting merge.")
            sys.exit(1)

        print(f"Merging {len(composite_paths)} single-page PDFs into {output_pdf}")
        os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
        first = Image.open(composite_paths[0]).convert("RGB")
        rest = [Image.open(p).convert("RGB") for p in composite_paths[1:]]
        first.save(output_pdf, "PDF", resolution=100.0, save_all=True, append_images=rest)

        print("Done.")
        print(f"Per-directory PDFs: {PER_DIR_PDF_NAME} inside each of {len(composite_paths)} directories")
        print(f"Merged PDF: {output_pdf}")
    finally:
        shutil.rmtree(composite_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
