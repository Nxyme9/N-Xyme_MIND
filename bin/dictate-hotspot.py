#!/usr/bin/env python3
import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import urllib.request
import json

API_URL = "http://127.0.0.1:8765"

class DictateHotspot(QWidget):
    def __init__(self):
        super().__init__()
        self._recording = False
        self._last = ""
        self.setup_ui()
        self._poll = QTimer()
        self._poll.timeout.connect(self.update_status)
        self._poll.start(300)
        
    def setup_ui(self):
        self.setWindowTitle("NXyme Dictate")
        self.setFixedSize(280, 130)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        geom = self.screen().geometry()
        self.move(geom.width() - self.width() - 20, 50)
        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 40, 240);
                border-radius: 12px;
                border: 2px solid #6c5ce7;
                color: #fff;
            }
            QPushButton {
                background-color: #6c5ce7;
                border-radius: 8px;
                color: #fff;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #8b7cf7; }
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        
        self.status = QLabel("Click to Record")
        self.status.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.status)
        
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.result)
        
        btns = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self.start_rec)
        btns.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.clicked.connect(self.stop_rec)
        btns.addWidget(self.stop_btn)
        lay.addLayout(btns)
        
    def start_rec(self):
        try:
            urllib.request.urlopen(f"{API_URL}/start", 
                data=json.dumps({"device":1}).encode(), timeout=2)
            self._recording = True
        except Exception as e:
            print(f"Start: {e}")
    
    def stop_rec(self):
        try:
            urllib.request.urlopen(f"{API_URL}/stop", timeout=2)
            self._recording = False
        except Exception as e:
            print(f"Stop: {e}")
    
    def update_status(self):
        try:
            req = urllib.request.urlopen(f"{API_URL}/status", timeout=0.5)
            data = json.loads(req.read().decode())
            state = data.get("state", "unknown")
            
            if state == "recording":
                self.status.setText("RECORDING")
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
            elif state == "processing":
                self.status.setText("Processing...")
            else:
                self.status.setText("Click to Record")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
            
            result = data.get("last_result")
            if result:
                txt = result.get("processed") or result.get("text", "")
                if txt != self._last:
                    self._last = txt
                    self.result.setText(txt)
        except:
            pass

def main():
    app = QApplication(sys.argv)
    win = DictateHotspot()
    win.show()
    win.raise_()
    app.exec()

if __name__ == "__main__":
    main()