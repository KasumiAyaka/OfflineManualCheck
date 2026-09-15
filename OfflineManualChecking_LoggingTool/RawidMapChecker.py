#!/usr/bin/env python3
# *_rawidmap.txt (format: PL eventid rawid1 zone rawid2 ax ay x y ph1 ph2 trk_type) を
# eventid -> PL の昇順に並べて1行ずつ表示し、
# マウス/キーボードで6択のチェック結果（6を選ぶと自由コメント欄も入力）を記録するツール。
# 1行は実在(trk_type=0)・外挿(trk_type=1)・近くのトラック/Reference(trk_type=-1)のいずれか1件を表し、
# それぞれ独立してチェックする（Make_rawidmap_from_TrackList.cppの出力フォーマットに対応）。
# 出力フォーマット: PL eventid rawid1 zone rawid2 trk_type 入力した結果 入力したコメント
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
FIELDS = ["PL", "eventid", "rawid1", "zone", "rawid2", "ax", "ay", "x", "y", "ph1", "ph2", "trk_type"]
KEY_FIELDS = ["PL", "eventid", "rawid1", "zone", "rawid2", "trk_type"]  # 出力行の先頭6列 = 一意なキー
DISPLAY_FIELDS = ["eventid", "PL", "rawid1", "ax", "ay", "x", "y", "ph1", "ph2"]  # 表に常時表示する列
DISPLAY_LABELS = {"ph1": "VPH1(PH)", "ph2": "VPH2(PH)"}  # 見出しを差し替える列
SCAN_AREA_FIELDS = ["zone", "rawid2"]  # "scan area info" ボタンを押したときだけ表示する列

# 右上の表示モード切り替え。"Muon" は trk_type 0(実在)/1(外挿)、"Reference" は trk_type -1 のみ表示する。
MODES = ["Muon", "Reference"]
MODE_FILTERS = {
    "Muon": lambda t: t in (0, 1),
    "Reference": lambda t: t == -1,
}

# 見た目の調整用（ここを変えるだけで文字サイズ・背景色を変更できます）
TABLE_FONT = ("Consolas", 16)
TABLE_HEADER_BG = "#cfe2f3"
TABLE_VALUE_BG = "#ffffff"
BUTTON_FONT = ("", 13)
OPTION_BUTTON_FONT = ("", 18)
OPTION_BUTTON_BG = "#ffffff"
OPTION_BUTTON_SELECTED_BG = "#a5d6a7"
PH_DEFAULT_FG = "#000000"
PH_REFERENCE_FG = "#b26a00"  # 外挿行でmuonのphを参考表示するときの文字色
PROGRESS_FONT = ("", 14, "bold")
TYPE_FONT = ("", 22, "bold")
COMMENT_FONT = ("", 13)
OPTION_COLUMNS = 3


def _to_int(text, default=0):
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def _format_ph(text):
    v = _to_int(text, default=None)
    if v is None or v == -1:
        return "-1"
    return f"{v % 10000}({v // 10000})"


