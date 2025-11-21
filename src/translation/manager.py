import asyncio
import logging
from typing import Dict

from src.utils.event_bus import EventBus
from src.utils.dialogue_logger import DialogueLogger
from .llm_client import LLMClient
from .context_manager import ContextManager
from .latency_tracker import LatencyTracker

class TranslationManager:
    """
    Manages the translation workflow:
    STT -> LLM1 (Translate) -> Overlay
           LLM1 -> LLM2 (Context) -> ContextManager
    """
    def __init__(self, event_bus: EventBus, config: Dict):
        self.bus = event_bus
        self.config = config
        self.logger = logging.getLogger("System")
        
        # Initialize components
        self.llm_client = LLMClient(config)
        self.context_manager = ContextManager(max_tokens=config.get("context_tokens", 500))
        self.dialogue_logger = DialogueLogger(output_dir=config.get("log_dir", "logs/dialogue"))
        self.latency_tracker = LatencyTracker()
        
        # Configuration for context update strategy
        # Default to False (use translated text) to maintain backward compatibility
        self.use_original_text_for_context = config.get("use_original_text_for_context", False)
        
        # Configuration for context update frequency
        self.context_update_interval = int(config.get("context_update_interval", 1))
        self.pending_sentences_buffer = []
        
        # State
        self.sentence_counter = 0
        
        # Subscribe to events
        self.bus.subscribe("stt.final_sentence", self._on_final_sentence_wrapper)
        
    def set_target_language(self, lang: str):
        if self.llm_client:
            self.llm_client.set_target_language(lang)

    def reset_context(self):
        """Resets the context manager and updates overlay."""
        if self.context_manager:
            self.context_manager.update_context("")
            self.bus.emit("llm2.context_update_finished", {"context": ""})
            self.logger.info("Translation Context Reset.")
        
    def _on_final_sentence_wrapper(self, data: Dict):
        """
        Wrapper to schedule the async handler on the event loop.
        """
        asyncio.create_task(self.handle_final_sentence(data))

    async def handle_final_sentence(self, data: Dict):
        """
        Process a fully transcribed sentence.
        Input data expected: {"sentence": "sentence text", ...}
        """
        sentence_text = data.get("sentence", "")
        if not sentence_text:
            return

        self.sentence_counter += 1
        current_id = self.sentence_counter
        
        self.latency_tracker.start(current_id)
        self.logger.info(f"Translation started for ID {current_id}: {sentence_text[:20]}...")

        # 1. Get Context
        context = self.context_manager.get_context()
        self.logger.info(f"Context retrieved for ID {current_id}: {context[:20]}...")

        # 2. Translate (LLM1)
        # Notify start
        self.bus.emit("llm1.translate_started", {"id": current_id})
        
        self.logger.info(f"Calling LLM translate for ID {current_id}")
        trans_result = await self.llm_client.translate(sentence_text, context)
        translated_text = trans_result.get("translated_text", "")
        
        self.logger.info(f"LLM translate result for ID {current_id}: {translated_text[:20]}...")
        
        if not translated_text:
            self.logger.warning(f"Translation failed for ID {current_id}")
            return

        # Notify finish / Update Overlay
        self.bus.emit("translation.formatted_update", {
            "original": sentence_text,
            "translation": translated_text
        }) # Using a generic display event or the one in spec?
        # Spec says `overlay.translation_rendered` is triggered by Overlay, so we emit something Overlay listens to.
        # Spec Section 15: LLM -> on_translation_ready -> Overlay
        self.bus.emit("llm.translation_ready", {
            "id": current_id,
            "original": sentence_text,
            "translation": translated_text
        })

        latency = self.latency_tracker.stop(current_id)
        
        # 3. Context Update Logic (Buffered)
        # Determine which text to accumulate
        text_for_context = sentence_text if self.use_original_text_for_context else translated_text
        self.pending_sentences_buffer.append(text_for_context)
        
        new_context = context # Default to current context if not updating this turn

        if len(self.pending_sentences_buffer) >= self.context_update_interval:
            # Time to update context
            self.bus.emit("llm2.context_update_started", {"id": current_id})
            
            # Join buffered sentences
            combined_text = " ".join(self.pending_sentences_buffer)
            
            new_context = await self.llm_client.summarize_context(
                context, 
                combined_text, 
                use_original=self.use_original_text_for_context
            )
            
            self.context_manager.update_context(new_context)
            self.bus.emit("llm2.context_update_finished", {"context": new_context})
            
            # Clear buffer
            self.pending_sentences_buffer = []
        else:
             self.logger.info(f"Buffering context update ({len(self.pending_sentences_buffer)}/{self.context_update_interval})")

        # 4. Log
        self.dialogue_logger.append_record({
            "sentence_id": current_id,
            "source_sentence": sentence_text,
            "translated_sentence": translated_text,
            "scenario_context": new_context,
            "tokens_in": trans_result.get("tokens_in", 0),
            "tokens_out": trans_result.get("tokens_out", 0),
            "latency_ms": latency
        })
        
        self.logger.info(f"Translation finished ID {current_id} in {latency:.2f}ms")

    def stop(self):
        self.dialogue_logger.close()
