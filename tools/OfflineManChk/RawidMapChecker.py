#!/usr/bin/env python3
# *_rawidmap.txt (format: PL eventid rawid1 zone rawid2 ax ay x y ph%10000) を
# eventid -> PL の昇順に並べて1行ずつ表示し、
# マウス/キーボードで6択のチェック結果（6を選ぶと自由コメント欄も入力）を記録するツール。
# 出力フォーマット: PL eventid rawid1 zone rawid2 入力した結果 入力したコメント
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

OPTIONS = [
    "Both exists",
    "Only the lens side exists.",
    "Only the stage side exists.",
    "Neither exists.",
    "Cannot judge.",
    "Add comments.",
]
FIELDS = ["PL", "eventid", "rawid1", "zone", "rawid2", "ax", "ay", "x", "y", "ph"]
KEY_FIELDS = FIELDS[:5]  # PL eventid rawid1 zone rawid2 (出力行の先頭5列 = 一意なキー)

# 見た目の調整用（ここを変えるだけで文字サイズ・背景色を変更できます）
TABLE_FONT = ("Consolas", 16)
TABLE_HEADER_BG = "#cfe2f3"
TABLE_VALUE_BG = "#ffffff"
BUTTON_FONT = ("", 13)
OPTION_BUTTON_FONT = ("", 18)
OPTION_BUTTON_BG = "#ffffff"
OPTION_BUTTON_SELECTED_BG = "#a5d6a7"
PROGRESS_FONT = ("", 14, "bold")
TYPE_FONT = ("", 22, "bold")
COMMENT_FONT = ("", 13)
OPTION_COLUMNS = 3


def _to_int(text, default=0):
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


