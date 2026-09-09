rem E:\udd\hayakawa\prg\NINJA\Analythe\bin\Release
set prg=.\Make_man_chk_pred.exe

rem if not exist %prg% goto :eofrem copy E:\udd\hayakawa\prg\NINJA\Analythe\bin\Release\Make_man_chk_pred.exe %prg%

if "%3"=="" goto :usage

set input=%1
set Area_path=%2
set output=%3

if not exist %output% mkdir %output%

%prg% %input% %Area_path% %output%

::goto :eof
goto :skip

:usage
input.momch I:\NINJA\E71a\ECC5\Area0 output_folder_path\

goto :eof

goto :skip
Make_man_chk_pred.exe [ev.momch] [path_to_ecc_area0] [output_prefix]とすると、
与えたmomchファイルに含まれる全イベントを対象に、
各飛跡をvertexを跨いだ反対側に向けてPL3枚分外挿し、
その情報をイベントごとに{output_prefix}ev???.txt
というファイルに出力します。
外挿先の情報はHTSの各Areaごとの座標系に変換された上で、
pl area extr_npl ax ay x y zという形式で出力されます。
見に行く際には当該Areaのセットを忘れないよう。

なお元々のManual_check_track_extrapolateには
外挿先周辺のBasetrackやLinkletの情報から候補を選出する
機能もありましたが、Make_man_chk_predでは作成中です。

:skip