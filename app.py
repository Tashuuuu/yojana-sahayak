"""Streamlit UI for Yojana Sahayak Voice Edition with evidence diagnostics."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

from src.pipeline import answer_audio, answer_question  # noqa: E402
from src.voice import read_call_log  # noqa: E402

st.set_page_config(page_title="Yojana Sahayak — Voice Edition", page_icon="🎙️", layout="wide")
st.title("Yojana Sahayak — Voice Edition")
st.caption("Ask about government schemes in Hindi, Hinglish or English. Answers are checked against retrieved source text.")

is_dry_run = os.getenv("DRY_RUN", "0").strip() == "1"
with st.sidebar:
    st.subheader("Runtime mode")
    if is_dry_run:
        st.warning("DRY RUN is ON. No Gnani or LLM API calls are made. Voice and answers are simulated from local source text.")
    else:
        st.success("DRY RUN is OFF. A voice question sends audio to Gnani Prisma STT. Timbre is called only when audio output is enabled and is not served from cache.")
    def _has(name: str) -> str:
        return "set" if os.getenv(name, "").strip() and "your_" not in os.getenv(name, "") else "MISSING"
    st.caption(
        f"DRY_RUN={os.getenv('DRY_RUN', '0')!r} · Gnani STT key: {_has('GNANI_STT_API_KEY')} · "
        f"Gnani TTS key: {_has('GNANI_TTS_API_KEY')} · Groq key: {_has('GROQ_API_KEY')}"
    )
    typed_language = st.radio("Typed question language", ["Hindi", "English"], horizontal=True)
    generate_audio = st.checkbox("Speak the verified answer (Gnani Timbre TTS)", value=True)
    fresh_tts = st.checkbox("Always call Timbre (ignore audio cache)", value=True,
                            help="Cached audio costs no credits, so a repeated question will not reduce your balance.")
    os.environ["TTS_CACHE"] = "0" if fresh_tts else "1"
    st.caption("Gnani credits are spent ONLY by: (1) a recorded voice question (Prisma STT) and (2) spoken answers (Timbre TTS). "
               "Typed questions with audio off use Groq only, never Gnani.")
    with st.expander("Real Gnani calls made by this app"):
        calls = read_call_log()
        if not calls:
            st.write("No real Gnani request has been made yet.")
        for row in reversed(calls):
            st.write(row)
    st.divider()
    st.subheader("About this assistant")
    st.write("The application retrieves official scheme passages, generates an answer from that evidence, then checks each sentence with multilingual NLI.")
    st.caption("Informational only. Confirm current eligibility and benefits on the linked official source.")


def render_result(result: dict) -> None:
    transcript = result.get("transcription")
    if transcript:
        st.markdown("#### Speech transcript")
        st.write(transcript.get("text", ""))
        st.caption(f"Detected language: {transcript.get('detected_language_code', 'unknown')}")
        request_id = transcript.get("request_id", "")
        if request_id == "dry-run":
            st.caption("STT mode: simulated; no Prisma request was sent.")
        elif request_id:
            st.caption(f"Gnani Prisma request ID: `{request_id}`")
        else:
            st.caption("No Prisma request ID was returned. Check the Gnani dashboard/API logs to confirm usage.")

    diagnostics = result.get("retrieval_diagnostics", {})
    if diagnostics:
        languages = ", ".join(diagnostics.get("languages_found", [])) or "none"
        st.caption(
            f"Retrieved {diagnostics.get('chunks_used', 0)} evidence chunks · "
            f"source languages: {languages} · "
            f"best similarity: {diagnostics.get('best_similarity', 0):.3f}"
        )
        requested_lang = result.get("lang")
        if diagnostics.get("chunks_used") and requested_lang not in diagnostics.get("languages_found", []):
            source_language = result.get("verification_language", "the retrieved source language")
            if result.get("answer_translated"):
                st.info(
                    f"No {requested_lang.upper()} source passage is available yet. The answer was generated and "
                    f"verified against {source_language.upper()} official text first, then translated. "
                    "Add verified Hindi scheme records to improve direct Hindi retrieval."
                )
            elif result.get("translation_failed"):
                st.warning(
                    f"Only {source_language.upper()} source text is available. The facts were checked, "
                    "but the Hindi translation did not pass validation, so it was withheld."
                )
            else:
                st.info(
                    f"Only {source_language.upper()} source text is available. A complete answer could not be "
                    "verified, so the assistant withheld it. Add verified Hindi records for direct Hindi retrieval."
                )

    status = result.get("status", "refused")
    if status == "verified":
        st.success("Verified answer")
    elif status == "partial":
        st.warning("Partially verified — unsupported sentences were withheld")
    else:
        st.error("Unable to verify a complete answer from the available sources")

    st.markdown("#### Answer (verified content only)")
    if result.get("answer") and result.get("answer") != "NO_ANSWER":
        st.write(result["answer"])
    else:
        st.write(result.get("spoken_text", ""))
    if result.get("answer_translated"):
        st.caption(
            f"The answer was verified against {result.get('verification_language', 'source-language').upper()} "
            "official text before translation into your selected language."
        )
    if result.get("answer_reason"):
        st.info(result["answer_reason"])

    verification_language = result.get("verification_language", result.get("lang", "en"))
    st.markdown(f"#### Sentence-level verification ({verification_language.upper()} source-language checks)")
    labels = result.get("verification", {}).get("sentences", [])
    if labels:
        for index, item in enumerate(labels, start=1):
            label = item.get("label", "Unsupported")
            line = f"{index}. {label.upper()} — {item.get('text', '')}"
            if label == "Supported":
                st.success(line)
            elif label == "Contradicted":
                st.error(line)
            else:
                st.warning(line)
    else:
        st.caption("No generated factual sentence was available to verify.")

    st.metric("Groundedness", f"{100 * result.get('verification', {}).get('groundedness', 0):.1f}%")
    st.markdown("#### What the assistant will speak")
    st.write(result.get("spoken_text", ""))
    audio = result.get("spoken_audio")
    if audio:
        st.audio(audio, format="audio/wav")
    elif generate_audio:
        st.caption("No audio was returned.")
    else:
        st.caption("Audio generation was not requested. Enable it in the sidebar when you are ready to test Timbre.")

    st.markdown("#### Official sources")
    seen_urls: set[str] = set()
    for chunk in result.get("chunks", []):
        url = chunk.get("source_url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            scheme = chunk.get("name_en") or chunk.get("scheme_id", "Scheme")
            section = chunk.get("section", "")
            st.markdown(f"- [{scheme} — {section}]({url})")
    if not seen_urls:
        st.caption("No source was retrieved for this question.")

    with st.expander("Inspect retrieved evidence (important for debugging)"):
        evidence = result.get("chunks", []) or result.get("retrieved_candidates", [])
        if not evidence:
            st.write("No evidence chunks were retrieved.")
        for rank, chunk in enumerate(evidence, start=1):
            title = (
                f"{rank}. {chunk.get('name_en') or chunk.get('scheme_id', 'Scheme')} · "
                f"{chunk.get('section', 'Section')} · {str(chunk.get('lang', '')).upper()} · "
                f"score {float(chunk.get('similarity_score', chunk.get('score', 0))):.3f}"
            )
            with st.expander(title):
                st.write(chunk.get("text", ""))
                if chunk.get("source_url"):
                    st.markdown(f"[Open source]({chunk['source_url']})")

    with st.expander("Processing latency and request details"):
        st.json({
            "latency_seconds": result.get("latency", {}),
            "retrieval_diagnostics": diagnostics,
            "verification_language": result.get("verification_language"),
            "answer_translated": result.get("answer_translated"),
            "draft_answer_not_displayed_as_verified": result.get("draft_answer"),
            "supported_source_answer": result.get("supported_source_answer"),
        })


st.markdown("### Ask by voice")
st.caption("Record a question of 30 seconds or less. With DRY_RUN=0, submitting a recording sends it to Gnani Prisma STT.")
voice_clip = st.audio_input("Record your scheme question")
if st.button("Process voice question", type="primary", disabled=voice_clip is None):
    try:
        with st.spinner("Transcribing and checking official scheme evidence..."):
            result = answer_audio(voice_clip.getvalue(), make_audio=generate_audio)
        st.session_state["last_result"] = result
    except Exception as exc:
        st.error(f"Voice request failed: {exc}")

st.divider()
st.markdown("### Or type a question")
question = st.text_input("Your question", placeholder="PM-KISAN योजना के बारे में बताइए")
if st.button("Get verified answer"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            language = "hi" if typed_language == "Hindi" else "en"
            with st.spinner("Retrieving evidence, generating an answer and checking each sentence..."):
                result = answer_question(question, lang=language, make_audio=generate_audio)
            st.session_state["last_result"] = result
        except Exception as exc:
            st.error(f"Question processing failed: {exc}")

if st.session_state.get("last_result"):
    st.divider()
    render_result(st.session_state["last_result"])
