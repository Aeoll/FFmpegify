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
import ffmpeg


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

        # If the video already exists create do not overwrite it
        counter = 1
        while pathlib.Path(outputf).exists():
            outputf = str(saveDir.with_name('_' + outname + "_video_" + str(counter) + "." + self.VIDFORMAT))
            counter = counter + 1
        return outputf


    def input_stream(self, infile):
        # Generate ffmpeg stream

        IN_ARGS = dict() # arguments for input stream (would be placed prior to -i on commandline)

        # Parse input filename for framenumber
        # simple regex match - find digits at the end of the filename.
        # Examples: frame.0001.exr, frame0001.exr, frame1.exr
        stem = infile.stem
        suffix = infile.suffix
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


            if suffix in gamma:
                IN_ARGS['gamma'] = self.GAMMA
            IN_ARGS['start_number'] = str(start_num).zfill(padding)
            IN_ARGS['framerate'] = str(self.FRAME_RATE)
            STREAM = ffmpeg.input(inputf_abs, **IN_ARGS)
            return STREAM
        return None



    def add_audio(self, infile, STREAM):
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
                return STREAM.input(str(tracks[0]), {'itsoffset': str(self.AUDIO_OFFSET)})
        except Exception as e:
            print("Error adding audio: " + str(e))
        return STREAM


    def add_scaling(self, STREAM):

        scalekw = {}
        downscale_w = "'min(" + str(self.MAX_WIDTH) + ",trunc(iw/2)*2)'"
        downscale_h = "min'(" + str(self.MAX_HEIGHT) + ",trunc(ih/2)*2)'"

        # Video scaling. Want to guarantee even dimensions even if max_width and max_height aren't specified.
        # TODO replace some of this stuff with a crop filter.
        if self.MAX_HEIGHT <= 0 and self.MAX_WIDTH <= 0:
            scale = ['trunc(iw/2)*2', 'trunc(ih/2)*2']
        elif self.MAX_WIDTH <= 0:
            scale = ["-2", downscale_h]
            # maintain original aspect ratio
            scalekw["force_original_aspect_ratio"] = "decrease"
        elif self.MAX_HEIGHT <= 0:
            scale = [downscale_w, "-2"]
        else:
            # Original method
            # scale = [downscale_w, downscale_h]
            # scalekw["force_original_aspect_ratio"] = "decrease"
            # scalekw["pad"] = str(MAX_WIDTH) + ":" + str(MAX_HEIGHT) + ":(ow-iw)/2:(oh-ih)/2"
            # This currently causes issues if the W or H are greater than the max and the
            # other dimension is no longer divisible by 2 when scaled down, so add padding.
            max_asp = float(MAX_WIDTH)/MAX_HEIGHT
            A = downscale_w
            B = "if(gt(ih,"+str(MAX_HEIGHT)+"), trunc(("+str(MAX_HEIGHT)+"*dar)/2)*2, -2)"
            C = "if(gt(iw,"+str(MAX_WIDTH)+ "), trunc(("+str(MAX_WIDTH) +"*dar)/2)*2, -2)"
            D = downscale_h
            scale = ["'if( gt(dar,"+str(max_asp)+"), "+ A +", "+B+")'", "'if( gt(dar,"+str(max_asp)+"), "+C+", "+D+" )'"]


        STREAM = STREAM.filter('scale', scale[0], scale[1], **scalekw)

        return STREAM


    def build_output(self, infile, STREAM):
        outputf = self.get_output_filename(infile)

        OUT_ARGS = dict()

        if self.isVidOut:
            # Codecs TODO DNxHR and ProRes?
            if self.CODEC == "H.264":
                OUT_ARGS['vcodec'] = 'libx264'
                OUT_ARGS['vprofile'] ="baseline"
                OUT_ARGS['pix_fmt'] ="yuv420p"
                OUT_ARGS['crf'] = str(self.CRF)
                OUT_ARGS['preset']  = self.PRESET
                # Colours are always slightly off... not sure how to fix. libx264rgb seems to help but still not right?
                # John Carmack blogpost: https://www.facebook.com/permalink.php?story_fbid=2413101932257643&id=100006735798590
                # OUT_ARGS['vcodec'] = 'libx264rgb'
                # OUT_ARGS['pix_fmt'] ="yuv444p"
                # OUT_ARGS['pix_fmt'] ="yuvj420p"
            elif self.CODEC == "DNxHR":
                OUT_ARGS['vcodec'] = 'dnxhd'
                OUT_ARGS['profile']  = 'dnxhr_hq'
            else:
                pass
        elif self.VIDFORMAT == 'jpg':
            OUT_ARGS['q:v'] = '2'


        if self.MAX_FRAMES > 0:
            OUT_ARGS['-vframes'] = str(self.MAX_FRAMES)

        # Add premult filter. Maybe causing problems??
        if self.isVidOut and self.PREMULT:
            STREAM = STREAM.filter('premultiply', inplace="1")

        # Add scaling
        STREAM = self.add_scaling(STREAM)
        OUT_ARGS["sws_flags"] = self.SCALER

        # Add audio options if audio stream added
        if self.AUDIO:
            OUT_ARGS['c:a': 'aac']
            OUT_ARGS['b:a': '320k']
            OUT_ARGS['shortest': None]


        STREAM = STREAM.output(outputf, **OUT_ARGS)

        return STREAM



    def video_to_video(self, infile):
        # ==================================
        # Vid-Vid conversion (with audio)
        # TODO
        # ==================================
        saveDir = infile
        STREAM = ffmpeg.input(infile)

        OUT_ARGS = dict()
        if self.CODEC == "H.264":
            OUT_ARGS['vcodec'] = "libx264"
            OUT_ARGS['pix_fmt'] = 'yuv420p'
            OUT_ARGS['crf'] = str(self.CRF)
            OUT_ARGS['preset'] = self.PRESET
        outputf = str(saveDir.with_name(stem + "_converted." + self.VIDFORMAT))
        STREAM = STREAM.output(outputf, **OUT_ARGS)

        return STREAM


    def convert(self, path):
        infile = self.get_input_file(path)
        suffix = infile.suffix
        if (suffix in alltypes):
            STREAM = self.input_stream(infile)
            if not STREAM:
                print("Cannot find valid input file.")
                return
            STREAM = self.add_audio(infile, STREAM)
            STREAM = self.build_output(infile, STREAM)
        elif suffix in vid_suff:
            STREAM = self.video_to_video(infile)
        else:
            print("Invalid file extension")
            return

        (stdout, stderr) = STREAM.run(capture_stdout=True, capture_stderr=True)
        print(stderr.decode("utf-8")) # ffmpeg pipes everything to stderr

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
