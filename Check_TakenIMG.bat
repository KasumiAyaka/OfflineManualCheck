if "%1"=="" goto :usage

set input_path=K:\NINJA\E71a\ManualCheck\ScanData

tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_FTS\ECC6\IMG ScanData\FTS_IMG_%1.pdf 
tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_FTS\ECC6\Ref\IMG ScanData\FTS_Ref_%1.pdf
tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_UTS\ECC6\IMG ScanData\UTS_IMG_%1.pdf
tools\CheckImg\make_check_pdfs_pl.py %input_path%\chk_UTS\ECC6\Ref\IMG ScanData\UTS_Ref_%1.pdf


goto :eof

:usage
#date