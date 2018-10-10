#! /usr/bin/python3 -OOt

import pathlib
import re
import sys
import glob
import os
import subprocess
from pathlib import *
import time
import json

def convert(path, config):
    # get config settings
    START_FRAME = int(config['startFrame'])
    MAX_FRAMES = int(config['maxFrames'])
    MAX_WIDTH = int(config['maxWidth'])
    MAX_HEIGHT = int(config['maxHeight'])
    SCALER = config['scaler']
    CRF = int(config['quality'])
    FRAME_RATE = int(config['FPS'])
    PRESET = config['preset']
    CODEC = config['codec']
    VIDFORMAT = config['format']
    GAMMA = config['gamma']
    NAME_LEVELS = int(config['namelevels'])
    
    AUDIO = False
    AUDIO_OFFSET = int(config['audiooffset'])

    standard = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
    gamma = ['.exr', '.tga']
    alltypes = standard + gamma

    # Check if being output to video or frames
    isVidOut = True
    vids = ['mov', 'mp4']
    if VIDFORMAT not in vids:
        isVidOut = False

    file = pathlib.Path(path)
    saveDir = file # set the directory to save the output to
    
    # For Directories
    if os.path.isdir(path):
        files = os.listdir(path)
        for f in files:
            fpath = pathlib.Path(f)
            if fpath.suffix in alltypes:
                file = file.joinpath(fpath)
                break
    stem = file.stem
    suffix = file.suffix

    if( suffix in alltypes ):
        l = len(stem)
        back = stem[::-1]
        m = re.search( '\d+', back)
        if(m):
            # simple regex match - find digit from the end of the stem
            sp = m.span(0)
            sp2 = [l-a for a in sp]
            sp2.reverse()

            # glob for other frames in the folder and find the first frame to use as start number
            preframepart = stem[0:sp2[0]]
            postframepart = stem[sp2[1]:]
            frames = sorted(file.parent.glob(preframepart + '*' + postframepart + suffix))
            start_num = int(frames[0].name[sp2[0]:sp2[1]])
            if START_FRAME > 0:
                start_num = START_FRAME

            # get padding for frame num
            padding = sp2[1] - sp2[0]
            padstring = '%' + format(padding, '02') + 'd' # eg %05d
            # fix for unpadded frame numbers
            if len(frames[0].name) != len(frames[-1].name): 
                padstring  = '%' + 'd'    

            # get absolute path to the input file and set the outputfile
            inputf = stem[0:sp2[0]] + padstring + postframepart + suffix
            inputf_abs = str(file.with_name(inputf))

            # naming the video file based on parent dirs
            parts = file.parent.parts
            if(NAME_LEVELS > 0):
                sec = len(parts)-NAME_LEVELS
                parts = parts[sec:]
                outname = "_".join(parts)
            else:
                outname = str(file.parent)
            outname = re.sub(r'\W+', '_', outname)                

            outputf = str(saveDir.with_name( '_' + outname + "_video." + VIDFORMAT ))
            if not isVidOut:
                outputf = str(saveDir.with_name( '_' + preframepart + "_" + padstring + "." + VIDFORMAT ))

            # if the video already exists create do not overwrite it
            counter = 1
            while pathlib.Path(outputf).exists():
                outputf = str(saveDir.with_name( '_' + outname + "_video_" + str(counter) + "." + VIDFORMAT ))
                counter = counter + 1

            # create ffmpeg command and call it
            platform = sys.platform
            if platform == "win32":
                cmd = ['ffmpeg']
            elif platform.startswith('linux'): # full path to ffmpeg for linux
                cmd = ['/usr/bin/ffmpeg'] 
            else: # full path to ffmpeg for osx
                cmd = ['/usr/local/bin/ffmpeg'] 

            if(suffix in gamma):
                cmd.extend(('-gamma', GAMMA))
            cmd.extend(('-start_number', str(start_num).zfill(padding) ))
            cmd.extend(('-r', str(FRAME_RATE)))
            cmd.extend(('-i', inputf_abs))

            # AUDIO
            try:
                tracks = []
                tracks.extend(sorted(file.parent.glob('*.mp3')))
                tracks.extend(sorted(file.parent.glob('*.wav')))
                # also search immediate parent?
                tracks.extend(sorted(file.parents[1].glob('*.mp3')))
                tracks.extend(sorted(file.parents[1].glob('*.wav')))
                if( tracks ):
                    AUDIO = True
                    # audio track offset - add controls for this
                    cmd.extend(('-itsoffset', str(AUDIO_OFFSET)))
                    cmd.extend(('-i', str(tracks[0])))
            except:
                pass
            if isVidOut:
                # Codecs TODO DNxHR and ProRes
                if CODEC == "H.264":
                    cmd.extend(('-c:v', 'libx264'))
                    cmd.extend(('-pix_fmt', 'yuv420p', '-crf', str(CRF), '-preset', PRESET))
                elif CODEC == "DNxHR":
                    cmd.extend(('-c:v', 'dnxhd'))
                    cmd.extend(('-profile', 'dnxhr_hq'))
                else:
                    pass             

            if MAX_FRAMES > 0:
                cmd.extend(('-vframes', str(MAX_FRAMES)))    
            # scale down video if the image dimensions exceed the max width or height, while maintaining aspect ratio
            if MAX_HEIGHT <= 0 and MAX_WIDTH <= 0:
                scalestr = "scale='trunc(iw/2)*2':'trunc(ih/2)*2'"
            elif MAX_WIDTH <= 0:
                scalestr = "scale='-2:min'(" + str(MAX_HEIGHT) + ",trunc(ih/2)*2)':force_original_aspect_ratio=decrease"
            elif MAX_HEIGHT <= 0:
                scalestr = "scale='min(" + str(MAX_WIDTH) + ",trunc(iw/2)*2)':-2"
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
            if isVidOut:            
                cmd.extend(('-vf', 'premultiply=inplace=1, ' + scalestr))
            else:
                cmd.extend(('-vf', scalestr))
            cmd.extend(('-sws_flags', SCALER))
            if VIDFORMAT == 'jpg':
                cmd.extend(('-q:v', '2'))
            # AUDIO OPTIONS       
            if AUDIO:
                cmd.extend(('-c:a', 'aac'))
                cmd.append('-shortest')
            cmd.append(outputf)
            subprocess.run(cmd)
            # time.sleep(3000) # for debugging
        else:
            pass 
    else:
        print("Invalid file extension")

# Read config file for settings
def readSettings(settings):    
    try:
        with open(settings, 'r') as f:
            config = json.load(f)
    except Exception as e: print(e)
    f.close()
    return config

if __name__ == '__main__':
    path = Path(sys.argv[0]).with_name('settings.json')
    config = readSettings(path)
    convert(sys.argv[1], config)
    # input()