import os
import logging
import aiohttp
from .stt_manager import STTEngine

class APISTTEngine(STTEngine):
    def __init__(self, api_config, logger):
        self.config = api_config
        self.logger = logger
        self.provider = api_config.get("provider", "openai")
        self.model = api_config.get("model", "gpt-4o-mini-transcribe") # Note: real model name might differ
        self.api_key_env = api_config.get("api_key_env", "OPENAI_API_KEY")
        self.api_key = os.environ.get(self.api_key_env)
        
        if not self.api_key:
            self.logger.warning(f"API Key environment variable {self.api_key_env} not found.")

    async def transcribe(self, audio_chunk: bytes, sample_rate: int) -> str:
        """
        Sends audio chunk to API. 
        Note: Most APIs expect a file-like object with headers (WAV/MP3) rather than raw PCM.
        We might need to wrap the raw bytes into a WAV container in memory.
        """
        if self.provider == "openai":
            return await self._transcribe_openai(audio_chunk, sample_rate)
        elif self.provider == "google":
            # Placeholder
            return ""
        else:
            self.logger.error(f"Unknown provider: {self.provider}")
            return ""

    async def _transcribe_openai(self, raw_pcm, sample_rate):
        if not self.api_key:
            return ""
            
        # Convert Raw PCM to WAV in memory
        import io
        import wave
        
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1) # Assuming Mono from capture
                wf.setsampwidth(2) # Assuming 16-bit PCM for upload (or float32 needs conversion)
                wf.setframerate(sample_rate)
                
                # IMPORTANT: Input chunk is likely float32 [-1, 1] from our capture pipeline
                # OpenAI Whisper API typically accepts standard audio formats.
                # We need to convert float32 back to int16 bytes for standard WAV compatibility if needed,
                # or ensure we send float32 WAV if supported. 
                # Standard `wave` module usually expects bytes.
                
                # Conversion float32 -> int16
                import numpy as np
                # Check if raw_pcm is bytes or numpy array
                if isinstance(raw_pcm, np.ndarray):
                    audio_data = raw_pcm
                else:
                    audio_data = np.frombuffer(raw_pcm, dtype=np.float32)
                    
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())
                
            wav_buffer.seek(0)
            
            # Prepare request
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Multipart form data
            data = aiohttp.FormData()
            data.add_field('file', wav_buffer, filename='audio.wav', content_type='audio/wav')
            data.add_field('model', "whisper-1") # Currently standard model name
            data.add_field('language', 'en') # Or auto
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url, headers=headers, data=data) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            return result.get("text", "")
                        else:
                            err_text = await resp.text()
                            self.logger.error(f"OpenAI API Error {resp.status}: {err_text}")
                            return ""
                except Exception as e:
                    self.logger.error("OpenAI Request failed", exc=e)
                    return ""

