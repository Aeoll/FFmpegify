# FFmpegify

![alt text](https://github.com/Aeoll/FFmpegify/blob/master/img/example.gif "ffmpegify")

A Context Menu addition for fast conversion of image sequences to videos
- Supports JPG, PNG, TIFF, TGA and EXR sequences
- Supports arbitrary starting frame numbers and frame number padding
- Can output MOV, MP4, PNG Sequence and TIFF Sequence
- Supports maximum output width and height settings (maintains aspect ratio)   
- Applies a premultiply filter for better conversion of transparent images and gamma correct linear sequences (EXR, TGA)
- The settings can be adjusted in an 'ffmpegifySettings' dialog accessed by right clicking an empty area in Windows Explorer 

# Windows Setup
- Install Python36 to C:/Python36
- Install FFmpeg and ensure it is available to the command line (i.e added to the PATH environment variable)
- Install PyQt5 (needed for the settings menu) by running 'pip install PyQt5' from the command line
- Download and extract this repository to C:/FFmpegify
- Run ffmpegify.reg - FFmpegify will appear as a context menu item for all filetypes

# Mac Setup
- Install Python3 (the default install location is /usr/local/bin/python3)
- Install FFmpeg. The easiest way to do this is to install Homebrew https://brew.sh/ and then run `brew install ffmpeg` in a terminal
- Download and extract this repository to your chosen location
- Open 'Automator' and create a new 'Run Shell Script' automation as shown, with the ffmpegify path set to your chosen location
![alt text](https://github.com/Aeoll/FFmpegify/blob/master/img/osxsetup.png "osxsetup")
- FFmpegify will appear at the bottom of the Finder context menu for all filetypes

# Linux Setup (Nemo)
- Install the latest version of FFmpeg
- To add to the context menu of the Nemo file manager you use of nemo actions, described here https://wiki.archlinux.org/index.php/Nemo#Nemo_Actions
- Copy ffmpegify.nemo_action to /usr/share/nemo/actions/
- Copy ffmpegify.py to /usr/share/nemo/actions/ (ensure root has execution rights)

# Tips
- The frame numbering should be directly before the extension. (e.g MySequence.0034.jpg)
- The script works for any frame number selected - you do not need to select the fist frame in the sequence.