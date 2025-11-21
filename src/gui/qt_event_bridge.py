from PySide6.QtCore import QObject, Signal

class QtEventBridge(QObject):
    """
    Bridges non-Qt events (EventBus) to Qt Signals for thread-safe UI updates.
    """
    sig_stt_partial = Signal(str)
    sig_stt_final = Signal(str)
    sig_translation = Signal(str)
    sig_context = Signal(str)
    sig_log = Signal(str, str) # level, message

    def __init__(self, bus):
        super().__init__()
        self.bus = bus
        
        # Subscribe to EventBus events
        self.bus.subscribe("stt.partial", self._on_stt_partial)
        self.bus.subscribe("stt.final_sentence", self._on_stt_final)
        self.bus.subscribe("llm.translation_ready", self._on_translation_ready)
        self.bus.subscribe("llm2.context_update_finished", self._on_context_update)

    def _on_stt_partial(self, data):
        text = data.get("text", "")
        if text:
            self.sig_stt_partial.emit(text)

    def _on_stt_final(self, data):
        text = data.get("sentence", "")
        if text:
            self.sig_stt_final.emit(text)

    def _on_translation_ready(self, data):
        text = data.get("translation", "")
        if text:
            self.sig_translation.emit(text)

    def _on_context_update(self, data):
        context = data.get("context", "")
        if context:
            self.sig_context.emit(context)

    def emit_log(self, level, message):
        """Can be called by a custom logging handler."""
        self.sig_log.emit(level, message)