class RawidMapChecker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rawidmap Checker")
        self.geometry("1400x520")

        self.rows = []       # eventid -> PL の昇順にソート済み
        self.results = []    # 各rowに対応する (choice:int, comment:str) または None
        self.index = 0
        self.output_path = None

        self._build_ui()
        self.after(50, self._load_input)

    def _build_ui(self):
        self.type_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.type_var, font=TYPE_FONT, anchor="w").pack(fill="x", padx=10, pady=(10, 0))

        self.progress_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.progress_var, font=PROGRESS_FONT).pack(pady=(5, 0))

        table_frame = tk.Frame(self)
        table_frame.pack(pady=10)
        self.value_vars = {}
        for col, name in enumerate(FIELDS):
            tk.Label(table_frame, text=name, font=TABLE_FONT + ("bold",),
                     relief="ridge", borderwidth=1, width=10, bg=TABLE_HEADER_BG).grid(row=0, column=col, sticky="nsew")
            var = tk.StringVar(value="")
            tk.Label(table_frame, textvariable=var, font=TABLE_FONT,
                     relief="ridge", borderwidth=1, width=10, bg=TABLE_VALUE_BG).grid(row=1, column=col, sticky="nsew")
            self.value_vars[name] = var

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        self.buttons = []
        for i, text in enumerate(OPTIONS, start=1):
            b = tk.Button(btn_frame, text=f"{i}. {text}", width=24, font=OPTION_BUTTON_FONT,
                          bg=OPTION_BUTTON_BG, command=lambda i=i: self.on_select(i))
            b.grid(row=(i - 1) // OPTION_COLUMNS, column=(i - 1) % OPTION_COLUMNS, padx=5, pady=3, sticky="w")
            self.buttons.append(b)

        self.answer_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.answer_var, font=BUTTON_FONT, fg="#2e7d32").pack(pady=(0, 5))

        finish_frame = tk.Frame(self)
        finish_frame.pack(pady=5)
        tk.Button(finish_frame, text="終了 (Save & Exit)", font=BUTTON_FONT,
                  command=self.finish_and_exit).pack()

        self.comment_frame = tk.Frame(self)
        tk.Label(self.comment_frame, text="Comment:", font=COMMENT_FONT).pack(side="left")
        self.comment_entry = tk.Entry(self.comment_frame, width=45, font=COMMENT_FONT)
        self.comment_entry.pack(side="left", padx=5)
        self.comment_entry.bind("<Return>", lambda e: self.submit_comment())
        self.comment_entry.bind("<Escape>", lambda e: self.cancel_comment())
        tk.Button(self.comment_frame, text="OK (Enter)", font=COMMENT_FONT, command=self.submit_comment).pack(side="left")
        tk.Button(self.comment_frame, text="Cancel (Esc)", font=COMMENT_FONT, command=self.cancel_comment).pack(side="left", padx=5)

        # 下段: 左下にイベント番号ジャンプ、右下に前後移動ボタン
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        jump_frame = tk.Frame(bottom_frame)
        jump_frame.pack(side="left")
        tk.Label(jump_frame, text="Event:", font=BUTTON_FONT).pack(side="left")
        self.event_entry = tk.Entry(jump_frame, width=10, font=BUTTON_FONT)
        self.event_entry.pack(side="left", padx=5)
        self.event_entry.bind("<Return>", lambda e: self.jump_to_event())
        tk.Button(jump_frame, text="Go", font=BUTTON_FONT, command=self.jump_to_event).pack(side="left")
        self.jump_status_var = tk.StringVar(value="")
        tk.Label(jump_frame, textvariable=self.jump_status_var, font=BUTTON_FONT, fg="red").pack(side="left", padx=10)

        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(side="right")
        tk.Button(nav_frame, text="Next ▶ (.)", font=BUTTON_FONT, command=self.go_next).pack(side="right", padx=5)
        tk.Button(nav_frame, text="◀ Prev (,)", font=BUTTON_FONT, command=self.go_prev).pack(side="right", padx=5)

        self.bind("<Key>", self.on_key)

    # ------------------------------------------------------------------
    # 読み込み・出力ファイルの決定
    # ------------------------------------------------------------------
    def _load_input(self):
        path = filedialog.askopenfilename(
            title="Select *_rawidmap.txt",
            filetypes=[("rawidmap files", "*_rawidmap.txt"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            self.destroy()
            sys.exit(0)

        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < len(FIELDS):
                    continue
                self.rows.append(dict(zip(FIELDS, parts[:len(FIELDS)])))

        if not self.rows:
            messagebox.showerror("Error", "No valid rows found in the selected file.")
            self.destroy()
            sys.exit(1)

        # eventid -> PL の昇順に並べ替える
        self.rows.sort(key=lambda r: (_to_int(r["eventid"]), _to_int(r["PL"])))
        self.results = [None] * len(self.rows)

        base, ext = os.path.splitext(path)
        if base.endswith("_rawidmap"):
            base = base[: -len("_rawidmap")]
        self.output_path = base + "_result" + (ext or ".txt")

        self.index = 0
        if os.path.exists(self.output_path):
            choice = self._ask_output_choice(os.path.basename(self.output_path))
            if choice == "append":
                self._load_existing_results(self.output_path)
                first_unanswered = next((i for i, r in enumerate(self.results) if r is None), None)
                self.index = first_unanswered if first_unanswered is not None else len(self.rows) - 1
            elif choice == "new":
                self.output_path = self._next_numbered_path(self.output_path)
            # choice == "overwrite" -> results はまっさらのまま、output_pathも変更なし

        self.show_current()

    def _ask_output_choice(self, filename):
        result = {"choice": "new"}

        dlg = tk.Toplevel(self)
        dlg.title("Output file already exists")
        dlg.resizable(False, False)
        tk.Label(
            dlg,
            text=f"{filename} already exists.\nWhat would you like to do?",
            justify="left", padx=20, pady=15,
        ).pack()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=(0, 15), padx=15)

        def choose(c):
            result["choice"] = c
            dlg.destroy()

        tk.Button(btn_frame, text="Overwrite", width=14, command=lambda: choose("overwrite")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Append", width=14, command=lambda: choose("append")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="New file (numbered)", width=18, command=lambda: choose("new")).pack(side="left", padx=5)

        dlg.protocol("WM_DELETE_WINDOW", lambda: choose("new"))
        dlg.transient(self)
        dlg.grab_set()
        self.wait_window(dlg)
        return result["choice"]

    def _load_existing_results(self, path):
        row_index_by_key = {tuple(row[f] for f in KEY_FIELDS): i for i, row in enumerate(self.rows)}
        with open(path, encoding="utf-8") as f:
            for line in f:
                parsed = self._parse_result_line(line)
                if parsed is None:
                    continue
                key, choice, comment = parsed
                idx = row_index_by_key.get(key)
                if idx is not None:
                    self.results[idx] = (choice, comment)

    @staticmethod
    def _parse_result_line(line):
        parts = line.rstrip("\n").split(maxsplit=len(KEY_FIELDS))
        if len(parts) < len(KEY_FIELDS) + 1:
            return None
        key = tuple(parts[: len(KEY_FIELDS)])
        rest = parts[len(KEY_FIELDS)]
        for i, opt in enumerate(OPTIONS, start=1):
            if rest == opt:
                return key, i, ""
            if rest.startswith(opt + " "):
                return key, i, rest[len(opt):].strip()
        return None

    @staticmethod
    def _next_numbered_path(base_path):
        root, ext = os.path.splitext(base_path)
        n = 2
        while True:
            candidate = f"{root}_{n}{ext}"
            if not os.path.exists(candidate):
                return candidate
            n += 1

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------
    def _save_all(self):
        if not self.output_path:
            return
        with open(self.output_path, "w", encoding="utf-8") as f:
            for row, result in zip(self.rows, self.results):
                if result is None:
                    continue
                choice, comment = result
                line = f"{row['PL']} {row['eventid']} {row['rawid1']} {row['zone']} {row['rawid2']} {OPTIONS[choice - 1]}"
                if comment:
                    line += f" {comment}"
                f.write(line + "\n")

    # ------------------------------------------------------------------
    # 表示
    # ------------------------------------------------------------------
    @staticmethod
    def _row_type(row):
        if _to_int(row["rawid1"], default=None) == -1 and _to_int(row["rawid2"], default=None) == 0:
            return "prediction"
        return "Muon"

    def show_current(self):
        row = self.rows[self.index]
        result = self.results[self.index]

        self.type_var.set(self._row_type(row))
        answered = sum(1 for r in self.results if r is not None)
        self.progress_var.set(
            f"{self.index + 1} / {len(self.rows)}   ({answered} / {len(self.rows)} answered)   ->  {self.output_path}"
        )
        for name in FIELDS:
            self.value_vars[name].set(row[name])

        self.comment_frame.pack_forget()
        self.comment_entry.delete(0, tk.END)
        self.jump_status_var.set("")

        for b in self.buttons:
            b.config(bg=OPTION_BUTTON_BG)
        if result is not None:
            choice, comment = result
            self.buttons[choice - 1].config(bg=OPTION_BUTTON_SELECTED_BG)
            self.answer_var.set(f"Current answer: {OPTIONS[choice - 1]}" + (f"  ({comment})" if comment else ""))
        else:
            self.answer_var.set("")

    # ------------------------------------------------------------------
    # キー操作
    # ------------------------------------------------------------------
    def on_key(self, event):
        focused = self.focus_get()
        if focused in (self.comment_entry, self.event_entry):
            return
        if event.char in "123456":
            self.on_select(int(event.char))
        elif event.keysym == "Left" or event.char == ",":
            self.go_prev()
        elif event.keysym == "Right" or event.char == ".":
            self.go_next()

    # ------------------------------------------------------------------
    # 選択・コメント
    # ------------------------------------------------------------------
    def on_select(self, choice):
        if choice == 6:
            self.comment_frame.pack(pady=10)
            self.comment_entry.delete(0, tk.END)
            existing = self.results[self.index]
            if existing and existing[0] == 6:
                self.comment_entry.insert(0, existing[1])
            self.comment_entry.focus_set()
            return
        self._set_result(choice, "")

    def submit_comment(self):
        comment = self.comment_entry.get().strip()
        self.comment_frame.pack_forget()
        self._set_result(6, comment)

    def cancel_comment(self):
        self.comment_frame.pack_forget()
        self.comment_entry.delete(0, tk.END)
        self.focus_set()

    def _set_result(self, choice, comment):
        self.results[self.index] = (choice, comment)
        self._save_all()
        self.index = min(self.index + 1, len(self.rows) - 1)
        self.show_current()
        self.focus_set()

    # ------------------------------------------------------------------
    # 前後移動・イベント番号ジャンプ
    # ------------------------------------------------------------------
    def go_prev(self):
        if self.index > 0:
            self.index -= 1
            self.show_current()

    def go_next(self):
        if self.index < len(self.rows) - 1:
            self.index += 1
            self.show_current()

    def jump_to_event(self):
        text = self.event_entry.get().strip()
        if not text:
            return
        try:
            target = int(text)
        except ValueError:
            self.jump_status_var.set("invalid number")
            return
        for i, row in enumerate(self.rows):
            if _to_int(row["eventid"]) == target:
                self.index = i
                self.show_current()
                self.event_entry.delete(0, tk.END)
                self.focus_set()
                return
        self.jump_status_var.set(f"eventid {target} not found")

    # ------------------------------------------------------------------
    # 終了
    # ------------------------------------------------------------------
    def finish_and_exit(self):
        self._save_all()
        self.destroy()

    def on_close(self):
        self._save_all()
        self.destroy()


if __name__ == "__main__":
    app = RawidMapChecker()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
