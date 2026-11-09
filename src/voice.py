"""Gnani Prisma v3.0 STT and Timbre v2.5 TTS REST wrappers."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import wave
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)  # .env must beat stale shell variables such as DRY_RUN=1
STT_URL = os.getenv("GNANI_STT_URL", "https://api.vachana.ai/stt/v3").strip()
TTS_URL = os.getenv("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference").strip()
CACHE_DIR = ROOT / ".cache" / "tts"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
CALL_LOG = ROOT / ".cache" / "gnani_calls.jsonl"


def log_call(service: str, **info: Any) -> None:
    """Append one line per REAL Gnani request so the UI can show proof of usage."""
    try:
        CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CALL_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"t": time.strftime("%H:%M:%S"), "service": service, **info},
                                    ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_call_log(limit: int = 20) -> list[dict]:
    if not CALL_LOG.exists():
        return []
    rows = []
    for line in CALL_LOG.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _api_error(response: requests.Response, service: str) -> RuntimeError:
    """Readable error that includes Gnani's own message (401/402/403/429 etc.)."""
    hint = {401: "API key missing/invalid", 402: "insufficient credits", 403: "key lacks scope or credits",
            429: "rate limited (1 active request at a time)"}.get(response.status_code, "")
    return RuntimeError(f"Gnani {service} HTTP {response.status_code} {hint}: {(response.text or '')[:300]}")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _secret(name: str) -> str:
    value = _env(name) or _env("GNANI_API_KEY")
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your local .env file.")
    return value


def _dry_run() -> bool:
    return _env("DRY_RUN", "0") == "1"


def _lang_short(language_code: str, transcript: str = "") -> str:
    code = (language_code or "").lower()
    if code.startswith("hi"):
        return "hi"
    if code.startswith("en"):
        return "en"
    return "hi" if re.search(r"[\u0900-\u097f]", transcript or "") else "en"


def _silent_wav(seconds: float = 0.25, sample_rate: int = 24000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * int(sample_rate * seconds))
    return output.getvalue()


