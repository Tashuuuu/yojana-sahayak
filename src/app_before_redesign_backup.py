import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.pipeline import answer_question
from src.voice import transcribe, speak


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Yojana Sahayak",
    page_icon="🇮🇳",
    layout="wide",
)

# --------------------------------------------------
# STYLING
# --------------------------------------------------

st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}
.main-title {
    font-size: 2.3rem;
    font-weight: 700;
    color: #17365D;
    margin-bottom: 0;
}
.subtitle {
    color: #64748b;
    font-size: 1rem;
    margin-top: 5px;
}
.info-box {
    background-color: #eef5ff;
    padding: 14px;
    border-radius: 10px;
    border-left: 4px solid #2563eb;
    margin: 15px 0;
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<div class="main-title">🇮🇳 Yojana Sahayak</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Your bilingual assistant for Indian government welfare schemes'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()

st.markdown("""
<div class="info-box">
<b>Welcome!</b> Ask questions about Indian government welfare schemes
in English or Hindi. You can type your question or use your microphone.
Answers are checked against retrieved government-source passages.
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_audio_name" not in st.session_state:
    st.session_state.last_audio_name = None


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("About")

    st.write(
        "Yojana Sahayak helps users understand Indian government "
        "welfare schemes through multilingual retrieval, "
        "AI-generated answers, answer verification and voice interaction."
    )

    st.divider()

    st.subheader("Capabilities")
    st.write("✅ English and Hindi questions")
    st.write("✅ Multilingual semantic retrieval")
    st.write("✅ FAISS similarity search")
    st.write("✅ AI-generated answers")
    st.write("✅ NLI-based answer verification")
    st.write("✅ Speech-to-text")
    st.write("✅ Text-to-speech")

    st.divider()

    speak_answers = st.checkbox(
        "Speak verified answers",
        value=True,
    )

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_audio_name = None
        st.rerun()


# --------------------------------------------------
# DISPLAY CONVERSATION HISTORY
# --------------------------------------------------

def show_sources(chunks):
    if not chunks:
        return

    with st.expander("View supporting source passages"):
        for rank, chunk in enumerate(chunks, start=1):
            name = chunk.get("name_en", chunk.get("scheme_id", "Scheme"))

            st.markdown(
                f"**Source {rank}: {name} — {chunk.get('section', 'Overview')}**"
            )

            st.write(chunk.get("text", ""))

            score = chunk.get("similarity_score")
            if score is not None:
                st.caption(f"Similarity score: {score:.4f}")

            source_url = chunk.get("source_url", "")
            if source_url:
                st.markdown(f"[View official source]({source_url})")

            if rank < len(chunks):
                st.divider()


def show_message(message):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            status = message.get("status")

            if status == "verified":
                st.success("Answer verified against retrieved evidence.")
            elif status == "partial":
                st.warning("The generated answer was not fully supported.")
            else:
                st.warning("A verified answer could not be produced.")

            show_sources(message.get("chunks", []))

            audio_bytes = message.get("audio")
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")


for message in st.session_state.messages:
    show_message(message)


# --------------------------------------------------
# PROCESS QUESTION
# --------------------------------------------------

def process_question(question, lang, audio_input=False):

    question = (question or "").strip()

    if not question:
        st.warning("Please enter or record a question.")
        return

    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        try:
            with st.spinner("Searching, generating and verifying your answer..."):
                result = answer_question(question, lang=lang, k=4)

            status = result.get("status", "refused")
            chunks = result.get("chunks", [])

            answer_text = result.get("spoken_text", "")

            if status == "verified":
                st.success("Verified answer")
                st.markdown(answer_text)
            elif status == "partial":
                st.warning("The answer could not be fully verified.")
                st.markdown(answer_text)
            else:
                st.warning("I could not verify an answer from the available sources.")
                st.markdown(answer_text)

            show_sources(chunks)

            # Show verification details
            verification = result.get("verification", {})
            sentences = verification.get("sentences", [])

            if sentences:
                with st.expander("Answer verification details"):
                    for sentence in sentences:
                        label = sentence.get("label", "Unknown")
                        text = sentence.get("text", "")

                        if label == "Supported":
                            st.write(f"✅ **{label}:** {text}")
                        else:
                            st.write(f"⚠️ **{label}:** {text}")

                    groundedness = verification.get("groundedness")
                    if groundedness is not None:
                        st.caption(
                            f"Groundedness score: {groundedness:.2f}"
                        )

            # Generate speech only for verified answers
            audio_bytes = None

            if speak_answers and status == "verified" and answer_text:
                try:
                    with st.spinner("Generating spoken answer..."):
                        audio_bytes = speak(
                            answer_text,
                            lang=result.get("lang", lang),
                        )

                    st.audio(audio_bytes, format="audio/wav")

                except Exception as voice_error:
                    st.warning(
                        f"Text answer is available, but speech generation "
                        f"failed: {voice_error}"
                    )

            # Show timing information
            latency = result.get("latency", {})
            if latency:
                with st.expander("Performance details"):
                    for stage, seconds in latency.items():
                        st.write(f"**{stage}:** {seconds:.2f} seconds")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer_text,
                "status": status,
                "chunks": chunks,
                "audio": audio_bytes,
            })

        except Exception as error:
            st.error(f"Something went wrong: {error}")

            st.session_state.messages.append({
                "role": "assistant",
                "content": "An error occurred while processing the question.",
                "status": "refused",
                "chunks": [],
                "audio": None,
            })


# --------------------------------------------------
# TEXT INPUT
# --------------------------------------------------

st.divider()

st.subheader("Ask a question")

language = st.selectbox(
    "Question language",
    options=["English", "हिन्दी"],
    index=0,
)

selected_lang = "en" if language == "English" else "hi"

question = st.chat_input(
    "Ask about a government scheme..."
)

if question:
    process_question(question, selected_lang)


# --------------------------------------------------
# VOICE INPUT
# --------------------------------------------------

st.subheader("Or ask using your voice")

audio_value = st.audio_input("Record your question")

if audio_value is not None:

    audio_name = getattr(audio_value, "name", "recorded_audio.wav")

    if st.button("Process voice question", type="primary"):

        try:
            with st.spinner("Converting speech into text..."):
                transcription = transcribe(
                    audio_value.getvalue()
                )

            recognized_text = transcription.get("text", "").strip()
            detected_lang = transcription.get("lang", "hi")

            if recognized_text:
                st.success("Speech recognized successfully.")

                st.write("**Recognized question:**")
                st.info(recognized_text)

                st.caption(
                    "Detected language: "
                    + transcription.get("detected_language_code", detected_lang)
                )

                process_question(
                    recognized_text,
                    detected_lang,
                    audio_input=True,
                )
            else:
                st.warning("No speech was recognized. Please try again.")

        except Exception as error:
            st.error(f"Voice processing failed: {error}")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Yojana Sahayak | MSc AIML Project | "
    "Multilingual Retrieval, Answer Verification and Voice Assistant"
)
