# Yojana Sahayak UI concepts

Open `index.html` in a browser to compare the three static concepts. No server or dependencies are required. The prototypes are illustrative only: their microphone, chat actions, playback, and answers are not connected to Streamlit, Gnani, or the answer pipeline.

## Concepts

- `voice-first.html`: puts speech input, transcript correction, answer playback, verification, and evidence at the center.
- `chat-evidence.html`: keeps a conversation view and exposes retrieved evidence and answer states alongside it.
- `scheme-finder.html`: makes topic shortcuts and popular questions the entry point, then shows an answer with evidence.

All three have responsive layouts, a light/dark toggle, language selector mockup, sample verified answer, and source/evidence presentation. The sample answer and source excerpt are placeholders for design discussion, not verified project output.

## Current app capability map (from `src/app.py` and supporting modules)

| Capability | Current implementation | UI implication |
|---|---|---|
| Typed questions | `st.chat_input` and quick-prompt buttons in `app.py` | Keep text as a first-class fallback to voice. |
| Voice question capture | `st.audio_input`; audio is deduplicated by SHA-256 before submission | Give recording and submit states clear feedback. |
| Speech transcription | `voice.transcribe()` uses Gnani Prisma; detected language is passed to the pipeline | Show the recognized transcript and offer correction before answering. Current UI displays it only transiently. |
| Language choice | English/Hindi selector; voice input can use detected language | Keep language visible; do not promise Hinglish output as a separate language until supported. |
| Retrieval | `retrieve()` returns up to four ranked scheme chunks with similarity scores and source metadata | Present source name, section, excerpt, and official URL. Similarity scores need not be shown to ordinary users. |
| Answer generation | `generate_answer()` uses retrieved context and can return `NO_ANSWER` | Distinguish a generated answer from a safe refusal. |
| Groundedness checks | `verify_answer()` labels each sentence Supported, Unsupported, or Contradicted and returns a groundedness fraction | Show sentence labels accessibly; avoid relying on color alone. |
| Speak-only-verified gate | `pipeline.answer_question()` refuses mixed/unsupported answers and translates supported text for Hindi | Explain why audio is absent when an answer is refused or partial. |
| Speech output | `voice.speak()` selects Hindi Nalini or English Kaveri and caches WAV output | Put playback beside the answer; show a helpful unavailable state if TTS fails. |
| Supporting passages | Current UI has an expander with retrieved chunk text and source links | Surface the best evidence without forcing users to open a technical panel. |
| Verification detail | Current UI has a per-sentence verification expander and groundedness score | Keep a concise status visible, with details expandable. |
| Conversation state | Streamlit session state keeps question/answer turns for the active session | Chat layout can support follow-up questions; new-chat clears this state. |
| Read-aloud preference | Toggle controls whether the UI calls TTS for verified answers | Preserve a visible, understandable preference control. |
| New chat | Clears stored messages and audio dedupe hash | Retain a clear reset action. |
| Failure handling | Pipeline refusals and exceptions produce user-facing messages; diagnostics are stored separately | Make recovery guidance clear without exposing raw errors. |
| Technical diagnostics | Latency stages are available in the assistant message | Keep timing and model diagnostics out of the main user journey; expose for demo/review if needed. |

## Scope notes discovered in code

- The current page has functional quick prompts, but the category cards are decorative HTML with no click action.
- The current `app.py` includes both `st.audio_input` and `st.chat_input`; typed input is anchored at the bottom while voice input sits in the page body.
- The pipeline currently translates Hindi questions to English and retrieves English chunks. Hindi generated speech is translated after verification. The UI should present this accurately.
- The synopsis describes Hindi/English scheme text and Hinglish speech, but the current retrieval pipeline explicitly requests English chunks. Confirm this before presenting bilingual source retrieval as implemented.
- The current CSS hard-codes light colors for the app and native Streamlit elements. The theme buttons in these mockups are concept previews; they do not change the Streamlit app.
