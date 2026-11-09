# Yojana Sahayak — Voice Edition

**Ask in Hindi, Hinglish or English. Hear only what's verified.**

A voice-first assistant for Indian government welfare schemes. Gnani Prisma v3.0 transcribes the user's question; multilingual E5 and FAISS retrieve official bilingual scheme sections; an open-weight Llama model generates a short answer; mDeBERTa-v3 NLI checks each sentence; and Gnani Timbre v2.5 speaks only sentences labelled **Supported**. When the answer cannot be verified, the system speaks a fixed safe fallback.

## Required components

- Gnani Prisma v3.0 STT; Prisma v2.5 is the documented fallback when v3 is unavailable. The current REST contract uses `language_code=indic-auto`, `multi_lang_codes=hi-IN,en-IN`, and `keywords` (the project-facing argument is called `keyterms`).
- `intfloat/multilingual-e5-base` with E5 `query:` and `passage:` prefixes.
- FAISS `IndexFlatIP` over normalized embeddings.
- Open-weight Llama through Groq as the primary design; local Ollama Llama 3.1 8B is an explicitly permitted open-weight fallback. Current Groq Developer/free access no longer includes Llama 3.3 70B; check account access. The other synopsis-approved fallback is Gemini via Google AI Studio (not open-weight, so disclose it).
- `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` for sentence-level verification.
- Gnani Timbre v2.5 with Nalini (`hi-IN`) and Kaveri (`en-IN`).
- Streamlit for voice input, transcript, answer labels, official sources and WAV playback.

## Run locally

1. Use Python 3.11 or 3.12 and install `requirements.txt`.
2. Copy `.env.example` to `.env`; enter Gnani and Groq credentials.
3. Ensure `data/schemes.jsonl` contains official English and Hindi records. See `data/SCHEME_DATA_FORMAT.md`.
4. Run `python -m src.ingest` and `python -m src.retrieve`.
5. Run `python -m pytest -q` for offline/unit tests.
6. Run one real STT/TTS smoke test with `python scripts/real_smoke.py` after reviewing that script's confirmation prompt.
7. Launch with `streamlit run app.py`.

## Data and evaluation limits

The repository snapshot used to prepare this code has only two schemes and six English sections. The intended scope requires 20 schemes in both English and Hindi and a 40-question evaluation split of 30 answerable / 10 unanswerable. The code supports that structure, but the missing official scheme texts and corrected question labels must be supplied by the team. Run `python -m eval.validate_scope` to check the final data before reporting results.

Do not claim 20 schemes, 30/10 evaluation, verifier precision/recall, or latency figures until the data and corresponding real measurements exist. Existing `results/` files are historical and must be regenerated after the final code/data are in place.
