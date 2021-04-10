import re, sys, glob, os, time, json, subprocess
from pathlib import Path
import ffmpeg

standardImg = [".jpg", ".jpeg", ".png", ".tiff", ".tif"]
linearImg = [".exr", ".tga"]
imgTypes = standardImg + linearImg
vidTypes = [".mov", ".mp4", ".webm", ".mkv", ".avi"]
vidOutput = ["mov", "mp4", "mp4-via-jpg", "webm"]

class FFMPEGIFY:
    def __init__(self, config):
        self.CUSTOM_FFMPEG = None
        self.AUDIO = None
        self.STREAMINFO = None
        self.AUDIOINFO = None

        '''
        Extract config to constants
        '''
        self.START_FRAME = int(config["startFrame"])
        self.MAX_FRAMES = int(config["maxFrames"])
        self.MAX_WIDTH = int(config["maxWidth"])
        self.MAX_HEIGHT = int(config["maxHeight"])
        self.SCALER = config["scaler"]
        self.CRF = int(config["quality"])
        self.FRAME_RATE = int(config["FPS"])
        self.PRESET = config["preset"]
        self.CODEC = config["codec"]
        self.VIDFORMAT = config["format"]
        if self.CODEC == "ProResHQ":
            self.VIDFORMAT = "mov"

        self.GAMMA = config["gamma"]
        self.PREMULT = config["premult"]
        self.NAME_LEVELS = int(config["namelevels"])  # Create output file in higher-up directories
        self.USE_AUDIO = config["useaudio"]
        self.AUDIO_OFFSET = int(config["audiooffset"])

        self.isVidOut = True  # Check if being output to video or frames
        if self.VIDFORMAT not in vidOutput:
            self.isVidOut = False

    def set_ffmpeg(self, ffmpeg_path):
        '''
        Set a custom ffmpeg location
        '''
        if ffmpeg_path:
            self.CUSTOM_FFMPEG = ffmpeg_path

    def get_metadata(self, inputf):
        '''
        Use ffprobe to load metadata
        '''
        # ffprobeInfo = ffmpeg.probe(str(inputf))
        ffprobeInfo = ffmpeg.probe(str(inputf), v = "quiet")
        self.STREAMINFO = ffprobeInfo["streams"][0]
        if ffprobeInfo["format"]["nb_streams"] > 1:
            self.AUDIOINFO = ffprobeInfo["streams"][1]

    def get_input_file(self, path):
        '''
        Get the input selected frame. If the input path is a directory it searches contained files for a valid frame.
        '''
        infile = Path(path)
        if os.path.isdir(path):
            files = os.listdir(path)
            for f in files:
                fpath = Path(f)
                if fpath.suffix in imgTypes:
                    infile = infile.joinpath(fpath)
                    break
        return infile

    def get_output_filename(self, infile):
        '''
        Creates the output filepath. Avoids overwrites
        '''
        saveDir = infile  # naming the video file based on parent dir. Could change this later.
        parts = infile.parent.parts
        if self.NAME_LEVELS > 0:
            sec = len(parts) - self.NAME_LEVELS
            parts = parts[sec:]
            outname = "_".join(parts)
        else:
            outname = str(infile.parent)
        outname = re.sub(r"\W+", "_", outname)
        outputf = str(saveDir.with_name("_" + outname + "_video." + self.VIDFORMAT))
        if not self.isVidOut:
            outputf = str(
                saveDir.with_name(
                    "_" + preframepart + "_" + padstring + "." + self.VIDFORMAT
                )
            )

        # If the video already exists create do not overwrite it
        counter = 1
        while Path(outputf).exists():
            outputf = str(
                saveDir.with_name(
                    "_" + outname + "_video_" + str(counter) + "." + self.VIDFORMAT
                )
            )
            counter = counter + 1
        return outputf

    def input_stream(self, infile):
        '''
        Generate ffmpeg arg stream. Arguments for the input stream would be placed prior to -i on commandline?
        '''
        IN_ARGS = (dict())

        # Parse input filename for framenumber. simple regex match - find digits at the end of the filename.
        # Examples: frame.0001.exr, frame0001.exr, frame1.exr
        stem = infile.stem
        suffix = infile.suffix
        l = len(stem)
        back = stem[::-1]
        m = re.search("\d+", back)
        if m:
            sp = m.span(0)
            sp2 = [l - a for a in sp]
            sp2.reverse()

            # glob for other frames in the folder and find the first frame to use as start number
            preframepart = stem[0 : sp2[0]]
            postframepart = stem[sp2[1] :]
            frames = sorted(
                infile.parent.glob(preframepart + "*" + postframepart + suffix)
            )
            start_num = int(frames[0].name[sp2[0] : sp2[1]])
            if self.START_FRAME > 0:
                start_num = self.START_FRAME

            # get padding for frame num
            padding = sp2[1] - sp2[0]
            padstring = "%" + format(padding, "02") + "d"  # eg %05d
            # fix for unpadded frame numbers
            if len(frames[0].name) != len(frames[-1].name):
                padstring = "%" + "d"

            # get absolute path to the input file
            inputf = stem[0 : sp2[0]] + padstring + postframepart + suffix
            inputf_abs = str(infile.with_name(inputf))

            if suffix in linearImg:
                IN_ARGS["gamma"] = self.GAMMA
            IN_ARGS["start_number"] = str(start_num).zfill(padding)
            IN_ARGS["framerate"] = str(self.FRAME_RATE)
            STREAM = ffmpeg.input(inputf_abs, **IN_ARGS)
            return STREAM
        return None

    def add_audio(self, infile, STREAM):
        '''
        Search for adjacent audio files and add to the stream
        '''
        try:
            tracks = []
            tracks.extend(sorted(infile.parent.glob("*.mp3")))
            tracks.extend(sorted(infile.parent.glob("*.wav")))
            if tracks and self.USE_AUDIO:
                self.AUDIO = ffmpeg.input(
                    str(tracks[0]), **{"itsoffset": str(self.AUDIO_OFFSET)}
                )
                print("Found audio tracks: " + str(tracks))
        except Exception as e:
            print("Error adding audio: " + str(e))

    def add_scaling(self, STREAM):
        '''
        Scale the output. FFprobe is used to get input image/video dimensions
        '''
        scalekw = {}
        scalekw["out_color_matrix"] = "bt709"
        iw = self.STREAMINFO["width"] # "coded_width" can be larger than 'width' and causes errors in vid-vid conversion?
        ih = self.STREAMINFO["height"] # "coded_height" can be larger than 'height' and causes errors in vid-vid conversion?
        # Round to even pixel dimensions
        rounded_w = iw - (iw % 2)
        rounded_h = ih - (ih % 2)
        downscale_w = min(self.MAX_WIDTH, rounded_w)
        downscale_h = min(self.MAX_HEIGHT, rounded_h)
        print("iw: {} ih: {} downscale_w: {} downscale_h: {}".format(iw, ih, downscale_w, downscale_h))

        # If no max dim just crop odd pixels
        if self.MAX_HEIGHT <= 0 and self.MAX_WIDTH <= 0:
            scale = [rounded_w, rounded_h]
            return STREAM.filter("crop", scale[0], scale[1])

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

        return STREAM.filter("scale", scale[0], scale[1], **scalekw)

    def build_output(self, infile, STREAM):
        '''
        Construct output stream arguments and output filepath (image sequence input)
        '''
        outputf = self.get_output_filename(infile)
        OUT_ARGS = dict()

        if self.isVidOut:
            if self.CODEC == "H.264":
                OUT_ARGS["vcodec"] = "libx264"
                OUT_ARGS["vprofile"] = "baseline"
                OUT_ARGS["pix_fmt"] = "yuv420p"
                OUT_ARGS["crf"] = str(self.CRF)
                OUT_ARGS["preset"] = self.PRESET
                OUT_ARGS[
                    "x264opts"
                ] = "colorprim=bt709:transfer=bt709:colormatrix=smpte170m"
                OUT_ARGS["max_muxing_queue_size"] = 4096
            elif self.CODEC == "ProResHQ":
                OUT_ARGS["vcodec"] = "prores"
                OUT_ARGS["profile"] = "3" # 422 HQ
                OUT_ARGS["pix_fmt"] = "yuv422p10le"
                OUT_ARGS["qscale"] = "13" # prores quality - could add configuration option for this? 9-13 is recommended
            else:
                pass

            if self.VIDFORMAT == "webm":
                # Possibly implement two-pass for webm
                OUT_ARGS = dict()
                OUT_ARGS["crf"] = str(self.CRF)
                OUT_ARGS["vcodec"] = "libvpx-vp9"
                OUT_ARGS["b:v"] = 0
        elif self.VIDFORMAT == "jpg":
            OUT_ARGS["q:v"] = "2"

        if self.MAX_FRAMES > 0:
            OUT_ARGS["-vframes"] = str(self.MAX_FRAMES)

        # Add premult filter. Maybe causing problems??
        if self.isVidOut and self.PREMULT:
            STREAM = STREAM.filter("premultiply", inplace="1")

        # Add scaling
        STREAM = self.add_scaling(STREAM)
        OUT_ARGS["sws_flags"] = self.SCALER

        # Add audio options if audio stream added
        if self.AUDIO:
            OUT_ARGS["c:a"] = "aac"
            OUT_ARGS["b:a"] = "320k"
            OUT_ARGS["shortest"] = None
            STREAM = STREAM.output(self.AUDIO, outputf, **OUT_ARGS)
            print("GOT AUDIO")
        else:
            OUT_ARGS["an"] = None
            STREAM = STREAM.output(outputf, **OUT_ARGS)
            print("NO AUDIO")
        return STREAM

    def has_audio_streams(self, file_path):
        streams = ffmpeg.probe(file_path)["streams"]
        for stream in streams:
            if stream["codec_type"] == "audio":
                return True
        return False

    def build_output_video_to_video(self, infile):
        '''
        Construct output stream arguments and output filepath (video as input)
        TODO vid-vid convert with audio?
        https://github.com/kkroening/ffmpeg-python/issues/204
        '''
        stem = infile.stem
        saveDir = infile

        STREAM = ffmpeg.input(str(infile))
        audio_in = STREAM.audio

        OUT_ARGS = dict()
        if self.isVidOut:
            template = "_converted."
            if self.CODEC == "H.264":
                OUT_ARGS["vcodec"] = "libx264"
                OUT_ARGS["pix_fmt"] = "yuv420p"
                OUT_ARGS["vprofile"] = "baseline"
                OUT_ARGS["crf"] = str(self.CRF)
                OUT_ARGS["preset"] = self.PRESET
            elif self.CODEC == "ProResHQ":
                OUT_ARGS["vcodec"] = "prores"
                OUT_ARGS["profile"] = "3"
                OUT_ARGS["pix_fmt"] = "yuv422p10le"
                OUT_ARGS["qscale"] = "13"

            if not self.AUDIOINFO:
                OUT_ARGS["an"] = None
                print("NO AUDIO")
        else:
            template = "_converted.%04d."  # Output image sequence

        STREAM = self.add_scaling(STREAM)
        OUT_ARGS["sws_flags"] = self.SCALER

        outputf = str(saveDir.with_name(stem + template + self.VIDFORMAT))
        STREAM = ffmpeg.output(STREAM, audio_in, outputf, **OUT_ARGS)
        return STREAM

    def convert(self, path):
        '''
        Compile final command and run ffmpeg
        '''

        infile = self.get_input_file(path)
        self.get_metadata(infile)
        suffix = str(infile.suffix)
        if suffix in imgTypes:
            STREAM = self.input_stream(infile)
            if not STREAM:
                print("Cannot find valid input file.")
                return
            self.add_audio(infile, STREAM)
            STREAM = self.build_output(infile, STREAM)
        elif suffix in vidTypes:
            STREAM = self.build_output_video_to_video(infile)
        else:
            print("Invalid file extension: " + str(suffix))
            return

        # (stdout, stderr) = STREAM.run(capture_stdout=True, capture_stderr=True) # original call - using ffmpeg.run()
        if not self.CUSTOM_FFMPEG:
            cmd = STREAM.compile()
        else:
            cmd = STREAM.compile(cmd=self.CUSTOM_FFMPEG)

        cmd = [re.sub(r'^(\d:a)$', '\\1?', arg) for arg in cmd] # add optional (?) flag to audio streams. Prevents error in vid->vid if no audio present
        print(" ".join(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stderr.decode("utf-8"))

# =================================================================
# Configuration readers and main entry point
# =================================================================

from configparser import ConfigParser

def read_config(config_file):
    '''
    Read config.ini. Used to define custom ffmpeg / settings.json locations
    '''
    config = ConfigParser()
    config.read(str(config_file))

    custom_ffmpeg_path = None
    try:
        ffmpeg_path = config.get('config', 'ffmpeg')
        # set the custom ffmpeg location if it exists
        if ffmpeg_path and Path(ffmpeg_path).exists():
            custom_ffmpeg_path = str(ffmpeg_path)
    except:
        print("custom ffmpeg path not used")

    # set  the custom settings json file if it exists
    custom_settings_file = str(config_file.with_name("settings.json"))
    try:
        settings_file = config.get('config', 'settings')
        if settings_file and Path(settings_file).exists():
            custom_settings_file = str(settings_file)
        else:
            print("unable to find settings file in custom location - using default location")
    except:
        print("custom settings.json path not used")

    return custom_ffmpeg_path, custom_settings_file

def read_settings(settings_file):
    '''
    Read json settings file which defines video conversion parameters
    '''
    try:
        with open(settings_file, "r") as f:
            config = json.load(f)
            return config
    except Exception as e:
        print(e)


if __name__ == "__main__":
    path = Path(sys.argv[0])
    custom_ffmpeg, settings_file = read_config(path.with_name("config.ini"))

    settings = read_settings(settings_file)
    F = FFMPEGIFY(settings)
    F.set_ffmpeg(custom_ffmpeg)
    try:
        F.convert(sys.argv[1])
        # input()
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        input()
