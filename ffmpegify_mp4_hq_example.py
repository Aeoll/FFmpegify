import pathlib
import re
import sys
import subprocess

# =========================
# Editable Settings
# =========================
FRAME_RATE = 25    # Frames per second
MAX_WIDTH = 1920   # Set to -1 for no maximum width
MAX_HEIGHT = 1080  # Set to -1 for no maximum height
CRF = 14           # Quality (bitrate) setting from 1->50. Lower is higher quality 
PRESET = "slower"  # slow, medium, ultrafast etc
VIDFORMAT = "mp4"  # output format

def convert(path):
    file = pathlib.Path(path)
    stem = file.stem
    suffix = file.suffix
    standard = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
    gamma = ['.exr', '.tga']
    alltypes = standard + gamma

    if( suffix in alltypes ):
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
            outputf = str(file.with_name( '_' + file.parent.name + "_video." + VIDFORMAT ))

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
            scalestr = "scale='min(" + str(MAX_WIDTH) + ",trunc(iw/2)*2)':min'(" + str(MAX_HEIGHT) + ",trunc(ih/2)*2)':force_original_aspect_ratio=decrease"
            cmd.extend(('-vf', 'premultiply=inplace=1, ' + scalestr))
            cmd.append(outputf)
            subprocess.run(cmd)
        else:
            pass 
    else:
        print("Invalid file extension")

if __name__ == '__main__':
    convert(sys.argv[1])