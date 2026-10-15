# ScanParamEditor

`ScamParam\{FTS,UTS}\ninja_e71a.yaml` の `ScanParamBase`(`&ScanParamBase` アンカーのブロック)にある
`ScanArea` / `ThrBinary` / `ThickOfLayer` を、選択式で書き換えるツール。他のパラメータやファイル全体の書式(インデント・改行コード・コメント)はそのまま保持する。

`ThrBinary`・`ScanArea`・`ThickOfLayer` は別々の項目として選ぶ(一部だけ変えることもできる)。
選択肢は「499999 tracks detectedと出力された → ThrBinaryを下げる」のように、現場で起きた症状と
その対応をセットにして表示できる。

CLI版(`scan_param_editor.exe`)と GUI版(`scan_param_editor_gui.exe`)の2種類があり、
どちらも同じロジック(`scan_param_editor.py`)・同じ `config.yaml` を使う。パソコン操作に
不慣れな人には GUI版をおすすめする。

## 配布・使い方(共通)

1. 使いたい方の exe (`scan_param_editor.exe` または `scan_param_editor_gui.exe`)と
   `config.yaml` を同じフォルダに置いて、使いたいPCにコピーする(Pythonは不要)。
2. `config.yaml` を、そのPCでの実際のファイルパスと使いたい選択肢に合わせて編集する。
   - `targets`: 書き換え対象にしたい `ninja_e71a*.yaml` の一覧(表示名とパス)。
     `defaults`(ThrBinary/ScanArea/ThickOfLayer)を指定しておくと、その target で
     「デフォルトに戻す」が使えるようになる(省略した target では使えない)。
   - `thrbinary_choices`: ThrBinary を変更する選択肢の一覧。`operation: delta`(現在値からの加減算、下げるなら負の値)か `operation: set`(値を直接指定)を選べる。症状と対応をセットにした名前を付けておくとよい。
   - `scanarea_choices`: ScanArea を変更する選択肢の一覧(座標ペアの個数は自由)。
   - `thickoflayer_choices`: ThickOfLayer を変更する選択肢の一覧。`thrbinary_choices` と同じく `operation: delta`/`set` が使える。
   - どの一覧も項目数は自由に増減できる。
   - `backup_dir`(省略可): バックアップをまとめて置くフォルダ。省略時は従来どおり対象ファイルと同じフォルダに保存される。
3. 書き換え前に自動でバックアップを作成する。`config.yaml` に `backup_dir` を指定していれば
   そのフォルダに `<親フォルダ名>_<ファイル名>.bak_YYYYMMDD_HHMMSS`、指定していなければ
   対象ファイルと同じフォルダに `<対象ファイル>.bak_YYYYMMDD_HHMMSS` として保存する。
   (ThrBinary・ScanArea・ThickOfLayer のどれも「変更しない」を選んだ場合は何も書き換えずに終了する)
4. `defaults` を設定した target では、個別に選ぶ代わりに「デフォルトに戻す」を選ぶだけで
   ThrBinary/ScanArea/ThickOfLayer を一括で既定値に戻せる(この場合もバックアップは作成される)。

設定ファイルを明示的に指定したい場合は `scan_param_editor.exe C:\path\to\config.yaml`
のように引数で渡す(省略時は exe と同じフォルダの `config.yaml` を使う)。GUI版も同様。

## GUI版(`scan_param_editor_gui.exe`)の操作

1. 起動すると、設定ファイルの `targets` がプルダウンに並んでいる。① で書き換えたい対象ファイルを選ぶと、その下に現在の `ScanArea`/`ThrBinary`/`ThickOfLayer` が表示される。
2. ② で ThrBinary の変更(該当する症状・対応、または「変更しない」)をクリックで選ぶ。
3. ③ で ScanArea の変更(該当する選択肢、または「変更しない」)をクリックで選ぶ。
4. ④ で ThickOfLayer の変更(該当する選択肢、または「変更しない」)をクリックで選ぶ。
5. 選んだ内容が画面下の「変更後のプレビュー」にリアルタイムで表示される。「変更前のパラメータ」「変更後のプレビュー」はどちらも内容の行数ぴったりに自動で高さが広がるので、スクロールせずに全部表示される(ウィンドウ自体の高さも、画面に収まる範囲で内容に合わせて自動調整される)。
6. 緑色の「書き換える」ボタンを押すと、変更前後の値を示す確認ダイアログが出る。「はい」で確定、「いいえ」でキャンセル。
7. 完了すると「完了」ダイアログが出て、バックアップファイルのパスも表示される。
8. オレンジ色の「デフォルトに戻す」ボタンは、選んでいる対象ファイルの `config.yaml` に `defaults` が設定されている場合だけ押せる。押すと②③④の選択内容に関係なく、ThrBinary/ScanArea/ThickOfLayer を全て既定値に一括で戻す(確認ダイアログあり、バックアップも作成される)。`defaults` が設定されていない対象ファイルではグレー表示になり押せない。

## CLI版(`scan_param_editor.exe`)の操作

1. 書き換える対象ファイルを番号で選ぶ
2. 対象ファイルに `defaults` が設定されている場合、「デフォルトに戻す」か「個別に選択する」かを選ぶ
   (「デフォルトに戻す」を選ぶとそのまま手順6の確認に進み、ThrBinary/ScanArea/ThickOfLayer が全て既定値になる)
3. ThrBinary の変更(該当する症状/対応、または「変更しない」)を番号で選ぶ
4. ScanArea の変更(該当する選択肢、または「変更しない」)を番号で選ぶ
5. ThickOfLayer の変更(該当する選択肢、または「変更しない」)を番号で選ぶ
6. 変更前後の値が表示されるので、`y` で確定(それ以外でキャンセル)

## 再ビルド方法(スクリプトを修正した場合)

```
pip install pyinstaller pyyaml ttkbootstrap
build_exe.bat
```

`dist\scan_param_editor.exe`(CLI版)と `dist\scan_param_editor_gui.exe`(GUI版)が生成される。
GUI版は ttkbootstrap を使っているため、ビルド時に `--collect-all ttkbootstrap` が必要
(`build_exe.bat` には組み込み済み)。
