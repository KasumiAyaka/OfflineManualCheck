::@echo off
if "%2"=="" goto :usage

set n=00%3
set pl=!n:~-3!
set fname=%2

rem IMG
set uts=ScanData\ChkRes\ECC%1UTS_%fname%.txt
set fts= ScanData\ChkRes\ECC%1FTS_%fname%.txt
set uts_path=ScanData\chk_FTS\ECC%1\IMG 
set fts_path=ScanData\chk_FTS\ECC%1\IMG 

rem Ref
set uts_ref=ScanData\ChkRes\ECC%1UTS_%fname%_Ref.txt
set fts_ref=ScanData\ChkRes\ECC%1FTS_%fname%_Ref.txt
set uts_ref_path=ScanData\chk_UTS\ECC%1%\Ref\IMG
set fts_ref_path=ScanData\chk_FTS\ECC%1%\Ref\IMG


::goto :Ref
rem eyechk
python tools\CheckImg\check_quality.py %uts% %uts_path% 
python tools\CheckImg\check_quality.py %fts% %fts_path% 
pause

rem chk res
::gawk '{if($2=="k:Retake"){print $0}}' %uts% 
::gawk '{if($2=="k:Retake"){print $0}}' %fts%
::gawk '{if($2=="l:?"){print $0}}' %uts%
::gawk '{if($2=="l:?"){print $0}}' %fts%

rem move
python tools\CheckImg\move_retake_dirs.py --src-dir %uts_path% --dry-run  --no-move-chk  %fts% 
python tools\CheckImg\move_retake_dirs.py --src-dir %fts_path% --dry-run  --no-move-chk   %uts%


::goto :skip
:Ref
python tools\CheckImg\check_quality.py %uts_ref% %uts_ref_path% 
python tools\CheckImg\check_quality.py %fts_ref% %fts_ref_path% 
pause


rem move
python tools\CheckImg\move_retake_dirs.py %uts_ref%
python tools\CheckImg\move_retake_dirs.py %fts_ref%


:skip

goto :eof
:usage
echo #ecc fname
