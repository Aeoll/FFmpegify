# FFmpegify

![alt text](https://github.com/Aeoll/FFmpegify/blob/master/example.gif "ffmpegify")

A Context Menu addition for Windows for quick conversion of image sequences to videos
- Supports JPG, PNG, TIFF, TGA and EXR sequences (single-layer EXRs only)
- Supports arbitrary starting frame numbers, image sizes and frame number padding

# Setup
- Install Python36 to C:/Python36 (Or other location and edit ffmpegify.reg)
- Install FFmpeg and ensure it is available to the command line (i.e added to the PATH environment variable)
- Download and extract this repository to C:/FFmpegify (Or other location and edit ffmpegify.reg)
- Run ffmpegify.reg - FFmpegify will appear as a context menu item for all filetypes.
- For guaranteed results the frame number should be directly before the extension. (e.g MySequence.0034.jpg or MySeq2_003.exr)
- The script will work on any frame number - you do not need to select the fist frame in the sequence. 

# Alternate settings
- 2 other python files are included which demonstrate alternate ffmpeg settings for output format, conversion speed and bitrate.
