import threading
import time
import wave
import numpy as np
import pyaudiowpatch as pyaudio
from typing import Optional, Dict, Any
from src.utils.event_bus import EventBus
from src.utils.logger import SystemLogger
from src.audio.chunk_processor import ChunkProcessor

class AudioFormatConverter:
    """Converts audio to mono, 44100Hz, float32."""
    
    def convert(self, raw_bytes: bytes, source_rate: int, source_channels: int) -> np.ndarray:
        # 1. Bytes -> Int16 numpy array
        # pyaudiowpatch loopback usually gives Int16 or Float32 depending on setup, 
        # but here we assume Int16 based on the stream open format paInt16.
        audio_data = np.frombuffer(raw_bytes, dtype=np.int16)
        
        # 2. Reshape to (samples, channels)
        if source_channels > 1:
            audio_data = audio_data.reshape(-1, source_channels)
            # Mix to mono - CRITICAL for consistency
            audio_data = audio_data.mean(axis=1)
        
        # 3. Convert to float32 [-1.0, 1.0]
        # Note: PyAudio Int16 is [-32768, 32767].
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        
        # IMPORTANT: Check if the audio needs normalization or gain boost
        # Sometimes loopback volume is very low.
        # rms = np.sqrt(np.mean(audio_float32**2))
        # if rms > 0 and rms < 0.1:
        #    audio_float32 = audio_float32 * (0.1 / rms) # Normalize to target RMS
        
        # 4. Resample if needed (Linear interpolation for simplicity)
        if source_rate != 44100:
            audio_float32 = self._resample(audio_float32, source_rate, 44100)
            
        return audio_float32

    def _resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        # Use librosa for high quality resampling in capture as well if available
        try:
            import librosa
            return librosa.resample(audio, orig_sr=source_rate, target_sr=target_rate)
        except ImportError:
            duration_s = len(audio) / source_rate
            target_length = int(duration_s * target_rate)
            return np.interp(
                np.linspace(0, len(audio), target_length, endpoint=False),
                np.arange(len(audio)),
                audio
            )

class AudioCapture:
    def __init__(self, bus: EventBus, config: Dict[str, Any], logger: SystemLogger, save_wav_path: Optional[str] = None):
        self.bus = bus
        self.config = config
        self.logger = logger
        self.save_wav_path = save_wav_path
        
        self.output_device_name = config.get("audio", {}).get("output_device", "default")
        self.use_loopback = config.get("audio", {}).get("use_loopback", True)
        self.chunk_ms = config.get("chunk", {}).get("size_ms", 640)
        self.overlap_ms = config.get("chunk", {}).get("overlap_ms", 160)
        
        self.chunk_processor = ChunkProcessor(bus, 44100, self.chunk_ms, self.overlap_ms)
        self.format_converter = AudioFormatConverter()
        
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        self._wav_file = None

    @staticmethod
    def list_audio_devices() -> list[dict]:
        """Lists available audio input devices (including loopback)."""
        devices = []
        try:
            p = pyaudio.PyAudio()
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                host_api_index = wasapi_info["index"]
            except OSError:
                # Fallback or error if WASAPI not found
                p.terminate()
                return []

            for i in range(p.get_device_count()):
                try:
                    dev = p.get_device_info_by_index(i)
                    if dev["hostApi"] == host_api_index and dev["maxInputChannels"] > 0:
                        devices.append({
                            "index": i,
                            "name": dev["name"],
                            "is_loopback": dev.get("isLoopbackDevice", False)
                        })
                except Exception:
                    pass
            p.terminate()
        except Exception as e:
            SystemLogger("AudioCapture").error(f"Error listing devices: {e}")
        return devices

    def start(self):
        """Starts the audio capture stream."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            wasapi_info = self.pyaudio_instance.get_host_api_info_by_type(pyaudio.paWASAPI)
            
            target_device = None
            device_index = self.config.get("audio", {}).get("device_index")
            
            if device_index is not None:
                try:
                    target_device = self.pyaudio_instance.get_device_info_by_index(device_index)
                    self.logger.info(f"Using configured device: {target_device['name']} (Index: {device_index})")
                except Exception as e:
                    self.logger.error(f"Failed to find configured device index {device_index}, falling back to default.", exc=e)
            
            if target_device is None:
                # Fallback: Default behavior (Find default loopback)
                default_speakers = self.pyaudio_instance.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                
                if not default_speakers["isLoopbackDevice"]:
                    found_loopback = False
                    for loopback in self.pyaudio_instance.get_loopback_device_info_generator():
                        if default_speakers["name"] in loopback["name"]:
                            default_speakers = loopback
                            found_loopback = True
                            break
                    if not found_loopback:
                        self.logger.warning("Could not find specific loopback device, trying default loopback...")
                
                target_device = default_speakers
                self.logger.info(f"Selected Default Device: {target_device['name']}")
            
            native_rate = int(target_device["defaultSampleRate"])
            native_channels = int(target_device["maxInputChannels"])
            
            self.logger.info(f"Opening stream: Rate={native_rate}, Channels={native_channels}, DeviceIdx={target_device['index']}")

            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=native_channels,
                rate=native_rate,
                frames_per_buffer=4096,
                input=True,
                input_device_index=target_device["index"]
            )
            
            self.bus.emit("audio.stream_opened", {
                "device_name": target_device["name"],
                "sample_rate": native_rate,
                "channels": native_channels
            })
            
            if self.save_wav_path:
                self._init_wav_file(native_rate, native_channels)

            self.stop_event.clear()
            self.capture_thread = threading.Thread(
                target=self._capture_loop, 
                args=(native_rate, native_channels),
                daemon=True
            )
            self.capture_thread.start()
            
        except Exception as e:
            self.logger.error("Failed to open WASAPI device", exc=e)
            raise

    def _find_output_device(self, wasapi_info):
        if self.output_device_name == "default":
            return wasapi_info["defaultOutputDevice"]
        
        count = self.pyaudio_instance.get_device_count()
        for i in range(count):
            info = self.pyaudio_instance.get_device_info_by_index(i)
            if info["hostApi"] == wasapi_info["index"]:
                if self.output_device_name.lower() in info["name"].lower():
                    return i
        
        raise ValueError(f"Device '{self.output_device_name}' not found")

    def _init_wav_file(self, rate, channels):
        try:
            self._wav_file = wave.open(self.save_wav_path, 'wb')
            self._wav_file.setnchannels(channels)
            self._wav_file.setsampwidth(2) # 2 bytes for Int16
            self._wav_file.setframerate(rate)
            self.logger.info(f"Recording to {self.save_wav_path}")
        except Exception as e:
            self.logger.error("Failed to initialize WAV file", exc=e)

    def _capture_loop(self, source_rate, source_channels):
        while not self.stop_event.is_set():
            try:
                # Read raw bytes
                data = self.stream.read(4096, exception_on_overflow=False)
                
                # Write to WAV if enabled
                if self._wav_file:
                    self._wav_file.writeframes(data)
                
                # Convert and Process
                audio_float32 = self.format_converter.convert(data, source_rate, source_channels)
                self.chunk_processor.push(audio_float32)
                
            except Exception as e:
                self.logger.error("Capture loop error", exc=e)
                break

    def stop(self):
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join()
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            
        if self._wav_file:
            self._wav_file.close()
            
        self.bus.emit("audio.stream_closed", {})

