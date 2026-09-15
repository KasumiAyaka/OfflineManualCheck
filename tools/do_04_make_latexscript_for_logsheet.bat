if "%1"=="" goto :usage
set wpath=K:\NINJA\E71a\ManualCheck
pushd %wpath%

rem log sheet作成用のアウトプット

tools\MakeLatexScript\btrklist_to_pl.py TrackList\btrklist%1.txt %1
move TrackList\btrklist%1.txt K:\NINJA\E71a\ManualCheck\Log\SubFiles

popd
goto :eof

:usage
eccnum
