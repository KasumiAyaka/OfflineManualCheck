import os
import sys
from pathlib import Path
import shutil


if len(sys.argv) < 3:
    print("No arguement!")
    print("---USAGE------------------------------------")
    print("get_file_list.py [input.txt] [output-path]")
    print("--------------------------------------------")
    sys.exit()

print("Argument:{}".format(sys.argv[1]))

# check contents of "sys.argv"
print("sys.argv = {}\n".format(sys.argv))

Input_tracklist=sys.argv[1]
Output_dir_path=sys.argv[2]+"\\TrackList"
if not os.path.exists(Output_dir_path):
    os.makedirs(Output_dir_path)

#Set event list
f = open(Input_tracklist, 'r')
#data = f.read()
pl=0
for line in f:
    result = line.split()
    if result[0] == '-':
      k = 0
      pl = int(result[2])
      print(pl)
    Output = "%s\\PL%03d.yaml"%(Output_dir_path,pl)
    w = open(Output, 'a')
    w.write(line)
 

f.close()
