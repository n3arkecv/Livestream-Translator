class SentenceAssembler:
    def __init__(self, bus, logger):
        self.bus = bus
        self.logger = logger
        self.current_partial = ""
        self.last_final = ""
        
    def add_partial(self, text: str):
        """
        Receives partial text from STT engine.
        Simple logic for now: 
        - If text ends with punctuation, treat as final.
        - Else update partial.
        """
        clean_text = text.strip()
        if not clean_text:
            return

        # Basic boundary detection
        if clean_text.endswith(('.', '?', '!')):
            self.last_final = clean_text
            self.current_partial = ""
            
            self.bus.emit("stt.final_sentence", {
                "sentence": self.last_final,
                "sentence_id": id(self.last_final) # Simple ID for now
            })
            self.logger.info(f"[Assembler] Final: {self.last_final}")
        else:
            self.current_partial = clean_text
            self.bus.emit("stt.partial_transcript", {"text": self.current_partial})

