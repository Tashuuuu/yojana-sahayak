# Gnani Prisma (speech-to-text) and Timbre (text-to-speech)
import io
import json
import os
import re
import time
import wave

import requests
from dotenv import load_dotenv

load_dotenv()

DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
STT_KEY = os.getenv("GNANI_STT_API_KEY", "")
TTS_KEY = os.getenv("GNANI_TTS_API_KEY", "")
STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"


def _lang_short(code: str) -> str:
    """'hi-IN' -> 'hi'; anything else -> 'en'."""
    return "hi" if (code or "").lower().startswith("hi") else "en"


def _silent_wav(seconds: float = 1.0, rate: int = 24000) -> bytes:
    """Make a valid WAV file containing silence (used in dry-run mode)."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buffer.getvalue()


def prep_for_tts(text: str) -> str:
    """Make text easier for the voice to read (currency sign, extra spaces)."""
    has_english = re.search(r"[A-Za-z]", text) is not None
    text = text.replace("₹", "rupees " if has_english else "रुपये ")
    return re.sub(r"\s+", " ", text).strip()


def transcribe(wav_bytes: bytes, keyterms: list[str] | None = None,
               model: str = "prisma-v3.0", language_code: str = "hi-IN,en-IN") -> dict:
    """Speech -> text. Returns {'text', 'lang', 'detected_language_code', 'request_id'}."""
    if DRY_RUN:
        return {"text": "पीएम किसान में कौन आवेदन कर सकता है?", "lang": "hi",
                "detected_language_code": "hi-IN", "request_id": "dry-run"}
    if not STT_KEY:
        raise RuntimeError("GNANI_STT_API_KEY is missing. Put it in .env")

    data = {"model": model, "language_code": language_code, "format": "transcribe"}
    if keyterms:
        data["keyterms"] = json.dumps(keyterms[:200], ensure_ascii=False)

    for attempt in range(3):
        response = requests.post(
            STT_URL,
            headers={"X-API-Key-ID": STT_KEY},
            files={"audio_file": ("question.wav", wav_bytes, "audio/wav")},
            data=data,
            timeout=60,
        )
        if response.status_code == 429:          # "too many requests": wait, then retry
            time.sleep(2 ** attempt)
            continue
        break

    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"STT failed: {body.get('error')}")
    code = body.get("detected_language_code", "hi-IN")
    return {"text": body["transcript"], "lang": _lang_short(code),
            "detected_language_code": code, "request_id": body.get("request_id")}


def speak(text: str, lang: str = "hi") -> bytes:
    """Text -> speech. Returns WAV bytes."""
    text = prep_for_tts(text)
    if DRY_RUN:
        return _silent_wav()
    if not TTS_KEY:
        raise RuntimeError("GNANI_TTS_API_KEY is missing. Put it in .env")

    voice, code = ("Nalini", "hi-IN") if lang == "hi" else ("Kaveri", "en-IN")
    payload = {
        "text": text, "voice": voice, "model": "timbre-v2.5", "language": code, "speed": 1.0,
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    for attempt in range(3):
        response = requests.post(
            TTS_URL,
            headers={"X-API-Key-ID": TTS_KEY, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if response.status_code in (429, 500, 503):
            time.sleep(2 ** attempt)
            continue
        break
    response.raise_for_status()
    return response.content