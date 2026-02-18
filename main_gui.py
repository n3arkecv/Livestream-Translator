import sys
import os
import asyncio
import logging
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.event_bus import EventBus
from src.utils.logger import SystemLogger
from src.audio.capture import AudioCapture
from src.transcription.stt_manager import STTManager
from src.translation.manager import TranslationManager
from src.gui.main_window import MainWindow
from src.gui.qt_event_bridge import QtEventBridge

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BackendWorker(QThread):
    def __init__(self, bus, config, logger):
        super().__init__()
        self.bus = bus
        self.config = config
        self.logger = logger
        self.loop = None
        self.capture = None
        self.stt_manager = None
        self.translation_manager = None
        self._ready_event = threading.Event()

    def run(self):
        self.logger.info("BackendWorker thread started")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize components inside the thread to be safe
        self.capture = AudioCapture(self.bus, self.config, self.logger)
        self.stt_manager = STTManager(self.bus, self.config, self.logger)
        self.translation_manager = TranslationManager(self.bus, self.config)
        
        self._ready_event.set()
        
        try:
            self.loop.run_forever()
        except Exception as e:
            self.logger.error(f"Backend loop error: {e}")
        finally:
            self.loop.close()
            self.logger.info("BackendWorker thread stopped")

    def wait_until_ready(self):
        self._ready_event.wait()

    def start_services(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self._start_services_async)

    def stop_services(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self._stop_services_async)

    def set_language(self, lang_code):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self.stt_manager.set_language(lang_code))
            
    def set_translation_language(self, lang_name):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self.translation_manager.set_target_language(lang_name))
            
    def reset_context(self):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self.translation_manager.reset_context())
    
    def set_model(self, model_id):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self._update_model_async(model_id))

    def set_audio_device(self, device_index):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self._update_audio_device_async(device_index))

    def set_device(self, device):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self._update_device_async(device))

    def set_compute_type(self, compute_type):
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: self._update_compute_type_async(compute_type))

    def _update_device_async(self, device):
        self.logger.info(f"Updating STT device to: {device}")
        if "stt" not in self.config:
            self.config["stt"] = {}
        self.config["stt"]["device"] = device
        
        # Reload the STT engine with new device
        if self.stt_manager:
            self.stt_manager.reload_engine()

    def _update_compute_type_async(self, compute_type):
        self.logger.info(f"Updating STT compute type to: {compute_type}")
        if "stt" not in self.config:
            self.config["stt"] = {}
        self.config["stt"]["compute_type"] = compute_type
        
        # Reload the STT engine with new compute type
        if self.stt_manager:
            self.stt_manager.reload_engine()

    def _update_model_async(self, model_id):
        self.logger.info(f"Updating STT model to: {model_id}")
        
        if "stt" not in self.config:
            self.config["stt"] = {}
            
        mode = "local"
        actual_model = model_id
        
        if model_id.startswith("api:"):
            mode = "api"
            parts = model_id.split(":")
            if len(parts) >= 3:
                # format: api:provider:model
                provider = parts[1]
                actual_model = parts[2]
                if "api" not in self.config["stt"]:
                    self.config["stt"]["api"] = {}
                self.config["stt"]["api"]["provider"] = provider
                self.config["stt"]["api"]["model"] = actual_model
        
        old_mode = self.config["stt"].get("mode", "local")
        self.config["stt"]["mode"] = mode
        self.config["stt"]["model"] = actual_model
        
        if self.stt_manager:
            self.stt_manager.mode = mode
            if mode != old_mode:
                self.logger.info(f"STT Mode changed from {old_mode} to {mode}. Reloading engine...")
                self.stt_manager.reload_engine()
            else:
                # Just reload model if same mode
                self.stt_manager.set_model(actual_model)

    def _update_audio_device_async(self, device_index):
        self.logger.info(f"Updating audio device to index: {device_index}")
        if "audio" not in self.config:
            self.config["audio"] = {}
        self.config["audio"]["device_index"] = device_index
        
        # If capture is initialized and running, restart it
        if self.capture and self.capture.stream and self.capture.stream.is_active():
             self.logger.info("Restarting audio capture with new device...")
             self.capture.stop()
             # Give it a moment to fully close if needed, though stop() is synchronous usually
             self.capture.start()

    def stop_thread(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.quit()
        self.wait()

    def _start_services_async(self):
        self.logger.info("Starting STT and Audio Capture...")
        self.stt_manager.start_processing()
        self.capture.start()

    def _stop_services_async(self):
        self.logger.info("Stopping STT and Audio Capture...")
        self.capture.stop()
        self.stt_manager.stop_processing()
        if self.translation_manager:
            self.translation_manager.stop()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Livestream Translator")

    # 1. Shared Components
    logger = SystemLogger("GUI_App")
    bus = EventBus()
    bridge = QtEventBridge(bus)
    
    # 2. Configuration (from smoke test)
    config = {
        "audio": {
            "output_device": "default",
            "use_loopback": True
        },
        "chunk": {
            "size_ms": 250,
            "overlap_ms": 50
        },
        "stt": {
            "mode": "local",
            "model": "deepdml/faster-whisper-large-v3-turbo-ct2",
            "device": "cuda",
            "compute_type": "float16"
        }
    }

    # Load User_config.txt
    config_path = os.path.join(os.path.dirname(__file__), "User_config.txt")
    if os.path.exists(config_path):
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    os.environ[key] = value # Set as env var for other components
                    
                    # Update config dict if applicable
                    if key == "LLM_TRANSLATION_MODEL":
                        # This might be used by translation manager, which reads from config or env?
                        # TranslationManager uses config passed to it.
                        config["llm_translation_model"] = value
                    elif key == "LLM_SUMMARY_MODEL":
                        config["llm_summary_model"] = value
                    elif key == "USE_ORIGINAL_TEXT_FOR_CONTEXT":
                        config["use_original_text_for_context"] = (value.lower() == "true")
                    elif key == "TARGET_TRANSLATION_LANGUAGE":
                        config["target_translation_language"] = value
                    elif key == "STT_MODEL":
                        config["stt"]["model"] = value
                        if value.startswith("api:"):
                            config["stt"]["mode"] = "api"
                            parts = value.split(":")
                            if len(parts) >= 3:
                                if "api" not in config["stt"]:
                                    config["stt"]["api"] = {}
                                config["stt"]["api"]["provider"] = parts[1]
                                config["stt"]["api"]["model"] = parts[2]
                        else:
                            config["stt"]["mode"] = "local"
                    elif key == "STT_DEVICE":
                        config["stt"]["device"] = value
                    elif key == "STT_COMPUTE_TYPE":
                        config["stt"]["compute_type"] = value
                    elif key == "STT_LANGUAGE":
                        config["stt_language"] = value
                    elif key == "AUDIO_DEVICE_INDEX":
                        try:
                            config["audio"]["device_index"] = int(value)
                        except ValueError:
                            pass
                    elif key == "OVERLAY_FONT_SIZE":
                        try:
                            config["overlay_font_size"] = int(value)
                        except ValueError:
                            pass
                    elif key == "OVERLAY_HISTORY_LINES":
                        try:
                            config["overlay_history_lines"] = int(value)
                        except ValueError:
                            pass

    # 3. Backend Worker
    worker = BackendWorker(bus, config, logger)
    worker.start()
    worker.wait_until_ready() # Wait for loop to initialize

    # 4. GUI
    window = MainWindow(bridge)
    
    # Connect Window signals to Backend
    window.sig_start.connect(worker.start_services)
    window.sig_stop.connect(worker.stop_services)
    window.sig_update_language.connect(worker.set_language)
    window.sig_update_translation_language.connect(worker.set_translation_language)
    window.sig_update_model.connect(worker.set_model)
    window.sig_update_device.connect(worker.set_device)
    window.sig_update_compute_type.connect(worker.set_compute_type)
    window.sig_update_audio_device.connect(worker.set_audio_device)
    window.sig_reset_context.connect(worker.reset_context)
    
    window.show()

    logger.info("Application started")
    
    exit_code = app.exec()
    
    # Cleanup
    logger.info("Shutting down...")
    worker.stop_services()
    worker.stop_thread()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

