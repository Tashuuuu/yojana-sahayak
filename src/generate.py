# writes a short answer using ONLY the retrieved text (via Groq's free API)
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = (
    "You answer questions about Indian government welfare schemes. "
    "Use ONLY the CONTEXT below. If the CONTEXT does not contain the answer, reply with exactly: NO_ANSWER. "
    "Answer in {lang_name}. Use at most 3 short sentences. Each sentence must be a plain factual statement "
    "that is directly stated in the CONTEXT. Do not add advice, opinions, or facts from memory. "
    "Write amounts in words (for example 'six thousand rupees') so they can be read aloud."
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


def generate_answer(query: str, chunks: list[dict], lang: str) -> str:
    """Return a short answer from the chunks, or the text NO_ANSWER."""
    if DRY_RUN:
        # Fake LLM: use the first sentence of the best chunk (same language if possible).
        # Always grounded in real data, so it works in English and Hindi.
        if not chunks:
            return "NO_ANSWER"
        same_lang = [c for c in chunks if c.get("lang") == lang]
        best = (same_lang or chunks)[0]
        return _first_sentence(best["text"]) or "NO_ANSWER"

    lang_name = "Hindi (Devanagari script)" if lang == "hi" else "English"
    context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(lang_name=lang_name)},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"},
    ]
    result = _get_client().chat.completions.create(
        model=MODEL, messages=messages, temperature=0, max_tokens=250)
    return result.choices[0].message.content.strip()