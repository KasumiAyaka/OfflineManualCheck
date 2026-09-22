if "%1"=="" goto :usage

type ScanData\ChkRes\ECC%1UTS_????.txt  > ECC%1UTS.txt
type ScanData\ChkRes\ECC%1UTS_*_Ref.txt > ECC%1UTS_Ref.txt
type ScanData\ChkRes\ECC%1FTS_????.txt > ECC%1FTS.txt
type ScanData\ChkRes\ECC%1FTS_*_Ref.txt > ECC%1FTS_Ref.txt

::type  ECC%1UTS.txt ECC%1FTS.txt  > ECC%1Retake.txt
::type  ECC%1UTS_Ref.txt ECC%1FTS_Ref.txt > ECC%1Retake_Ref.txt

python tools\OfflineManChk\extract_retake_tracklist.py RetakeTrackList\ECC%1 ECC%1UTS.txt ECC%1UTS_Ref.txt ECC%1FTS.txt ECC%1FTS_Ref.txt --dry-run 
pause
python tools\OfflineManChk\extract_retake_tracklist.py RetakeTrackList\ECC%1 ECC%1UTS.txt ECC%1UTS_Ref.txt ECC%1FTS.txt ECC%1FTS_Ref.txt


goto :eof
:usage
# ecc