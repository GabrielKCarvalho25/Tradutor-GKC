import sys
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
import win32api
import win32gui
import win32con
import ctypes

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Make the window frameless, tool-like, and topmost natively in PyQt
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Make the main widget background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setGeometry(100, 100, 800, 200)

        # Main Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Background Container: Semi-transparent blue box
        self.bg_container = QWidget()
        self.bg_container.setStyleSheet("background-color: rgba(0, 50, 150, 150); border: 2px solid cyan;")
        
        container_layout = QVBoxLayout(self.bg_container)
        
        # Translation Text Label
        self.text_label = QLabel("Waiting for Translation...")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: white; padding: 10px;")
        font = QFont("Arial", 24, QFont.Weight.Bold)
        self.text_label.setFont(font)
        
        container_layout.addWidget(self.text_label)
        layout.addWidget(self.bg_container)
        self.setLayout(layout)

        # Make the window click-through
        self._set_click_through()
        self.locked = True
        self.drag_pos = None

        # Exclude window from screen capture so it doesn't interfere with OCR!
        WDA_EXCLUDEFROMCAPTURE = 0x00000011
        ctypes.windll.user32.SetWindowDisplayAffinity(self.winId().__int__(), WDA_EXCLUDEFROMCAPTURE)

    def _set_click_through(self):
        """
        Uses the Win32 API to make the window completely transparent to mouse clicks
        so it doesn't interrupt or steal focus from exclusive fullscreen games.
        """
        hwnd = self.winId().__int__()
        
        # Get the current window style
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # Add the Layered and Transparent flags to bypass mouse input
        # WS_EX_TOOLWINDOW removes it from the alt-tab / taskbar menu
        # WS_EX_TOPMOST forces it above applications
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST)

    def toggle_lock(self):
        self.locked = not self.locked
        hwnd = self.winId().__int__()
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        if self.locked:
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TRANSPARENT)
            self.bg_container.setStyleSheet("background-color: rgba(0, 50, 150, 150); border: 2px solid cyan;")
            self.update_text("Trancado (Locked).\\nPressione F10 para Traduzir ou F8 para Mover.")
        else:
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style & ~win32con.WS_EX_TRANSPARENT)
            self.bg_container.setStyleSheet("background-color: rgba(200, 50, 50, 200); border: 4px dashed yellow;")
            self.update_text("Destrancado! (Unlocked)\\nArraste pelo mouse para mover a janela.\\nPressione F8 novamente para trancar.")

    def mousePressEvent(self, event):
        if not getattr(self, 'locked', True) and event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if not getattr(self, 'locked', True) and getattr(self, 'drag_pos', None):
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = None

    def update_text(self, new_text):
        """Callable locally or from a background capture/translation thread."""
        self.text_label.setText(new_text)

    def set_font(self, family, size):
        font = QFont(family, size, QFont.Weight.Bold)
        self.text_label.setFont(font)

    def set_paused(self, paused: bool):
        if paused:
            self.setWindowOpacity(0.05)
            self.update_text("")
        else:
            self.setWindowOpacity(1.0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    sys.exit(app.exec())
