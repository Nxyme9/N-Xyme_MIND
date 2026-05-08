#!/usr/bin/env python3
import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'wayland'
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import urllib.request
import json

API = "http://127.0.0.1:8765"

class Hotspot(QWidget):
    def __init__(self):
        super().__init__()
        self._last = ""
        self._poll = QTimer()
        self._poll.timeout.connect(self._update)
        self._poll.start(300)
        self._build()
        
    def _build(self):
        self.setWindowTitle("NXyme Dictate")
        self.setFixedSize(280, 130)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        g = self.screen().geometry()
        self.move(g.width() - self.width() - 20, 50)
        
        self.setStyleSheet("""
            QWidget { background-color: rgba(30,30,40,240); border-radius:12px; border:2px solid #6c5ce7; color:#fff; }
            QPushButton { background-color: #6c5ce7; border-radius:8px; color:#fff; font-weight:bold; }
            QPushButton:hover { background-color: #8b7cf7; }
        """)
        
        l = QVBoxLayout(self)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(8)
        
        self._status = QLabel("Click to Record")
        self._status.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self._status)
        
        self._result = QLabel("")
        self._result.setWordWrap(True)
        self._result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self._result)
        
        b = QHBoxLayout()
        self._start = QPushButton("Start")
        self._start.setFixedHeight(40)
        self._start.clicked.connect(lambda: self._call("/start"))
        b.addWidget(self._start)
        
        self._stop = QPushButton("Stop")
        self._stop.setFixedHeight(40)
        self._stop.clicked.connect(lambda: self._call("/stop"))
        b.addWidget(self._stop)
        l.addLayout(b)
        
    def _call(self, path):
        try: urllib.request.urlopen(f"{API}{path}", data=b"{}", timeout=2)
        except: pass
    
    def _update(self):
        try:
            d = json.loads(urllib.request.urlopen(f"{API}/status", timeout=0.5).read())
            s = d.get("state", "")
            self._status.setText("RECORDING" if s == "recording" else "Processing..." if s == "processing" else "Click to Record")
            self._start.setEnabled(s != "recording")
            self._stop.setEnabled(s == "recording")
            r = d.get("last_result", {})
            t = r.get("processed") or r.get("text", "")
            if t != self._last:
                self._last = t
                self._result.setText(t)
        except: pass
    
    def show(self):
        super().show()
        self.raise_()
        self.activateWindow()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Hotspot()
    w.show()
    sys.exit(app.exec())