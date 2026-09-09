#listup dir name
import os
import sys

#input:prediction dirPath
#output:batch file
def get_dir_size(path='.'):
    if not os.path.exists(path):
        print('存在しないPath: %s' % path)
        return 0

    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    except FileNotFoundError as e:
        print(e)
    finally:
        return total


def scan_dir_size(dirPath, OutFile):
    if not os.path.exists(dirPath):
        print('ディレクトリが存在しません')
        return

    filesAndDirs = os.listdir(dirPath)
    subDirs = [os.path.join(dirPath, f) for f in filesAndDirs
               if os.path.isdir(os.path.join(dirPath, f))]
    files = [os.path.join(dirPath, f) for f in filesAndDirs
             if os.path.isfile(os.path.join(dirPath, f))]

    sumSize = 0
    #w = open('pickup_track_info.bat', 'w')
    w = open(OutFile, 'w')
    for f in files:
        sizeGb = os.path.getsize(f) / 1000 / 1000 / 1000
        print("filePath: %s, size: %.2f Gbyte" % (f, sizeGb))
        pros="gawk -f mkpred.awk %s >> TrackList.txt\n"%(f)
        w.write(pros)
        sumSize += sizeGb
    for folder in subDirs:
        sizeGb = get_dir_size(folder) / 1000 / 1000 / 1000
        print("dirPath: %s, size: %.2f Gbyte" % (folder, sizeGb))
        sumSize += sizeGb
    print("合計: %.2f Gbyte" % sumSize)
    w.close();


if __name__ == '__main__':
    argvs = sys.argv
    if len(argvs) == 3:
        scan_dir_size(argvs[1],argvs[2])
    else:
        print('引数にディレクトリのパスを設定してください。')