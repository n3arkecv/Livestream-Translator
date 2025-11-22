import asyncio
import logging
import queue
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any

class STTEngine(ABC):
    @abstractmethod
    async def transcribe(self, audio_chunk: Any, sample_rate: int) -> str:
        pass

class STTManager:
    def __init__(self, bus, config: Dict[str, Any], logger):
        self.bus = bus
        self.config = config
        self.logger = logger
        self.engine: STTEngine = None
        self.mode = config.get("stt", {}).get("mode", "local")
        
        # Buffer for "Streaming" style accumulation
        import numpy as np
        self.audio_buffer = np.array([], dtype=np.float32)
        self.silence_counter = 0
        self.chunks_since_transcribe = 0
        self.VAD_THRESHOLD = 0.005 # Adjust based on noise floor
        self.SILENCE_CHUNKS_THRESHOLD = 1 # 1 * 200ms = 200 silence triggers finalize
        self.MAX_BUFFER_DURATION = 10.0 # Force finalize after 15 seconds
        self.TRANSCRIBE_INTERVAL = 2 # Transcribe every 2 chunks (400ms) to save GPU
        
        # Use thread-safe queue for audio data transfer (can be called from any thread)
        self.audio_queue = queue.Queue(maxsize=20)  # Thread-safe queue
        
        self._setup_engine()
        
        # Subscribe to audio events
        self.bus.subscribe("audio.chunk_ready", self.handle_chunk)
        
        # We need to start the processing loop explicitly
        self._processing_task = None

    def set_language(self, lang_code):
        """Sets the language on the engine if supported."""
        if self.engine and hasattr(self.engine, 'set_language'):
            self.engine.set_language(lang_code)
        else:
            self.logger.warning("Engine does not support language switching or not initialized")

    def set_model(self, model_name):
        """Reloads the model on the engine if supported."""
        if self.engine and hasattr(self.engine, 'reload_model'):
            # This might block, so ideally it should be called in a way that doesn't freeze the UI too long
            # But since we are in BackendWorker thread (asyncio loop), we should be careful.
            # Ideally, reload_model should be async or fast. 
            # Loading a model takes time (seconds), so it WILL block the loop if not threaded.
            # For simplicity now, we just call it.
            self.engine.reload_model(model_name)
        else:
            self.logger.warning("Engine does not support model reloading")

    def reload_engine(self):
        """Reloads the entire STT engine with current config."""
        self.logger.info("Reloading STT engine with updated configuration...")
        self._setup_engine()

    def _setup_engine(self):
        stt_config = self.config.get("stt", {})
        if self.mode == "api":
            from .api_stt_engine import APISTTEngine
            self.engine = APISTTEngine(stt_config.get("api", {}), self.logger)
        elif self.mode == "local":
            from .local_stt_engine import LocalSTTEngine
            model = stt_config.get("model", "small.en")
            device = stt_config.get("device", "cuda")
            compute_type = stt_config.get("compute_type", "float16")
            self.engine = LocalSTTEngine(model_name=model, device=device, compute_type=compute_type, logger=self.logger)
        else:
            self.logger.error(f"Unknown STT mode: {self.mode}")

    def start_processing(self):
        """Start the background task to process audio chunks from queue."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # If no loop running (e.g. called before loop start), we can't create task yet.
            # Ideally this is called inside an async context.
            return
        
        self._processing_task = loop.create_task(self._process_queue())
    
    def stop_processing(self):
        """Stop the background processing task."""
        if self._processing_task:
            self._processing_task.cancel()

    def handle_chunk(self, data):
        """
        Handles the 'audio.chunk_ready' event.
        This might be called from the AudioCapture thread.
        Instead of trying to schedule async task directly (which is tricky cross-thread),
        we just put data into a thread-safe queue.
        """
        chunk = data.get("chunk")
        
        import numpy as np
        
        # Ensure chunk is numpy array and correct format
        if not isinstance(chunk, np.ndarray):
            return
        
        # Put chunk in thread-safe queue (non-blocking)
        try:
            self.audio_queue.put_nowait(chunk)
        except queue.Full:
            self.logger.warning("Audio queue full, dropping chunk")
        except Exception as e:
            self.logger.error(f"Error putting chunk in queue: {e}")
    
    async def _process_queue(self):
        """Background task that continuously processes chunks from queue."""
        while True:
            try:
                # Poll thread-safe queue (with small sleep to avoid busy-waiting)
                # In a real app, we might use an asyncio.Queue and bridge it, 
                # but queue.Queue + polling is safe and simple for now.
                try:
                    chunk = self.audio_queue.get_nowait()
                    await self._process_chunk(chunk)
                except queue.Empty:
                    # No chunk available, sleep briefly to yield control
                    await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in queue processing: {e}")
                await asyncio.sleep(0.1)

    async def _process_chunk(self, chunk):
        if not self.engine:
            return

        try:
            import numpy as np
            
            # Ensure 1D array (mono)
            if chunk.ndim > 1:
                if chunk.ndim == 2:
                    chunk = chunk.mean(axis=1) if chunk.shape[1] > 1 else chunk[:, 0]
                else:
                    chunk = chunk.flatten()
            
            # Ensure float32
            if chunk.dtype != np.float32:
                chunk = chunk.astype(np.float32)

            # --- VAD & Buffering Logic ---
            
            # 1. Check Energy of NEW chunk
            rms = np.sqrt(np.mean(chunk**2))
            if rms < self.VAD_THRESHOLD:
                self.silence_counter += 1
            else:
                self.silence_counter = 0
                
            # 2. Append to Buffer
            self.audio_buffer = np.concatenate((self.audio_buffer, chunk))
            self.chunks_since_transcribe += 1
            
            # 3. Check buffer limits
            buffer_duration_sec = len(self.audio_buffer) / 44100
            
            should_finalize = False
            if self.silence_counter >= self.SILENCE_CHUNKS_THRESHOLD and buffer_duration_sec > 0.3:
                should_finalize = True
            elif buffer_duration_sec > self.MAX_BUFFER_DURATION: # Force finalize if too long
                should_finalize = True
                
            # If buffer is very short and silent, skip processing to save GPU
            if buffer_duration_sec < 0.1:
                return

            # 4. Transcribe Accumulated Buffer
            # Optimize: Only transcribe if finalizing OR enough time passed (throttle)
            # Dynamic throttle based on auto-detect mode
            throttle_interval = self.TRANSCRIBE_INTERVAL
            if hasattr(self.engine, 'is_auto_detect') and self.engine.is_auto_detect():
                throttle_interval = self.TRANSCRIBE_INTERVAL + 1 # Slower updates for auto-detect
                
            if should_finalize or self.chunks_since_transcribe >= throttle_interval:
                self.bus.emit("stt.decode_started", {})
                text = await self.engine.transcribe(self.audio_buffer, 44100)
                self.chunks_since_transcribe = 0 # Reset throttle counter
                
                if text:
                    if should_finalize:
                        # Finalize
                        self.bus.emit("stt.final_sentence", {"sentence": text})
                        self.audio_buffer = np.array([], dtype=np.float32)
                        self.silence_counter = 0
                    else:
                        # Partial
                        self.bus.emit("stt.partial", {"text": text})
                else:
                    # No text found
                    if should_finalize:
                        # Just clear buffer if we thought we were finishing but got nothing (noise)
                        self.audio_buffer = np.array([], dtype=np.float32)
                        self.silence_counter = 0
            else:
                # Skip transcription for this chunk, just accumulate
                pass
                
        except Exception as e:
            self.logger.error("STT processing failed", exc=e)
            # Reset buffer on error to avoid stuck state
            self.audio_buffer = np.array([], dtype=np.float32)
