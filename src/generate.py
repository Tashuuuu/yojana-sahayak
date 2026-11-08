# writes a short answer using ONLY the retrieved text (via Groq's free API)
import os

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


def generate_answer(query: str, chunks: list[dict], lang: str) -> str:
    """Return a short answer from the chunks, or the text NO_ANSWER."""
    if DRY_RUN:
        if "आवेदन" in query or "apply" in query.lower() or "eligible" in query.lower():
            return ("पात्र किसान परिवारों को हर साल छह हज़ार रुपये मिलते हैं।" if lang == "hi"
                    else "Eligible farmer families receive six thousand rupees per year.")
        return "NO_ANSWER"

    lang_name = "Hindi (Devanagari script)" if lang == "hi" else "English"
    context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(lang_name=lang_name)},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"},
    ]
    result = _get_client().chat.completions.create(
        model=MODEL, messages=messages, temperature=0, max_tokens=250)
    return result.choices[0].message.content.strip()