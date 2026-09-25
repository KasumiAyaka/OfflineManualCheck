#!/usr/bin/env python3
"""Build report.html summarizing analyze.py's results, from the CSVs it wrote.

Usage:
    python make_report.py [--outdir .]
"""
import argparse
import os

import pandas as pd

METRIC_LABELS = {
    "scale_x": "scale_x = sqrt(a²+c²)",
    "scale_y": "scale_y = sqrt(b²+d²)",
    "scale_dev": "scale_dev = max(|scale_x-1|, |scale_y-1|)",
    "det": "det = a·d - b·c",
    "det_dev": "det_dev = |det - 1|",
    "rotation_deg": "rotation_deg = atan2(c, a) [deg]",
    "nonortho": "nonortho = (a·b + c·d) / (scale_x·scale_y)",
    "translation_mag": "translation_mag = sqrt(e²+f²) [um]",
}

PRIMARY_METRICS = ["scale_dev", "det_dev", "rotation_deg", "translation_mag"]


def fmt(x, sig=4):
    try:
        return f"{float(x):.{sig}g}"
    except (TypeError, ValueError):
        return str(x)


def df_to_html_table(df, float_cols=None, css_class="data-table"):
    float_cols = float_cols or []
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in df.columns:
            v = r[c]
            cells.append(f"<td>{fmt(v) if c in float_cols else v}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table class="{css_class}"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def build_breakdown_table(unique_df):
    tbl = (
        unique_df.groupby(["ecc", "scan_type", "category", "outcome"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ("OK", "FAIL"):
        if col not in tbl.columns:
            tbl[col] = 0
    tbl = tbl[["ecc", "scan_type", "category", "OK", "FAIL"]]
    total = pd.DataFrame([{
        "ecc": "合計", "scan_type": "", "category": "",
        "OK": tbl["OK"].sum(), "FAIL": tbl["FAIL"].sum(),
    }])
    tbl = pd.concat([tbl, total], ignore_index=True)
    return df_to_html_table(tbl, css_class="data-table breakdown")


def build_summary_table(stats_df):
    sub = stats_df[stats_df["metric"].isin(PRIMARY_METRICS)].copy()
    sub["metric"] = sub["metric"].map(lambda m: METRIC_LABELS.get(m, m))
    cols = ["metric", "outcome", "n", "mean", "std", "median", "p05", "p95", "min", "max"]
    sub = sub[cols]
    float_cols = ["mean", "std", "median", "p05", "p95", "min", "max"]
    return df_to_html_table(sub, float_cols=float_cols)


def build_threshold_table(thr_df):
    df = thr_df.copy()
    df = df[["metric", "rule", "accuracy", "precision", "recall", "tp", "fp", "fn", "tn"]]
    float_cols = ["accuracy", "precision", "recall"]
    return df_to_html_table(df, float_cols=float_cols, css_class="data-table thr-table")


def pick_representative(unique_df, outcome):
    """The row of the given outcome whose det_dev is closest to that
    outcome's own median det_dev - i.e. a typical, non-outlier example."""
    sub = unique_df[unique_df["outcome"] == outcome]
    med = sub["det_dev"].median()
    idx = (sub["det_dev"] - med).abs().idxmin()
    return unique_df.loc[idx]


def build_example_card(row, outcome, threshold):
    a, b, c, d = row["AffineParam_a"], row["AffineParam_b"], row["AffineParam_c"], row["AffineParam_d"]
    e, f = row["AffineParam_e"], row["AffineParam_f"]
    badge = "fail" if outcome == "FAIL" else "ok"
    verdict = "FAIL" if row["det_dev"] > threshold else "OK"
    real_judgment = "実際に PatternMatchFailed へ移動" if outcome == "FAIL" else "実際に ChkRes で j:OK と判定"
    location = row["source_dir"]
    return f"""
    <div class="example-card">
      <div class="example-head">
        <span class="badge {badge}">{outcome}</span>
        <span class="example-title">ECC{row['ecc']} {row['scan_type']} {row['category']} Event{int(row['event']):05d}/PL{int(row['pl']):03d}</span>
      </div>
      <p class="example-path"><code>{location}\\tomographic_images.json</code></p>
      <p class="example-formula">AffineParam = [a, b, c, d, e, f] = [{fmt(a,6)}, {fmt(b,6)}, {fmt(c,6)}, {fmt(d,6)}, {fmt(e,6)}, {fmt(f,6)}]</p>
      <table class="data-table example-table">
        <thead><tr><th>指標</th><th>計算式</th><th>数値</th></tr></thead>
        <tbody>
          <tr><td>scale_x</td><td>√(a²+c²)</td><td>{fmt(row['scale_x'],5)}</td></tr>
          <tr><td>scale_y</td><td>√(b²+d²)</td><td>{fmt(row['scale_y'],5)}</td></tr>
          <tr><td>det</td><td>a·d − b·c</td><td>{fmt(row['det'],5)}</td></tr>
          <tr class="highlight"><td><b>det_dev</b></td><td>|det − 1|</td><td><b>{fmt(row['det_dev'],4)}</b></td></tr>
          <tr><td>scale_dev</td><td>max(|scale_x−1|, |scale_y−1|)</td><td>{fmt(row['scale_dev'],4)}</td></tr>
          <tr><td>rotation_deg</td><td>atan2(c, a)</td><td>{fmt(row['rotation_deg'],4)}°</td></tr>
        </tbody>
      </table>
      <p class="example-verdict">
        判定: det_dev = {fmt(row['det_dev'],4)} {'&gt;' if verdict=='FAIL' else '&le;'} 0.0025 &rarr;
        <b class="badge {badge}">{verdict}</b>({real_judgment})
      </p>
    </div>
    """


def build_flagged_table(flagged_df):
    df = flagged_df.copy()
    df["event"] = df["event"].apply(lambda v: f"{int(v):05d}")
    df["pl"] = df["pl"].apply(lambda v: f"{int(v):03d}")
    df["判定"] = df["agrees_with_human"].map(
        lambda ok: '<span class="badge fail">一致 (FAIL)</span>' if ok else '<span class="badge ok">誤検出 (実際はOK)</span>'
    )
    df = df.rename(columns={
        "ecc": "ECC", "scan_type": "scan_type", "category": "category",
        "event": "Event", "pl": "PL", "det_dev": "det_dev",
    })
    df = df[["ECC", "scan_type", "category", "Event", "PL", "det_dev", "判定"]]
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in df.columns:
            v = r[c]
            cells.append(f"<td>{fmt(v) if c == 'det_dev' else v}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table class="data-table flagged-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def build_unreviewed_table(scored_df, label):
    df = scored_df.copy()
    df = df[df["predicted"] == "FAIL"].sort_values(["pl", "event"])
    if df.empty:
        return f"<p>{label}: 全{len(scored_df)}件、基準でFAILと予測されたものは<b>0件</b>。</p>"
    df["Event"] = df["event"].apply(lambda v: f"{int(v):05d}")
    df["PL"] = df["pl"].apply(lambda v: f"{int(v):03d}")
    df = df[["Event", "PL", "det_dev"]]
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        cells = [f"<td>{r['Event']}</td>", f"<td>{r['PL']}</td>", f"<td>{fmt(r['det_dev'])}</td>"]
        rows.append(f"<tr>{''.join(cells)}</tr>")
    table = f'<table class="data-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    return f"<p>{label}: 全{len(scored_df)}件中、基準でFAILと予測: <b>{len(df)}件</b></p>{table}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()
    outdir = args.outdir

    unique_df = pd.read_csv(os.path.join(outdir, "unique_scans.csv"))
    stats_df = pd.read_csv(os.path.join(outdir, "summary_stats.csv"))
    thr_df = pd.read_csv(os.path.join(outdir, "threshold_scan.csv"))

    n_ok = int((unique_df["outcome"] == "OK").sum())
    n_fail = int((unique_df["outcome"] == "FAIL").sum())
    n_dirs = len(pd.read_csv(os.path.join(outdir, "records.csv")))

    detdev_row = thr_df[thr_df["metric"] == "det_dev"].iloc[0]
    scaledev_row = thr_df[thr_df["metric"] == "scale_dev"].iloc[0]

    breakdown_html = build_breakdown_table(unique_df)
    summary_html = build_summary_table(stats_df)
    threshold_html = build_threshold_table(thr_df)

    det_threshold = float(detdev_row["cut"])
    fail_example = pick_representative(unique_df, "FAIL")
    ok_example = pick_representative(unique_df, "OK")
    examples_html = build_example_card(fail_example, "FAIL", det_threshold) + build_example_card(ok_example, "OK", det_threshold)

    flagged_path = os.path.join(outdir, "flagged.csv")
    flagged_section = ""
    if os.path.isfile(flagged_path):
        flagged_df = pd.read_csv(flagged_path)
        n_flag = len(flagged_df)
        n_tp = int(flagged_df["agrees_with_human"].sum())
        n_fp = n_flag - n_tp
        flagged_section = f"""
  <h2>基準でFAILと判定される一覧(レビュー済みデータ)</h2>
  <p>det_dev &gt; {det_threshold:.4g} を <code>records.csv</code>(ディレクトリ単位)に適用した結果。全{n_flag}件のうち、
    実際の目視判定もFAILで一致するもの {n_tp}件、実際はOKなのに誤ってFAILと判定したもの {n_fp}件。</p>
  <details>
    <summary style="cursor:pointer; color:var(--accent); font-weight:600; margin-bottom:10px;">全{n_flag}件の詳細を表示</summary>
    <div class="table-wrap" style="margin-top:10px;">
      {build_flagged_table(flagged_df)}
    </div>
  </details>
"""

    fts_ref_path = os.path.join(outdir, "scored_ECC6_FTS_Ref.csv")
    unreviewed_section = ""
    if os.path.isfile(fts_ref_path):
        fts_ref_df = pd.read_csv(fts_ref_path)
        unreviewed_section = f"""
  <h2>未レビュー領域への基準適用(予測のみ)</h2>
  <p class="note">
    以下のディレクトリは <code>ChkRes.txt</code>(目視判定)・<code>PatternMatchFailed</code>(移動記録)のいずれも存在せず、
    <b>これまで一度も人の目視レビューが行われていない</b>。基準による予測のみで、実際の目視判定との一致/不一致は確認できない。
    (<code>ScanData\\UTS\\ECC6\\Ref\\IMG</code> は <code>ChkRes\\ECC6UTS_Ref.txt</code> の追加により、この節ではなく上のレビュー済みデータ側に統合された。)
  </p>
  <p><code>ScanData\\FTS\\ECC6\\Ref</code></p>
  {build_unreviewed_table(fts_ref_df, "FTS ECC6 Ref")}
"""

    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>断層画像取得 成功/失敗判定基準の検討</title>
<style>
  :root {{
    --ink: #1a1a1a;
    --ink-soft: #4a4a4a;
    --muted: #767676;
    --line: #dfe1e6;
    --surface: #ffffff;
    --page: #f5f6f8;
    --accent: #2a5db0;
    --ok: #2a78d6;
    --fail: #d9622b;
    --ok-soft: #eaf1fb;
    --fail-soft: #fdece3;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--page);
    color: var(--ink);
    font-family: "Yu Gothic", "Meiryo", "Segoe UI", -apple-system, sans-serif;
    line-height: 1.7;
  }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 40px 28px 80px; }}
  h1 {{ font-size: 26px; margin: 0 0 6px; }}
  h2 {{ font-size: 19px; margin: 44px 0 14px; padding-top: 18px; border-top: 1px solid var(--line); }}
  h2:first-of-type {{ border-top: none; padding-top: 0; }}
  .subtitle {{ color: var(--muted); font-size: 14px; margin: 0 0 32px; }}
  p {{ color: var(--ink-soft); }}
  code {{ background: #eef0f3; padding: 2px 6px; border-radius: 4px; font-size: 0.92em; }}

  .callout {{
    background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--accent);
    border-radius: 8px; padding: 20px 24px; margin: 18px 0;
  }}
  .callout .rule {{ font-size: 17px; font-weight: 600; color: var(--accent); margin-bottom: 10px; }}
  .metrics-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 12px; }}
  .metric-pill {{
    background: var(--page); border: 1px solid var(--line); border-radius: 8px;
    padding: 10px 16px; font-size: 13px; color: var(--ink-soft);
  }}
  .metric-pill b {{ display: block; font-size: 20px; color: var(--ink); font-weight: 700; }}

  table.data-table {{
    width: 100%; border-collapse: collapse; font-size: 13.5px; background: var(--surface);
    border: 1px solid var(--line); border-radius: 8px; overflow: hidden;
  }}
  table.data-table th, table.data-table td {{
    padding: 8px 12px; border-bottom: 1px solid var(--line); text-align: right;
  }}
  table.data-table th {{ background: #eef1f5; text-align: right; font-weight: 600; color: var(--ink-soft); }}
  table.data-table th:first-child, table.data-table td:first-child {{ text-align: left; }}
  table.data-table td:nth-child(2), table.data-table th:nth-child(2) {{ text-align: left; }}
  table.data-table tr:last-child td {{ border-bottom: none; }}
  .breakdown td:nth-child(3), .breakdown th:nth-child(3) {{ text-align: left; }}
  .table-wrap {{ overflow-x: auto; }}

  .badge {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .badge.ok {{ background: var(--ok-soft); color: var(--ok); }}
  .badge.fail {{ background: var(--fail-soft); color: var(--fail); }}

  .fig-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 18px 0; }}
  .fig-grid.single {{ grid-template-columns: 1fr; max-width: 560px; }}
  figure {{ margin: 0; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }}
  figure img {{ width: 100%; display: block; border-radius: 4px; }}
  figcaption {{ font-size: 12.5px; color: var(--muted); margin-top: 8px; text-align: center; }}

  .example-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 18px 0; }}
  .example-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 18px 20px; }}
  .example-head {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }}
  .example-title {{ font-weight: 600; font-size: 14.5px; }}
  .example-path {{ font-size: 12px; color: var(--muted); margin: 0 0 10px; word-break: break-all; }}
  .example-formula {{ font-size: 12.5px; color: var(--ink-soft); background: var(--page); border-radius: 6px; padding: 8px 10px; margin: 0 0 12px; }}
  table.example-table th, table.example-table td {{ text-align: right; }}
  table.example-table th:first-child, table.example-table td:first-child {{ text-align: left; }}
  table.example-table th:nth-child(2), table.example-table td:nth-child(2) {{ text-align: left; }}
  table.example-table tr.highlight td {{ background: #f4f8fd; }}
  .example-verdict {{ margin: 14px 0 0; font-size: 13.5px; }}
  @media (max-width: 700px) {{ .example-grid {{ grid-template-columns: 1fr; }} }}

  table.flagged-table {{ font-size: 12.5px; }}
  table.flagged-table td, table.flagged-table th {{ padding: 6px 10px; }}
  details summary::-webkit-details-marker {{ display: none; }}

  ul {{ color: var(--ink-soft); }}
  .note {{ background: #fff9ec; border: 1px solid #f0dfae; border-radius: 8px; padding: 14px 18px; color: #6b5323; font-size: 14px; }}
  footer {{ margin-top: 50px; color: var(--muted); font-size: 12.5px; }}
  @media (max-width: 700px) {{ .fig-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">

  <h1>断層画像取得 成功/失敗判定基準の検討</h1>
  <p class="subtitle">AffineParam(lens/stage画像の位置合わせアフィン変換)を使い、目視判定(check_quality.py)の代わりになる数値基準を探した結果</p>

  <h2>データ</h2>
  <p>
    <span class="badge fail">FAIL</span> = <code>ScanData\\PatternMatchFailed\\...</code> に移動された(取得失敗と判断された)ディレクトリ、
    <span class="badge ok">OK</span> = <code>ScanData\\ChkRes\\*.txt</code> で最終的に <code>j:OK</code> と判定され、現在も <code>ScanData\\&lt;UTS|FTS&gt;\\...</code> に残っているディレクトリ。
    ディレクトリ単位では全 {n_dirs} 件。
  </p>
  <p class="note">
    <b>重要な前提:</b> AffineParamはEvent(飛跡)ごとの値ではなく、<b>同じPL・同じZone(物理走査エリア)を通る全Eventで完全に同一の値</b>になることを確認した
    (例: FTS ECC4 PL064 Zone5 を通る Event00633・Event03933・Event06107・Event07277 は6つの数値が1ビットも違わず一致)。
    そのため統計は「(ECC, scan_type, IMG/Ref, PL, AffineParamの値)が一意になるスキャン単位」に重複除去してから取っている。
    重複除去後は <b>{n_ok + n_fail} 件</b>(OK {n_ok} 件 / FAIL {n_fail} 件)。
  </p>

  <div class="table-wrap">
    {breakdown_html}
  </div>

  <h2>結論: 使える基準</h2>
  <div class="callout">
    <div class="rule">det_dev = |a·d − b·c − 1| &gt; 0.0025 なら FAIL、それ以下なら OK</div>
    <p style="margin:0;">アフィン行列の行列式が1からどれだけずれているかを見る、最もシンプルで強力な基準。</p>
    <div class="metrics-row">
      <div class="metric-pill"><b>{fmt(detdev_row['accuracy'],3)}</b>正解率 (accuracy)</div>
      <div class="metric-pill"><b>{fmt(detdev_row['recall'],3)}</b>FAIL検出率 (recall)</div>
      <div class="metric-pill"><b>{fmt(detdev_row['precision'],3)}</b>適合率 (precision)</div>
    </div>
  </div>
  <p>
    ほぼ同じ性能で <code>scale_dev = max(|scale_x−1|, |scale_y−1|)</code>(x/y方向の拡大率のずれ。
    <code>scale_x = sqrt(a²+c²)</code>, <code>scale_y = sqrt(b²+d²)</code>)を使うルール
    (<b>scale_dev &gt; 0.0031 なら FAIL</b>、accuracy {fmt(scaledev_row['accuracy'],3)} / recall {fmt(scaledev_row['recall'],3)} / precision {fmt(scaledev_row['precision'],3)})も使える。
  </p>
  <p>
    回転角(<code>rotation_deg</code>)は単独では検出率22.5%と弱いが、<b>|rotation_deg| &gt; 1度の場合は今回のデータで100%FAILだった</b>ため、
    「回転が大きければ確実にFAIL」という補助フィルタとして使える。
    一方、並進量(<code>translation_mag</code>、ステージ位置そのもの)はFAIL/OKで有意差がなく判定には使えない
    ―― これは想定通りで、手法の健全性を裏付ける結果でもある。
  </p>

  <h2>具体例: FAILとOKをそれぞれ1件</h2>
  <p>全データの中で、それぞれの集団の <b>det_devの中央値に最も近い</b>(極端な外れ値ではない)代表例を1件ずつ選び、計算過程を示す。</p>
  <div class="example-grid">
    {examples_html}
  </div>

  <div class="fig-grid">
    <figure><img src="hist_det_dev.png" alt="det_dev histogram"><figcaption>det_dev のFAIL/OKヒストグラム</figcaption></figure>
    <figure><img src="hist_scale_dev.png" alt="scale_dev histogram"><figcaption>scale_dev のFAIL/OKヒストグラム</figcaption></figure>
    <figure><img src="hist_rotation_deg.png" alt="rotation_deg histogram"><figcaption>rotation_deg のFAIL/OKヒストグラム</figcaption></figure>
    <figure><img src="scatter_scale.png" alt="scale scatter"><figcaption>scale_x vs scale_y 散布図</figcaption></figure>
  </div>

  <h2>指標ごとの記述統計(主要指標)</h2>
  <div class="table-wrap">
    {summary_html}
  </div>

  <h2>1変数しきい値ルールの性能(全指標)</h2>
  <div class="table-wrap">
    {threshold_html}
  </div>

  {flagged_section}
  {unreviewed_section}

  <h2>注意点</h2>
  <ul>
    <li>上記のしきい値でもFAILの約6%を見逃し、OKの約2%を誤ってFAILと判定する。目視確認では数値以外の情報(画像そのものの見た目)も考慮していると考えられるため、この基準は<b>目視確認の完全な代替ではなく、大部分を自動でスクリーニングし、境界線上のケースだけ目視確認する一次フィルタ</b>として使うのが適切。</li>
    <li>データの大部分はECC4のUTSから来ており、基準の妥当性は主にECC4に基づく。ECC6はFAILが3件(FTSは0件)と少ないため、ECC6や今後の他ECCへの一般化は追加データで確認するのが望ましい。</li>
  </ul>

  <h2>再現方法</h2>
  <p>作業ディレクトリ内で以下を順に実行すると、全てのCSV・プロット・このHTMLが再生成される。</p>
  <pre style="background:#eef0f3; padding:14px 18px; border-radius:8px; overflow-x:auto;"><code>python collect_data.py   # ScanData を読み、records.csv を作る
python analyze.py        # records.csv から統計・プロットを作る
python make_report.py    # このHTMLレポートを作る</code></pre>

  <footer>
    詳細な数値・生データは同ディレクトリ内の records.csv / unique_scans.csv / summary_stats.csv / threshold_scan.csv、
    経緯・方針の全文は README.md を参照。
  </footer>

</div>
</body>
</html>
"""

    out_path = os.path.join(outdir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
