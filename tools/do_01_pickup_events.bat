if "%1"=="" goto :usage
set wpath=K:\NINJA\E71a\ManualCheck
pushd %wpath%

set input_path=T:\NINJA\E71a\work\kasumi\ManualCheck\Analysis\ECC%1\data_after_partner_search
set water_path=T:\NINJA\E71a\work\Momch_after_divide_Area\Add_sandmuonflg_sf_information\ECC%1_water_CentralArea.momch
set output_path=K:\NINJA\E71a\ManualCheck\Momch
set prg_path=src

rem manualcheckが必要なイベントをmomchから抽出する。先にeventリストを作っておく。
%prg_path%\pickup_selected_event_from_momch.exe %water_path% K:\NINJA\E71a\ManualCheck\ManualCheck_EventList\ECC%1water.txt %output_path%\ECC%1water.momch 
%prg_path%\pickup_selected_event_from_momch.exe %input_path%\iron.momch K:\NINJA\E71a\ManualCheck\ManualCheck_EventList\ECC%1iron.txt %output_path%\ECC%1iron.momch 

goto :eof

:usage
#ecc

