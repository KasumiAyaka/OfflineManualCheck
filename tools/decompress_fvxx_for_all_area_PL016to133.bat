::@echo off
setlocal enabledelayedexpansion

if "%2"=="" goto :usage

set dletter=%1
set ECC=%2



set /a pl0=16
set /a pl1=133

:loop
set n=00%pl0%
set pl=!n:~-3!
set area=1

:loop_area

if %area%==1 set ecc_path=%dletter%:\NINJA\E71a\ECC%2\Area%area%\PL%pl%
if %area% gtr 1 set ecc_path=I:\NINJA\E71a\ECC%2\Area%area%\PL%pl%


pushd %ecc_path%
python I:\prg\python\python_app\python_app\file_7z_decompress.py f%pl%2_thick_0.vxx
popd

set /a area=area+1
if %area% gtr 6 goto :nextpl
goto :loop_area
:nextpl
set /a pl0=pl0+1
if %pl0% gtr %pl1% goto :eof
goto :loop


goto :eof
:usage
echo DriveLetter #ecc 
