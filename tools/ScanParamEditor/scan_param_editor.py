"""
ScanParamEditor
================
ninja_e71a*.yaml (ScamParam) の ScanParamBase.ScanArea / ThrBinary / ThickOfLayer を書き換えるツール。

「499999 tracks detectedと出力された → ThrBinaryを下げる」のように、現場で起きた
状況(症状)に対する対応として ThrBinary・ScanArea・ThickOfLayer をそれぞれ別々に
選べるようにしている(全部変える必要はなく、一部だけ変えることもできる)。

設定ファイル(config.yaml)に書き換え対象ファイルのパスと選択肢を定義しておくことで、
PCごとにパスや選択肢が違っても exe 本体は共通で使える。

使い方:
    scan_param_editor.exe                  (exeと同じフォルダの config.yaml を使う)
    scan_param_editor.exe path\to\config.yaml   (設定ファイルを明示指定)
"""

import datetime
import os
import re
import sys

import yaml


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config(config_path):
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    targets = config.get("targets") or []
    thr_choices = config.get("thrbinary_choices") or []
    area_choices = config.get("scanarea_choices") or []
    thickness_choices = config.get("thickoflayer_choices") or []

    if not targets:
        raise ValueError("config.yaml の targets が空です。")
    if not thr_choices and not area_choices and not thickness_choices:
        raise ValueError("config.yaml の thrbinary_choices / scanarea_choices / thickoflayer_choices が全て空です。")

    for t in targets:
        if "name" not in t or "path" not in t:
            raise ValueError(f"targets の項目に name/path が不足しています: {t}")
        defaults = t.get("defaults")
        if defaults is not None:
            for key in ("ThrBinary", "ScanArea", "ThickOfLayer"):
                if key not in defaults:
                    raise ValueError(f"targets の defaults には ThrBinary/ScanArea/ThickOfLayer が全て必要です: {t}")
    for c in thr_choices:
        if "name" not in c or "operation" not in c or "value" not in c:
            raise ValueError(f"thrbinary_choices の項目に name/operation/value が不足しています: {c}")
        if c["operation"] not in ("set", "delta"):
            raise ValueError(f"thrbinary_choices の operation は set か delta のみ指定できます: {c}")
    for c in area_choices:
        if "name" not in c or "ScanArea" not in c:
            raise ValueError(f"scanarea_choices の項目に name/ScanArea が不足しています: {c}")
    for c in thickness_choices:
        if "name" not in c or "operation" not in c or "value" not in c:
            raise ValueError(f"thickoflayer_choices の項目に name/operation/value が不足しています: {c}")
        if c["operation"] not in ("set", "delta"):
            raise ValueError(f"thickoflayer_choices の operation は set か delta のみ指定できます: {c}")

    backup_dir = config.get("backup_dir") or None
    if backup_dir:
        if not os.path.isabs(backup_dir):
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(config_path)), backup_dir)
        backup_dir = os.path.normpath(backup_dir)

    return targets, thr_choices, area_choices, thickness_choices, backup_dir


def safe_input(prompt=""):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\n入力を中断しました。終了します。")
        sys.exit(0)


SKIP = object()  # 「変更しない」を表す番兵


def choose_from_list(items, label, display, allow_skip=False, skip_label="変更しない(そのまま)"):
    print(f"\n== {label} ==")
    for i, item in enumerate(items, 1):
        print(f"  {i}: {display(item)}")
    skip_num = len(items) + 1
    if allow_skip:
        print(f"  {skip_num}: {skip_label}")
    print("  0: 終了")
    while True:
        raw = safe_input("番号を選んでください: ").strip()
        if raw == "0":
            print("終了します。")
            sys.exit(0)
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(items):
                return items[n - 1]
            if allow_skip and n == skip_num:
                return SKIP
        print("入力が正しくありません。もう一度入力してください。")


def fmt_num(n):
    if isinstance(n, float) and n.is_integer():
        return str(int(n))
    return str(n)


def detect_line_ending(text):
    idx = text.find("\n")
    if idx > 0 and text[idx - 1] == "\r":
        return "\r\n"
    return "\n"


def build_scanarea_block(pairs, nl):
    lines = [f"    ScanArea: [{nl}"]
    for pair in pairs:
        x, y = pair[0], pair[1]
        lines.append(f"      [ {fmt_num(x)}, {fmt_num(y)} ],{nl}")
    lines.append(f"    ]{nl}")
    return "".join(lines)


