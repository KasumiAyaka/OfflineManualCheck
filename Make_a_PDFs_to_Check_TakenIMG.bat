if "%2"=="" goto :usage
rem pdfを作成する。

set input_path=K:\NINJA\E71a\ManualCheck\ScanData

tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_FTS\ECC%2\IMG ScanData\FTS_IMG_ECC%2_%1.pdf 
tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_FTS\ECC%2\Ref\IMG ScanData\FTS_Ref_ECC%2_%1.pdf
tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_UTS\ECC%2\IMG ScanData\UTS_IMG_ECC%2_%1.pdf
tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_UTS\ECC%2\Ref\IMG ScanData\UTS_Ref_ECC%2_%1.pdf


goto :eof
 
:usage
filename_date #ECC