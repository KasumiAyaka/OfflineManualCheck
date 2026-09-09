if "%2"=="" goto :usage
set wpath=K:\NINJA\E71a\ManualCheck
pushd %wpath%
rem PLカットとmuonだけのmomchにしている。

rem make momch
call tools\pickup_events.bat %1
I:\NINJA\E71a\work\kasumi\ECC\MuonAnalysis\x64\Release\mk_only_muon_momch.exe Momch\ECC%1iron.momch Momch\ECC%1iron_muononly.momch
C:\Users\kasumi\source\repos\ArrangeMomch\x64\Release\apply_PLcut.exe Momch\ECC%1iron_muononly.momch Momch\ECC%1iron_muononly_PLcut.momch 130
C:\Users\kasumi\source\repos\ArrangeMomch\x64\Release\apply_PLcut.exe Momch\ECC%1water.momch Momch\ECC%1water_PLcut.momch 130

rem make prediction
start T:\NINJA\E71a\work\kasumi\ManualCheck_CentralArea_water\mkpred.bat Momch\ECC%1iron_muononly_PLcut.momch %2:\NINJA\E71a\ECC%1\Area0 Pred\ECC%1\iron\
start T:\NINJA\E71a\work\kasumi\ManualCheck_CentralArea_water\mkpred.bat Momch\ECC%1water_PLcut.momch %2:\NINJA\E71a\ECC%1\Area0 Pred\ECC%1\water\

del Momch\ECC%1iron.momch
del Momch\ECC%1iron_muononly.momch
del Momch\ECC%1water.momch

popd

goto :eof
:usage
echo Input : ECCnum ECC-driveletter