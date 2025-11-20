from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, QGroupBox
from PySide6.QtCore import Signal, Slot
from .overlay_window import OverlayWindow

class MainWindow(QMainWindow):
    # Signals to control the backend
    sig_start = Signal()
    sig_stop = Signal()

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("Livestream Translator Control")
        self.resize(400, 500)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Control Panel
        grp_control = QGroupBox("Control")
        layout_control = QHBoxLayout()
        
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.on_start_clicked)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        self.btn_stop.setEnabled(False)

        layout_control.addWidget(self.btn_start)
        layout_control.addWidget(self.btn_stop)
        grp_control.setLayout(layout_control)
        main_layout.addWidget(grp_control)

        # Overlay Control
        grp_overlay = QGroupBox("Overlay")
        layout_overlay = QHBoxLayout()
        
        self.btn_toggle_overlay = QPushButton("Show/Hide Overlay")
        self.btn_toggle_overlay.setCheckable(True)
        self.btn_toggle_overlay.setChecked(True)
        self.btn_toggle_overlay.clicked.connect(self.toggle_overlay)
        
        layout_overlay.addWidget(self.btn_toggle_overlay)
        grp_overlay.setLayout(layout_overlay)
        main_layout.addWidget(grp_overlay)

        # Logs
        grp_logs = QGroupBox("System Log")
        layout_logs = QVBoxLayout()
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout_logs.addWidget(self.txt_log)
        grp_logs.setLayout(layout_logs)
        main_layout.addWidget(grp_logs)

        # Initialize Overlay
        self.overlay = OverlayWindow()
        self.overlay.show()

        # Connect Bridge Signals
        self.bridge.sig_log.connect(self.append_log)
        self.bridge.sig_stt_partial.connect(self.overlay.update_partial)

    def on_start_clicked(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.append_log("INFO", "Starting services...")
        self.sig_start.emit()

    def on_stop_clicked(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.append_log("INFO", "Stopping services...")
        self.sig_stop.emit()

    def toggle_overlay(self, checked):
        if checked:
            self.overlay.show()
        else:
            self.overlay.hide()

    @Slot(str, str)
    def append_log(self, level, message):
        # Simple color coding could be added here
        self.txt_log.appendPlainText(f"[{level}] {message}")

    def closeEvent(self, event):
        self.overlay.close()
        self.sig_stop.emit()
        super().closeEvent(event)

