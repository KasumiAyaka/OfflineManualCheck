if "%1"=="" goto :usage
set wpath=K:\NINJA\E71a\ManualCheck
pushd %wpath%

rem C:\Users\kasumi\source\repos\ManualCheck\x64\Release
src\Make_rawidmap_from_TrackList.exe TrackList %1 
move TrackList\btrklist2_rawidmap.txt OfflineManualChecking_LoggingTool\TrackListForOfflineManChk 

popd
goto :eof

:usage
eccnum
