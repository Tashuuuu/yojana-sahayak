import hashlib
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.pipeline import answer_question
from src.voice import transcribe, speak


# ------------------------------------------------------------
# PAGE SETUP
# ------------------------------------------------------------

st.set_page_config(
    page_title="Yojana Sahayak | Government Scheme Assistance",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# A public-facing interface: calm colours, clear hierarchy, and
# technical diagnostics kept out of the main user experience.
st.markdown(
    """
    <style>
    :root {
        --ys-navy: #183653;
        --ys-blue: #285b83;
        --ys-green: #26734d;
        --ys-saffron: #d88932;
        --ys-ink: #253443;
        --ys-muted: #687887;
        --ys-border: #e3e9ed;
        --ys-paper: #ffffff;
        --ys-bg: #f5f7f8;
    }

    .stApp {
        background: var(--ys-bg);
        color: var(--ys-ink);
    }

    [data-testid="stHeader"] {
        background: rgba(245, 247, 248, 0.92);
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    .block-container {
        max-width: 1120px;
        padding-top: 1.2rem;
        padding-bottom: 7rem;
    }

    .ys-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.35rem 0 1rem 0;
        border-bottom: 1px solid var(--ys-border);
        margin-bottom: 1.6rem;
    }

    .ys-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        color: var(--ys-navy);
        font-size: 1.25rem;
        font-weight: 750;
        letter-spacing: -0.03em;
    }

    .ys-brand-mark {
        width: 42px;
        height: 42px;
        display: grid;
        place-items: center;
        border-radius: 13px;
        background: var(--ys-navy);
        color: white;
        font-size: 1.35rem;
    }

    .ys-topnote {
        color: var(--ys-muted);
        font-size: 0.82rem;
        text-align: right;
    }

    .ys-hero {
        background: linear-gradient(115deg, #183653 0%, #285b83 100%);
        color: white;
        padding: 2rem 2.1rem;
        border-radius: 20px;
        margin: 0.5rem 0 1.5rem 0;
        box-shadow: 0 8px 24px rgba(24, 54, 83, 0.10);
    }

    .ys-eyebrow {
        color: #dce9f2;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 0.55rem;
    }

    .ys-hero h1 {
        color: white;
        font-size: clamp(1.8rem, 4vw, 2.55rem);
        line-height: 1.15;
        margin: 0 0 0.7rem 0;
        letter-spacing: -0.04em;
    }

    .ys-hero p {
        color: #edf4f8;
        font-size: 1rem;
        line-height: 1.65;
        max-width: 690px;
        margin: 0;
    }

    .ys-section-title {
        color: var(--ys-navy);
        font-size: 1.15rem;
        font-weight: 750;
        margin: 1.4rem 0 0.2rem 0;
    }

    .ys-section-subtitle {
        color: var(--ys-muted);
        font-size: 0.9rem;
        margin-bottom: 0.9rem;
    }

    .ys-category {
        background: white;
        border: 1px solid var(--ys-border);
        border-radius: 15px;
        padding: 1rem;
        min-height: 118px;
    }

    .ys-category-icon {
        font-size: 1.45rem;
        margin-bottom: 0.35rem;
    }

    .ys-category-title {
        color: var(--ys-navy);
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .ys-category-desc {
        color: var(--ys-muted);
        font-size: 0.82rem;
        line-height: 1.4;
    }

    .ys-trust {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem 1.2rem;
        color: var(--ys-muted);
        font-size: 0.82rem;
        margin: 0.8rem 0 1.4rem 0;
    }

    .ys-answer-label {
        color: var(--ys-green);
        font-weight: 750;
        font-size: 0.9rem;
        margin-bottom: 0.45rem;
    }

    .ys-disclaimer {
        color: var(--ys-muted);
        font-size: 0.78rem;
        line-height: 1.55;
        border-top: 1px solid var(--ys-border);
        margin-top: 2rem;
        padding-top: 1rem;
    }

    div[data-testid="stChatMessage"] {
        background: white;
        border: 1px solid var(--ys-border);
        border-radius: 16px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.8rem;
    }

    div[data-testid="stChatInput"] {
        border-color: #d8e0e6;
    }

    div[data-testid="stAudioInput"] {
        background: white;
        border: 1px solid var(--ys-border);
        border-radius: 14px;
        padding: 0.7rem;
    }

    .stButton > button {
        border-radius: 11px;
        border: 1px solid #d9e2e8;
        font-weight: 600;
    }

    .stButton > button[kind="primary"] {
        background: var(--ys-green);
        border-color: var(--ys-green);
    }

    a {
        color: var(--ys-blue) !important;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .ys-hero {
            padding: 1.4rem;
            border-radius: 16px;
        }
        .ys-topnote {
            display: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

if "speak_answers" not in st.session_state:
    st.session_state.speak_answers = True


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def add_question(question: str, lang: str, source: str = "text") -> None:
    """Run the existing answer pipeline and store a complete conversation turn."""
    question = (question or "").strip()
    if not question:
        st.warning("Please enter or record a question.")
        return

    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    try:
        with st.spinner("Finding relevant scheme information and checking the answer..."):
            result = answer_question(question, lang=lang, k=4)

        status = result.get("status", "refused")
        answer_text = result.get("spoken_text") or (
            "I could not verify an answer from the available official-source information."
        )
        audio_bytes = None
        voice_error = None

        if (
            st.session_state.speak_answers
            and status == "verified"
            and answer_text
        ):
            try:
                with st.spinner("Preparing the spoken answer..."):
                    audio_bytes = speak(answer_text, lang=result.get("lang", lang))
            except Exception as exc:
                voice_error = str(exc)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_text,
            "status": status,
            "chunks": result.get("chunks", []),
            "verification": result.get("verification", {}),
            "audio": audio_bytes,
            "latency": result.get("latency", {}),
            "voice_error": voice_error,
            "input_source": source,
        })

    except Exception as exc:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Something went wrong while processing this question. Please try again.",
            "status": "refused",
            "chunks": [],
            "verification": {},
            "audio": None,
            "latency": {},
            "voice_error": str(exc),
            "input_source": source,
        })


def show_sources(chunks):
    if not chunks:
        st.caption("No supporting passages were retrieved for this response.")
        return

    with st.expander("View official supporting information"):
        for rank, chunk in enumerate(chunks, start=1):
            scheme_name = chunk.get("name_en") or chunk.get("scheme_id", "Government scheme")
            section = (chunk.get("section") or "Overview").replace("_", " ").title()

            st.markdown(f"**{rank}. {scheme_name} — {section}**")
            st.write(chunk.get("text", ""))

            source_url = chunk.get("source_url", "")
            if source_url:
                st.markdown(f"[Open source website]({source_url})")

            if rank < len(chunks):
                st.divider()


def show_verification(verification):
    sentences = verification.get("sentences", []) if verification else []
    if not sentences:
        return

    with st.expander("How this answer was checked"):
        for sentence in sentences:
            label = sentence.get("label", "Unknown")
            text = sentence.get("text", "")
            if label == "Supported":
                st.markdown(f"✅ **Supported by the retrieved information**")
            else:
                st.markdown(f"⚠️ **{label}**")
            st.write(text)

        score = verification.get("groundedness")
        if score is not None:
            st.caption(f"Evidence support score: {score:.2f}")


def show_conversation():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant":
                status = message.get("status", "refused")

                if status == "verified":
                    st.success("This response was checked against the retrieved scheme information.")
                elif status == "partial":
                    st.warning("Some parts of this response could not be fully supported. Please check the sources.")
                else:
                    st.info("A reliable answer could not be verified from the available information.")

                show_sources(message.get("chunks", []))
                show_verification(message.get("verification", {}))

                if message.get("audio"):
                    st.audio(message["audio"], format="audio/wav")

                if message.get("voice_error"):
                    st.caption("The written response is available, but audio could not be generated.")

                # Technical timings are available but hidden from ordinary users.
                latency = message.get("latency", {})
                if latency:
                    with st.expander("Technical details"):
                        for stage, seconds in latency.items():
                            st.write(f"**{stage.replace('_', ' ').title()}:** {seconds:.2f} seconds")


# ------------------------------------------------------------
# TOP NAVIGATION AND HERO
# ------------------------------------------------------------

top_left, top_right = st.columns([3, 1])

with top_left:
    st.markdown(
        """
        <div class="ys-brand">
            <div class="ys-brand-mark">🇮🇳</div>
            <div>Yojana Sahayak</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_right:
    st.markdown(
        '<div class="ys-topnote">A simpler way to understand<br>government welfare schemes</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <section class="ys-hero">
        <div class="ys-eyebrow">Government scheme information assistant</div>
        <h1>Find the support you may be eligible for.</h1>
        <p>
            Ask questions about Indian government welfare schemes in English or Hindi.
            Get clear explanations, check the supporting information, or ask using your voice.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# LANGUAGE AND PREFERENCES
# ------------------------------------------------------------

pref_col, voice_col, clear_col = st.columns([1.2, 1.5, 1])

with pref_col:
    language = st.selectbox(
        "Language / भाषा",
        options=["English", "हिन्दी"],
        index=0,
        key="question_language",
    )

selected_lang = "en" if language == "English" else "hi"

with voice_col:
    st.session_state.speak_answers = st.toggle(
        "Read verified answers aloud",
        value=st.session_state.speak_answers,
    )

with clear_col:
    st.write("")
    if st.button("Start new chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_audio_hash = None
        st.rerun()


# ------------------------------------------------------------
# POPULAR SCHEME SHORTCUTS
# ------------------------------------------------------------

if not st.session_state.messages:
    st.markdown('<div class="ys-section-title">What can we help you with?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ys-section-subtitle">Choose a common topic, or type your own question below.</div>',
        unsafe_allow_html=True,
    )

    categories = st.columns(4)
    category_data = [
        ("🌾", "Farmers", "PM-KISAN and agricultural support"),
        ("🔥", "Households", "Ujjwala and household support"),
        ("🎓", "Students", "Scholarships and education"),
        ("🏥", "Healthcare", "Health coverage and assistance"),
    ]

    for col, (icon, title, description) in zip(categories, category_data):
        with col:
            st.markdown(
                f"""
                <div class="ys-category">
                    <div class="ys-category-icon">{icon}</div>
                    <div class="ys-category-title">{title}</div>
                    <div class="ys-category-desc">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="ys-section-title">Try asking</div>', unsafe_allow_html=True)
    prompt_cols = st.columns(2)
    quick_prompts = [
        "Who is eligible for PM-KISAN?",
        "What benefits are provided under PM Ujjwala Yojana?",
    ]

    for col, prompt in zip(prompt_cols, quick_prompts):
        with col:
            if st.button(prompt, use_container_width=True):
                add_question(prompt, selected_lang)
                st.rerun()


# ------------------------------------------------------------
# CONVERSATION
# ------------------------------------------------------------

if st.session_state.messages:
    st.markdown('<div class="ys-section-title">Your conversation</div>', unsafe_allow_html=True)
    show_conversation()


# ------------------------------------------------------------
# VOICE QUESTION INPUT
# ------------------------------------------------------------

st.markdown('<div class="ys-section-title">Prefer speaking?</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ys-section-subtitle">Record your question. We will convert it to text before finding an answer.</div>',
    unsafe_allow_html=True,
)

audio_value = st.audio_input("Record a question")

if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    audio_hash = hashlib.sha256(audio_bytes).hexdigest()

    if audio_hash != st.session_state.last_audio_hash:
        if st.button("Submit recorded question", type="primary"):
            try:
                with st.spinner("Recognising your speech..."):
                    transcription = transcribe(audio_bytes)

                recognized_text = (transcription.get("text") or "").strip()
                detected_lang = transcription.get("lang", selected_lang)

                if recognized_text:
                    st.session_state.last_audio_hash = audio_hash
                    st.success("We heard:")
                    st.info(recognized_text)
                    add_question(recognized_text, detected_lang, source="voice")
                    st.rerun()
                else:
                    st.warning("We could not recognise the speech. Please try recording again.")

            except Exception:
                st.error("Voice recognition is temporarily unavailable. You can type your question instead.")


# ------------------------------------------------------------
# CHAT INPUT
# ------------------------------------------------------------

question = st.chat_input(
    "Ask about eligibility, benefits, documents or how to apply..."
)

if question:
    add_question(question, selected_lang)
    st.rerun()


# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------

st.markdown(
    """
    <div class="ys-trust">
        <span>✓ English and Hindi support</span>
        <span>✓ Responses checked against retrieved information</span>
        <span>✓ Official source links where available</span>
    </div>
    <div class="ys-disclaimer">
        <strong>Important:</strong> Yojana Sahayak is an independent educational
        information assistant and is not an official government website or service.
        Scheme rules, eligibility and application requirements may change. Always
        confirm details with the linked official source or the relevant government
        department before applying.
    </div>
    """,
    unsafe_allow_html=True,
)
