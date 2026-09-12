import argparse
import glob
import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

PER_DIR_PDF_NAME = "check.pdf"
PATTERN_FILES = ["pattern_match_0.png", "pattern_match_1.png", "pattern_match_2.png"]
RESULT_FILE = "result.png"
SUBDIRS = ["lens", "stage"]
TOMOGRAPHIC_JSON_FILE = "tomographic_images.json"

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
HEADER_FONT_SIZE = 28
LABEL_FONT_SIZE = 24

# A4 landscape page, rendered at DPI so that PAGE_W x PAGE_H pixels maps
# exactly to 297mm x 210mm when the PDF is saved with resolution=DPI.
DPI = 150.0
PAGE_W = round(297 / 25.4 * DPI)
PAGE_H = round(210 / 25.4 * DPI)

MARGIN = 40
HEADER_PAD = 10
GAP_COL = 24  # gap between the left (pattern_match) and right (lens/stage) columns
GAP_ROW = 14  # gap between images stacked within a column
LABEL_PAD = 4  # padding around the lens/stage label overlaid on its image

# Populated once per worker process by _init_worker (avoids re-loading the
# font files and avoids pickling ImageFont objects across processes).
_HEADER_FONT = None
_LABEL_FONT = None


def _init_worker():
    global _HEADER_FONT, _LABEL_FONT
    try:
        _HEADER_FONT = ImageFont.truetype(FONT_PATH, HEADER_FONT_SIZE)
        _LABEL_FONT = ImageFont.truetype(FONT_PATH, LABEL_FONT_SIZE)
    except Exception:
        _HEADER_FONT = ImageFont.load_default()
        _LABEL_FONT = ImageFont.load_default()


def read_affine_param_text(pl_dir):
    """Read AffineParam from <pl_dir>/tomographic_images.json, formatted for display."""
    json_path = os.path.join(pl_dir, TOMOGRAPHIC_JSON_FILE)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            affine_param = json.load(f)["AffineParam"]
        return "AffineParam: [" + ", ".join(f"{v:.6f}" for v in affine_param) + "]"
    except Exception:
        return f"AffineParam: ({TOMOGRAPHIC_JSON_FILE} not found)"


def find_pattern_source(pl_dir):
    """lens and stage share identical pattern_match_*.png; prefer lens, fall
    back to stage."""
    for sub in SUBDIRS:
        d = os.path.join(pl_dir, sub)
        if all(os.path.exists(os.path.join(d, f)) for f in PATTERN_FILES):
            return d
    return None


def fit_size(img_w, img_h, box_w, box_h):
    """Largest (w, h) that preserves aspect ratio and fits within the box."""
    scale = min(box_w / img_w, box_h / img_h)
    return max(1, round(img_w * scale)), max(1, round(img_h * scale))


