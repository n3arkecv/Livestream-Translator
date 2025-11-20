from PySide6.QtCore import QObject, Signal

class QtEventBridge(QObject):
    """
    Bridges non-Qt events (EventBus) to Qt Signals for thread-safe UI updates.
    """
    sig_stt_partial = Signal(str)
    sig_stt_final = Signal(str)
    sig_log = Signal(str, str) # level, message

    def __init__(self, bus):
        super().__init__()
        self.bus = bus
        
        # Subscribe to EventBus events
        self.bus.subscribe("stt.partial", self._on_stt_partial)
        self.bus.subscribe("stt.final_sentence", self._on_stt_final)
        
        # We should also subscribe to logs if SystemLogger emits events, 
        # but currently SystemLogger might just write to file/console. 
        # We might need to modify SystemLogger or wrap it to emit events, 
        # OR we can just emit signals when we use the logger if we pass this bridge around.
        # For now, let's assume we might add a log handler that emits signals, 
        # or just rely on explicit events if the logger supports it.
        # Looking at existing logger.py, it doesn't seem to use EventBus.
        # We'll bridge what we can.

    def _on_stt_partial(self, data):
        text = data.get("text", "")
        if text:
            self.sig_stt_partial.emit(text)

    def _on_stt_final(self, data):
        text = data.get("sentence", "")
        if text:
            self.sig_stt_final.emit(text)

    def emit_log(self, level, message):
        """Can be called by a custom logging handler."""
        self.sig_log.emit(level, message)
