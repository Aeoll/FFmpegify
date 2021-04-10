# FFmpegify

A Context Menu script for fast conversion of image sequences to videos, or videos to other formats
- Supports JPG, PNG, TIFF, TGA and EXR sequence image inputs, and MOV and MP4 video inputs
- Supports arbitrary starting frame numbers and frame number padding
- Supports MOV, MP4, PNG Sequence and TIFF Sequence outputs
- Option for maximum output width and height (maintains aspect ratio)
- Applies a premultiply filter for better conversion of transparent images and gamma adjust linear image sequences (EXR, TGA)
- Many settings can be adjusted with the 'FFmpegifySettings' dialog accessed by right-clicking an empty area in File Explorer

# Windows Installation
- Install Python3. Install FFmpeg and ensure it is available to the command line (i.e added to the PATH environment variable)
- Install the necessary python libraries with `pip install -r requirements.txt`
- Adjust the entries in 'ffmpegify.reg' to point to the correct Python install and FFmpegify locations and run the file. FFmpegify will appear as a context menu item for all file types.

# Mac Installation
- Install Python3 (the default install location is /usr/local/bin/python3)
- Install FFmpeg. The easiest way to do this is to install Homebrew https://brew.sh/ and then run `brew install ffmpeg` in a terminal
- Download and extract this repository to your chosen location
- Open 'Automator' and create a new 'Run Shell Script' automation as shown, with the ffmpegify path set to your chosen location
![alt text](https://github.com/Aeoll/FFmpegify/blob/master/img/osxsetup.png "osxsetup")
- FFmpegify will appear at the bottom of the Finder context menu for all filetypes

# Linux Installation (Nemo)
- Install the latest version of FFmpeg
- To add to the context menu of the Nemo file manager you use of nemo actions, described here https://wiki.archlinux.org/index.php/Nemo#Nemo_Actions
- Copy ffmpegify.nemo_action to /usr/share/nemo/actions/
- Copy ffmpegify.py to /usr/share/nemo/actions/ (ensure root has execution rights)

# Tips
- You can edit the 'config.ini' script to define a custom ffmpeg path or a custom path for the 'settings.json' file which contains video conversion options.
- The frame numbering should be directly before the extension. (e.g MySequence.0034.jpg)
- The script works for any frame number selected - you do not need to select the fist frame in the sequence.