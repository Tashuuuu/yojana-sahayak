# Yojana Sahayak — Voice Edition

**Ask in Hindi, Hinglish or English. Hear only what's verified.**

Yojana Sahayak is a voice-first assistant for Indian government welfare schemes. It answers from official scheme text, checks every sentence of its own answer, and speaks only the sentences that pass the check. If an answer cannot be verified, it says so instead of guessing.

Built by **Akriti Sengar** and **Bhawna Rani** for the Gnani AI challenge.

> Yojana Sahayak is an independent educational information assistant. It is not a government website or service. Scheme rules and eligibility can change, so always confirm details on the linked official source before applying.

## Why this exists

A language model can sound confident and still be wrong. For welfare schemes, a wrong answer about who is eligible or how much is paid can cost someone a benefit. This project adds a verification step between the model and the user, so only answers that are supported by official text are read out.

## How it works

```
Voice or text question
        |
        v
Gnani Prisma v3.0 (speech to text)
        |
        v
multilingual-e5-base embeddings  -->  FAISS search over official
                                      bilingual scheme sections
        |
        v
Open-weight Llama writes a short answer from the retrieved text
        |
        v
mDeBERTa-v3 NLI checks each sentence against the retrieved text
        |
        +--> Supported sentences  --> Gnani Timbre v2.5 speaks them
        |
        +--> Not verified         --> fixed safe fallback message
```

1. **Speech to text.** Gnani Prisma v3.0 transcribes the question. Prisma v2.5 is the documented fallback when v3 is unavailable. The REST call uses `language_code=indic-auto`, `multi_lang_codes=hi-IN,en-IN` and `keywords` (called `keyterms` inside the project).
2. **Retrieval.** `intfloat/multilingual-e5-base` embeds the question (`query:` prefix) and the scheme sections (`passage:` prefix). A FAISS `IndexFlatIP` index over normalised embeddings returns the best-matching official sections in English and Hindi.
3. **Answer generation.** An open-weight Llama model writes a short answer using only the retrieved sections. Primary design: Llama through Groq. Permitted open-weight fallback: local Ollama with Llama 3.1 8B. The other synopsis-approved fallback is Gemini through Google AI Studio, which is **not** open-weight and must be disclosed if used.
4. **Verification.** `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` checks every sentence of the answer against the retrieved text. Each sentence gets a label, and the answer gets an overall groundedness score.
5. **Speech output.** Gnani Timbre v2.5 speaks only the sentences labelled **Supported**, using Nalini (`hi-IN`) for Hindi and Kaveri (`en-IN`) for English.
6. **Safe fallback.** If the answer cannot be verified, the app shows and speaks: *"I could not verify a complete answer from the available official sources. Please check the scheme's official website."*

## What you see in the app

- Voice input or typed questions, in English or Hindi, with a language toggle and dark mode
- The transcript, marked "Asked by voice" when a question was spoken
- A verified or "couldn't verify" label on every answer
- The groundedness score and a per-sentence check (Supported / Unsupported / Contradicted)
- The official scheme sections the answer was built from, each with a link to the official source
- Audio playback of verified answers (WAV)

## Tech stack

| Part | Tool |
|---|---|
| Speech to text | Gnani Prisma v3.0 (v2.5 fallback) |
| Embeddings | `intfloat/multilingual-e5-base` |
| Vector search | FAISS `IndexFlatIP` |
| Answer generation | Llama via Groq (Ollama Llama 3.1 8B fallback) |
| Verification | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` |
| Text to speech | Gnani Timbre v2.5 (Nalini `hi-IN`, Kaveri `en-IN`) |
| Interface | Streamlit |

## Project structure

```
app.py            Streamlit app
src/              ingestion, retrieval, generation, verification, speech
data/             official scheme records (see data/SCHEME_DATA_FORMAT.md)
index/            FAISS index files
eval/             evaluation questions and scripts
scripts/          helper scripts, including real_smoke.py
tests/            offline unit tests
results/          evaluation outputs
assets/           images used by the app
```

## Run locally

1. Use Python 3.11 or 3.12 and install the requirements:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and enter your Gnani and Groq credentials.
3. Make sure `data/schemes.jsonl` contains official English and Hindi records. The format is described in `data/SCHEME_DATA_FORMAT.md`.
4. Build the index and test retrieval:
   ```
   python -m src.ingest
   python -m src.retrieve
   ```
5. Run the offline tests:
   ```
   python -m pytest -q
   ```
6. Run one real speech-to-text and text-to-speech smoke test. Read the confirmation prompt first, because it makes real API calls:
   ```
   python scripts/real_smoke.py
   ```
7. Start the app:
   ```
   streamlit run app.py
   ```

Note: Groq's free Developer access no longer includes Llama 3.3 70B. Check which Llama models your account can use, or switch to the Ollama fallback.

## Evaluation and limits

- Retrieval, answer verification and speech output are working end to end in the demo.
- Formal evaluation numbers (retrieval quality, verifier precision and recall, response time) are not reported here yet. They will be added only after being measured on the final data with the final code. Run `python -m eval.validate_scope` to check the data and question split before measuring.
- A high groundedness score means the answer matches the retrieved official text. It does not guarantee that the scheme rules are current. The source text is only as up to date as the data in `data/`.
- Scheme coverage is limited to the records in `data/`. Questions outside that coverage should return the safe fallback, not a guess.
- The verifier is an NLI model. It can make mistakes, especially on Hindi sentences and on numbers.

## Team

- Akriti Sengar
- Bhawna Rani

## License

MIT. See [LICENSE](LICENSE).
