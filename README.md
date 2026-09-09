# ManualCheck

NINJA実験 E71a のマニュアルチェック(手動確認)作業用ディレクトリ。ScanDataから対象イベントを抽出し、飛跡を外挿・整理して、チェックシート(LaTeX/PDF)を作るまでのパイプラインを管理している。

## 1. ディレクトリ構造

```
ManualCheck/
├─ Check_TakenIMG.bat        撮影済み画像の確認用PDFを作るバッチ(単独ツール)
├─ ManualCheck_EventList/    ECCごとのチェック対象イベントIDリスト(water/iron)、生成バッチ
├─ Momch/                    チェック対象イベントだけを抜き出した momch ファイル
├─ Pred/                     各イベント・各飛跡をPL方向に外挿した予測値(ev???.txt)、ECC別/water・iron別
├─ TrackList/                predをPLごとにまとめ、参照飛跡を突き合わせた最終的なTrackList・btrklist
├─ TrackList0/                do_03の中間生成物(PL分割前のTrackList、Divide_by_pl.py の出力など)
├─ src/                      パイプラインで使う実行ファイル(.exe)とローカル用バッチ(mkpred.bat)
├─ tools/                    パイプライン本体のバッチ(do_01〜do_04)とPythonスクリプト群
│  ├─ CheckImg/               チェック用PDF生成スクリプト
│  ├─ MakeLatexScript/        btrklist → LaTeXマクロ変換スクリプト(btrklist_to_pl.py)
│  └─ MakeTrackList/          predのマージ・PL分割スクリプト(MakePred.py, Divide_by_pl.py)
├─ Log/                      チェックシート用LaTeXソース・生成PDF・texスタイルファイル
├─ github_repository_memo.txt  src配下のexeがどのGitHubリポジトリのビルド物かのメモ
└─ .gitignore                 このリポジトリで管理しない大容量フォルダの指定
```

**git管理していないフォルダ**(`.gitignore` で除外、いずれも生データや大容量バイナリのため):

- `Demo/`
- `ScanData/` — スキャン画像本体・生画像チェック結果など
- `ECC6/` — ECC6専用の作業ディレクトリ(画像フォルダ `IMG` に800MB超のデータを含む)
- `NINJA_TrackList/`

## 2. バッチファイルの説明

パイプラインの主要な流れは `tools\do_01`〜`do_04` の順に実行する(すべて `ECCnum` を第1引数に取る)。

### `tools\do_01_pickup_events.bat <ECCnum>`
`ManualCheck_EventList\ECC{num}water.txt` / `ECC{num}iron.txt`(チェック対象イベントIDのリスト、あらかじめ `ManualCheck_EventList\make_event_list.bat` で作成しておく)を使い、`src\pickup_selected_event_from_momch.exe` で元の大きな momch ファイルから対象イベントだけを抜き出し、`Momch\ECC{num}water.momch` / `ECC{num}iron.momch` を作る。

### `tools\do_02_master_make_momch_and_pred.bat <ECCnum> <ECC-drive-letter>`
1. 上記のイベント抽出処理(`tools\do_01_pickup_events.bat`)を呼び出す。
2. `mk_only_muon_momch.exe` でミューオンのみに絞り、`apply_PLcut.exe` で PL130 までにカットした momch(`Momch\ECC{num}iron_muononly_PLcut.momch` など)を作る。
3. `mkpred.bat`(`Make_man_chk_pred.exe` のラッパー、外部パス上のもの)を起動し、各飛跡をvertexの反対側にPL3枚分外挿した予測値を `Pred\ECC{num}\iron\` / `water\` に出力する。
4. カット前の中間 momch ファイルを削除する。

### `tools\do_03_master_maketracklist.bat <ECCnum> <ECC-drive-letter>`
1. `tools\MakeTrackList\MakePred.py` で `Pred\ECC{num}\iron`・`water` の予測値ファイル群を1つのテキスト(`TrackList0\TrackList{num}.txt`)にまとめる。
2. `tools\MakeTrackList\Divide_by_pl.py` でPLごとのyamlファイル(`TrackList0\ECC{num}\TrackList\PL???.yaml`)に分割する。
3. `Pickup_reference_track_for_each_track.exe` で各予測飛跡に対応する参照飛跡(基準となる実飛跡)を突き合わせ、`TrackList\ECC{num}\` と `TrackList\btrklist{num}.txt` を作る。
4. `btrklist{num}_rawidmap.txt` からPL番号の一覧を作り、`TrackList\PLlist{num}.txt` として重複除去・ソート済みで出力する。

### `tools\do_04_make_latexscript_for_logsheet.bat <ECCnum>`
`tools\MakeLatexScript\btrklist_to_pl.py` を使って `TrackList\btrklist{num}.txt` を LaTeX マクロ形式(`\PL{...}{...}{...}{...}` / `\Events{...}`)に変換し、チェックシート(`Log\` 配下の `.tex`)に組み込む素材を作る。

### その他の単独バッチ
- **`Check_TakenIMG.bat <日付等>`**: `ScanData` 配下のFTS/UTS画像チェック結果からPDF(`ScanData\FTS_IMG_*.pdf` など)を作る、撮影後の目視確認用ツール。
- **`ManualCheck_EventList\make_event_list.bat <ECCnum>`**: 外部の解析結果(`vtxpos_chk.txt`)を gawk でフィルタし、チェック対象となるイベントIDのリスト(`ECC{num}water.txt` / `iron.txt`)を作る。do_01の前段。
- **`src\mkpred.bat`**: `Make_man_chk_pred.exe` を呼ぶだけのラッパー(momchファイルとArea0のパスを渡すと、各飛跡をPL3枚分外挿した予測値をイベントごとのファイルに出力する)。
- **`tools\decompress_fvxx_for_all_area_PL016to133.bat <ドライブレター> <ECCnum>`**: PL016〜PL133・Area1〜6の圧縮スキャンデータ(`f{pl}2_thick_0.vxx`)を一括で解凍する独立ユーティリティ。

## 3. その他の情報

- **`src/` の実行ファイルについて**: `src\apply_PLcut.exe` や `Pickup_reference_track_for_each_track.exe` はこのリポジトリにも置いてあるが、`do_02`/`do_03` は実際にはこのマシン上の外部パス(`C:\Users\kasumi\source\repos\...\Release\...exe`)を直接呼んでいる箇所がある。ビルドを更新した場合は `src/` 配下のコピーも手動で更新する必要がある。
- **`github_repository_memo.txt`**: `src/` の各exeがどのGitHubリポジトリ(`MuonAnalysis`, `E71a_analysis_kasumi_local` など)のビルド物かをまとめたメモ。ビルド元を追いたいときに参照する。
- **`Pred\memo.txt`**: ECCごとの water/iron イベント数の集計メモ。
- **`Log/`**: `do_04` で生成した `.tex`(`SubFiles/` 以下)を取り込んでコンパイルした、チェックシート本体(`ManualCheckLog_v1〜v3.tex`)とそのPDF(`PDF/`)。`tikz-feynhand` 関連ファイルは飛跡図を描くための外部LaTeXパッケージ。
- 本リポジトリは GitHub の `KasumiAyaka/OfflineManualCheck` にpushされている(オフライン環境用に、大容量データを含まないファイル群だけを取り出したもの)。
