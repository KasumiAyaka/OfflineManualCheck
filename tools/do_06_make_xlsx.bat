if "%1"=="" goto :usage
python tools\OfflineManChk\rawidmap_to_xlsx.py OfflineManualChecking_LoggingTool\TrackListForOfflineManChk\btrklist$1_rawidmap.txt 

goto :eof

:usage
# ecc