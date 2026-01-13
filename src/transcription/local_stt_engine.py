import os
import logging
import numpy as np
from .stt_manager import STTEngine

class LocalSTTEngine(STTEngine):
    def __init__(self, model_name="small.en", device="cuda", compute_type="float16", logger=None):
        self.logger = logger or logging.getLogger("LocalSTT")
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.target_language = None
        
        self._load_model()

    def set_language(self, lang_code):
        """Sets the target language for transcription (e.g. 'en', 'ja', 'zh'). None for auto-detect."""
        self.target_language = lang_code if lang_code != "auto" else None
        self.logger.info(f"Target language set to: {self.target_language}")
        
    def is_auto_detect(self):
        return self.target_language is None

    def reload_model(self, model_name):
        """Reloads the model with a new model name."""
        if model_name == self.model_name:
            return
        
        self.logger.info(f"Reloading model to: {model_name}")
        # Unload current model (if possible) to free VRAM
        self.model = None
        import gc
        gc.collect()
        
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
            self.logger.info(f"Loading FasterWhisper model: {self.model_name} on {self.device} ({self.compute_type})")
            self.model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
            self.logger.info("Model loaded successfully.")
        except ImportError:
            self.logger.error("faster_whisper not installed. Please install it with 'pip install faster-whisper'")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            # Fallback to CPU if CUDA fails?
            if self.device == "cuda":
                self.logger.warning("Falling back to CPU int8")
                self.device = "cpu"
                self.compute_type = "int8"
                try:
                    self.model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
                except Exception as e2:
                    self.logger.error(f"Fallback failed: {e2}")

    async def transcribe(self, audio_chunk: np.ndarray, sample_rate: int) -> str:
        """
        Transcribe audio chunk using FasterWhisper.
        Note: FasterWhisper expects float32 array, which we already have.
        It also handles resampling internally if needed, but typically expects 16kHz.
        However, passing 'sample_rate' argument to transcribe() is not standard in WhisperModel.transcribe().
        WhisperModel.transcribe() usually expects audio at 16k. 
        If our input is 44.1k, we SHOULD resample it to 16k before passing to model, 
        OR rely on faster-whisper's internal resampling if it supports it (it accepts ndarray).
        
        Actually, faster-whisper/CTranslate2 expects 16kHz audio. 
        We should resample if input is 44100.
        """
        if not self.model:
            return ""

        # Resample if needed (Naive check, ideally we assume input is standard 44100 from capture)
        # FasterWhisper expects 16000 Hz
        if sample_rate != 16000:
            audio_chunk = self._resample(audio_chunk, sample_rate, 16000)
            
        # IMPORTANT: Whisper expects float32 in range [-1, 1], which we have.
        # BUT, faster-whisper documentation sometimes implies it might need normalization or specific scaling.
        # Let's ensure it's not too quiet or clipped.
        # Some issues suggest Whisper is sensitive to amplitude. 
        # Let's try to normalize the chunk to -1..1 range if max amp is too low, or just leave it.
        # Actually, standard whisper preprocessing does not strictly require normalization, but it helps.
        
        # Run inference in a thread pool to avoid blocking the async loop
        import asyncio
        loop = asyncio.get_running_loop()
        
        try:
            # Relax VAD settings slightly to catch more speech
            segments, info = await loop.run_in_executor(
                None, 
                lambda: list(self.model.transcribe(
                    audio_chunk, 
                    beam_size=5, 
                    language=self.target_language, # Use configured language
                    condition_on_previous_text=True,
                    vad_filter=True, # Re-enable VAD
                    vad_parameters=dict(min_silence_duration_ms=500) # Default 500
                ))
            )
            
            # Combine segments
            text = " ".join([segment.text for segment in segments]).strip()
            
            return text
            
        except Exception as e:
            self.logger.error(f"Transcribe error: {e}")
            return ""

    def _resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        if source_rate == target_rate:
            return audio
        
        # If input has multiple channels, mix to mono first if not already
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        try:
            import librosa
            # Librosa expects (channels, samples) or (samples,)
            # Our audio is (samples,)
            # Use fast resampling
            return librosa.resample(audio, orig_sr=source_rate, target_sr=target_rate)
        except ImportError:
            # Fallback to naive linear interpolation if librosa is missing (but we just installed it)
            self.logger.warning("Librosa not found, using naive resampling (quality might be lower)")
            duration_s = len(audio) / source_rate
            target_length = int(duration_s * target_rate)
            return np.interp(
                np.linspace(0, len(audio), target_length, endpoint=False),
                np.arange(len(audio)),
                audio
            )

