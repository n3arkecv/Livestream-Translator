import asyncio
import logging
import sys
import os

# Ensure project root is in path so we can import src
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.event_bus import EventBus
from src.utils.logger import SystemLogger
from src.audio.capture import AudioCapture
from src.transcription.stt_manager import STTManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = SystemLogger("SmokeTest")

async def main():
    logger.info("Starting System Audio to STT Smoke Test...")
    logger.info("Please ensure some audio (English speech) is playing on your system.")
    
    # 1. Event Bus
    bus = EventBus()
    
    # 2. Configuration
    config = {
        "audio": {
            "output_device": "default", # Uses default output device
            "use_loopback": True
        },
        "chunk": {
            "size_ms": 3000, # 3 second chunks for better context
            "overlap_ms": 0
        },
        "stt": {
            "mode": "local",
            "model": "deepdml/faster-whisper-large-v3-turbo-ct2", # Turbo model on HuggingFace
            "device": "cuda",    # Use CUDA for GPU acceleration
            "compute_type": "float16" # Standard for CUDA
        }
    }
    
    # 3. STT Manager
    # STTManager needs to be started inside the loop so it can create the processing task
    stt_manager = STTManager(bus, config, logger)
    stt_manager.start_processing()
    
    # 4. Audio Capture
    capture = AudioCapture(bus, config, logger)
    
    # 5. Subscribe to results
    def on_stt_result(data):
        text = data.get('text', '').strip()
        if text:
            print(f"\n>> [STT RESULT]: {text}\n")

    def on_chunk(data):
        chunk = data.get('chunk')
        import numpy as np
        rms = np.sqrt(np.mean(chunk**2))
        print(f"[Audio] Chunk received. RMS: {rms:.4f} {'(Silence)' if rms < 0.01 else '(Audio Detected)'}")

    bus.subscribe("stt.partial", on_stt_result)
    bus.subscribe("audio.chunk_ready", on_chunk)
    
    # 6. Start Capture
    logger.info("Initializing Audio Capture...")
    try:
        capture.start()
        logger.info("Audio Capture started. Listening for system audio...")
    except Exception as e:
        logger.error(f"Failed to start capture: {e}")
        return

    # 7. Run for a duration
    print("\n" + "="*40)
    print("LISTENING INDEFINITELY...")
    print("Play a YouTube video or speak into a mic routed to output.")
    print("Press Ctrl+C to stop the test.")
    print("="*40 + "\n")
    
    try:
        # Keep the loop alive
        i = 0
        while True:
            await asyncio.sleep(1)
            i += 1
            if i % 5 == 0:
                print(f"Tick {i}s...")
                
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        print("Stopping components...")
        capture.stop()
        stt_manager.stop_processing()
        print("Test Finished.")

if __name__ == "__main__":
    try:
        # Check if faster-whisper is installed
        import faster_whisper
        asyncio.run(main())
    except ImportError:
        print("Error: 'faster-whisper' is not installed. Please run 'pip install faster-whisper'.")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