SCANPARAMBASE_RE = re.compile(r"^ScanParamBase: &ScanParamBase\r?\n(.*?)(?=^\S)", re.M | re.S)
SCANAREA_RE = re.compile(r"    ScanArea: \[\r?\n(?:.*?\r?\n)*?    \]\r?\n", re.S)
THRBINARY_RE = re.compile(r"    ThrBinary: (\S+)\r?\n")
THICKOFLAYER_RE = re.compile(r"    ThickOfLayer: (\S+)\r?\n")


def get_scanparambase_body(text):
    m = SCANPARAMBASE_RE.search(text)
    if not m:
        raise ValueError("ScanParamBase: &ScanParamBase が見つかりません。ファイル形式を確認してください。")
    body = m.group(1)
    if not SCANAREA_RE.search(body):
        raise ValueError("ScanParamBase 内に ScanArea が見つかりません。")
    if not THRBINARY_RE.search(body):
        raise ValueError("ScanParamBase 内に ThrBinary が見つかりません。")
    if not THICKOFLAYER_RE.search(body):
        raise ValueError("ScanParamBase 内に ThickOfLayer が見つかりません。")
    return m, body


def get_current_thrbinary(body):
    return int(THRBINARY_RE.search(body).group(1))


def get_current_thickoflayer(body):
    return float(THICKOFLAYER_RE.search(body).group(1))


def get_current_scanarea_text(body):
    return SCANAREA_RE.search(body).group(0).strip()


def compute_new_thrbinary(choice, current):
    if choice["operation"] == "set":
        return int(choice["value"])
    return int(current) + int(choice["value"])


def compute_new_thickoflayer(choice, current):
    if choice["operation"] == "set":
        return float(choice["value"])
    return float(current) + float(choice["value"])


def compute_backup_path(target_path, backup_dir, timestamp):
    """backup_dir が指定されていればそこに、なければ対象ファイルと同じフォルダにバックアップを作る。
    backup_dir にまとめる場合、複数の targets が同じファイル名(例: ninja_e71a.yaml)を
    使っていても区別できるよう、親フォルダ名を接頭辞として付ける。"""
    basename = os.path.basename(target_path)
    if not backup_dir:
        return f"{target_path}.bak_{timestamp}"
    parent_name = os.path.basename(os.path.dirname(target_path))
    prefix = f"{parent_name}_" if parent_name else ""
    return os.path.join(backup_dir, f"{prefix}{basename}.bak_{timestamp}")


def apply_changes(text, new_thrbinary, new_scanarea_pairs, new_thickoflayer=None):
    """new_thrbinary / new_scanarea_pairs / new_thickoflayer が None の場合はその項目を変更しない。"""
    m, body = get_scanparambase_body(text)
    nl = detect_line_ending(text)
    new_body = body

    if new_scanarea_pairs is not None:
        new_area_block = build_scanarea_block(new_scanarea_pairs, nl)
        new_body = SCANAREA_RE.sub(lambda _: new_area_block, new_body, count=1)

    if new_thrbinary is not None:
        new_thr_line = f"    ThrBinary: {int(new_thrbinary)}{nl}"
        new_body = THRBINARY_RE.sub(lambda _: new_thr_line, new_body, count=1)

    if new_thickoflayer is not None:
        new_thickness_line = f"    ThickOfLayer: {float(new_thickoflayer):.1f}{nl}"
        new_body = THICKOFLAYER_RE.sub(lambda _: new_thickness_line, new_body, count=1)

    header = text[m.start():m.start() + (len(m.group(0)) - len(body))]
    return text[:m.start()] + header + new_body + text[m.end():]


