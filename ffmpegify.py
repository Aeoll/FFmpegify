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


standard = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
gamma = ['.exr', '.tga']
alltypes = standard + gamma
vid_suff = ['.mov', '.mp4', '.webm', '.mkv', '.avi'] # do vid-vid conversion with audio as well?
vids = ['mov', 'mp4', 'mp4-via-jpg']



class FFMPEGIFY():

    def __init__(self, config):
        # get config settings
        self.START_FRAME = int(config['startFrame'])
        self.MAX_FRAMES = int(config['maxFrames'])
        self.MAX_WIDTH = int(config['maxWidth'])
        self.MAX_HEIGHT = int(config['maxHeight'])
        self.SCALER = config['scaler']
        self.CRF = int(config['quality'])
        self.FRAME_RATE = int(config['FPS'])
        self.PRESET = config['preset']
        self.CODEC = config['codec']
        self.VIDFORMAT = config['format']
        self.GAMMA = config['gamma']
        self.PREMULT = int(config['premult'])
        self.NAME_LEVELS = int(config['namelevels'])  # Create output file in higher-up directories
        self.AUDIO = False
        self.AUDIO_OFFSET = int(config['audiooffset'])

        self.isVidOut = True # Check if being output to video or frames
        if self.VIDFORMAT not in vids:
            self.isVidOut = False


    def get_input_file(self, path):
        # Parse filename
        infile = pathlib.Path(path)
        if os.path.isdir(path):
            files = os.listdir(path)
            for f in files:
                fpath = pathlib.Path(f)
                if fpath.suffix in alltypes:
                    infile = infile.joinpath(fpath)
                    break
        return infile


    def get_output_filename(self, infile):
        # OUTPUT FILENAME
        saveDir = infile # naming the video file based on parent dir. Could change this later.
        parts = infile.parent.parts
        if (self.NAME_LEVELS > 0):
            sec = len(parts) - self.NAME_LEVELS
            parts = parts[sec:]
            outname = "_".join(parts)
        else:
            outname = str(infile.parent)
        outname = re.sub(r'\W+', '_', outname)
        outputf = str(saveDir.with_name('_' + outname + "_video." + self.VIDFORMAT))
        if not self.isVidOut:
            outputf = str(saveDir.with_name('_' + preframepart + "_" + padstring + "." + self.VIDFORMAT))

        # if the video already exists create do not overwrite it
        counter = 1
        while pathlib.Path(outputf).exists():
            outputf = str(saveDir.with_name('_' + outname + "_video_" + str(counter) + "." + self.VIDFORMAT))
            counter = counter + 1
        return outputf

    def input_stream(self, infile):
        l = len(stem)
        back = stem[::-1]
        m = re.search('\d+', back)
        if (m):
            # simple regex match - find digit from the end of the stem
            sp = m.span(0)
            sp2 = [l - a for a in sp]
            sp2.reverse()

            # glob for other frames in the folder and find the first frame to use as start number
            preframepart = stem[0:sp2[0]]
            postframepart = stem[sp2[1]:]
            frames = sorted(infile.parent.glob(preframepart + '*' + postframepart + suffix))
            start_num = int(frames[0].name[sp2[0]:sp2[1]])
            if self.START_FRAME > 0:
                start_num = self.START_FRAME

            # get padding for frame num
            padding = sp2[1] - sp2[0]
            padstring = '%' + format(padding, '02') + 'd'  # eg %05d
            # fix for unpadded frame numbers
            if len(frames[0].name) != len(frames[-1].name):
                padstring = '%' + 'd'

            # get absolute path to the input file
            inputf = stem[0:sp2[0]] + padstring + postframepart + suffix
            inputf_abs = str(infile.with_name(inputf))


            # ============================================
            # FFPROBE - Probably easier to use this metadata
            # =============================================
            # ffprobe = ['ffprobe']
            # ffprobe.extend(('-v', 'quiet'))
            # ffprobe.extend(('-print_format', 'json'))
            # ffprobe.append(str(infile))
            # ffprobe.append('-show_format')
            # ffprobe.append('-show_streams')
            # ffpr = subprocess.check_output(ffprobe)
            # ffjson = json.loads(ffpr)
            # IN_W = ffjson['streams'][0]['coded_width']
            # IN_H = ffjson['streams'][0]['coded_height']
            # IN_DURATION = ffjson['streams'][0]['duration']
            # IN_FRAMES = int(ffjson['streams'][0]['nb_frames'])
            # IN_FPS = ffjson['streams'][0]['r_frame_rate']
            # ===================================

            return (inputf, inputf_abs, start_num)
        return (None, None, None)


    def add_audio(self, infile, cmd):
        # AUDIO
        try:
            tracks = []
            tracks.extend(sorted(infile.parent.glob('*.mp3')))
            tracks.extend(sorted(infile.parent.glob('*.wav')))
            # also search immediate parent?
            tracks.extend(sorted(infile.parents[1].glob('*.mp3')))
            tracks.extend(sorted(infile.parents[1].glob('*.wav')))
            if (tracks):
                self.AUDIO = True
                # audio track offset - add controls for this?
                cmd.extend(('-itsoffset', str(self.AUDIO_OFFSET)))
                cmd.extend(('-i', str(tracks[0])))
        except:
            pass
        return cmd

    def convert(self, path):
        infile = self.get_input_file(path)

        stem = infile.stem
        suffix = infile.suffix

        # create ffmpeg command to append to
        platform = sys.platform
        if platform == "win32":
            cmd = ['ffmpeg']
        elif platform.startswith('linux'):  # full path to ffmpeg for linux
            cmd = ['/usr/bin/ffmpeg']
        else:  # full path to ffmpeg for osx
            cmd = ['/usr/local/bin/ffmpeg']

        if (suffix in alltypes):

            inputf, inputf_abs, start_num = input_stream(infile)
            if inputf:
                outputf = self.output_filename(inputf)


                # scale down video if the image dimensions exceed the max width or height, while maintaining aspect ratio
                if self.MAX_HEIGHT <= 0 and self.MAX_WIDTH <= 0:
                    scalestr = "scale='trunc(iw/2)*2':'trunc(ih/2)*2'"
                elif self.MAX_WIDTH <= 0:
                    scalestr = "scale='-2:min'(" + str(self.MAX_HEIGHT) + ",trunc(ih/2)*2)':force_original_aspect_ratio=decrease"
                elif self.MAX_HEIGHT <= 0:
                    scalestr = "scale='min(" + str(self.MAX_WIDTH) + ",trunc(iw/2)*2)':-2"
                else:
                    # this currently causes issues if the W or H are greater than the max, and the other dimension is no longer divisible by 2 when scaled down so pad it
                    scalestr = "scale='min(" + str(self.MAX_WIDTH) + ",trunc(iw/2)*2)':min'(" + str(self.MAX_HEIGHT) + ",trunc(ih/2)*2)':force_original_aspect_ratio=decrease,pad=" + str(self.MAX_WIDTH) + ":" + str(self.MAX_HEIGHT) + ":(ow-iw)/2:(oh-ih)/2"
                    # maybe skip force ratio and do it manually? DOesnt work yet...
                    max_asp = float(self.MAX_WIDTH) / self.MAX_HEIGHT
                    A = "min(trunc(iw/2)*2," + str(self.MAX_WIDTH) + ")"
                    B = "if( gt(ih," + str(self.MAX_HEIGHT) + "), trunc((" + str(self.MAX_HEIGHT) + "*dar)/2)*2, -2 )"
                    C = "if(gt(iw," + str(self.MAX_WIDTH) + "), trunc((" + str(self.MAX_WIDTH) + "/dar)/2)*2 ,-2)"
                    D = "min( trunc(ih/2)*2," + str(self.MAX_HEIGHT) + ")"
                    scalestr = "scale='if( gt(dar," + str(max_asp) + "), " + A + ", " + B + ")':'if( gt(dar," + str(max_asp) + "), " + C + ", " + D + " )'"

                if (suffix in gamma):
                    cmd.extend(('-gamma', self.GAMMA))
                cmd.extend(('-start_number', str(start_num).zfill(padding)))
                cmd.extend(('-r', str(self.FRAME_RATE)))
                cmd.extend(('-i', inputf_abs))

                cmd = self.add_audio(infile, cmd)

                if self.isVidOut:
                    # Codecs TODO DNxHR and ProRes?
                    if self.CODEC == "H.264":
                        cmd.extend(('-c:v', 'libx264'))
                        cmd.extend(('-pix_fmt', 'yuv420p', '-crf', str(self.CRF), '-preset', self.PRESET))
                        # colours are always slightly off... not sure how to fix. libx264rgb seems to help but still not right?
                        # cmd.extend(('-c:v', 'libx264rgb'))
                        # cmd.extend(('-pix_fmt', 'yuv444p', '-crf', str(self.CRF), '-preset', self.PRESET))
                    elif self.CODEC == "DNxHR":
                        cmd.extend(('-c:v', 'dnxhd'))
                        cmd.extend(('-profile', 'dnxhr_hq'))
                    else:
                        pass

                if self.MAX_FRAMES > 0:
                    cmd.extend(('-vframes', str(self.MAX_FRAMES)))
                if self.isVidOut:
                    if self.PREMULT:
                        cmd.extend(('-vf', 'premultiply=inplace=1, ' + scalestr)) # premult is causing all the problems?? Leave it off...
                    else:
                        cmd.extend(('-vf', scalestr))
                else:
                    cmd.extend(('-vf', scalestr))
                cmd.extend(('-sws_flags', self.SCALER))
                if self.VIDFORMAT == 'jpg':
                    cmd.extend(('-q:v', '2'))
                # AUDIO OPTIONS
                if self.AUDIO:
                    cmd.extend(('-c:a', 'aac'))
                    cmd.extend(('-b:a', '320k'))
                    cmd.append('-shortest')
                cmd.append(outputf)
                subprocess.run(cmd)
            else:
                pass
        # ==================================
        # Vid-Vid conversion (with audio)
        # TODO
        # ==================================
        elif suffix in vid_suff:
            cmd.extend(('-i', infile))
            if self.CODEC == "H.264":
                cmd.extend(('-c:v', 'libx264'))
                cmd.extend(('-pix_fmt', 'yuv420p', '-crf', str(self.CRF), '-preset', self.PRESET))

            outputf = str(saveDir.with_name(stem + "_converted." + self.VIDFORMAT))
            cmd.append(outputf)
            subprocess.run(cmd)
        else:
            print("Invalid file extension")

# Read config file for settings
def readSettings(settings):
    try:
        with open(settings, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(e)
    f.close()
    return config

if __name__ == '__main__':
    path = Path(sys.argv[0]).with_name('settings.json')
    config = readSettings(path)
    F = FFMPEGIFY(config)
    F.convert(sys.argv[1])
    # input()
