import argparse
import glob
import os
import sys
import tempfile
import shutil

from PIL import Image, ImageDraw, ImageFont

PER_DIR_PDF_NAME = "check.pdf"
FILES = ["pattern_match_0.png", "pattern_match_1.png", "pattern_match_2.png", "result.png"]

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
FONT_SIZE = 26
HEADER_PAD = 14


def get_font():
    try:
        return ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        return ImageFont.load_default()


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


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a per-directory check.pdf (folder path + pattern_match_0/1/2.png + "
            "result.png) for every Event*/PL*/* directory under the input directory, "
            "then merge all of them into a single combined PDF."
        )
    )
    parser.add_argument("input_dir", help=r'Root IMG directory, e.g. "K:\NINJA\E71a\ManualCheck\ScanData\UTS\ECC6\IMG"')
    parser.add_argument("output_pdf", help=r'Path of the merged output PDF, e.g. "K:\NINJA\E71a\ManualCheck\ScanData\UTS\ECC6\IMG\ALL_check.pdf"')
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

    font = get_font()
    composite_dir = tempfile.mkdtemp(prefix="check_pdfs_")

    try:
        composite_paths = []
        skipped = []
        for i, d in enumerate(dirs):
            if not all(os.path.exists(os.path.join(d, f)) for f in FILES):
                skipped.append(d)
                continue
            try:
                canvas = build_composite(d, font)
            except Exception as e:
                print(f"ERROR building composite for {d}: {e}")
                skipped.append(d)
                continue

            pdf_path = os.path.join(d, PER_DIR_PDF_NAME)
            canvas.save(pdf_path, "PDF", resolution=100.0)

            comp_path = os.path.join(composite_dir, f"{i:04d}.png")
            canvas.save(comp_path)
            composite_paths.append(comp_path)

            if (i + 1) % 50 == 0 or i == len(dirs) - 1:
                print(f"  processed {i + 1}/{len(dirs)}")

        if skipped:
            print(f"Skipped {len(skipped)} directories (missing files or error):")
            for s in skipped:
                print(" ", s)

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
