#! /usr/bin/python3 -OOt

import pathlib
import re
import sys
import glob
import os
import subprocess
from pathlib import Path
import time
import json
import ffmpeg


standardImg = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
linearImg = ['.exr', '.tga']
imgTypes = standardImg + linearImg
vidTypes = ['.mov', '.mp4', '.webm', '.mkv', '.avi'] # do vid-vid conversion with audio as well?
vidOutput = ['mov', 'mp4', 'mp4-via-jpg', 'webm']


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
        self.USE_AUDIO = int(config['useaudio'])
        self.AUDIO = None
        self.AUDIO_OFFSET = int(config['audiooffset'])


        self.STREAMINFO = None
        self.AUDIOINFO = None

        self.isVidOut = True # Check if being output to video or frames
        if self.VIDFORMAT not in vidOutput:
            self.isVidOut = False

    def get_metadata(self, inputf):
        # Use ffprobe to load metadata
        print(inputf)
        ffprobeInfo = ffmpeg.probe(str(inputf))
        self.STREAMINFO = ffprobeInfo['streams'][0]
        if ffprobeInfo['format']['nb_streams'] > 1:
            self.AUDIOINFO = ffprobeInfo['streams'][1]

    def get_input_file(self, path):
        # Parse filename
        infile = pathlib.Path(path)
        if os.path.isdir(path):
            files = os.listdir(path)
            for f in files:
                fpath = pathlib.Path(f)
                if fpath.suffix in imgTypes:
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
        if m:
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




            if suffix in linearImg:
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
            # tracks.extend(sorted(infile.parents[1].glob('*.mp3')))
            # tracks.extend(sorted(infile.parents[1].glob('*.wav')))
            if (tracks and self.USE_AUDIO):
                self.AUDIO = ffmpeg.input(str(tracks[0]), **{'itsoffset': str(self.AUDIO_OFFSET)})
                print("Found audio tracks: " + str(tracks))
        except Exception as e:
            print("Error adding audio: " + str(e))


    def add_scaling(self, STREAM):
        scalekw = {}
        scalekw['out_color_matrix'] = "bt709"
        iw = self.STREAMINFO['coded_width']
        ih = self.STREAMINFO['coded_height']
        # Round to even pixel dimensions
        rounded_w = iw - (iw % 2)
        rounded_h  = ih - (ih % 2)
        downscale_w = min(self.MAX_WIDTH, rounded_w)
        downscale_h = min(self.MAX_HEIGHT, rounded_h)

        print("iw: {}    ih: {}      downscale_w: {}      downscale_h: {}".format(iw, ih, downscale_w, downscale_h))

        # If no max dim just crop odd pixels
        if self.MAX_HEIGHT <= 0 and self.MAX_WIDTH <= 0:
            scale = [rounded_w, rounded_h]
            return STREAM.filter('crop', scale[0], scale[1])

        if (self.MAX_WIDTH) > 0 and (self.MAX_HEIGHT > 0):
            # The smaller downscale_w / rounded_w, the more extreme the cropping (1.0 means no cropping)
            # If width cropping is more extreme, we can set height cropping to 0
            if (downscale_w / rounded_w) > (downscale_h / rounded_h):
                self.MAX_WIDTH = 0
            else:
                self.MAX_HEIGHT = 0

        if self.MAX_WIDTH == 0:
            scale = ["-2", downscale_h]
        elif self.MAX_HEIGHT == 0:
            scale = [downscale_w, "-2"]
        # else:
        #     scale = [downscale_w, downscale_h]
        #     scalekw["force_original_aspect_ratio"] = "decrease"

        return STREAM.filter('scale', scale[0], scale[1], **scalekw)





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
                OUT_ARGS['x264opts'] = 'colorprim=bt709:transfer=bt709:colormatrix=smpte170m'
                OUT_ARGS['max_muxing_queue_size'] = 4096
                # OUT_ARGS['color_primaries'] = 'bt709'
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
            if self.VIDFORMAT == 'webm':
                # Possibly implement two-pass for webm
                OUT_ARGS = dict()
                OUT_ARGS['crf'] = str(self.CRF)
                OUT_ARGS['vcodec'] = "libvpx-vp9"
                OUT_ARGS['b:v'] = 0


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
            OUT_ARGS['c:a'] = 'aac'
            OUT_ARGS['b:a'] = '320k'
            OUT_ARGS['shortest'] = None
            STREAM = STREAM.output(self.AUDIO, outputf, **OUT_ARGS)
            print("GOT AUDIO")
        else:
            OUT_ARGS['an'] = None
            STREAM = STREAM.output(outputf, **OUT_ARGS)
            print("NO AUDIO")

        return STREAM



    def video_to_video(self, infile):
        # ==================================
        # Vid-Vid conversion (with audio)
        # TODO
        # ==================================
        stem = infile.stem
        saveDir = infile
        STREAM = ffmpeg.input(str(infile))
        audio_in = STREAM.audio

        OUT_ARGS = dict()
        if self.isVidOut:
            template = "_converted."
            if self.CODEC == "H.264":
                OUT_ARGS['vcodec'] = "libx264"
                OUT_ARGS['pix_fmt'] = 'yuv420p'
                OUT_ARGS['crf'] = str(self.CRF)
                OUT_ARGS['preset'] = self.PRESET
                OUT_ARGS['vprofile'] = "baseline"
            if not self.AUDIOINFO:
                OUT_ARGS['an'] = None
                print("NO AUDIO")
        else:
            template = "_converted.%04d." # Output image sequence

        STREAM = self.add_scaling(STREAM)
        OUT_ARGS["sws_flags"] = self.SCALER

        outputf = str(saveDir.with_name(stem + template + self.VIDFORMAT))
        STREAM = ffmpeg.output(STREAM, audio_in, outputf, **OUT_ARGS)
        return STREAM


    def convert(self, path):
        infile = self.get_input_file(path)
        self.get_metadata(infile)
        suffix = str(infile.suffix)
        if (suffix in imgTypes):
            STREAM = self.input_stream(infile)
            if not STREAM:
                print("Cannot find valid input file.")
                return
            self.add_audio(infile, STREAM)
            STREAM = self.build_output(infile, STREAM)
        elif (suffix in vidTypes):
            STREAM = self.video_to_video(infile)
        else:
            print("Invalid file extension: " + str(suffix))
            return

        print(" ".join(STREAM.compile()))
        (stdout, stderr) = STREAM.run(capture_stdout=True, capture_stderr=True)
        print(stderr.decode("utf-8"))

# Read config file for settings
def readSettings(settings):
    try:
        with open(settings, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        print(e)

if __name__ == '__main__':
    path = Path(sys.argv[0]).with_name('settings.json')
    config = readSettings(path)
    F = FFMPEGIFY(config)
    try:
        F.convert(sys.argv[1])
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stdout)

    input()
