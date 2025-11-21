import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.event_bus import EventBus
from src.translation.manager import TranslationManager

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def load_config_from_file():
    """
    Parse User_config.txt for API keys and model configurations.
    """
    config = {
        "api_key": None,
        "llm_translation_model": "gpt-4o-mini",
        "llm_summary_model": "gpt-4o-mini",
        "use_original_text_for_context": False,
        "context_update_interval": 1
    }
    
    try:
        with open("User_config.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == "OPENAI_API_KEY":
                        config["api_key"] = value
                    elif key == "LLM_TRANSLATION_MODEL":
                        config["llm_translation_model"] = value
                    elif key == "LLM_SUMMARY_MODEL":
                        config["llm_summary_model"] = value
                    elif key == "USE_ORIGINAL_TEXT_FOR_CONTEXT":
                        config["use_original_text_for_context"] = (value.lower() == "true")
                    elif key == "CONTEXT_UPDATE_INTERVAL":
                        try:
                            config["context_update_interval"] = int(value)
                        except ValueError:
                            print(f"Warning: Invalid CONTEXT_UPDATE_INTERVAL '{value}', using default 1")
                        
    except FileNotFoundError:
        print("Error: User_config.txt not found.")
        return None
    
    return config

async def main():
    print("=== Translation Module Smoke Test ===")
    
    file_config = load_config_from_file()
    if not file_config or not file_config.get("api_key"):
        print("Please set OPENAI_API_KEY in User_config.txt")
        return

    print(f"Using Translation Model: {file_config['llm_translation_model']}")
    print(f"Using Summary Model:     {file_config['llm_summary_model']}")
    print(f"Context Update Strategy: {'Original Text' if file_config['use_original_text_for_context'] else 'Translated Text'}")
    print(f"Context Update Interval: Every {file_config['context_update_interval']} sentences")

    # 1. Setup
    bus = EventBus()
    config = {
        "api_key": file_config["api_key"],
        "llm_translation_model": file_config["llm_translation_model"],
        "llm_summary_model": file_config["llm_summary_model"],
        "use_original_text_for_context": file_config["use_original_text_for_context"],
        "context_update_interval": file_config["context_update_interval"],
        "context_tokens": 500,
        "log_dir": "logs/smoke_test"
    }
    
    manager = TranslationManager(bus, config)
    
    # 2. Define Listener for Output
    def on_translation_ready(data):
        print("\n" + "="*40)
        print(f"Original:    {data.get('original')}")
        print(f"Translation: {data.get('translation')}")
        print("="*40 + "\n")

    def on_context_updated(data):
        print(f"[Scenario Context Updated]: {data.get('context')}")
        print("Enter next sentence (Ctrl+C to exit): ", end="", flush=True)

    bus.subscribe("llm.translation_ready", on_translation_ready)
    bus.subscribe("llm2.context_update_finished", on_context_updated)

    print("\nSystem ready. Enter a sentence to translate.")
    print("Enter sentence (Ctrl+C to exit): ", end="", flush=True)

    # 3. Input Loop
    loop = asyncio.get_running_loop()
    try:
        while True:
            # Use run_in_executor to avoid blocking the async loop with input()
            sentence = await loop.run_in_executor(None, sys.stdin.readline)
            if not sentence:
                break
            
            sentence = sentence.strip()
            if sentence:
                # Simulate STT event
                bus.emit("stt.final_sentence", {"text": sentence})
                # We need to wait a bit or just let the loop handle it
                # The TranslationManager handles it asynchronously
            else:
                print("Enter sentence (Ctrl+C to exit): ", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
