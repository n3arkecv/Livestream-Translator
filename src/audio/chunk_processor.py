import numpy as np
from src.utils.event_bus import EventBus

class ChunkProcessor:
    def __init__(self, bus: EventBus, sample_rate: int, chunk_ms: int = 640, overlap_ms: int = 160):
        self.bus = bus
        self.sample_rate = sample_rate
        self.chunk_samples = int(sample_rate * chunk_ms / 1000)
        self.overlap_samples = int(sample_rate * overlap_ms / 1000)
        self.buffer = np.zeros(0, dtype=np.float32)
        self.chunk_id = 0
        
        # Validate
        if self.overlap_samples >= self.chunk_samples:
            raise ValueError("Overlap cannot be greater than or equal to chunk size")

    def push(self, data: np.ndarray):
        self.buffer = np.concatenate([self.buffer, data])
        
        step = self.chunk_samples - self.overlap_samples
        
        while len(self.buffer) >= self.chunk_samples:
            # Extract chunk
            chunk = self.buffer[:self.chunk_samples]
            
            # Emit event
            self.chunk_id += 1
            # Debug log (remove later)
            # print(f"[DEBUG] Chunk {self.chunk_id} ready, size: {len(chunk)}")
            
            self.bus.emit(
                "audio.chunk_ready",
                {
                    "chunk_id": self.chunk_id,
                    "overlap_ms": self.overlap_samples * 1000 / self.sample_rate,
                    "duration_ms": self.chunk_samples * 1000 / self.sample_rate,
                    "chunk": chunk  # Passing the actual data in the event payload for now
                }
            )
            
            # Slide window: remove the non-overlapping part
            self.buffer = self.buffer[step:]