def _draw_label(draw, x, y, text, font):
    """Overlay a label at the top-left corner of the image placed at (x, y)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    box = (
        x,
        y,
        x + text_w + LABEL_PAD * 2,
        y + text_h + LABEL_PAD * 2,
    )
    draw.rectangle(box, fill="white", outline="black")
    draw.text((x + LABEL_PAD - bbox[0], y + LABEL_PAD - bbox[1]), text, fill="black", font=font)


def build_composite(pl_dir, header_font, label_font):
    pattern_dir = find_pattern_source(pl_dir)
    pattern_imgs = [
        Image.open(os.path.join(pattern_dir, f)).convert("RGB") for f in PATTERN_FILES
    ]

    result_items = []  # list of (label, image), lens first (top), stage second (bottom)
    for sub in SUBDIRS:
        result_path = os.path.join(pl_dir, sub, RESULT_FILE)
        if os.path.exists(result_path):
            result_items.append((sub, Image.open(result_path).convert("RGB")))

    affine_text = read_affine_param_text(pl_dir)

    canvas = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(canvas)

    y = MARGIN

    header_bbox = draw.textbbox((0, 0), pl_dir, font=header_font)
    draw.text((MARGIN, y + HEADER_PAD - header_bbox[1]), pl_dir, fill="black", font=header_font)
    y += (header_bbox[3] - header_bbox[1]) + HEADER_PAD * 2

    affine_bbox = draw.textbbox((0, 0), affine_text, font=label_font)
    draw.text((MARGIN, y + HEADER_PAD - affine_bbox[1]), affine_text, fill="black", font=label_font)
    y += (affine_bbox[3] - affine_bbox[1]) + HEADER_PAD * 2

    body_top = y
    body_h = PAGE_H - body_top - MARGIN
    col_w = (PAGE_W - 2 * MARGIN - GAP_COL) / 2
    left_x = MARGIN
    right_x = MARGIN + col_w + GAP_COL

    # Left column: pattern_match_0/1/2.png stacked vertically.
    slot_h = (body_h - (len(pattern_imgs) - 1) * GAP_ROW) / len(pattern_imgs)
    y = body_top
    for im in pattern_imgs:
        w, h = fit_size(im.width, im.height, col_w, slot_h)
        x = left_x + (col_w - w) / 2
        canvas.paste(im.resize((w, h)), (round(x), round(y)))
        y += h + GAP_ROW

    # Right column: lens result.png on top, stage result.png on bottom.
    slot_h = (body_h - (len(result_items) - 1) * GAP_ROW) / max(len(result_items), 1)
    y = body_top
    for label, im in result_items:
        w, h = fit_size(im.width, im.height, col_w, slot_h)
        x = right_x + (col_w - w) / 2
        px, py = round(x), round(y)
        canvas.paste(im.resize((w, h)), (px, py))
        _draw_label(draw, px, py, label, label_font)
        y += h + GAP_ROW

    return canvas


def _process_dir(args):
    """Runs in a worker process: builds the per-PL check.pdf and a composite
    PNG (used later by the main process to build the merged PDF)."""
    index, pl_dir, composite_dir = args

    if find_pattern_source(pl_dir) is None:
        return index, pl_dir, None, "missing pattern_match files (lens/stage)"
    if not any(
        os.path.exists(os.path.join(pl_dir, sub, RESULT_FILE)) for sub in SUBDIRS
    ):
        return index, pl_dir, None, "missing result.png (lens/stage)"

    try:
        canvas = build_composite(pl_dir, _HEADER_FONT, _LABEL_FONT)
    except Exception as e:
        return index, pl_dir, None, f"error: {e}"

    pdf_path = os.path.join(pl_dir, PER_DIR_PDF_NAME)
    canvas.save(pdf_path, "PDF", resolution=DPI)

    comp_path = os.path.join(composite_dir, f"{index:04d}.png")
    canvas.save(comp_path)
    return index, pl_dir, comp_path, None


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a per-PL check.pdf (A4 landscape page: PL folder path header, "
            "pattern_match_0/1/2.png shared by lens/stage stacked on the left, "
            "lens/result.png and stage/result.png stacked on the right) for "
            "every Event*/PL* directory under the input directory, then merge "
            "all of them into a single combined PDF."
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
        d for d in glob.glob(os.path.join(root, "Event*", "PL*")) if os.path.isdir(d)
    )
    print(f"Found {len(dirs)} target directories under {root}")
    if not dirs:
        print("No target directories found, aborting.")
        sys.exit(1)

    print(f"Using {args.jobs} worker processes")
    composite_dir = tempfile.mkdtemp(prefix="check_pdfs_pl_")

    try:
        tasks = [(i, d, composite_dir) for i, d in enumerate(dirs)]
        results = [None] * len(dirs)
        skipped = []

        with mp.Pool(processes=args.jobs, initializer=_init_worker) as pool:
            done = 0
            for index, pl_dir, comp_path, err in pool.imap_unordered(_process_dir, tasks, chunksize=1):
                results[index] = comp_path
                if err:
                    skipped.append((pl_dir, err))
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
        first.save(output_pdf, "PDF", resolution=DPI, save_all=True, append_images=rest)

        print("Done.")
        print(f"Per-directory PDFs: {PER_DIR_PDF_NAME} inside each of {len(composite_paths)} directories")
        print(f"Merged PDF: {output_pdf}")
    finally:
        shutil.rmtree(composite_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
