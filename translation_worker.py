import asyncio
import numpy as np
import mss
from PyQt6.QtCore import QThread, pyqtSignal
from deep_translator import GoogleTranslator
import google.generativeai as genai

# Windows Runtime APIs for blazing fast native OCR
import winrt.windows.media.ocr as ocr
import winrt.windows.graphics.imaging as imaging
import winrt.windows.storage.streams as streams

class TranslationWorker(QThread):
    # Signal to send translated string back to the GUI Thread
    translation_ready = pyqtSignal(str)

    def __init__(self, target_language="pt"):
        super().__init__()
        self.running = False
        self.target_language = target_language
        self.translator = GoogleTranslator(source='en', target=self.target_language)
        
        # Initialize native Windows 10/11 OCR Engine securely
        self.ocr_engine = ocr.OcrEngine.try_create_from_user_profile_languages()
        self.last_text = ""
        self.capture_bbox = {"top": 0, "left": 0, "width": 800, "height": 200}
        self.api_key = None
        self.ai_model = None

    def set_api_key(self, api_key):
        self.api_key = api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            system_instruction = "You are a fast, direct translation engine for video games. Translate the given text accurately and naturally. Do not add conversational filler. No memory required."
            self.ai_model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)

    def set_bbox(self, x, y, width, height):
        """Update the bounding box based on the overlay window's position."""
        self.capture_bbox = {"top": int(y), "left": int(x), "width": int(width), "height": int(height)}

    def toggle(self):
        self.running = not self.running

    def set_target_language(self, lang_code):
        self.target_language = lang_code
        self.translator.target = lang_code

    def run(self):
        """Standard QThread execution loop."""
        # Use a new asyncio loop for the thread so WinRT awaits work properly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._capture_loop())

    async def _capture_loop(self):
        with mss.mss() as sct:
            while True:
                if not self.running:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    # Capture localized bounding box
                    img = sct.grab(self.capture_bbox)
                    
                    # Convert raw bgra pixels to WinRT SoftwareBitmap
                    bitmap = self._create_software_bitmap(img.bgra, img.width, img.height)
                    
                    # Run Native OCR
                    ocr_result = await self.ocr_engine.recognize_async(bitmap)
                    text = ocr_result.text.strip()
                    
                    print(f"BBox: {self.capture_bbox} | OCR Found: {text!r}")
                    
                    # Only translate if text actually found and changed
                    if text and text != self.last_text:
                        self.last_text = text
                        # Semantic Translation
                        try:
                            if getattr(self, "ai_model", None):
                                prompt = f"Translate the following game text to {self.target_language}:\n'{text}'\nReturn ONLY the translation."
                                try:
                                    safety_settings = [
                                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                                    ]
                                    response = await self.ai_model.generate_content_async(prompt, safety_settings=safety_settings)
                                    translated_text = response.text.strip()
                                except Exception as ai_e:
                                    print(f"AI API Error: {ai_e}")
                                    translated_text = self.translator.translate(text)
                            else:
                                translated_text = self.translator.translate(text)
                                
                            print(f"Translated: {translated_text!r}")
                            # Dispatch Signal to GUI
                            self.translation_ready.emit(translated_text)
                        except Exception as transl_err:
                            print(f"Translation Output Error: {transl_err}")
                            self.translation_ready.emit(f"[Erro de Tradução] {transl_err}")
                    
                except Exception as e:
                    print(f"Error in translation loop: {e}")
                
                # Sleep between loops to save CPU (200ms = 5fps capture, fine for text)
                await asyncio.sleep(0.2)

    def _create_software_bitmap(self, bgra_bytes, width, height):
        """Convert raw mss pixels into a format the Windows OCR API can read."""
        # Create a DataWriter to hold the pixel bytes
        data_writer = streams.DataWriter()
        data_writer.write_bytes(bytearray(bgra_bytes))
        buffer = data_writer.detach_buffer()

        # Create SoftwareBitmap from buffer using correct Python winrt projection syntax
        bitmap = imaging.SoftwareBitmap(
            imaging.BitmapPixelFormat.BGRA8,
            width,
            height,
            imaging.BitmapAlphaMode.PREMULTIPLIED
        )
        bitmap.copy_from_buffer(buffer)
        return bitmap
