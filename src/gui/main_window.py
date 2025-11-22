from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, QGroupBox, QComboBox, QSpinBox, QStyle
from PySide6.QtCore import Signal, Slot, QSize
from PySide6.QtGui import QIcon, QFont
from src.utils.localization import i18n
from .overlay_window import OverlayWindow
from .settings_window import SettingsWindow
from src.audio.capture import AudioCapture

class MainWindow(QMainWindow):
    # Signals to control the backend
    sig_start = Signal()
    sig_stop = Signal()
    sig_update_language = Signal(str)
    sig_update_translation_language = Signal(str)
    sig_update_model = Signal(str)
    sig_update_device = Signal(str)  # New signal for device (cpu/cuda)
    sig_update_compute_type = Signal(str)  # New signal for compute type (int8/float16)
    sig_update_audio_device = Signal(object) # Can be int or None
    sig_reset_context = Signal()

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("Livestream Translator Control")
        self.resize(400, 650)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # STT Model Settings Panel (New Section)
        self.grp_stt_settings = QGroupBox(i18n.get("grp_stt_settings"))
        layout_stt_settings = QVBoxLayout()
        
        # Model Selector
        layout_model = QHBoxLayout()
        self.lbl_model = QLabel(i18n.get("lbl_model"))
        self.combo_model = QComboBox()
        
        # Define model structure
        # Format: (Display Name, Model ID)
        # If Model ID is None, it's a category header
        model_structure = [
            ("--- Turbo Model ---", None),
            ("Turbo v3 (High Accuracy)", "deepdml/faster-whisper-large-v3-turbo-ct2"),
            
            ("--- En Only Models ---", None),
            ("Tiny.en", "tiny.en"),
            ("Base.en", "base.en"),
            ("Small.en", "small.en"),
            ("Medium.en", "medium.en"),
            
            ("--- Multilingual Models ---", None),
            ("Tiny", "tiny"),
            ("Base", "base"),
            ("Small", "small"),
            ("Medium", "medium"),
            
            ("--- Large Models ---", None),
            ("Large v1", "large-v1"),
            ("Large v2", "large-v2"),
            ("Large v3", "large-v3"),
            
            ("--- Distill Models ---", None),
            ("Distil Small.en", "distil-small.en"),
            ("Distil Medium.en", "distil-medium.en"),
            ("Distil Large v3", "distil-large-v3"),
        ]

        for display, model_id in model_structure:
            self.combo_model.addItem(display, model_id)
            if model_id is None:
                # Disable the header item
                index = self.combo_model.count() - 1
                self.combo_model.model().item(index).setEnabled(False)
                # Optional: Make it look like a header (e.g. bold) - might need custom delegate or stylesheet, 
                # but simple disable is enough for now as requested "segregate... with title"

        # Select Turbo v3 by default (index 1, since index 0 is header)
        self.combo_model.setCurrentIndex(1)
        self.combo_model.currentIndexChanged.connect(self.on_model_changed)
        
        layout_model.addWidget(self.lbl_model)
        layout_model.addWidget(self.combo_model)
        layout_stt_settings.addLayout(layout_model)

        # Device Selector (CPU/CUDA)
        layout_device = QHBoxLayout()
        self.lbl_device = QLabel(i18n.get("lbl_device"))
        self.combo_device = QComboBox()
        self.combo_device.addItem("CUDA (GPU)", "cuda")
        self.combo_device.addItem("CPU", "cpu")
        self.combo_device.currentIndexChanged.connect(self.on_device_changed)
        
        layout_device.addWidget(self.lbl_device)
        layout_device.addWidget(self.combo_device)
        layout_stt_settings.addLayout(layout_device)

        # Compute Type Selector (int8/fp16)
        layout_compute = QHBoxLayout()
        self.lbl_compute_type = QLabel(i18n.get("lbl_compute_type"))
        self.combo_compute_type = QComboBox()
        self.combo_compute_type.addItem("float16 (Higher Quality)", "float16")
        self.combo_compute_type.addItem("int8 (Faster)", "int8")
        self.combo_compute_type.currentIndexChanged.connect(self.on_compute_type_changed)
        
        layout_compute.addWidget(self.lbl_compute_type)
        layout_compute.addWidget(self.combo_compute_type)
        layout_stt_settings.addLayout(layout_compute)
        
        self.grp_stt_settings.setLayout(layout_stt_settings)
        main_layout.addWidget(self.grp_stt_settings)

        # Control Panel
        self.grp_control = QGroupBox(i18n.get("grp_control"))
        layout_control = QVBoxLayout()

        # Audio Device Selector
        layout_audio = QHBoxLayout()
        self.lbl_audio = QLabel(i18n.get("lbl_audio_input"))
        self.combo_audio = QComboBox()
        self.btn_refresh_audio = QPushButton("R") # Refresh button
        self.btn_refresh_audio.setToolTip(i18n.get("btn_refresh_tooltip"))
        self.btn_refresh_audio.setFixedWidth(30)
        self.btn_refresh_audio.clicked.connect(self.refresh_audio_devices)
        
        self.combo_audio.currentIndexChanged.connect(self.on_audio_device_changed)
        
        layout_audio.addWidget(self.lbl_audio)
        layout_audio.addWidget(self.combo_audio)
        layout_audio.addWidget(self.btn_refresh_audio)
        layout_control.addLayout(layout_audio)
        
        # Language Selector
        layout_lang = QHBoxLayout()
        self.lbl_lang = QLabel(i18n.get("lbl_stt_lang"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Auto Detect", "auto")
        self.combo_lang.addItem("English", "en")
        self.combo_lang.addItem("Japanese", "ja")
        self.combo_lang.addItem("Chinese", "zh")
        self.combo_lang.addItem("Korean", "ko")
        self.combo_lang.addItem("Spanish", "es")
        self.combo_lang.addItem("French", "fr")
        self.combo_lang.addItem("German", "de")
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        
        layout_lang.addWidget(self.lbl_lang)
        layout_lang.addWidget(self.combo_lang)
        layout_control.addLayout(layout_lang)

        # Target Translation Language Selector
        layout_trans_lang = QHBoxLayout()
        self.lbl_trans_lang = QLabel(i18n.get("lbl_target_lang"))
        self.combo_trans_lang = QComboBox()
        self.combo_trans_lang.setEditable(True)
        self.combo_trans_lang.addItem("Traditional Chinese")
        self.combo_trans_lang.addItem("English")
        self.combo_trans_lang.addItem("Japanese")
        self.combo_trans_lang.addItem("Korean")
        self.combo_trans_lang.addItem("Spanish")
        self.combo_trans_lang.addItem("Simplified Chinese")
        self.combo_trans_lang.currentTextChanged.connect(self.on_translation_language_changed)
        
        layout_trans_lang.addWidget(self.lbl_trans_lang)
        layout_trans_lang.addWidget(self.combo_trans_lang)
        layout_control.addLayout(layout_trans_lang)

        # Buttons
        layout_btns = QHBoxLayout()
        
        self.btn_start_stop = QPushButton(i18n.get("btn_start"))
        self.btn_start_stop.setCheckable(True)
        self.btn_start_stop.setMinimumHeight(40)
        self.btn_start_stop.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_start_stop.clicked.connect(self.on_start_stop_clicked)
        layout_btns.addWidget(self.btn_start_stop)
        
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFont(QFont("Segoe UI Emoji", 18)) # Use emoji font for better rendering
        self.btn_settings.setToolTip(i18n.get("btn_settings_tooltip"))
        self.btn_settings.setFixedSize(40, 40)
        self.btn_settings.clicked.connect(self.on_settings_clicked)
        layout_btns.addWidget(self.btn_settings)
        
        layout_control.addLayout(layout_btns)
        
        # Context Control
        layout_context_btns = QHBoxLayout()
        self.btn_reset_context = QPushButton(i18n.get("btn_reset_context"))
        self.btn_reset_context.setToolTip(i18n.get("btn_reset_context_tooltip"))
        self.btn_reset_context.clicked.connect(self.on_reset_context_clicked)
        
        self.btn_hide_context = QPushButton(i18n.get("btn_hide_context"))
        self.btn_hide_context.setCheckable(True)
        self.btn_hide_context.setChecked(True) # Default Show
        self.btn_hide_context.clicked.connect(self.toggle_context)
        
        layout_context_btns.addWidget(self.btn_reset_context)
        layout_context_btns.addWidget(self.btn_hide_context)
        layout_control.addLayout(layout_context_btns)
        
        self.grp_control.setLayout(layout_control)
        main_layout.addWidget(self.grp_control)

        # Overlay Control
        self.grp_overlay = QGroupBox(i18n.get("grp_overlay"))
        layout_overlay = QHBoxLayout()
        
        self.btn_toggle_overlay = QPushButton(i18n.get("btn_toggle_overlay"))
        self.btn_toggle_overlay.setCheckable(True)
        self.btn_toggle_overlay.setChecked(True)
        self.btn_toggle_overlay.clicked.connect(self.toggle_overlay)
        
        layout_overlay.addWidget(self.btn_toggle_overlay)
        
        # Font Size Control
        self.lbl_size = QLabel(i18n.get("lbl_font_size"))
        self.combo_size = QComboBox()
        self.combo_size.addItem("Small", 18)
        self.combo_size.addItem("Medium", 24)
        self.combo_size.addItem("Large", 36)
        self.combo_size.addItem("Extra Large", 48)
        self.combo_size.setCurrentIndex(1) # Default Medium
        self.combo_size.currentIndexChanged.connect(self.on_font_size_changed)
        
        layout_overlay.addWidget(self.lbl_size)
        layout_overlay.addWidget(self.combo_size)
        
        # History Lines Control
        self.lbl_hist = QLabel(i18n.get("lbl_history_lines"))
        self.spin_hist = QSpinBox()
        self.spin_hist.setRange(0, 5)
        self.spin_hist.setValue(3) # Default 3
        self.spin_hist.valueChanged.connect(self.on_history_lines_changed)
        
        layout_overlay.addWidget(self.lbl_hist)
        layout_overlay.addWidget(self.spin_hist)
        
        self.grp_overlay.setLayout(layout_overlay)
        main_layout.addWidget(self.grp_overlay)

        # Logs
        self.grp_logs = QGroupBox(i18n.get("grp_logs"))
        layout_logs = QVBoxLayout()
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout_logs.addWidget(self.txt_log)
        self.grp_logs.setLayout(layout_logs)
        main_layout.addWidget(self.grp_logs)

        # Initialize Overlay
        self.overlay = OverlayWindow()
        self.overlay.show()

        # Connect Bridge Signals
        self.bridge.sig_log.connect(self.append_log)
        self.bridge.sig_stt_partial.connect(self.overlay.update_partial)
        self.bridge.sig_stt_final.connect(self.overlay.on_final_sentence)
        self.bridge.sig_translation.connect(self.overlay.update_translation)
        self.bridge.sig_context.connect(self.overlay.update_context)

        # Load initial overlay settings
        self.load_overlay_settings()

        # Initial population of audio devices
        self.refresh_audio_devices()

        # Initialize device and compute type from config (will be set by main_gui)
        # Default to CUDA and float16
        self.combo_device.setCurrentIndex(0)  # CUDA by default
        self.combo_compute_type.setCurrentIndex(0)  # float16 by default

    def load_overlay_settings(self):
        import os
        config_path = "User_config.txt"
        opacity = 40 # Default
        target_lang = None
        gui_lang = "en"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("OVERLAY_OPACITY="):
                            try:
                                opacity = int(line.split("=")[1].strip())
                            except ValueError:
                                pass
                        elif line.startswith("TARGET_TRANSLATION_LANGUAGE="):
                             target_lang = line.split("=")[1].strip()
                        elif line.startswith("GUI_LANGUAGE="):
                             gui_lang = line.split("=")[1].strip()
            except Exception:
                pass
        
        self.overlay.set_background_opacity(opacity)
        
        # Set GUI language
        i18n.set_language(gui_lang)
        self.update_ui_text()
        
        if target_lang:
             self.sig_update_translation_language.emit(target_lang)
             self.combo_trans_lang.setCurrentText(target_lang)
             self.append_log("INFO", f"Translation Language set to: {target_lang}")

    def refresh_audio_devices(self):
        self.combo_audio.blockSignals(True)
        self.combo_audio.clear()
        
        # Add Default option
        self.combo_audio.addItem("Default System Output (Loopback)", None)
        
        try:
            devices = AudioCapture.list_audio_devices()
            for dev in devices:
                name = dev["name"]
                if dev["is_loopback"]:
                    name = f"[Loopback] {name}"
                self.combo_audio.addItem(name, dev["index"])
        except Exception as e:
            self.append_log("ERROR", f"Failed to list audio devices: {e}")
            
        self.combo_audio.blockSignals(False)

    def on_audio_device_changed(self, index):
        device_index = self.combo_audio.currentData()
        device_name = self.combo_audio.currentText()
        self.append_log("INFO", f"Selected Audio Device: {device_name}")
        self.sig_update_audio_device.emit(device_index)

    def on_language_changed(self, index):
        lang_code = self.combo_lang.currentData()
        self.append_log("INFO", f"STT Language changed to: {lang_code}")
        self.sig_update_language.emit(lang_code)

    def on_translation_language_changed(self, text):
        self.append_log("INFO", f"Target Translation Language changed to: {text}")
        self.sig_update_translation_language.emit(text)

    def on_model_changed(self, index):
        model_name = self.combo_model.currentData()
        self.append_log("INFO", f"Switching model to: {model_name} (may take a few seconds)")
        self.sig_update_model.emit(model_name)

    def on_device_changed(self, index):
        device = self.combo_device.currentData()
        self.append_log("INFO", f"Switching device to: {device}")
        
        # Lock compute type to int8 if CPU is selected
        if device == "cpu":
            # Find index for int8
            index_int8 = self.combo_compute_type.findData("int8")
            if index_int8 != -1:
                self.combo_compute_type.setCurrentIndex(index_int8)
            self.combo_compute_type.setEnabled(False)
            self.append_log("INFO", "Compute type locked to int8 for CPU")
        else:
            self.combo_compute_type.setEnabled(True)
            
        self.sig_update_device.emit(device)

    def on_compute_type_changed(self, index):
        compute_type = self.combo_compute_type.currentData()
        self.append_log("INFO", f"Switching compute type to: {compute_type}")
        self.sig_update_compute_type.emit(compute_type)

    def on_font_size_changed(self, index):
        size = self.combo_size.currentData()
        if size:
            self.overlay.set_font_size(size)

    def on_history_lines_changed(self, value):
        self.overlay.set_history_lines(value)

    def on_start_stop_clicked(self, checked):
        if checked:
            # Start
            self.btn_start_stop.setText(i18n.get("btn_stop"))
            # Disable STT settings during run
            self.combo_model.setEnabled(False)
            self.combo_device.setEnabled(False)
            self.combo_compute_type.setEnabled(False)
            self.append_log("INFO", "Starting services...")
            self.sig_start.emit()
        else:
            # Stop
            self.btn_start_stop.setText(i18n.get("btn_start"))
            # Enable STT settings when stopped
            self.combo_model.setEnabled(True)
            self.combo_device.setEnabled(True)
            self.combo_compute_type.setEnabled(True)
            self.append_log("INFO", "Stopping services...")
            self.sig_stop.emit()

    def on_settings_clicked(self):
        settings = SettingsWindow(parent=self)
        if settings.exec():
            self.append_log("INFO", "Settings saved. Restart application for full effect.")
            self.load_overlay_settings()
            # Reload GUI texts might be needed, but restart is suggested in log
            self.update_ui_text()

    def update_ui_text(self):
        self.setWindowTitle(i18n.get("window_title"))
        self.grp_stt_settings.setTitle(i18n.get("grp_stt_settings"))
        self.lbl_model.setText(i18n.get("lbl_model"))
        self.lbl_device.setText(i18n.get("lbl_device"))
        self.lbl_compute_type.setText(i18n.get("lbl_compute_type"))
        self.grp_control.setTitle(i18n.get("grp_control"))
        self.lbl_audio.setText(i18n.get("lbl_audio_input"))
        self.btn_refresh_audio.setToolTip(i18n.get("btn_refresh_tooltip"))
        self.lbl_lang.setText(i18n.get("lbl_stt_lang"))
        self.lbl_trans_lang.setText(i18n.get("lbl_target_lang"))
        self.btn_start_stop.setText(i18n.get("btn_stop") if self.btn_start_stop.isChecked() else i18n.get("btn_start"))
        self.btn_settings.setToolTip(i18n.get("btn_settings_tooltip"))
        self.btn_reset_context.setText(i18n.get("btn_reset_context"))
        self.btn_reset_context.setToolTip(i18n.get("btn_reset_context_tooltip"))
        self.btn_hide_context.setText(i18n.get("btn_hide_context"))
        self.grp_overlay.setTitle(i18n.get("grp_overlay"))
        self.btn_toggle_overlay.setText(i18n.get("btn_toggle_overlay"))
        self.lbl_size.setText(i18n.get("lbl_font_size"))
        self.lbl_hist.setText(i18n.get("lbl_history_lines"))
        self.grp_logs.setTitle(i18n.get("grp_logs"))

    def on_reset_context_clicked(self):
        self.sig_reset_context.emit()
        self.append_log("INFO", "Scenario Context has been reset.")

    def toggle_context(self, checked):
        self.overlay.set_context_visibility(checked)
        state = "Shown" if checked else "Hidden"
        self.append_log("INFO", f"Context Overlay {state}")

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

