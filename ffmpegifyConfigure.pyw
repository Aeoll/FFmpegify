from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import os
import sys
import json
from pathlib import *

# So much boilerplate...Wow.. Just use Qt Designer...

class Example(QDialog):
    presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
    formats = ["mov", "mp4"]

    def __init__(self, ffmpegify_loc):
        super().__init__()
        self.loc = ffmpegify_loc
        self.initUI()
        
    def initUI(self):    
        self.cf = self.readSettings()
        layout = QFormLayout()

        # FRAMERATE
        self.fps_label = QLabel("Frame Rate")
        self.fps_widget = QSpinBox()
        self.fps_widget.setValue(int(self.cf['FPS']))    
        layout.addRow(self.fps_label, self.fps_widget)

        # QUALITY
        self.cf_label = QLabel("Quality Factor (0-51)")
        self.cf_widget = QSpinBox()
        self.cf_widget.setValue(int(self.cf['quality']))    
        layout.addRow(self.cf_label, self.cf_widget)

        # MAXWIDTH
        self.maxw_label = QLabel("Minimum Width (0 to disable)")
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

        # END FRAME (LEN)
        self.endframe_label = QLabel("Frame limit (0 to disable)")
        self.endframe_widget = QSpinBox()
        self.endframe_widget.setRange(0, 5000)    
        self.endframe_widget.setValue(int(self.cf['maxFrames']))    
        layout.addRow(self.endframe_label, self.endframe_widget)
        
        # PRESET
        self.preset_label = QLabel("Preset")
        self.preset_widget = QComboBox()
        for p in self.presets:
            self.preset_widget.addItem(p)   
        self.preset_widget.setCurrentText(self.cf['preset'])
        layout.addRow(self.preset_label, self.preset_widget)
        
        # FORMAT
        self.format_label = QLabel("Format")
        self.format_widget = QComboBox()
        for p in self.formats:
            self.format_widget.addItem(p)        
        self.format_widget.setCurrentText(self.cf['format'])            
        layout.addRow(self.format_label, self.format_widget)

        # ButtonBox
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)    
        self.bbox.setCenterButtons(True)  
        self.bbox.accepted.connect(self.writeSettings)
        self.bbox.rejected.connect(self.reject)
        layout.addWidget(self.bbox)        

        self.setLayout(layout)  
        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('FFmpegify Settings')    
        self.show()        

    # Prevent hitting Enter from pressing OK button
    def keyPressEvent(self, event):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                pass

    def readSettings(self):    
        with open(Path(self.loc).with_name('settings.json'), 'r') as f:
            config = json.load(f)
        return config

    # Connect to OK button
    def writeSettings(self):
        cfg = {}
        cfg['FPS'] = str(self.fps_widget.value())
        cfg['maxFrames'] = str(self.endframe_widget.value())
        cfg['maxWidth'] = str(self.maxw_widget.value())
        cfg['maxHeight'] = str(self.maxh_widget.value())
        cfg['quality'] = str(self.cf_widget.value())
        cfg['preset'] = self.preset_widget.currentText()
        cfg['format'] = self.format_widget.currentText()
        with open(Path(self.loc).with_name('settings.json'), 'w') as f:
            json.dump(cfg, f)
        self.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ffmpegify_loc = sys.argv[0]
    ex = Example(ffmpegify_loc)
    sys.exit(app.exec_())