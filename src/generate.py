# writes a short answer using ONLY the retrieved text (via Groq's free API)
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")  # llama-3.3-70b-versatile was shut down by Groq

SYSTEM_PROMPT = (
    "You answer questions about Indian government welfare schemes. "
    "Use ONLY the CONTEXT below. "
    "Copy the wording of the CONTEXT as closely as possible. Do not paraphrase and do not reword facts. "
    "If the CONTEXT is about the topic of the question, answer with what it says, even if it answers only part of the question. "
    "Reply with exactly NO_ANSWER only if the CONTEXT has nothing relevant to the question. "
    "Answer in {lang_name}. Use at most 3 short sentences. "
    "Each sentence must make sense on its own (do not start with 'these' or 'they'). "
    "Do not add advice, opinions, steps, documents or facts from memory. "
    "Write numbers, dates and amounts exactly as they appear in the CONTEXT (keep digits as digits; "
    "do not spell them out in words)."
)

_client = None


def _get_client():
    """Create the Groq client the first time it is needed."""
    global _client
    if _client is None:
        _client = OpenAI(base_url="https://api.groq.com/openai/v1",
                         api_key=os.environ["GROQ_API_KEY"])
    return _client


def _first_sentence(text: str) -> str:
    """First sentence of a text (splits on . ! ? and the Hindi danda)."""
    parts = re.split(r"(?<=[.!?।])\s+", text.strip())
    return parts[0].strip() if parts else ""


def _ask(system: str, user: str, max_tokens: int = 2000) -> str:
    """One call to the LLM. gpt-oss models 'think' first, so give room and keep it fast."""
    extra = {"reasoning_effort": "low"} if "gpt-oss" in MODEL else {}
    result = _get_client().chat.completions.create(
        model=MODEL, temperature=0, max_tokens=max_tokens, **extra,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    text = (result.choices[0].message.content or "").strip()
    return text.replace("\u2011", "-")  # model sometimes uses non-breaking hyphens


def generate_answer(query: str, chunks: list[dict], lang: str) -> str:
    """Return a short answer from the chunks, or the text NO_ANSWER."""
    if DRY_RUN:
        # Fake LLM: first sentence of the best chunk (same language if possible).
        if not chunks:
            return "NO_ANSWER"
        same_lang = [c for c in chunks if c.get("lang") == lang]
        best = (same_lang or chunks)[0]
        return _first_sentence(best["text"]) or "NO_ANSWER"

    lang_name = "Hindi (Devanagari script)" if lang == "hi" else "English"
    context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in chunks)
    return _ask(SYSTEM_PROMPT.format(lang_name=lang_name),
                f"CONTEXT:\n{context}\n\nQUESTION: {query}")


def translate(text: str, lang: str) -> str:
    """Translate verified English text to Hindi for speech. English passes through."""
    if lang != "hi" or DRY_RUN or not text.strip():
        return text
    out = _ask(
        "Translate the user's text into simple spoken Hindi (Devanagari script). "
        "Keep the meaning exactly the same. Do not add, remove or explain anything. "
        "Output only the translation.", text)
    return out or text



def to_english(text: str) -> str:
    """Translate Hindi questions while preserving official scheme names."""
    if DRY_RUN or not text.strip():
        return text

    # Preserve official English names of schemes that were mistranslated.
    scheme_names = {
        "प्रधानमंत्री सुरक्षा बीमा योजना":
            "Pradhan Mantri Suraksha Bima Yojana (PMSBY)",
        "राष्ट्रीय साधन-सह-योग्यता छात्रवृत्ति योजना":
            "National Means-cum-Merit Scholarship Scheme (NMMS)",
    }

    translated_input = text
    for hindi_name, official_name in scheme_names.items():
        translated_input = translated_input.replace(
            hindi_name, official_name
        )

    try:
        out = _ask(
            "Translate the user's question from Hindi into clear English. "
            "Preserve official scheme names, their English spellings, "
            "and abbreviations exactly as provided. Never translate "
            "or rename an official scheme name. "
            "Output only the English translation.",
            translated_input,
            max_tokens=500
        )
        return out or translated_input
    except Exception:
        return translated_input
