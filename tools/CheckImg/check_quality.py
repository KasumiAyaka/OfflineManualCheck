#!/usr/bin/env python3
# python3 check_quality.py <output_file.txt> <input_dir>
#
# make_check_pdfs_pl.py と同じレイアウト(pattern_match_0/1/2.png +
# lens/stage の result.png + フォルダパス + AffineParam)を、check.pdf を
# 経由せずその場でメモリ上に作って表示し、Eyecheck.py と同様に
# ボタン/キー入力でクオリティを記録するツール。
#
# 表示している画像に対して j(OK) / k(Retake) / l(?) のいずれかを選ぶと
# 次のディレクトリに進む。Back/Next で選択せずに移動、Quitで終了。
# 終了時に <output_file.txt> へ "<相対PLディレクトリ> <選択結果>" を
# 1行ずつ追記する。

import glob
import os
import sys
import tkinter as tk

from PIL import Image, ImageFont, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_check_pdfs_pl as pdfmod

CHOICES = ["Quit", "Back", "Next", "j:OK", "k:Retake", "l:?"]
BINDKEYS = ["q", ",", ".", "j", "k", "l"]

# 画面に収まる範囲で表示画像を拡大/縮小する際の余白。
# SCREEN_MARGIN_H はタイトルバー・ボタン列・タスクバー分の余裕を見て、
# ウィンドウの縦の長さを少し短くするために横より大きめにしてある。
SCREEN_MARGIN_W = 20
SCREEN_MARGIN_H = 220


def find_target_dirs(root_dir):
    return sorted(
        d for d in glob.glob(os.path.join(root_dir, "Event*", "PL*")) if os.path.isdir(d)
    )


def build_display_image(pl_dir, header_font, label_font):
    """make_check_pdfs_pl.py と同じ合成画像を、PDFを経由せずに作る。"""
    if pdfmod.find_pattern_source(pl_dir) is None:
        return None, "missing pattern_match files (lens/stage)"
    if not any(
        os.path.exists(os.path.join(pl_dir, sub, pdfmod.RESULT_FILE))
        for sub in pdfmod.SUBDIRS
    ):
        return None, "missing result.png (lens/stage)"
    try:
        canvas = pdfmod.build_composite(pl_dir, header_font, label_font)
    except Exception as e:
        return None, f"error: {e}"
    return canvas, None


def main():
    if len(sys.argv) != 3:
        print("Usage: python check_quality.py <output_file.txt> <input_dir>")
        sys.exit(1)

    outname = sys.argv[1]
    root_dir = os.path.abspath(sys.argv[2])

    dirs = find_target_dirs(root_dir)
    print(f"Found {len(dirs)} target directories under {root_dir}")
    if not dirs:
        sys.exit(1)

    try:
        header_font = ImageFont.truetype(pdfmod.FONT_PATH, pdfmod.HEADER_FONT_SIZE)
        label_font = ImageFont.truetype(pdfmod.FONT_PATH, pdfmod.LABEL_FONT_SIZE)
    except Exception:
        header_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    results = {}

    root = tk.Tk()
    root.title("Check Image Quality Viewer")

    label = tk.Label(root)
    label.pack()

    photo_holder = {}
    idx = {"cur": 0, "next": 0}

    def rel_name(pl_dir):
        return os.path.relpath(pl_dir, root_dir).replace(os.sep, "/")

    def on_choice(choice):
        pl_dir = dirs[idx["cur"]]
        if choice in ("Next", "Back", "Quit"):
            if choice == "Next":
                idx["next"] = idx["cur"] + 1
            elif choice == "Back":
                idx["next"] = max(0, idx["cur"] - 1)
            else:
                idx["next"] = -1
        else:
            results[rel_name(pl_dir)] = choice
            print(rel_name(pl_dir), choice)
            idx["next"] = idx["cur"] + 1
        root.quit()

    for choice in CHOICES:
        button = tk.Button(root, text=choice, command=lambda c=choice: on_choice(c))
        button.pack(side=tk.LEFT)
    for choice, key in zip(CHOICES, BINDKEYS):
        root.bind(key, lambda event, c=choice: on_choice(c))

    def show(index):
        pl_dir = dirs[index]
        canvas, err = build_display_image(pl_dir, header_font, label_font)
        if canvas is None:
            print(f"Skipping {pl_dir}: {err}")
            return False

        screen_w = root.winfo_screenwidth() - SCREEN_MARGIN_W
        screen_h = root.winfo_screenheight() - SCREEN_MARGIN_H
        w, h = canvas.size
        # 画面に収まる最大サイズまで拡大する(小さい画面でだけ縮小)。
        scale = min(screen_w / w, screen_h / h)
        disp = (
            canvas.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
            if scale != 1.0
            else canvas
        )

        photo = ImageTk.PhotoImage(disp)
        photo_holder["img"] = photo
        label.config(image=photo)
        root.title(f"[{index + 1}/{len(dirs)}] {rel_name(pl_dir)}")
        root.geometry(f"{disp.width}x{disp.height + 50}")
        return True

    index = 0
    while 0 <= index < len(dirs):
        idx["cur"] = index
        if not show(index):
            index += 1
            continue
        root.mainloop()
        index = idx["next"]

    root.destroy()

    with open(outname, "a", encoding="utf-8") as f:
        for name, choice in results.items():
            f.write(f"{name} {choice}\n")

    print(f"Wrote {len(results)} judgement(s) to {outname}")


if __name__ == "__main__":
    main()
