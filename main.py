import sys
import threading
import keyboard
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QComboBox, QFontComboBox, QSpinBox, QLineEdit

from translation_worker import TranslationWorker
# Import the overlay once it's created
from overlay import OverlayWindow

class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translation Overlay Config")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        # Language Selector
        self.lang_label = QLabel("Target Language:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Portuguese (Brazil)", "Spanish", "French"])
        
        # Font Settings
        self.font_label = QLabel("Font:")
        self.font_combo = QFontComboBox()
        self.size_spinBox = QSpinBox()
        self.size_spinBox.setValue(18)

        # AI API Settings
        self.api_label = QLabel("Google Gemini API Key (Optional but recommended):")
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter API Key for AI translations...")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Start Button
        self.start_button = QPushButton("START")
        self.start_button.clicked.connect(self.start_overlay)

        # Dynamic update signals
        self.font_combo.currentFontChanged.connect(self.update_font)
        self.size_spinBox.valueChanged.connect(self.update_font)
        self.lang_combo.currentTextChanged.connect(self.update_language)

        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_combo)
        layout.addWidget(self.api_label)
        layout.addWidget(self.api_input)
        layout.addWidget(self.font_label)
        layout.addWidget(self.font_combo)
        layout.addWidget(self.size_spinBox)
        layout.addWidget(self.start_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.overlay = None
        self.worker = None

        # Setup Global Hotkeys
        self.setup_hotkeys()

    def update_font(self):
        if getattr(self, "overlay", None):
            family = self.font_combo.currentFont().family()
            size = self.size_spinBox.value()
            self.overlay.set_font(family, size)

    def update_language(self):
        if getattr(self, "worker", None):
            lang_map = {"Portuguese (Brazil)": "pt", "Spanish": "es", "French": "fr"}
            lang = self.lang_combo.currentText()
            self.worker.set_target_language(lang_map.get(lang, "pt"))

    def setup_hotkeys(self):
        # We run the hotkey listener in a daemon thread so it doesn't block the PyQt loop
        threading.Thread(target=self.hotkey_listener, daemon=True).start()

    def hotkey_listener(self):
        # F8 toggles the overlay movability
        keyboard.add_hotkey('f8', self.toggle_overlay_lock)
        # F10 starts/stops the translation loop
        keyboard.add_hotkey('f10', self.toggle_translation)
        # F9 quits the app gracefully
        keyboard.add_hotkey('f9', self.quit_app)
        keyboard.wait()

    def toggle_overlay_lock(self):
        print("F8 Pressed: Toggling overlay lock...")
        if self.overlay:
            self.overlay.toggle_lock()

    def toggle_translation(self):
        print("F10 Pressed: Toggling translation loop...")
        if self.overlay and self.worker:
            self.worker.toggle()
            if self.worker.running:
                self.overlay.set_paused(False)
                # Update the bbox just before we start capturing
                rect = self.overlay.geometry()
                self.worker.set_bbox(rect.x(), rect.y(), rect.width(), rect.height())
                self.overlay.update_text("Translation Pipeline Activated\nWaiting for game text...")
            else:
                self.overlay.set_paused(True)

    def quit_app(self):
        print("F9 Pressed: Exiting application...")
        QApplication.quit()

    def start_overlay(self):
        if not self.overlay:
            self.overlay = OverlayWindow()
            self.worker = TranslationWorker()
            
            # Pass the API key to the worker if provided
            api_key = self.api_input.text().strip()
            if api_key:
                self.worker.set_api_key(api_key)

            # Connect the signal from the background thread to the UI refresh function
            self.worker.translation_ready.connect(self.overlay.update_text)
            self.worker.start()
        
        self.update_font()
        self.update_language()
        self.overlay.show()
        # Optionally hide the config window
        # self.hide()

import os

if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    app = QApplication(sys.argv)
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec())
