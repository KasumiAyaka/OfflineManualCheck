::@echo off
if "%3"=="" goto :usage

set n=00%3
set pl=!n:~-3!

set m=0000%2
set eve=!n:~-5!




if not exist ScanData\PatternMatchFailed\UTS\ECC%1\IMG\Event%eve% mkdir ScanData\PatternMatchFailed\UTS\ECC%1\IMG\Event%eve%
move ScanData\\UTS\ECC%1\IMG\Event%eve%\PL%pl%

goto :eof
:usage
echo #ecc #event #pl
