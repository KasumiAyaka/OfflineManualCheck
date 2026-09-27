if "%1"=="" goto :usage

goto :skip_old_ver
type ScanData\ChkRes\ECC%1UTS_????.txt  > ECC%1UTS.txt
type ScanData\ChkRes\ECC%1UTS_*_Ref.txt > ECC%1UTS_Ref.txt
type ScanData\ChkRes\ECC%1FTS_????.txt > ECC%1FTS.txt
type ScanData\ChkRes\ECC%1FTS_*_Ref.txt > ECC%1FTS_Ref.txt

::type  ECC%1UTS.txt ECC%1FTS.txt  > ECC%1Retake.txt
::type  ECC%1UTS_Ref.txt ECC%1FTS_Ref.txt > ECC%1Retake_Ref.txt

python tools\OfflineManChk\extract_retake_tracklist.py RetakeTrackList\ECC%1 ECC%1UTS.txt ECC%1UTS_Ref.txt ECC%1FTS.txt ECC%1FTS_Ref.txt --dry-run 
pause
python tools\OfflineManChk\extract_retake_tracklist.py RetakeTrackList\ECC%1 ECC%1UTS.txt ECC%1UTS_Ref.txt ECC%1FTS.txt ECC%1FTS_Ref.txt
python tools\OfflineManChk\retake_tracklist_to_pl.py RetakeTrackList\ECC%1 %1 RetakeTrackList\ECC%1.tex 
rem del ECC%1*.txt
:skip_old_ver


::goto :skip_new_ver
rem Judge Retake or not
python AffineFailureAnalysis\predict_ecc_failures.py %1 --out RetakeTrackList\ECC%1_Retake.csv 
rem[--threshold 0.00252129]
rem Make Retake Event List
python AffineFailureAnalysis\export_chkres.py %1 --records RetakeTrackList\ECC%1_Retake.csv --outdir RetakeTrackList
pause
rem Make Latex script
python tools\OfflineManChk\extract_retake_tracklist.py RetakeTrackList\ECC%1 RetakeTrackList\ECC%1UTS_affine_fail.txt --dry-run 
python tools\OfflineManChk\extract_retake_tracklist.py RetakeTrackList\ECC%1 RetakeTrackList\ECC%1UTS_affine_fail.txt 
:skip_new_ver

goto :eof
:usage
# ecc 
