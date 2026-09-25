# 断層画像取得の成功・失敗判定基準の検討(AffineParamベース)

## 目的

`check_quality.py` で目視により

- **FAIL**(取得失敗と判断): `ScanData\PatternMatchFailed\...` に移動されたもの
- **OK**(問題なしと判断): `ScanData\ChkRes\*.txt` で最終的に `j:OK` と判定され、現在も `ScanData\<UTS|FTS>\...` に残っているもの

の2集団に分けたデータについて、`tomographic_images.json` の `AffineParam`(lens画像とstage画像を重ね合わせるアフィン変換 `[a, b, c, d, e, f]`)などの数値から、目視に頼らず機械的に成功/失敗を判定できる基準があるかを調べた。

## 重要な前提: AffineParamは「Event単位」ではなく「(PL, Zone)単位」

調査の過程で、**AffineParamは個々のEvent(飛跡)ごとの値ではなく、同じPL・同じZone(物理的な走査エリア)を通った複数のEventで完全に同一の値になる**ことが分かった(例: FTS ECC4 PL064 Zone5 を通る `Event00633`, `Event03933`, `Event06107`, `Event07277` は6つの数値が1ビットも違わず一致し、同じPL064でもZone2の `Event12037` は異なる値になる)。

これはAffineParamが「その物理エリアのlens/stage画像の位置合わせがどれだけ上手くいったか」を表すスキャン側の量であり、たまたまそこを通った飛跡の特性ではないことを意味する。そのため、**統計はEvent/PLディレクトリ単位ではなく、(ECC, scan_type, IMG/Ref, PL, AffineParamの値)が一意になる「スキャン単位」に重複除去してから取る**必要がある(`analyze.py` が自動で行う)。重複除去前は1350件のディレクトリがあったが、重複除去後は897件のユニークなスキャンになった(OK 799件、FAIL 98件)。

**注意**: 同じ(PL, Zone)を通る複数のEventで、人の目視判定自体が割れる(一方はOK、他方はk:Retake/l:?)ケースが3グループ見つかっている。これは判定対象が「そのZoneのアフィン変換の質」ではなく「個々の候補飛跡のマッチング」であるためで、目視判定にも一定のばらつきがあることを示している(`analyze.py` 実行時に警告として表示される)。

## 結論: 使える基準

**`det_dev = |a*d - b*c - 1|`(アフィン行列の行列式が1からどれだけずれているか)** が最もシンプルかつ強力な判定基準になる。

> **det_dev > 0.0025 なら FAIL、それ以下なら OK** と判定するルールで
> - 正解率(accuracy): **98.4%**
> - FAILを正しく検出できる割合(recall): **94.9%**(98件中93件を検出)
> - FAILと判定したものが実際にFAILである割合(precision): **91.2%**

ほぼ同じ性能で、より直感的な **`scale_dev = max(|scale_x-1|, |scale_y-1|)`**(x方向・y方向のスケール(拡大率)が1からどれだけずれているか。ここで `scale_x = sqrt(a²+c²)`, `scale_y = sqrt(b²+d²)`)を使うルール(**scale_dev > 0.0031 なら FAIL**)でも accuracy 98.2%, recall 92.9%, precision 91.0% と同程度の性能が出る。

いずれの指標も「拡大率がぴったり1(=lensとstageの画像が同じ大きさで重なる)ならOK、大きくずれるほどFAILの可能性が高い」という直感に合致する。

回転角(`rotation_deg`)は単独では recall 20.4%(98件中20件しか検出できない)と弱いが、**`|rotation_deg| > 1度` の場合は今回のデータでは100%(precision 1.0)FAILだった**ため、「回転が大きい場合は確実にFAIL」という補助的なフィルタとして使える。

並進量(`translation_mag`、ステージ位置そのもの)はFAIL/OKで有意差がなく(accuracy 89.1%は「全部OKと予測」と同水準)、判定には使えない ―― これは想定通りで、手法の健全性を裏付ける結果でもある。

### 数値の目安(記述統計より、詳細は `summary_stats.md`)

`det_dev` を directory 単位(重複除去前、`records.csv`)で0〜0.01の範囲にbin幅0.0002で拡大すると(`plot_det_dev_zoom.py`、`hist_det_dev_zoom.png`)、OK集団はほぼ全て0.0000〜0.0012に密集し最大値は0.00252、FAILは0.0006〜0.0075の間に薄く広がる(0.0025〜0.0063の間はどちらも0件の空白地帯がある)。

### 完全な基準ではない点(注意)