def _wav_duration(wav_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            if sample_rate <= 0:
                raise ValueError("Invalid WAV sample rate")
            return wav_file.getnframes() / sample_rate
    except (wave.Error, EOFError) as exc:
        raise ValueError("Prisma expects WAV audio bytes from the microphone.") from exc


def _post_with_retry(url: str, *, attempts: int = 3, **kwargs: Any) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(url, **kwargs)
            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            last_error = RuntimeError(f"HTTP {response.status_code}: {(response.text or '')[:250]}")
        except requests.RequestException as exc:
            last_error = exc
        if attempt < attempts - 1:
            time.sleep(1.0 * (2 ** attempt))
    raise RuntimeError(f"Gnani request failed after {attempts} attempts: {last_error}") from last_error


def _clean_keyterms(keyterms: list[str] | None) -> str | None:
    if not keyterms:
        return None
    terms: list[str] = []
    seen: set[str] = set()
    for term in keyterms:
        value = str(term).strip()
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            terms.append(value)
        if len(terms) >= 200:
            break
    return json.dumps(terms, ensure_ascii=False) if terms else None


def transcribe(
    wav_bytes: bytes,
    keyterms: list[str] | None = None,
    model: str | None = None,
    language_code: str | None = None,
) -> dict[str, str]:
    """Transcribe a <=30-second Hindi/Hinglish/English WAV clip with Prisma v3.0.

    Prisma v2.5 is retried only when the service specifically rejects the v3 model.
    """
    if not wav_bytes:
        raise ValueError("Audio input is empty.")
    model = model or _env("PRISMA_STT_MODEL", "prisma-v3.0")
    # Current Prisma v3 REST uses language_code=indic-auto plus multi_lang_codes
    # as the 2-4 language candidates. The public project contract still calls
    # these user-supplied values "keyterms"; Gnani's current REST field is "keywords".
    language_code = language_code or _env("PRISMA_LANGUAGE_CODE", "hi-IN,en-IN")
    if _dry_run():
        return {"text": "पीएम किसान में कौन आवेदन कर सकता है?", "lang": "hi",
                "detected_language_code": "hi-IN", "request_id": "dry-run"}

    duration = _wav_duration(wav_bytes)
    if duration > 30.0:
        raise ValueError(f"Please record a question of 30 seconds or less (received {duration:.1f}s).")

    data: dict[str, str] = {
        "model": model,
        "language_code": language_code,
        "format": "transcribe",
    }
    keyterms_value = _clean_keyterms(keyterms)
    if keyterms_value:
        # Documented REST field for Prisma v3.0 is `keyterms` (JSON array, up to 200).
        data["keyterms"] = keyterms_value
    headers = {"X-API-Key-ID": _secret("GNANI_STT_API_KEY")}
    response = _post_with_retry(
        STT_URL, headers=headers,
        files={"audio_file": ("question.wav", wav_bytes, "audio/wav")},
        data=data, timeout=(15, 60),
    )
    used_v25_fallback = False

    # The project synopsis specifies Prisma v2.5 as a model fallback by omitting `model`.
    # Fall back to v2.5 ONLY when Gnani says the model name itself is invalid.
    model_rejected = response.status_code == 400 and "INVALID_MODEL" in (response.text or "")
    if model_rejected and _env("PRISMA_V25_FALLBACK", "1") == "1":
        # Prisma v2.5 does not support indic-auto, language candidates, or v3 keywords.
        # Its fallback language therefore must be configured explicitly.
        fallback_language = _env("PRISMA_V25_LANGUAGE_CODE", "hi-IN")
        fallback_data = {"language_code": fallback_language, "format": "transcribe"}
        response = _post_with_retry(
            STT_URL, headers=headers,
            files={"audio_file": ("question.wav", wav_bytes, "audio/wav")},
            data=fallback_data, timeout=(15, 60),
        )
        used_v25_fallback = True

    if not response.ok:
        raise _api_error(response, "Prisma STT")
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Prisma returned non-JSON data: {(response.text or '')[:250]}") from exc
    if not body.get("success"):
        raise RuntimeError(f"Prisma STT failed: {body.get('error') or body}")
    transcript = str(body.get("transcript") or body.get("text") or "").strip()
    if not transcript:
        raise RuntimeError(f"Prisma response did not contain a transcript: {body}")
    detected = str(body.get("detected_language_code") or "")
    if not detected:
        detected = (fallback_language if used_v25_fallback
                    else ("hi-IN" if _lang_short("", transcript) == "hi" else "en-IN"))
    log_call("STT", model=str(body.get("model") or model), request_id=str(body.get("request_id") or ""),
             seconds=round(duration, 1))
    return {
        "text": transcript,
        "lang": _lang_short(detected, transcript),
        "detected_language_code": detected,
        "request_id": str(body.get("request_id") or ""),
    }


def _say_number(value: str, lang: str) -> str:
    try:
        from num2words import num2words
        number = float(value.replace(",", "")) if "." in value else int(value.replace(",", ""))
        return num2words(number, lang="hi" if lang == "hi" else "en")
    except Exception:
        return value


def prep_for_tts(text: str, lang: str = "hi") -> str:
    """Expand currency and numeric values into spoken words before sending to Timbre."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    lang = "hi" if str(lang).lower().startswith("hi") else "en"
    currency_word = "रुपये" if lang == "hi" else "rupees"
    currency = re.compile(r"(?:₹|\bRs\.?\s*|\bINR\s*)(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
    text = currency.sub(lambda match: f"{_say_number(match.group(1), lang)} {currency_word}", text)
    text = re.sub(r"\b\d[\d,]*(?:\.\d+)?\b",
                  lambda match: _say_number(match.group(0), lang), text)
    return re.sub(r"\s+", " ", text).strip()


def speak(text: str, lang: str = "hi", *, use_cache: bool | None = None) -> bytes:
    """Speak text with Gnani Timbre v2.5 and return validated WAV bytes."""
    lang = "hi" if str(lang).lower().startswith("hi") else "en"
    speech_text = prep_for_tts(text, lang)
    if not speech_text:
        raise ValueError("Timbre received empty text.")
    if _dry_run():
        return _silent_wav()
    if use_cache is None:
        use_cache = _env("TTS_CACHE", "1") != "0"

    cache_key = hashlib.sha256(f"timbre-v2.5|{lang}|{speech_text}".encode("utf-8")).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.wav"
    if use_cache and cache_file.exists():
        cached = cache_file.read_bytes()
        if cached[:4] == b"RIFF" and cached[8:12] == b"WAVE":
            return cached
        cache_file.unlink(missing_ok=True)

    voice, locale = ("Nalini", "hi-IN") if lang == "hi" else ("Kaveri", "en-IN")
    payload = {
        "text": speech_text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": locale,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 24000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }
    response = _post_with_retry(
        TTS_URL,
        headers={"X-API-Key-ID": _secret("GNANI_TTS_API_KEY"), "Content-Type": "application/json"},
        json=payload, timeout=(15, 60),
    )
    if not response.ok:
        raise _api_error(response, "Timbre TTS")
    audio = response.content
    if not audio or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise RuntimeError(
            "Timbre did not return WAV audio. "
            f"Content-Type={response.headers.get('Content-Type', 'unknown')}"
        )
    log_call("TTS", voice=voice, chars=len(speech_text))
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(audio)
    return audio
