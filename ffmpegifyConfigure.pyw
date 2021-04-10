from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *
import os
import sys
import json
from pathlib import *

class FFMPEGIFY_CONFIGURE(QDialog):
    presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
    formats = ["mov", "mp4", "webm", "png", "tiff", "jpg"]
    codecs = ["H.264", "ProResHQ"]
    scalers = ["bicubic", "bilinear", "lanczos", "neighbor"]

    def __init__(self, settings_file):
        super().__init__()
        self.settings_file = settings_file
        self.settings_file_fallback = str(Path(os.path.dirname(os.path.realpath(__file__))).joinpath("settings.json"))
        self.initUI()

    def initUI(self):
        self.cf = self.readSettings()

        # main top level layout
        mainlayout = QVBoxLayout()

        layout = QFormLayout()
        # FRAMERATE
        self.fps_label = QLabel("Frame Rate")
        self.fps_widget = QSpinBox()
        self.fps_widget.setValue(int(self.cf['FPS']))
        layout.addRow(self.fps_label, self.fps_widget)

        # QUALITY
        self.cf_label = QLabel("Quality (0-51: Lower=Better Quality)")
        self.cf_widget = QSpinBox()
        self.cf_widget.setValue(int(self.cf['quality']))
        layout.addRow(self.cf_label, self.cf_widget)

        # MAXWIDTH
        self.maxw_label = QLabel("Maximum Width (0 to disable)")
        self.maxw_widget = QSpinBox()
        self.maxw_widget.setRange(0, 5000)
        self.maxw_widget.setValue(int(self.cf['maxWidth']))
        layout.addRow(self.maxw_label, self.maxw_widget)

        # MAXHEIGHT
        self.maxh_label = QLabel("Maximum Height (0 to disable)")
        self.maxh_widget = QSpinBox()
        self.maxh_widget.setRange(0, 5000)
        self.maxh_widget.setValue(int(self.cf['maxHeight']))
        layout.addRow(self.maxh_label, self.maxh_widget)

        # SCALER
        self.scaler_label = QLabel("Scaling Algorithm")
        self.scaler_widget = QComboBox()
        for p in self.scalers:
            self.scaler_widget.addItem(p)
        self.scaler_widget.setCurrentText(self.cf['scaler'])
        layout.addRow(self.scaler_label, self.scaler_widget)

        # START FRAME
        self.startframe_label = QLabel("Start Frame (0 for first in sequence)")
        self.startframe_widget = QSpinBox()
        self.startframe_widget.setRange(0, 5000)
        self.startframe_widget.setValue(int(self.cf['startFrame']))
        layout.addRow(self.startframe_label, self.startframe_widget)

        # END FRAME (LEN)
        self.endframe_label = QLabel("Max Frames (0 for no maximum)")
        self.endframe_widget = QSpinBox()
        self.endframe_widget.setRange(0, 5000)
        self.endframe_widget.setValue(int(self.cf['maxFrames']))
        layout.addRow(self.endframe_label, self.endframe_widget)

        # GAMMA
        self.gamma_label = QLabel("Gamma (EXR/TGA only)")
        self.gamma_widget = QDoubleSpinBox()
        self.gamma_widget.setValue(float(self.cf['gamma']))
        layout.addRow(self.gamma_label, self.gamma_widget)

        # PREMULT
        self.premult_label = QLabel("Premultiply Alpha")
        self.premult_widget = QCheckBox()
        self.premult_widget.setTristate(False)
        self.premult_widget.setChecked(self.cf['premult']=="True")
        layout.addRow(self.premult_label, self.premult_widget)

        # PRESET
        self.preset_label = QLabel("Preset")
        self.preset_widget = QComboBox()
        for p in self.presets:
            self.preset_widget.addItem(p)
        self.preset_widget.setCurrentText(self.cf['preset'])
        layout.addRow(self.preset_label, self.preset_widget)

        # CODEC
        self.codec_label = QLabel("Codec")
        self.codec_widget = QComboBox()
        for p in self.codecs:
            self.codec_widget.addItem(p)
        self.codec_widget.setCurrentText(self.cf['codec'])
        layout.addRow(self.codec_label, self.codec_widget)

        # FORMAT
        self.format_label = QLabel("Format")
        self.format_widget = QComboBox()
        for p in self.formats:
            self.format_widget.addItem(p)
        self.format_widget.setCurrentText(self.cf['format'])
        layout.addRow(self.format_label, self.format_widget)

        # NAMING LEVELS
        self.namelevels_label = QLabel("Naming Levels (0 for full path)")
        self.namelevels_widget = QSpinBox()
        self.namelevels_widget.setRange(0, 10)
        self.namelevels_widget.setValue(int(self.cf['namelevels']))
        layout.addRow(self.namelevels_label, self.namelevels_widget)

        # AUDIO
        self.audio_label = QLabel("Enable Audio")
        self.audio_widget = QCheckBox()
        self.audio_widget.setTristate(False)
        self.audio_widget.setChecked(self.cf['useaudio']=="True")
        layout.addRow(self.audio_label, self.audio_widget)

        # AUDIO OFFSET
        self.audiooffset_label = QLabel("Audio Offset (Seconds)")
        self.audiooffset_widget = QSpinBox()
        self.audiooffset_widget.setRange(-200, 200)
        self.audiooffset_widget.setValue(int(self.cf['audiooffset']))
        layout.addRow(self.audiooffset_label, self.audiooffset_widget)

        # Add form to main layout
        mainlayout.addLayout(layout)

        # Spacer after form
        line = QFrame()
        line.setMinimumSize(0, 10)
        mainlayout.addWidget(line)

        # ButtonBox
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bbox.setCenterButtons(True)
        self.bbox.accepted.connect(self.writeSettings)
        self.bbox.rejected.connect(self.reject)
        mainlayout.addWidget(self.bbox)

        self.setLayout(mainlayout)
        self.setGeometry(350, 300, 250, 150)
        self.setWindowTitle('FFmpegify Settings')
        self.show()

    # Open it under the cursor
    def showEvent(self, event):
        geom = self.frameGeometry()
        geom.moveCenter(QCursor.pos())
        self.setGeometry(geom)
        super(FFMPEGIFY_CONFIGURE, self).showEvent(event)

    # Prevent hitting Enter from pressing OK button
    def keyPressEvent(self, event):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                pass

    def readSettings(self):
        try:
            with open(self.settings_file, 'r') as f:
                config = json.load(f)
        except:
            print("couldn't read custom settings file - using default")
            with open(self.settings_file_fallback, 'r') as f:
                config = json.load(f)
        return config

    # Connect to OK button
    def writeSettings(self):
        cfg = {}
        cfg['FPS'] = str(self.fps_widget.value())
        cfg['startFrame'] = str(self.startframe_widget.value())
        cfg['maxFrames'] = str(self.endframe_widget.value())
        cfg['maxWidth'] = str(self.maxw_widget.value())
        cfg['maxHeight'] = str(self.maxh_widget.value())
        cfg['scaler'] = self.scaler_widget.currentText()
        cfg['quality'] = str(self.cf_widget.value())
        cfg['gamma'] = str(self.gamma_widget.value())
        cfg['premult'] = "True" if self.premult_widget.isChecked() else "False"
        cfg['preset'] = self.preset_widget.currentText()
        cfg['codec'] = self.codec_widget.currentText()
        cfg['format'] = self.format_widget.currentText()
        cfg['namelevels'] = str(self.namelevels_widget.value())
        cfg['useaudio'] = "True" if self.audio_widget.isChecked() else "False"
        cfg['audiooffset'] = str(self.audiooffset_widget.value())

        sf = Path(self.settings_file)
        if not sf.exists():
            anchor = Path(sf.anchor)
            if anchor.exists():
                print(str(self.settings_file))
                sf.parent.mkdir(parents=True, exist_ok=True)
            else:
                print("unable to create settings file in custom location - using default location")
                self.settings_file = self.settings_file_fallback

        with open(self.settings_file, 'w') as f:
            json.dump(cfg, f, indent=4, sort_keys=False)
        self.accept()

# =================================================================
# Configuration and main entry point
# =================================================================

from configparser import ConfigParser

def get_settings_file(config_file):
    settings_file_default = config_file.with_name("settings.json")
    config = ConfigParser()
    config.read(str(config_file))

    # set  the custom settings json file if it exists
    settings_file = config.get('config', 'settings')
    return str(settings_file)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    path = Path(sys.argv[0])
    settings_file = get_settings_file(path.with_name("config.ini"))

    ex = FFMPEGIFY_CONFIGURE(settings_file)
    ex.show()
    sys.exit(app.exec_())