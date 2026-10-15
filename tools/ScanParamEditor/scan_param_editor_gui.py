"""
ScanParamEditor (GUI版)
========================
scan_param_editor.py(CLI版)と同じロジックを使い、マウス操作だけで
ninja_e71a*.yaml の ScanParamBase.ScanArea / ThrBinary / ThickOfLayer を
書き換えられるGUIツール。パソコン操作に不慣れな人向けに、番号入力ではなく
一覧からクリックして選ぶだけで使えるようにしている。

使い方:
    scan_param_editor_gui.exe                   (exeと同じフォルダの config.yaml を使う)
    scan_param_editor_gui.exe path\to\config.yaml   (設定ファイルを明示指定)
"""

import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *

import scan_param_editor as core


FONT_NORMAL = ("Meiryo UI", 12)
FONT_BOLD = ("Meiryo UI", 12, "bold")
FONT_HEADER = ("Meiryo UI", 17, "bold")
FONT_MONO = ("Consolas", 12)


class ScanParamEditorApp:
    def __init__(self, root, config_path):
        self.root = root
        self.config_path = config_path
        self.targets = []
        self.thr_choices = []
        self.area_choices = []
        self.thickness_choices = []
        self.backup_dir = None

        self.current_thr = None
        self.current_area_pairs = None
        self.current_area_text = ""
        self.current_thickness = None

        self._build_ui()
        self._load_config()
        self._fit_window_to_content()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.root.title("ScanParamEditor")
        self.root.geometry("660x700")
        self.root.minsize(540, 400)

        # 内容が画面より縦に長くなっても見切れないよう、スクロール可能な
        # キャンバスの中に本体(outer)を置く。
        canvas = tk.Canvas(self.root, highlightthickness=0)
        vscroll = tb.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        vscroll.pack(side=RIGHT, fill=Y)

        outer = tb.Frame(canvas, padding=16)
        outer_id = canvas.create_window((0, 0), window=outer, anchor="nw")

        def on_outer_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfigure(outer_id, width=event.width)

        outer.bind("<Configure>", on_outer_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        self._canvas = canvas
        self._outer = outer

        header = tb.Label(outer, text="ScanParamEditor", font=FONT_HEADER, bootstyle="primary")
        header.pack(anchor=W)
        sub = tb.Label(
            outer,
            text="対象ファイルを選び、症状/状況に合う対応を選んでください。両方「変更しない」も選べます。",
            font=FONT_NORMAL,
            bootstyle="secondary",
        )
        sub.pack(anchor=W, pady=(0, 12))

        # --- ① 対象ファイル ---------------------------------------------------
        box1 = tb.Labelframe(outer, text="① 書き換える対象ファイル", padding=12, bootstyle="primary")
        box1.pack(fill=X, pady=(0, 10))

        self.target_var = tk.StringVar()
        self.target_combo = tb.Combobox(box1, textvariable=self.target_var, state="readonly", font=FONT_NORMAL)
        self.target_combo.pack(fill=X)
        self.target_combo.bind("<<ComboboxSelected>>", lambda e: self._on_target_changed())

        self.target_path_label = tb.Label(box1, text="", font=FONT_MONO, bootstyle="secondary", wraplength=600)
        self.target_path_label.pack(fill=X, anchor=W, pady=(6, 0))

        # --- ② ThrBinary --------------------------------------------------
        box2 = tb.Labelframe(outer, text="② ThrBinary の変更(該当する症状・対応を選択)", padding=12, bootstyle="info")
        box2.pack(fill=X, pady=(0, 10))
        self.thr_var = tk.IntVar(value=-1)
        self.thr_radio_frame = tb.Frame(box2)
        self.thr_radio_frame.pack(fill=X)

        # --- ③ ScanArea ------------------------------------------------
        box3 = tb.Labelframe(outer, text="③ ScanArea の変更", padding=12, bootstyle="info")
        box3.pack(fill=X, pady=(0, 10))
        self.area_var = tk.IntVar(value=-1)
        self.area_radio_frame = tb.Frame(box3)
        self.area_radio_frame.pack(fill=X)

        # --- ④ ThickOfLayer --------------------------------------------
        box_thick = tb.Labelframe(outer, text="④ ThickOfLayer の変更", padding=12, bootstyle="info")
        box_thick.pack(fill=X, pady=(0, 10))
        self.thickness_var = tk.IntVar(value=-1)
        self.thickness_radio_frame = tb.Frame(box_thick)
        self.thickness_radio_frame.pack(fill=X)

        # --- 変更前/変更後(横並び比較) --------------------------------------
        compare_row = tb.Frame(outer)
        compare_row.pack(fill=BOTH, expand=YES, pady=(0, 10))

        box_before = tb.Labelframe(compare_row, text="変更前のパラメータ", padding=12, bootstyle="secondary")
        box_before.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 6))
        self.current_value_text = tk.Text(box_before, height=1, font=FONT_MONO, state="disabled",
                                           relief="flat", background="#f1f3f5", wrap="none")
        self.current_value_text.pack(fill=BOTH, expand=YES)

        box4 = tb.Labelframe(compare_row, text="変更後のプレビュー", padding=12, bootstyle="success")
        box4.pack(side=LEFT, fill=BOTH, expand=YES, padx=(6, 0))
        self.preview_text = tk.Text(box4, height=1, font=FONT_MONO, state="disabled",
                                     relief="flat", background="#eafaf1", wrap="none")
        self.preview_text.pack(fill=BOTH, expand=YES)

        # --- ボタン --------------------------------------------------
        # ttk の Button は font を直接指定できないため、文字を2pt拡大した専用スタイルを作る。
        button_style = tb.Style()
        button_style.configure("Big.success.TButton", font=FONT_NORMAL)
        button_style.configure("Big.warning.TButton", font=FONT_NORMAL)
        button_style.configure("Big.secondary.Outline.TButton", font=FONT_NORMAL)

        btn_frame = tb.Frame(outer)
        btn_frame.pack(fill=X, pady=(4, 0))

        self.apply_btn = tb.Button(
            btn_frame, text="書き換える", bootstyle="success", width=20,
            command=self._on_apply_clicked, style="Big.success.TButton",
        )
        self.apply_btn.pack(side=LEFT, padx=(0, 10), ipady=8)

        self.reset_btn = tb.Button(
            btn_frame, text="デフォルトに戻す", bootstyle="warning", width=18,
            command=self._on_reset_clicked, state="disabled", style="Big.warning.TButton",
        )
        self.reset_btn.pack(side=LEFT, padx=(0, 10), ipady=8)

        exit_btn = tb.Button(btn_frame, text="終了", bootstyle="secondary-outline", width=12,
                              command=self.root.destroy, style="Big.secondary.Outline.TButton")
        exit_btn.pack(side=LEFT, ipady=8)

        self.status_label = tb.Label(outer, text="", font=FONT_NORMAL, bootstyle="secondary")
        self.status_label.pack(anchor=W, pady=(1, 0))

    def _set_text(self, widget, text):
        """Text欄の内容を差し替え、スクロールが要らないよう行数・最長行の文字数ぴったりのサイズにする。"""
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        lines = text.split("\n") if text else [""]
        line_count = len(lines)
        max_len = max((len(line) for line in lines), default=1)
        widget.configure(height=max(line_count, 1), width=max(max_len, 1))
        widget.configure(state="disabled")

    def _fit_window_to_content(self):
        """選択肢の数(config.yaml次第)にかかわらず、起動時の縦サイズを
        本体の内容がすべて見える高さに自動調整する。画面より高くなる場合は
        画面に収まる高さにして、キャンバスのスクロールで残りを見られるようにする。
        """
        self.root.update_idletasks()
        content_w = self._outer.winfo_reqwidth()
        content_h = self._outer.winfo_reqheight()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        margin_w = 40   # スクロールバー分など
        margin_h = 80   # タイトルバー・タスクバー分の余白

        width = min(max(content_w + margin_w, 700), screen_w - 60)
        height = min(content_h + margin_h, screen_h - margin_h)

        self.root.geometry(f"{width}x{height}")

    # ------------------------------------------------------------- config
    def _load_config(self):
        try:
            (self.targets, self.thr_choices, self.area_choices,
             self.thickness_choices, self.backup_dir) = core.load_config(self.config_path)
        except Exception as e:
            messagebox.showerror("設定エラー", f"設定ファイルの読み込みに失敗しました。\n\n{e}\n\n設定ファイル: {self.config_path}")
            self.root.destroy()
            return

        self._build_radio_group(self.thr_radio_frame, self.thr_choices, self.thr_var,
                                 lambda c: f"{c['name']}  ({'set=' if c['operation'] == 'set' else ('+' if int(c['value']) >= 0 else '')}{c['value']})")
        self._build_radio_group(self.area_radio_frame, self.area_choices, self.area_var,
                                 lambda c: f"{c['name']}  ScanArea={c['ScanArea']}")
        self._build_radio_group(self.thickness_radio_frame, self.thickness_choices, self.thickness_var,
                                 lambda c: f"{c['name']}  ({'set=' if c['operation'] == 'set' else ('+' if float(c['value']) >= 0 else '')}{c['value']})")

        self.target_combo["values"] = [t["name"] for t in self.targets]
        if self.targets:
            self.target_combo.current(0)
            self._on_target_changed()

    def _build_radio_group(self, frame, choices, var, display):
        radio_style = tb.Style()
        radio_style.configure("Big.info.TRadiobutton", font=FONT_NORMAL)
        radio_style.configure("Big.secondary.TRadiobutton", font=FONT_NORMAL)
        for i, c in enumerate(choices):
            rb = tb.Radiobutton(frame, text=display(c), variable=var, value=i,
                                 bootstyle="info", command=self._refresh_preview,
                                 style="Big.info.TRadiobutton")
            rb.pack(anchor=W, pady=2)
        rb_skip = tb.Radiobutton(frame, text="変更しない(そのまま)", variable=var, value=-1,
                                  bootstyle="secondary", command=self._refresh_preview,
                                  style="Big.secondary.TRadiobutton")
        rb_skip.pack(anchor=W, pady=2)
        var.set(-1)

    # ------------------------------------------------------------- events
    def _get_selected_target(self):
        idx = self.target_combo.current()
        if idx < 0 or idx >= len(self.targets):
            return None
        return self.targets[idx]

    def _on_target_changed(self):
        target = self._get_selected_target()
        self.status_label.configure(text="")
        if target is None:
            return
        self.target_path_label.configure(text=target["path"])

        has_defaults = bool(target.get("defaults"))
        self.reset_btn.configure(state="normal" if has_defaults else "disabled")

        if not os.path.isfile(target["path"]):
            self._set_text(self.current_value_text, f"[エラー] ファイルが見つかりません:\n{target['path']}")
            self.current_thr = None
            self.current_area_text = ""
            self.current_thickness = None
            self._set_text(self.preview_text, "")
            self.apply_btn.configure(state="disabled")
            self.reset_btn.configure(state="disabled")
            self._fit_window_to_content()
            return

        try:
            with open(target["path"], encoding="utf-8", newline="") as f:
                text = f.read()
            _, body = core.get_scanparambase_body(text)
            self.current_thr = core.get_current_thrbinary(body)
            self.current_area_text = core.get_current_scanarea_text(body)
            self.current_thickness = core.get_current_thickoflayer(body)
        except Exception as e:
            self._set_text(self.current_value_text, f"[エラー] 解析に失敗しました:\n{e}")
            self.current_thr = None
            self.current_area_text = ""
            self.current_thickness = None
            self._set_text(self.preview_text, "")
            self.apply_btn.configure(state="disabled")
            self.reset_btn.configure(state="disabled")
            self._fit_window_to_content()
            return

        self._set_text(
            self.current_value_text,
            f"{self.current_area_text}\n    ThrBinary: {self.current_thr}\n    ThickOfLayer: {self.current_thickness}",
        )
        self.apply_btn.configure(state="normal")
        self._refresh_preview()

    def _refresh_preview(self):
        if self.current_thr is None:
            return

        thr_idx = self.thr_var.get()
        area_idx = self.area_var.get()

        if thr_idx == -1:
            new_thr = self.current_thr
            thr_desc = "変更しない"
        else:
            choice = self.thr_choices[thr_idx]
            new_thr = core.compute_new_thrbinary(choice, self.current_thr)
            thr_desc = choice["name"]

        if area_idx == -1:
            new_area_pairs = None
            area_desc = "変更しない"
            new_area_text = self.current_area_text
        else:
            choice = self.area_choices[area_idx]
            new_area_pairs = choice["ScanArea"]
            area_desc = choice["name"]
            new_area_text = core.build_scanarea_block(new_area_pairs, "\n").strip()

        thickness_idx = self.thickness_var.get()
        if thickness_idx == -1:
            new_thickness = self.current_thickness
            thickness_desc = "変更しない"
        else:
            choice = self.thickness_choices[thickness_idx]
            new_thickness = core.compute_new_thickoflayer(choice, self.current_thickness)
            thickness_desc = choice["name"]

        preview = (
            f"ThrBinary対応   : {thr_desc}\n"
            f"ScanArea対応    : {area_desc}\n"
            f"ThickOfLayer対応: {thickness_desc}\n\n"
            f"{new_area_text}\n"
            f"    ThrBinary: {new_thr}\n"
            f"    ThickOfLayer: {new_thickness}"
        )
        self._set_text(self.preview_text, preview)
        self._fit_window_to_content()

    # ------------------------------------------------------------- apply
    def _on_apply_clicked(self):
        target = self._get_selected_target()
        if target is None or self.current_thr is None:
            messagebox.showwarning("未選択", "対象ファイルを選択してください。")
            return

        thr_idx = self.thr_var.get()
        area_idx = self.area_var.get()

        new_thr = None
        thr_desc = "変更しない"
        if thr_idx != -1:
            choice = self.thr_choices[thr_idx]
            new_thr = core.compute_new_thrbinary(choice, self.current_thr)
            thr_desc = choice["name"]

        new_area_pairs = None
        area_desc = "変更しない"
        if area_idx != -1:
            choice = self.area_choices[area_idx]
            new_area_pairs = choice["ScanArea"]
            area_desc = choice["name"]

        thickness_idx = self.thickness_var.get()
        new_thickness = None
        thickness_desc = "変更しない"
        if thickness_idx != -1:
            choice = self.thickness_choices[thickness_idx]
            new_thickness = core.compute_new_thickoflayer(choice, self.current_thickness)
            thickness_desc = choice["name"]

        if new_thr is None and new_area_pairs is None and new_thickness is None:
            messagebox.showinfo("変更なし", "ThrBinary / ScanArea / ThickOfLayer のどれも「変更しない」が選ばれているため、何も変更しません。")
            return

        target_path = target["path"]
        with open(target_path, encoding="utf-8", newline="") as f:
            original_text = f.read()

        try:
            new_text = core.apply_changes(original_text, new_thr, new_area_pairs, new_thickness)
            _, new_body = core.get_scanparambase_body(new_text)
            new_thr_shown = core.get_current_thrbinary(new_body)
            new_area_shown = core.get_current_scanarea_text(new_body)
            new_thickness_shown = core.get_current_thickoflayer(new_body)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの書き換えに失敗しました。\n\n{e}")
            return

        confirm_msg = (
            f"対象ファイル:\n{target_path}\n\n"
            f"ThrBinary対応   : {thr_desc}\n"
            f"ScanArea対応    : {area_desc}\n"
            f"ThickOfLayer対応: {thickness_desc}\n\n"
            f"--- 変更前 ---\n{self.current_area_text}\n"
            f"    ThrBinary: {self.current_thr}\n"
            f"    ThickOfLayer: {self.current_thickness}\n\n"
            f"--- 変更後 ---\n{new_area_shown}\n"
            f"    ThrBinary: {new_thr_shown}\n"
            f"    ThickOfLayer: {new_thickness_shown}\n\n"
            f"この内容で書き換えますか？"
        )
        if not messagebox.askyesno("変更内容の確認", confirm_msg):
            self.status_label.configure(text="キャンセルしました。")
            return

        try:
            backup_path = self._write_with_backup(target_path, original_text, new_text)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの書き込みに失敗しました。\n\n{e}")
            return

        messagebox.showinfo("完了", f"書き換えが完了しました。\n\n対象ファイル:\n{target_path}\n\nバックアップ:\n{backup_path}")
        self.status_label.configure(text=f"書き換え完了: {target_path}")
        self._on_target_changed()

    def _write_with_backup(self, target_path, original_text, new_text):
        """バックアップを作成してから対象ファイルを書き換える。バックアップ先のパスを返す。"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = core.compute_backup_path(target_path, self.backup_dir, timestamp)
        if self.backup_dir:
            os.makedirs(self.backup_dir, exist_ok=True)
        with open(backup_path, "w", encoding="utf-8", newline="") as f:
            f.write(original_text)
        with open(target_path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        return backup_path

    # ------------------------------------------------------------- reset
    def _on_reset_clicked(self):
        target = self._get_selected_target()
        if target is None or self.current_thr is None:
            messagebox.showwarning("未選択", "対象ファイルを選択してください。")
            return

        defaults = target.get("defaults")
        if not defaults:
            messagebox.showwarning("未設定", "このファイルにはデフォルト値が設定されていません。")
            return

        target_path = target["path"]
        with open(target_path, encoding="utf-8", newline="") as f:
            original_text = f.read()

        try:
            new_thr = int(defaults["ThrBinary"])
            new_area_pairs = defaults["ScanArea"]
            new_thickness = float(defaults["ThickOfLayer"])
            new_text = core.apply_changes(original_text, new_thr, new_area_pairs, new_thickness)
            _, new_body = core.get_scanparambase_body(new_text)
            new_thr_shown = core.get_current_thrbinary(new_body)
            new_area_shown = core.get_current_scanarea_text(new_body)
            new_thickness_shown = core.get_current_thickoflayer(new_body)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの書き換えに失敗しました。\n\n{e}")
            return

        confirm_msg = (
            f"対象ファイル:\n{target_path}\n\n"
            f"ThrBinary・ScanArea・ThickOfLayer を全てデフォルト値に戻します。\n\n"
            f"--- 変更前 ---\n{self.current_area_text}\n"
            f"    ThrBinary: {self.current_thr}\n"
            f"    ThickOfLayer: {self.current_thickness}\n\n"
            f"--- 変更後(デフォルト) ---\n{new_area_shown}\n"
            f"    ThrBinary: {new_thr_shown}\n"
            f"    ThickOfLayer: {new_thickness_shown}\n\n"
            f"この内容で書き換えますか？"
        )
        if not messagebox.askyesno("デフォルトに戻す", confirm_msg):
            self.status_label.configure(text="キャンセルしました。")
            return

        try:
            backup_path = self._write_with_backup(target_path, original_text, new_text)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの書き込みに失敗しました。\n\n{e}")
            return

        messagebox.showinfo("完了", f"デフォルトに戻しました。\n\n対象ファイル:\n{target_path}\n\nバックアップ:\n{backup_path}")
        self.status_label.configure(text=f"デフォルトに戻しました: {target_path}")
        self.thr_var.set(-1)
        self.area_var.set(-1)
        self.thickness_var.set(-1)
        self._on_target_changed()


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    base_dir = get_base_dir()
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "config.yaml")

    root = tb.Window(themename="flatly")
    ScanParamEditorApp(root, config_path)
    root.mainloop()


if __name__ == "__main__":
    main()
