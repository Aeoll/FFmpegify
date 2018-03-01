import pathlib
import re
import sys
import os
import subprocess

# =========================
# Editable Settings
# =========================
FRAME_RATE = 25    # Frames per second
MAX_WIDTH = 1920   # Set to -1 for no maximum width. Max should be divisible by 2
MAX_HEIGHT = 1080  # Set to -1 for no maximum height. Max should be divisible by 2
CRF = 18           # Quality (bitrate) setting from 1->50. Lower is higher quality 
PRESET = "faster"  # slow, medium, ultrafast etc
VIDFORMAT = "mov"  # output format

def convert(path):
    standard = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
    gamma = ['.exr', '.tga']
    alltypes = standard + gamma

    origdir = pathlib.Path(path)
    file = origdir
    # get first image file in the directory
    files = os.listdir(path)
    for f in files:
        fpath = pathlib.Path(f)
        if fpath.suffix in alltypes:
            file = origdir.joinpath(fpath)
            break
    
    stem = file.stem
    suffix = file.suffix

    if file and suffix in alltypes:
        l = len(stem)
        back = stem[::-1]
        m = re.search( '\d+', back)
        if(m):
            # simple regex match - find digit from the end of the stem
            sp = m.span(0)
            sp2 = [l-a for a in sp]
            sp2.reverse()
            # get zfill for frame num
            padding = sp2[1] - sp2[0]
            padstring = '%' + format(padding, '02') + 'd' # eg %05d

            # glob for other frames in the folder and find the first frame to use as start number
            preframepart = stem[0:sp2[0]]
            postframepart = stem[sp2[1]:]
            frames = sorted(file.parent.glob(preframepart + '*' + postframepart))
            start_num = int(frames[0].name[sp2[0]:sp2[1]])

            # get absolute path to the input file and set the outputfile
            inputf = stem[0:sp2[0]] + padstring + postframepart + suffix
            inputf_abs = str(file.with_name(inputf))
            outputf = str(origdir.with_name( '_' + file.parent.name + "_video." + VIDFORMAT ))
            # if the video already exists create do not overwrite it
            counter = 1
            while pathlib.Path(outputf).exists():
                outputf = str(origdir.with_name( '_' + file.parent.name + "_video_" + str(counter) + "." + VIDFORMAT ))
                counter = counter + 1

            # create ffmpeg command and call it
            platform = sys.platform
            if platform == "win32":
                cmd = ['ffmpeg']
            else: # need to use full path to ffmpeg for osx and possibly linux?
                cmd = ['/usr/local/bin/ffmpeg'] 
 
            cmd.extend(('-r', str(FRAME_RATE)))
            if(suffix in gamma):
                cmd.extend(('-gamma', '2.2'))
            cmd.extend(('-start_number', str(start_num).zfill(padding) ))
            cmd.extend(('-i', inputf_abs))
            cmd.extend(('-c:v', 'libx264'))
            cmd.extend(('-pix_fmt', 'yuv420p', '-crf', str(CRF), '-preset', PRESET))
            # scale down video if the image dimensions exceed the max width or height, while maintaining aspect ratio
            if MAX_HEIGHT < 0 and MAX_WIDTH < 0:
                scalestr = "scale='trunc(iw/2)*2':'trunc(ih/2)*2'"
            elif MAX_WIDTH < 0:
                scalestr = "scale='min(" + str(MAX_WIDTH) + ",trunc(iw/2)*2)':-2"
            elif MAX_HEIGHT < 0:
                scalestr = "scale='-2:min'(" + str(MAX_HEIGHT) + ",trunc(ih/2)*2)':force_original_aspect_ratio=decrease"
            else:
                # this currently causes issues if the W or H are greater than the max, and the other dimension is no longer divisible by 2 when scaled down so pad it
                scalestr = "scale='min(" + str(MAX_WIDTH) + ",trunc(iw/2)*2)':min'(" + str(MAX_HEIGHT) + ",trunc(ih/2)*2)':force_original_aspect_ratio=decrease,pad="+ str(MAX_WIDTH) +":"+ str(MAX_HEIGHT) +":(ow-iw)/2:(oh-ih)/2"
                # maybe skip force ratio and do it manually? DOesnt work yet...
                max_asp = float(MAX_WIDTH)/MAX_HEIGHT
                A = "min(trunc(iw/2)*2," + str(MAX_WIDTH) + ")"
                B = "if( gt(ih,"+str(MAX_HEIGHT)+"), trunc(("+str(MAX_HEIGHT)+"*dar)/2)*2, -2 )"
                C = "if(gt(iw,"+str(MAX_WIDTH)+"), trunc(("+str(MAX_WIDTH)+"/dar)/2)*2 ,-2)"
                D = "min( trunc(ih/2)*2," + str(MAX_HEIGHT) + ")"
                scalestr = "scale='if( gt(dar,"+str(max_asp)+"), "+ A +", "+B+")':'if( gt(dar,"+str(max_asp)+"), "+C+", "+D+" )'"
                  
            cmd.extend(('-vf', 'premultiply=inplace=1, ' + scalestr))
            cmd.append(outputf)
            subprocess.run(cmd)
        else:
            pass 
    else:
        print("Invalid file extension")

if __name__ == '__main__':
    convert(sys.argv[1])