from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QColor

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool # Tool window style, usually no taskbar icon
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) # Default false, can click

        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(5)
        
        # 1. Ongoing Sentence (Partial)
        self.lbl_ongoing = QLabel("Listening...")
        self.lbl_ongoing.setStyleSheet("color: white; font-weight: bold;")
        self.lbl_ongoing.setWordWrap(True)
        self.lbl_ongoing.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        # Shadow for readability
        shadow1 = QGraphicsDropShadowEffect(self)
        shadow1.setBlurRadius(10)
        shadow1.setColor(QColor(0, 0, 0, 255))
        shadow1.setOffset(1, 1)
        self.lbl_ongoing.setGraphicsEffect(shadow1)

        # 2. Translated Sentence (Final)
        self.lbl_translated = QLabel("")
        self.lbl_translated.setStyleSheet("color: #E6F4FF; font-weight: bold;")
        self.lbl_translated.setWordWrap(True)
        self.lbl_translated.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        shadow2 = QGraphicsDropShadowEffect(self)
        shadow2.setBlurRadius(10)
        shadow2.setColor(QColor(0, 0, 0, 255))
        shadow2.setOffset(1, 1)
        self.lbl_translated.setGraphicsEffect(shadow2)
        
        # 3. Context (Scenario)
        self.lbl_context = QLabel("")
        self.lbl_context.setStyleSheet("color: #BBD2F3;")
        self.lbl_context.setWordWrap(True)
        self.lbl_context.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        shadow3 = QGraphicsDropShadowEffect(self)
        shadow3.setBlurRadius(8)
        shadow3.setColor(QColor(0, 0, 0, 255))
        shadow3.setOffset(1, 1)
        self.lbl_context.setGraphicsEffect(shadow3)

        self.layout.addWidget(self.lbl_ongoing)
        self.layout.addWidget(self.lbl_translated)
        self.layout.addWidget(self.lbl_context)
        
        # Initial settings
        self.resize(800, 200)
        self.font_size = 24
        self.update_font()
        
        # Background handling
        self.show_background = True
        self.bg_color = QColor(0, 0, 0, 100) # Semi-transparent black

        # Dragging state
        self.old_pos = None

    def update_font(self):
        font_ongoing = QFont("Segoe UI", self.font_size)
        self.lbl_ongoing.setFont(font_ongoing)
        
        font_trans = QFont("Segoe UI", int(self.font_size * 0.9))
        self.lbl_translated.setFont(font_trans)
        
        font_ctx = QFont("Segoe UI", int(self.font_size * 0.7))
        self.lbl_context.setFont(font_ctx)

    def set_font_size(self, size):
        self.font_size = size
        self.update_font()

    def set_opacity(self, opacity):
        self.setWindowOpacity(opacity)

    def update_partial(self, text):
        self.lbl_ongoing.setText(text)

    def update_translation(self, text):
        self.lbl_translated.setText(text)
        
    def update_context(self, text):
        self.lbl_context.setText(text)

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

    # Dragging implementation
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

