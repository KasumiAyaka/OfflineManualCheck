if "%2"=="" goto :usage
set wpath=K:\NINJA\E71a\ManualCheck
pushd %wpath%

rem make tracklist(ファイルの統合)
if not exist TrackList0 mkdir TrackList0
if not exist TrackList0\ECC%1 mkdir TrackList0\ECC%1
python tools\MakeTrackList\MakePred.py Pred\ECC%1\iron %1 TrackList0\ECC%1\iron.txt
python tools\MakeTrackList\MakePred.py Pred\ECC%1\water %1 TrackList0\ECC%1\water.txt
type TrackList0\ECC%1\iron.txt TrackList0\ECC%1\water.txt > TrackList0\TrackList%1.txt

rem output per PL
if exist TrackList0\ECC%1\TrackList del TrackList0\ECC%1\TrackList
if not exist TrackList0\ECC%1\TrackList mkdir TrackList0\ECC%1\TrackList
python tools\MakeTrackList\Divide_by_pl.py TrackList0\TrackList%1.txt TrackList0\ECC%1

rem pickup reference track and make tracklist
if not exist TrackList mkdir TrackList
if not exist TrackList\ECC%1 mkdir TrackList\ECC%1
C:\Users\kasumi\source\repos\ManualCheck\x64\Release\Pickup_reference_track_for_each_track.exe %1 TrackList0\ECC%1\TrackList TrackList\ECC%1 TrackList\btrklist%1.txt

rem make PL list
gawk "{print $1}" TrackList\btrklist%1_rawidmap.txt > tmp%1_1.txt
sort -k 1n tmp%1_1.txt > tmp%1_2.txt
uniq tmp%1_2.txt > TrackList\PLlist%1.txt
del tmp%1_*.txt

popd

goto :eof
:usage
echo Input : ECCnum ECC-driveletter