上記のしきい値でもFAILの一部を見逃し、OKの一部を誤ってFAILと判定する(詳細件数は `threshold_scan.md` を参照)。目視確認では、これらの「境界線上」のケースについて数値以外の情報(画像そのものの見た目)も考慮して判断していると考えられる。したがって、この基準は**目視チェックを完全に代替するものではなく、大部分を自動でスクリーニングし、境界線上のケースだけ目視確認する、という一次フィルタとして使うのが適切**。

一方で、det_devが極端に低い(OK集団の密集域に埋もれている)にもかかわらずFAIL判定されているケースについては、**むしろ目視判定の方が誤っている可能性がある**候補として個別に確認する価値がある(`det_dev_zoom_list.csv` 参照。実際にECC4の6件をこの方法で見直し、5件をOK判定に修正済み)。

## ディレクトリの内容

| ファイル | 内容 |
|---|---|
| `collect_data.py` | ChkRes判定(k:Retake/l:? → FAIL、j:OK → OK)を軸に、両集団のディレクトリを現在の実際の場所(`PatternMatchFailed` に移動済みか、元の `<UTS\|FTS>` 側に残っているか)から特定し、`tomographic_images.json` を読み込んで `records.csv` を作るスクリプト。`ChkRes\` 配下はサブフォルダも再帰的に探索する |
| `records.csv` | ディレクトリ単位の生データ(1350行) |
| `analyze.py` | `records.csv` から派生指標を計算し、重複除去・統計・しきい値探索・プロットを行うスクリプト |
| `unique_scans.csv` | 重複除去後のユニークスキャン単位データ(897行、派生指標付き) |
| `summary_stats.csv` / `.md` | 指標ごとのFAIL/OK記述統計(平均・標準偏差・分位点など) |
| `threshold_scan.csv` / `.md` | 各指標を1変数しきい値ルールにした場合の正解率/precision/recall |
| `hist_*.png` | 指標ごとのFAIL/OKヒストグラム(8種類) |
| `scatter_scale.png` | scale_x vs scale_y の散布図 |
| `list_flagged.py` / `flagged.csv` | det_dev基準を`records.csv`全件に適用し、FAILと判定される(ECC, Event, PL)を一覧化(目視判定との一致/誤検出を付記) |
| `plot_det_dev_zoom.py` / `hist_det_dev_zoom.png` / `det_dev_zoom_list.csv` | det_dev ≤ 0.01 の範囲をbin幅0.0002で拡大し、境界線上の個別ケースを特定するためのツール |
| `score_directory.py` / `scored_ECC6_FTS_Ref.csv` | ChkRes/PatternMatchFailedの記録が無い(未レビューの)任意ディレクトリに基準を直接適用し、予測のみを出す汎用ツール |
| `make_report.py` / `report.html` | 上記の結果一式をまとめたHTMLレポートを生成 |

## 再現方法

```
python collect_data.py         # ScanData を読み、records.csv を作る
python analyze.py              # records.csv から統計・プロットを作る
python list_flagged.py         # 基準でFAILと判定される一覧を作る
python plot_det_dev_zoom.py    # det_dev<=0.01 の拡大ヒストグラムを作る
python make_report.py          # report.html を作る
```

`--scandata-root` / `--records` / `--outdir` で入出力先を変更できる。データが更新された場合(新たにPatternMatchFailedへの振り分けやChkRes判定が追加された場合)は、これらを再実行すれば全ての集計・プロット・レポートが更新される。

## データの内訳(ユニークスキャン単位)

| ECC | scan_type | category | OK | FAIL |
|---|---|---|---|---|
| 4 | UTS | IMG | 148 | 39 |
| 4 | UTS | Ref/IMG | 150 | 36 |
| 4 | FTS | IMG | 62 | 4 |
| 4 | FTS | Ref/IMG | 59 | 4 |
| 6 | UTS | IMG | 181 | 9 |
| 6 | UTS | Ref/IMG | 179 | 6 |
| 6 | FTS | IMG | 20 | 0 |
| **合計** | | | **799** | **98** |

ECC6のUTS Ref/IMGは、目視レビュー結果が `ChkRes\ECC6UTS_Ref.txt` に追加されたことで新たにデータセットに加わった(以前は未レビューだったため`score_directory.py`による予測のみを別途示していたが、今回のレビューで解消された)。ECC6のFTS Refのみ、現時点でもChkRes判定が存在せず未レビューのまま
(`ScanData\FTS\ECC6\Ref`、`score_directory.py` で基準を直接適用した予測結果は `scored_ECC6_FTS_Ref.csv` / `report.html` 参照)。