class RawidMapChecker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rawidmap Checker")
        self.geometry("1300x520")

        self.rows = []       # eventid -> PL の昇順にソート済み(全trk_type)
        self.results = []    # 各rowに対応する (choice:int, comment:str) または None
        self.mode = "Muon"   # "Muon" (trk_type 0/1) または "Reference" (trk_type -1)
        self.view = []       # 現在のmodeで絞り込んだ self.rows へのインデックス列
        self.pos = 0         # self.view内での現在位置
        self.output_path = None

        self._build_ui()
        self.after(50, self._load_input)

    def _build_ui(self):
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.type_var = tk.StringVar(value="")
        tk.Label(top_frame, textvariable=self.type_var, font=TYPE_FONT, anchor="w").pack(side="left")

        mode_frame = tk.Frame(top_frame)
        mode_frame.pack(side="right")
        self.mode_buttons = {}
        for mode_name in MODES:
            b = tk.Button(mode_frame, text=mode_name, font=BUTTON_FONT, width=12,
                          command=lambda m=mode_name: self.set_mode(m))
            b.pack(side="left", padx=3)
            self.mode_buttons[mode_name] = b

        self.progress_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.progress_var, font=PROGRESS_FONT).pack(pady=(5, 0))

        table_frame = tk.Frame(self)
        table_frame.pack(pady=10)
        self.value_vars = {}
        self.value_labels = {}
        for col, name in enumerate(DISPLAY_FIELDS):
            label = DISPLAY_LABELS.get(name, name)
            tk.Label(table_frame, text=label, font=TABLE_FONT + ("bold",),
                     relief="ridge", borderwidth=1, width=10, bg=TABLE_HEADER_BG).grid(row=0, column=col, sticky="nsew")
            var = tk.StringVar(value="")
            value_label = tk.Label(table_frame, textvariable=var, font=TABLE_FONT, fg=PH_DEFAULT_FG,
                     relief="ridge", borderwidth=1, width=10, bg=TABLE_VALUE_BG)
            value_label.grid(row=1, column=col, sticky="nsew")
            self.value_vars[name] = var
            self.value_labels[name] = value_label

        self.ph_note_var = tk.StringVar(value="")
        ph_col = DISPLAY_FIELDS.index("ph1")
        tk.Label(table_frame, textvariable=self.ph_note_var, font=("", 10), fg=PH_REFERENCE_FG,
                 anchor="w").grid(row=2, column=ph_col, columnspan=2, sticky="w", pady=(3, 0))

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
        tk.Button(jump_frame, text="scan area info", font=BUTTON_FONT, command=self.show_scan_area_info).pack(side="left", padx=(10, 0))
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

        if os.path.exists(self.output_path):
            choice = self._ask_output_choice(os.path.basename(self.output_path))
            if choice == "append":
                self._load_existing_results(self.output_path)
            elif choice == "new":
                self.output_path = self._next_numbered_path(self.output_path)
            # choice == "overwrite" -> results はまっさらのまま、output_pathも変更なし

        self._rebuild_view()
        self.show_current()

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self._rebuild_view()
        self.show_current()

    def _rebuild_view(self):
        pred = MODE_FILTERS[self.mode]
        self.view = [i for i, row in enumerate(self.rows) if pred(_to_int(row["trk_type"], default=None))]
        first_unanswered = next((p for p, i in enumerate(self.view) if self.results[i] is None), None)
        self.pos = first_unanswered if first_unanswered is not None else max(len(self.view) - 1, 0)
        for name, btn in self.mode_buttons.items():
            btn.config(bg=OPTION_BUTTON_SELECTED_BG if name == self.mode else OPTION_BUTTON_BG)

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
                key_values = " ".join(row[f] for f in KEY_FIELDS)
                line = f"{key_values} {OPTIONS[choice - 1]}"
                if comment:
                    line += f" {comment}"
                f.write(line + "\n")

    # ------------------------------------------------------------------
    # 表示
    # ------------------------------------------------------------------
    def _find_muon_ph(self, eventid):
        # 同じeventidの実在(Muon, trk_type==0)行を探し、そのph1/ph2を返す。見つからなければNone。
        target = _to_int(eventid)
        for row in self.rows:
            if _to_int(row["trk_type"], default=None) == 0 and _to_int(row["eventid"]) == target:
                return row["ph1"], row["ph2"]
        return None

    @staticmethod
    def _row_type(row):
        t = _to_int(row["trk_type"], default=None)
        if t == 0:
            return "Muon"
        if t == 1:
            return "prediction"
        if t == -1:
            return "Reference"
        return "Unknown"

    def show_current(self):
        if not self.view:
            self.type_var.set("")
            for name in DISPLAY_FIELDS:
                self.value_vars[name].set("")
            self.value_labels["ph1"].config(fg=PH_DEFAULT_FG)
            self.value_labels["ph2"].config(fg=PH_DEFAULT_FG)
            self.ph_note_var.set("")
            self.progress_var.set(f"[{self.mode}] 0 / 0   (no rows for this type)   ->  {self.output_path}")
            self.comment_frame.pack_forget()
            self.answer_var.set("")
            for b in self.buttons:
                b.config(state="disabled", bg=OPTION_BUTTON_BG)
            return
        for b in self.buttons:
            b.config(state="normal")

        idx = self.view[self.pos]
        row = self.rows[idx]
        result = self.results[idx]

        self.type_var.set(self._row_type(row))
        answered = sum(1 for i in self.view if self.results[i] is not None)
        if self.mode == "Reference":
            # Referenceはトラック数ではなくイベント数(eventidの種類数)を分母にする
            total_for_progress = len({self.rows[i]["eventid"] for i in self.view})
        else:
            total_for_progress = len(self.view)
        self.progress_var.set(
            f"[{self.mode}] {self.pos + 1} / {len(self.view)}   ({answered} / {total_for_progress} answered)   ->  {self.output_path}"
        )
        for name in DISPLAY_FIELDS:
            if name not in ("ph1", "ph2"):
                self.value_vars[name].set(row[name])

        # ph1/ph2: 外挿(trk_type==1)行は自身のphを持たない(-1)ため、
        # 同じeventidの実在(Muon)行のphを参考値として色を変えて表示する。
        muon_ph = self._find_muon_ph(row["eventid"]) if _to_int(row["trk_type"], default=None) == 1 else None
        if muon_ph is not None:
            self.value_vars["ph1"].set(_format_ph(muon_ph[0]))
            self.value_vars["ph2"].set(_format_ph(muon_ph[1]))
            self.value_labels["ph1"].config(fg=PH_REFERENCE_FG)
            self.value_labels["ph2"].config(fg=PH_REFERENCE_FG)
            self.ph_note_var.set("* VPH(PH) shown above is the Muon track's value, for reference only.")
        else:
            self.value_vars["ph1"].set(_format_ph(row["ph1"]))
            self.value_vars["ph2"].set(_format_ph(row["ph2"]))
            self.value_labels["ph1"].config(fg=PH_DEFAULT_FG)
            self.value_labels["ph2"].config(fg=PH_DEFAULT_FG)
            self.ph_note_var.set("")

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
        if not self.view:
            return
        if choice == 6:
            self.comment_frame.pack(pady=10)
            self.comment_entry.delete(0, tk.END)
            existing = self.results[self.view[self.pos]]
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
        self.results[self.view[self.pos]] = (choice, comment)
        self._save_all()
        self.pos = min(self.pos + 1, len(self.view) - 1)
        self.show_current()
        self.focus_set()

    # ------------------------------------------------------------------
    # 前後移動・イベント番号ジャンプ
    # ------------------------------------------------------------------
    def show_scan_area_info(self):
        if not self.view:
            return
        row = self.rows[self.view[self.pos]]
        info = "\n".join(f"{name}: {row[name]}" for name in SCAN_AREA_FIELDS)
        messagebox.showinfo("Scan Area Info", info)

    def go_prev(self):
        if self.pos > 0:
            self.pos -= 1
            self.show_current()

    def go_next(self):
        if self.pos < len(self.view) - 1:
            self.pos += 1
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
        for p, i in enumerate(self.view):
            if _to_int(self.rows[i]["eventid"]) == target:
                self.pos = p
                self.show_current()
                self.event_entry.delete(0, tk.END)
                self.focus_set()
                return
        self.jump_status_var.set(f"eventid {target} not found in {self.mode} view")

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
