from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QPoint, QRect, QTimer
from PySide6.QtGui import QFont, QColor, QCursor, QLinearGradient, QPalette, QBrush

class OverlayWindow(QWidget):
    MARGIN = 10  # Resize boundary width

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # Enable mouse tracking for cursor updates
        self.setMouseTracking(True)

        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(5)
        
        # 1. Ongoing Sentence (Partial) with Shimmer
        self.lbl_ongoing = QLabel("Listening...")
        # We will use custom painting or timer-based stylesheet update for shimmer
        self.lbl_ongoing.setStyleSheet("color: #E0FFFF; font-weight: bold; font-style: italic;")
        self.lbl_ongoing.setWordWrap(True)
        self.lbl_ongoing.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        # Shadow for readability
        shadow1 = QGraphicsDropShadowEffect(self)
        shadow1.setBlurRadius(10)
        shadow1.setColor(QColor(0, 0, 0, 255))
        shadow1.setOffset(1, 1)
        self.lbl_ongoing.setGraphicsEffect(shadow1)

        # 2. Translated Sentence (Final) - Replaced by a list/history mechanism
        # We will keep the label for the MOST RECENT final sentence, and maybe shift others
        # User requested: "show only finalized sentence... when another sentence start, move this finalized sentence down"
        # This implies a history stack.
        # Let's use a VBox layout for history, but for simplicity and performance in overlay, 
        # maybe just 2 labels? Current Final and Previous Final?
        # Or a single label that appends text? 
        # "move this finalized sentence down" -> Newest on top? Or Newest on bottom?
        # Usually subtitles: Newest on bottom, old ones scroll up. 
        # OR: Voice Assistant style: Newest replaces old, old ones disappear or fade down.
        # Let's assume: 
        # Top: Ongoing (Shimmering)
        # Below: Finalized (Yellow)
        # When new final comes, old final moves down (becomes history).
        
        # Let's implement a simple "Current Final" and "History"
        self.lbl_final = QLabel("")
        self.lbl_final.setStyleSheet("color: #FFD700; font-weight: bold;")
        self.lbl_final.setWordWrap(True)
        self.lbl_final.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        shadow2 = QGraphicsDropShadowEffect(self)
        shadow2.setBlurRadius(10)
        shadow2.setColor(QColor(0, 0, 0, 255))
        shadow2.setOffset(1, 1)
        self.lbl_final.setGraphicsEffect(shadow2)
        
        # History Label (Gray/White, smaller?)
        self.lbl_history = QLabel("")
        self.lbl_history.setStyleSheet("color: #CCCCCC;")
        self.lbl_history.setWordWrap(True)
        self.lbl_history.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        shadow3 = QGraphicsDropShadowEffect(self)
        shadow3.setBlurRadius(8)
        shadow3.setColor(QColor(0, 0, 0, 255))
        shadow3.setOffset(1, 1)
        self.lbl_history.setGraphicsEffect(shadow3)

        self.layout.addWidget(self.lbl_ongoing)
        self.layout.addWidget(self.lbl_final)
        self.layout.addWidget(self.lbl_history) # History below
        
        self.layout.addStretch() # Push everything to top
        
        # Initial settings
        self.resize(800, 300)
        self.font_size = 24
        self.update_font()
        
        # Background handling
        self.show_background = True
        self.bg_color = QColor(0, 0, 0, 100)
        
        # Shimmer Timer
        self.shimmer_timer = QTimer(self)
        self.shimmer_timer.timeout.connect(self._update_shimmer)
        self.shimmer_step = 0
        self.is_transcribing = False
        
        # History Settings
        self.max_history_lines = 3

        # State for dragging/resizing
        self.old_pos = None
        self.resizing = False
        self.resize_edge = None # (horizontal, vertical) e.g. ('left', 'top')

    def _update_shimmer(self):
        # Simple CSS gradient animation is hard in Qt Labels.
        # We can simulate "Apple slide to unlock" shimmer by cycling colors 
        # from Dark Gray -> White -> Dark Gray
        
        if not self.is_transcribing:
            return
            
        # Cycle of colors
        colors = ["#666666", "#888888", "#AAAAAA", "#CCCCCC", "#EEEEEE", "#FFFFFF", "#EEEEEE", "#CCCCCC", "#AAAAAA", "#888888"]
        idx = self.shimmer_step % len(colors)
        color = colors[idx]
        
        self.lbl_ongoing.setStyleSheet(f"color: {color}; font-weight: bold; font-style: italic;")
        self.shimmer_step += 1

    def update_font(self):
        font_ongoing = QFont("Segoe UI", self.font_size)
        self.lbl_ongoing.setFont(font_ongoing)
        
        font_trans = QFont("Segoe UI", int(self.font_size)) # Final same size
        self.lbl_final.setFont(font_trans)
        
        font_hist = QFont("Segoe UI", int(self.font_size * 0.8))
        self.lbl_history.setFont(font_hist)

    def set_font_size(self, size):
        self.font_size = size
        self.update_font()
        
    def set_history_lines(self, count):
        self.max_history_lines = count
        if count == 0:
            self.lbl_history.hide()
            self.lbl_history.setText("")
        else:
            self.lbl_history.show()
            # Trim existing text if needed
            current_text = self.lbl_history.text()
            if current_text:
                lines = current_text.split('\n')[:count]
                self.lbl_history.setText('\n'.join(lines))

    def set_opacity(self, opacity):
        self.setWindowOpacity(opacity)

    def update_partial(self, text):
        self.lbl_ongoing.setText(text)
        if not self.is_transcribing:
            self.is_transcribing = True
            self.shimmer_timer.start(100) # 100ms update rate
            self.lbl_ongoing.show()

    def on_final_sentence(self, text):
        # Stop shimmer
        self.is_transcribing = False
        self.shimmer_timer.stop()
        self.lbl_ongoing.setText("")
        self.lbl_ongoing.hide() # Hide ongoing area to save space? Or keep it?
        # Let's keep it but empty so layout doesn't jump too much if using fixed height
        # But VBoxLayout will shrink it.
        
        # Move current final to history
        current = self.lbl_final.text()
        if current and self.max_history_lines > 0:
            # Move down
            hist = self.lbl_history.text()
            # Keep last N lines of history
            if hist:
                new_hist = f"{current}\n{hist}".strip()
            else:
                new_hist = current
                
            # Limit history length (lines)
            lines = new_hist.split('\n')[:self.max_history_lines]
            self.lbl_history.setText('\n'.join(lines))
            
        # Set new final
        self.lbl_final.setText(text)
        
    def update_translation(self, text):
        self.lbl_final.setText(text)
        
    def update_context(self, text):
        pass # Removed context label for now as per user request structure

    # Painting for background
    def paintEvent(self, event):
        if self.show_background:
            from PySide6.QtGui import QPainter, QBrush, QColor
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(self.bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 15, 15)
        super().paintEvent(event)

    # Dragging and Resizing implementation
    def _check_resize_area(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self.MARGIN
        
        h_edge = None
        v_edge = None
        
        if x < m: h_edge = 'left'
        elif x > w - m: h_edge = 'right'
        
        if y < m: v_edge = 'top'
        elif y > h - m: v_edge = 'bottom'
        
        return h_edge, v_edge

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            h, v = self._check_resize_area(event.position().toPoint())
            if h or v:
                self.resizing = True
                self.resize_edge = (h, v)
                self.old_pos = event.globalPosition().toPoint()
            else:
                self.resizing = False
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        if not self.resizing and not self.old_pos:
            # Update cursor shape
            h, v = self._check_resize_area(pos)
            if h == 'left' and v == 'top': self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif h == 'right' and v == 'bottom': self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif h == 'left' and v == 'bottom': self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif h == 'right' and v == 'top': self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif h: self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif v: self.setCursor(Qt.CursorShape.SizeVerCursor)
            else: self.setCursor(Qt.CursorShape.ArrowCursor)

        if self.resizing and self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            geom = self.geometry()
            h, v = self.resize_edge
            
            if h == 'right':
                geom.setWidth(geom.width() + delta.x())
            elif h == 'left':
                geom.setLeft(geom.left() + delta.x())
                
            if v == 'bottom':
                geom.setHeight(geom.height() + delta.y())
            elif v == 'top':
                geom.setTop(geom.top() + delta.y())
                
            self.setGeometry(geom)
            self.old_pos = event.globalPosition().toPoint()
            
        elif self.old_pos: # Dragging
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.resizing = False
        self.resize_edge = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

