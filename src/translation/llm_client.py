import logging
from typing import Dict, Optional
from openai import AsyncOpenAI, APIError
from .prompt_builder import PromptBuilder

class LLMClient:
    """
    Client for interacting with LLM APIs (OpenAI compatible).
    """
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        
        # Allow separate models for translation and context summary
        self.translation_model = config.get("llm_translation_model", config.get("llm_api", "gpt-4o-mini"))
        self.summary_model = config.get("llm_summary_model", config.get("llm_api", "gpt-4o-mini"))
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        self.prompt_builder = PromptBuilder()
        self.logger = logging.getLogger("System")

    async def translate(self, sentence: str, context: str) -> Dict:
        """
        Translates a sentence using the LLM.
        Returns a dictionary with the translation and token usage.
        """
        prompt = self.prompt_builder.build_translation_prompt(sentence, context)
        
        try:
            self.logger.info(f"LLMClient: Sending translation request for: {sentence[:20]}...")
            start_time = __import__('time').time()
            response = await self.client.chat.completions.create(
                model=self.translation_model,
                messages=[
                    {"role": "system", "content": "You are a helpful translator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            duration = __import__('time').time() - start_time
            
            content = response.choices[0].message.content.strip()
            usage = response.usage
            
            self.logger.info(f"LLMClient: Translation received in {duration:.2f}s: {content[:20]}...")
            
            return {
                "translated_text": content,
                "tokens_in": usage.prompt_tokens if usage else 0,
                "tokens_out": usage.completion_tokens if usage else 0,
                "latency_ms": duration * 1000
            }
            
        except Exception as e:
            self.logger.error(f"LLM Translation Error: {e}")
            return {
                "translated_text": "", # Return empty or original on failure? Spec says log error.
                "error": str(e)
            }

    async def summarize_context(self, old_context: str, sentence: str, use_original: bool = False) -> str:
        """
        Updates the scenario context.
        """
        prompt = self.prompt_builder.build_summary_prompt(old_context, sentence, use_original_text=use_original)
        
        try:
            self.logger.info(f"LLMClient: Sending context update request...")
            response = await self.client.chat.completions.create(
                model=self.summary_model,
                messages=[
                    {"role": "system", "content": "You are a helpful summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            content = response.choices[0].message.content.strip()
            self.logger.info(f"LLMClient: Context updated: {content[:20]}...")
            return content
        except Exception as e:
            self.logger.error(f"LLM Context Update Error: {e}")
            return old_context # Fallback to old context
