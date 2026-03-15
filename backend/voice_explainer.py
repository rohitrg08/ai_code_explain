import base64
import os
import tempfile
from typing import Dict

import pyttsx3
from gtts import gTTS


class VoiceExplainer:
    def synthesize(self, text: str) -> Dict[str, str]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Voice explanation text cannot be empty.")

        audio = self._synthesize_with_pyttsx3(cleaned_text)
        if audio:
            return {
                "engine": "pyttsx3",
                "mime_type": "audio/wav",
                "audio_base64": base64.b64encode(audio).decode("utf-8"),
            }

        audio = self._synthesize_with_gtts(cleaned_text)
        if audio:
            return {
                "engine": "gTTS",
                "mime_type": "audio/mpeg",
                "audio_base64": base64.b64encode(audio).decode("utf-8"),
            }

        raise RuntimeError("No voice engine was able to generate audio.")

    def _synthesize_with_pyttsx3(self, text: str) -> bytes | None:
        path = ""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                path = temp_file.name
            engine.save_to_file(text[:2000], path)
            engine.runAndWait()
            engine.stop()

            if not os.path.exists(path):
                return None
            with open(path, "rb") as audio_file:
                return audio_file.read()
        except Exception:
            return None
        finally:
            if path and os.path.exists(path):
                os.remove(path)

    def _synthesize_with_gtts(self, text: str) -> bytes | None:
        path = ""
        try:
            speech = gTTS(text=text[:2000], lang="en")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                path = temp_file.name
            speech.save(path)
            with open(path, "rb") as audio_file:
                return audio_file.read()
        except Exception:
            return None
        finally:
            if path and os.path.exists(path):
                os.remove(path)