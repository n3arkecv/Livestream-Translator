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
        
        # Use thread-safe queue for audio data transfer (can be called from any thread)
        self.audio_queue = queue.Queue(maxsize=10)  # Thread-safe queue
        
        self._setup_engine()
        
        # Subscribe to audio events
        self.bus.subscribe("audio.chunk_ready", self.handle_chunk)
        
        # We need to start the processing loop explicitly
        self._processing_task = None

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
            self.bus.emit("stt.decode_started", {})
            
            import numpy as np
            
            # CRITICAL DEBUG: Check chunk shape and type BEFORE any processing
            # self.logger.debug(f"[STTManager] Chunk received: shape={chunk.shape}, dtype={chunk.dtype}, ndim={chunk.ndim}")
            
            # Ensure 1D array (mono)
            if chunk.ndim > 1:
                # self.logger.warning(f"[STTManager] Chunk is {chunk.ndim}D, flattening to mono. Original shape: {chunk.shape}")
                if chunk.ndim == 2:
                    # If it's (samples, channels), mix to mono
                    chunk = chunk.mean(axis=1) if chunk.shape[1] > 1 else chunk[:, 0]
                else:
                    chunk = chunk.flatten()
            
            rms = np.sqrt(np.mean(chunk**2))
            if rms < 0.01:
                 # Skip silence
                 return
            
            # Explicitly ensure float32 for local engine consistency
            if chunk.dtype != np.float32:
                chunk = chunk.astype(np.float32)
            
            text = await self.engine.transcribe(chunk, 44100)
            
            if text:
                # self.logger.info(f"STT Result: {text}") # Log any result
                self.bus.emit("stt.partial", {"text": text})
            else:
                pass
                
        except Exception as e:
            self.logger.error("STT processing failed", exc=e)
