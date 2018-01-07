# FFmpegify

![alt text](https://github.com/Aeoll/FFmpegify/blob/master/example.gif "ffmpegify")

A Context Menu addition for fast conversion of image sequences to videos
- Supports JPG, PNG, TIFF, TGA and EXR sequences (single-layer EXRs only)
- Supports arbitrary starting frame numbers, image sizes and frame number padding
- Applies a premultiply filter for better conversion of transparent images  

# Windows Setup
- Install Python36 to C:/Python36 (Or other location and edit ffmpegify.reg)
- Install FFmpeg and ensure it is available to the command line (i.e added to the PATH environment variable)
- Download and extract this repository to C:/FFmpegify (Or other location and edit ffmpegify.reg)
- Run ffmpegify.reg - FFmpegify will appear as a context menu item for all filetypes

# Mac Setup
- Install Python36 (the default install location is /usr/local/bin/python3)
- Install FFmpeg. The easiest way to do this is to install Homebrew https://brew.sh/ and then run `brew install ffmpeg` in a terminal
- Download and extract this repository to your chosen location
- Open 'Automator' and create a new 'Run Shell Script' automation as shown, with the ffmpegify path set to your chosen location
![alt text](https://github.com/Aeoll/FFmpegify/blob/master/osxsetup.png "osxsetup")
- FFmpegify will appear at the bottom of the Finder context menu for all filetypes

# Tips
- The frame numbering should be directly before the extension. (e.g MySequence.0034.jpg)
- The script works for any frame number selected - you do not need to select the fist frame in the sequence.
- 2 other python files are included which demonstrate alternate settings for output format, conversion speed and bitrate. These settings are defined at the top of the file