def main():
    base_dir = get_base_dir()
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "config.yaml")

    print("=== ScanParamEditor ===")
    print(f"設定ファイル: {config_path}")

    try:
        targets, thr_choices, area_choices, thickness_choices, backup_dir = load_config(config_path)
    except Exception as e:
        print(f"\n[エラー] 設定ファイルの読み込みに失敗しました: {e}")
        safe_input("Enterキーで終了します...")
        sys.exit(1)

    target = choose_from_list(targets, "書き換え対象ファイルを選択", lambda t: f"{t['name']}  [{t['path']}]")
    target_path = target["path"]

    if not os.path.isfile(target_path):
        print(f"\n[エラー] 対象ファイルが見つかりません: {target_path}")
        safe_input("Enterキーで終了します...")
        sys.exit(1)

    with open(target_path, encoding="utf-8", newline="") as f:
        original_text = f.read()

    try:
        _, body = get_scanparambase_body(original_text)
        current_thr = get_current_thrbinary(body)
        current_area_text = get_current_scanarea_text(body)
        current_thickness = get_current_thickoflayer(body)
    except Exception as e:
        print(f"\n[エラー] ファイルの解析に失敗しました: {e}")
        safe_input("Enterキーで終了します...")
        sys.exit(1)

    print(f"\n現在の値:\n{current_area_text}\n    ThrBinary: {current_thr}\n    ThickOfLayer: {current_thickness}")

    defaults = target.get("defaults")
    use_defaults = False
    if defaults:
        mode = choose_from_list(
            ["デフォルトに戻す(ThrBinary/ScanArea/ThickOfLayerを全て既定値にする)", "個別に選択する"],
            "操作を選択", lambda s: s,
        )
        use_defaults = mode.startswith("デフォルトに戻す")

    if use_defaults:
        new_thrbinary = int(defaults["ThrBinary"])
        new_scanarea = defaults["ScanArea"]
        new_thickness = float(defaults["ThickOfLayer"])
        thr_choice_desc = area_choice_desc = thickness_choice_desc = "デフォルトに戻す"
    else:
        # ThrBinary の変更(症状に対する対応)を選ぶ
        new_thrbinary = None
        thr_choice_desc = "変更しない"
        if thr_choices:
            choice = choose_from_list(
                thr_choices, "ThrBinary の変更(該当する症状/対応を選択)",
                lambda c: f"{c['name']}  ({'=' if c['operation'] == 'set' else '+' if int(c['value']) >= 0 else ''}{c['value']})",
                allow_skip=True,
            )
            if choice is not SKIP:
                new_thrbinary = compute_new_thrbinary(choice, current_thr)
                thr_choice_desc = choice["name"]
        else:
            print("\n(thrbinary_choices が設定されていないため ThrBinary は変更しません)")

        # ScanArea の変更を選ぶ
        new_scanarea = None
        area_choice_desc = "変更しない"
        if area_choices:
            choice = choose_from_list(
                area_choices, "ScanArea の変更(該当する選択肢を選択)",
                lambda c: f"{c['name']}  ScanArea={c['ScanArea']}",
                allow_skip=True,
            )
            if choice is not SKIP:
                new_scanarea = choice["ScanArea"]
                area_choice_desc = choice["name"]
        else:
            print("\n(scanarea_choices が設定されていないため ScanArea は変更しません)")

        # ThickOfLayer の変更を選ぶ
        new_thickness = None
        thickness_choice_desc = "変更しない"
        if thickness_choices:
            choice = choose_from_list(
                thickness_choices, "ThickOfLayer の変更(該当する選択肢を選択)",
                lambda c: f"{c['name']}  ({'=' if c['operation'] == 'set' else '+' if float(c['value']) >= 0 else ''}{c['value']})",
                allow_skip=True,
            )
            if choice is not SKIP:
                new_thickness = compute_new_thickoflayer(choice, current_thickness)
                thickness_choice_desc = choice["name"]
        else:
            print("\n(thickoflayer_choices が設定されていないため ThickOfLayer は変更しません)")

    if new_thrbinary is None and new_scanarea is None and new_thickness is None:
        print("\n変更がありません。終了します。")
        safe_input("Enterキーで終了します...")
        return

    try:
        new_text = apply_changes(original_text, new_thrbinary, new_scanarea, new_thickness)
        _, new_body = get_scanparambase_body(new_text)
        new_thr_shown = get_current_thrbinary(new_body)
        new_area_shown = get_current_scanarea_text(new_body)
        new_thickness_shown = get_current_thickoflayer(new_body)
    except Exception as e:
        print(f"\n[エラー] ファイルの書き換えに失敗しました: {e}")
        safe_input("Enterキーで終了します...")
        sys.exit(1)

    print("\n== 変更内容の確認 ==")
    print(f"対象ファイル    : {target_path}")
    print(f"ThrBinary対応   : {thr_choice_desc}")
    print(f"ScanArea対応    : {area_choice_desc}")
    print(f"ThickOfLayer対応: {thickness_choice_desc}")
    print("--- 変更前 ---")
    print(current_area_text)
    print(f"    ThrBinary: {current_thr}")
    print(f"    ThickOfLayer: {current_thickness}")
    print("--- 変更後 ---")
    print(new_area_shown)
    print(f"    ThrBinary: {new_thr_shown}")
    print(f"    ThickOfLayer: {new_thickness_shown}")

    ans = safe_input("\nこの内容で書き換えますか？ (y/N): ").strip().lower()
    if ans != "y":
        print("キャンセルしました。ファイルは変更していません。")
        safe_input("Enterキーで終了します...")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = compute_backup_path(target_path, backup_dir, timestamp)
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
    with open(backup_path, "w", encoding="utf-8", newline="") as f:
        f.write(original_text)
    print(f"バックアップを作成しました: {backup_path}")

    with open(target_path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print(f"書き換えが完了しました: {target_path}")

    safe_input("Enterキーで終了します...")


if __name__ == "__main__":
    main()
