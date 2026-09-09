rem gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7==1){print $2,$11,$7;k++}}END{print k}" T:\NINJA\E71a\work\kasumi\ManualCheck\Analysis\ECC%1\data_cut\tan4MD100npl11_no_cut_on_p_f07_vph20\water_vtxpos_chk.txt 
rem gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7>1&&($11<-2000||$11>-700)){print $2,$11,$7;k++}}END{print k}" T:\NINJA\E71a\work\kasumi\ManualCheck\Analysis\ECC%1\data_cut\tan4MD100npl11_no_cut_on_p_f07_vph20\water_vtxpos_chk.txt 
rem gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7==1){print $2,$11,$7;k++}}END{print k}" T:\NINJA\E71a\work\kasumi\ManualCheck\Analysis\ECC%1\data_cut\tan4MD100npl11_no_cut_on_p_f07_vph20\iron_vtxpos_chk.txt 
rem gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7>1&&($11<-500||$11>-300)){print $2,$11,$7;k++}}END{print k}" T:\NINJA\E71a\work\kasumi\ManualCheck\Analysis\ECC%1\data_cut\tan4MD100npl11_no_cut_on_p_f07_vph20\iron_vtxpos_chk.txt 

set input_path=T:\NINJA\E71a\work\kasumi\ManualCheck\Analysis\ECC%1\data_cut\tan4MD100npl11_no_cut_on_p_f07_vph20\
set output_path=K:\NINJA\E71a\ManualCheck\ManualCheck_EventList
gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7==1){print $2;k++}}" %input_path%\water_vtxpos_chk.txt  > %output_path%\\ECC%1water.txt
gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7>1&&($11<-2000||$11>-700)){print $2;k++}}" %input_path%\water_vtxpos_chk.txt  >> %output_path%\\ECC%1water.txt
gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7==1){print $2;k++}}" %input_path%\iron_vtxpos_chk.txt  > %output_path%\\ECC%1iron.txt
gawk "BEGIN{k==0}{if($16==13&&$6>-1&&$7>1&&($11<-500||$11>-300)){print $2;k++}}" %input_path%\iron_vtxpos_chk.txt  >> %output_path%\\ECC%1iron.txt
