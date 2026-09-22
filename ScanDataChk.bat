::@echo off
if "%1"=="" goto :usage

rem set n=00%3
rem set pl=!n:~-3!

set btrklist_path=K:\NINJA\E71a\ManualCheck\OfflineManualChecking_LoggingTool\TrackListForOfflineManChk

rem eyechk
python tools/OfflineManChk/check_rawidmap_images.py %btrklist_path%\btrklist%1_rawidmap.txt --scan-data-root  K:\NINJA\E71a\ManualCheck\ScanData



goto :eof
:usage
echo #ecc 
