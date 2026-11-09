import base64
import html
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.pipeline import answer_question
from src.voice import speak, transcribe


st.set_page_config(
    page_title="Yojana Sahayak | Government Scheme Assistance",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles(dark: bool) -> None:
    """Apply the Indigo palette consistently to the app and Streamlit widgets."""
    if dark:
        colors = {
            "bg": "#141420", "surface": "#201f30", "ink": "#f0efff",
            "muted": "#aaa8c4", "line": "#3a384e", "brand": "#aaa5fa",
            "soft": "#302e49", "good": "#85bfa0", "warn": "#e7b970",
            "bad": "#ee9aa0", "shadow": "0 12px 36px rgba(0,0,0,.18)",
        }
    else:
        colors = {
            "bg": "#f4f4fb", "surface": "#ffffff", "ink": "#292b48",
            "muted": "#70728a", "line": "#e1e1ee", "brand": "#5653a4",
            "soft": "#ecebfa", "good": "#31735b", "warn": "#8b641f",
            "bad": "#a25158", "shadow": "0 12px 36px rgba(41,43,72,.06)",
        }
    vars_css = ";".join(f"--ys-{key}:{value}" for key, value in colors.items())
    st.markdown(
        f"""
        <style>
        :root {{{vars_css}}}
        .stApp, [data-testid="stAppViewContainer"] {{background:var(--ys-bg); color:var(--ys-ink)}}
        .stMarkdown, .stMarkdown p, .stMarkdown li, [data-testid="stText"] {{color:var(--ys-ink)}}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{color:var(--ys-muted)}}
        header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu {{display:none!important}}
        [data-testid="stSidebar"] {{display:none}}
        .block-container {{max-width:1240px;padding-top:1.1rem;padding-bottom:5rem}}
        .ys-topbar {{display:flex;align-items:center;min-height:96px}}
        .ys-brand-logo {{display:block;width:min(100%, 430px);height:auto;max-height:104px;object-fit:contain;object-position:left center}}
        .ys-hero {{padding:1.65rem 1.8rem;border-radius:20px;background:linear-gradient(120deg,#403e82 0%,#625fb4 100%);color:#fff;margin:.9rem 0 1.15rem;box-shadow:var(--ys-shadow)}}
        .ys-eyebrow {{font-size:.72rem;text-transform:uppercase;letter-spacing:.13em;font-weight:800;color:#dcdbff}}
        .ys-hero h1 {{font-size:clamp(1.65rem,3vw,2.2rem);line-height:1.12;letter-spacing:-.04em;color:#fff;margin:.55rem 0 .45rem}}
        .ys-hero p {{max-width:760px;color:#eeedff;margin:0;line-height:1.55}}
        .ys-panel {{background:var(--ys-surface);border:1px solid var(--ys-line);border-radius:17px;padding:1.1rem 1.2rem;box-shadow:var(--ys-shadow)}}
        .ys-panel-title {{font-weight:800;color:var(--ys-ink);font-size:1rem;margin:0 0 .15rem}}
        .ys-muted {{color:var(--ys-muted);font-size:.82rem}}
        .ys-info {{background:var(--ys-soft);color:var(--ys-ink);border:1px solid var(--ys-line);border-radius:12px;padding:.85rem 1rem;font-size:.9rem;line-height:1.5}}
        .ys-status {{font-weight:800;font-size:.78rem;letter-spacing:.035em;color:var(--ys-good)}}
        .ys-status.partial {{color:var(--ys-warn)}}
        .ys-status.refused {{color:var(--ys-bad)}}
        .ys-evidence {{border-left:3px solid var(--ys-brand);background:var(--ys-soft);padding:.75rem .85rem;border-radius:0 11px 11px 0;margin:.55rem 0;font-size:.88rem}}
        .ys-check {{background:var(--ys-soft);border:1px solid var(--ys-line);border-radius:11px;padding:.7rem .8rem;margin:.55rem 0;font-size:.86rem}}
        .ys-check-label {{font-weight:800;font-size:.72rem;letter-spacing:.04em;color:var(--ys-good);margin-bottom:.2rem}}
        .ys-check-label.unsupported,.ys-check-label.contradicted {{color:var(--ys-warn)}}
        .ys-check-label.unknown {{color:var(--ys-muted)}}
        div[data-testid="stChatMessage"] {{background:var(--ys-surface)!important;color:var(--ys-ink)!important;border:1px solid var(--ys-line);border-radius:16px;padding:.85rem 1rem;margin:.55rem 0}}
        [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span {{color:var(--ys-ink)!important}}
        div.stChatInput, [data-testid="stChatInput"] {{background:var(--ys-surface)!important;border:1px solid var(--ys-line)!important;border-radius:15px!important;color:var(--ys-ink)!important;box-shadow:none!important}}
        div.stChatInput > div, [data-testid="stChatInput"] > div, [data-testid="stChatInput"] [data-baseweb="textarea"] {{background:var(--ys-surface)!important}}
        [data-testid="stChatInputTextArea"], [data-testid="stChatInput"] textarea {{background:var(--ys-surface)!important;color:var(--ys-ink)!important;-webkit-text-fill-color:var(--ys-ink)!important;caret-color:var(--ys-brand)}}
        [data-testid="stChatInputTextArea"]::placeholder, [data-testid="stChatInput"] textarea::placeholder {{color:var(--ys-muted)!important;-webkit-text-fill-color:var(--ys-muted)!important;opacity:1}}
        [data-testid="stChatInput"] button {{background:var(--ys-surface)!important;color:var(--ys-brand)!important}}
        [data-testid="stTextInput"] input {{background:var(--ys-surface)!important;color:var(--ys-ink)!important;border-color:var(--ys-line)!important}}
        .stButton>button {{background:var(--ys-surface)!important;color:var(--ys-ink)!important;border:1px solid var(--ys-line)!important;border-radius:10px;font-weight:650}}
        .stButton>button * {{color:inherit!important}}
        .stButton>button:hover {{border-color:var(--ys-brand)!important;color:var(--ys-brand)!important}}
        .stButton>button[kind="primary"] {{background:var(--ys-brand)!important;border-color:var(--ys-brand)!important;color:#fff!important}}
        .stButton>button[kind="primary"] * {{color:#fff!important}}
        [data-testid="stSegmentedControl"] button {{background:var(--ys-surface)!important;color:var(--ys-ink)!important;border-color:var(--ys-line)!important}}
        [data-testid="stSegmentedControl"] button * {{color:inherit!important}}
        [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{background:var(--ys-soft)!important;color:var(--ys-brand)!important}}
        [data-testid="stMetric"] {{background:var(--ys-soft)!important;color:var(--ys-ink)!important;padding:.7rem .8rem;border-radius:12px}}
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{color:var(--ys-ink)!important}}
        [data-testid="stAlert"] {{background:var(--ys-soft)!important;color:var(--ys-ink)!important;border-color:var(--ys-line)!important}}
        [data-testid="stAlert"] * {{color:var(--ys-ink)!important}}
        [data-testid="stCheckbox"] label {{white-space:nowrap;overflow:visible}}
        [data-testid="stExpander"] {{background:var(--ys-surface)!important;color:var(--ys-ink)!important;border-color:var(--ys-line);border-radius:12px}}
        [data-testid="stExpander"] summary, [data-testid="stExpander"] p {{color:var(--ys-ink)!important}}
        a {{color:var(--ys-brand)!important}}
        .ys-footer {{color:var(--ys-muted);font-size:.77rem;line-height:1.55;border-top:1px solid var(--ys-line);padding-top:1rem;margin-top:1.6rem}}
        @media(max-width:700px) {{.block-container{{padding-left:1rem;padding-right:1rem}}.ys-hero{{padding:1.25rem;border-radius:15px}}}}
        </style>
        """,
        unsafe_allow_html=True,
    )


for key, initial in {
    "messages": [],
    "speak_answers": True,
    "dark_mode": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = initial

inject_styles(st.session_state.dark_mode)


UI_TEXT = {
    "en": {
        "tagline": "Government scheme information, grounded in retrieved sources",
        "language": "Language",
        "dark_mode": "Dark mode",
        "new_chat": "＋ New chat",
        "hero_eyebrow": "Ask in your language · hear what’s verified",
        "hero_title": "Clear answers about government schemes.",
        "hero_description": "Ask in English or Hindi by voice or text. We check each answer against retrieved scheme information and show you the evidence.",
        "read_aloud": "Read verified answers aloud",
        "informational_aid": "Information aid · Confirm current rules with the linked official source.",
        "popular": "Popular questions",
        "prompt_farmer": "Who is eligible for PM-KISAN?",
        "prompt_ujjwala": "What benefits are provided under PM Ujjwala Yojana?",
        "conversation": "Conversation",
        "empty_conversation": "Your questions and answers will appear here.",
        "empty_input": "Type a question or record one to send it.",
        "evidence_title": "Evidence and answer checks",
        "evidence_intro": "Retrieved sources and sentence checks will appear here after your first question.",
        "evidence_empty": "Ask a question to see how its answer is supported.",
        "verified": "✓ VERIFIED RESPONSE",
        "partial": "! PARTLY SUPPORTED · NOT SPOKEN",
        "refused": "! COULDN’T VERIFY",
        "groundedness": "Groundedness",
        "groundedness_help": "Fraction of answer sentences labelled Supported.",
        "sentence_checks": "Sentence checks",
        "supported": "SUPPORTED",
        "unsupported": "UNSUPPORTED",
        "contradicted": "CONTRADICTED",
        "unknown": "UNKNOWN",
        "no_sentence": "No answer sentence passed verification, so the assistant did not speak an answer.",
        "retrieved_info": "Retrieved official information",
        "no_passages": "No sufficiently relevant passages were found.",
        "open_source": "Open official source ↗",
        "technical_details": "Technical details",
        "asked_voice": "Asked by voice",
        "audio_unavailable": "The written answer is available, but audio could not be generated.",
        "processing": "Finding scheme information and checking the answer…",
        "preparing_audio": "Preparing the spoken answer…",
        "transcribing": "Transcribing your recording…",
        "transcription_failed": "We couldn’t recognise the speech. Please record again or type your question.",
        "voice_unavailable": "Voice recognition is temporarily unavailable. You can type your question instead.",
        "chat_placeholder": "Ask about eligibility, benefits, documents or how to apply…",
        "about": "About this service",
        "disclaimer": "Yojana Sahayak is an independent educational information assistant, not a government website or service. Scheme rules and eligibility may change. Please confirm details with the linked official source or relevant department before applying.",
        "fallback": "I could not verify an answer from the available official-source information.",
        "error": "Something went wrong while processing this question. Please try again.",
    },
    "hi": {
        "tagline": "सरकारी योजनाओं की जानकारी, उपलब्ध स्रोतों के आधार पर",
        "language": "भाषा",
        "dark_mode": "डार्क मोड",
        "new_chat": "＋ नई बातचीत",
        "hero_eyebrow": "अपनी भाषा में पूछें · सत्यापित जवाब सुनें",
        "hero_title": "सरकारी योजनाओं के बारे में स्पष्ट जानकारी।",
        "hero_description": "हिंदी या अंग्रेज़ी में बोलकर या लिखकर पूछें। हम हर जवाब को मिली हुई योजना की जानकारी से जाँचते हैं और स्रोत भी दिखाते हैं।",
        "read_aloud": "सत्यापित जवाब ज़ोर से पढ़ें",
        "informational_aid": "यह जानकारी के लिए है · मौजूदा नियम आधिकारिक स्रोत से जाँचें।",
        "popular": "लोकप्रिय सवाल",
        "prompt_farmer": "पीएम-किसान के लिए कौन पात्र है?",
        "prompt_ujjwala": "पीएम उज्ज्वला योजना में क्या लाभ मिलते हैं?",
        "conversation": "बातचीत",
        "empty_conversation": "आपके सवाल और जवाब यहाँ दिखाई देंगे।",
        "empty_input": "सवाल लिखें या बोलकर रिकॉर्ड करें, फिर भेजें।",
        "evidence_title": "स्रोत और जवाब की जाँच",
        "evidence_intro": "आपका पहला सवाल पूछने के बाद स्रोत और वाक्य-जाँच यहाँ दिखाई देंगी।",
        "evidence_empty": "जवाब के समर्थन में मौजूद जानकारी देखने के लिए सवाल पूछें।",
        "verified": "✓ सत्यापित जवाब",
        "partial": "! कुछ हिस्सा समर्थित नहीं · जवाब बोला नहीं गया",
        "refused": "! सत्यापित नहीं हो सका",
        "groundedness": "स्रोत-समर्थन",
        "groundedness_help": "समर्थित माने गए जवाब के वाक्यों का अनुपात।",
        "sentence_checks": "हर वाक्य की जाँच",
        "supported": "समर्थित",
        "unsupported": "असमर्थित",
        "contradicted": "विरोधाभासी",
        "unknown": "अज्ञात",
        "no_sentence": "कोई वाक्य जाँच में समर्थित नहीं मिला, इसलिए जवाब बोलकर नहीं दिया गया।",
        "retrieved_info": "मिली हुई आधिकारिक जानकारी",
        "no_passages": "पर्याप्त रूप से संबंधित जानकारी नहीं मिली।",
        "open_source": "आधिकारिक स्रोत खोलें ↗",
        "technical_details": "तकनीकी विवरण",
        "asked_voice": "आवाज़ से पूछा गया",
        "audio_unavailable": "लिखित जवाब उपलब्ध है, लेकिन ऑडियो तैयार नहीं हो सका।",
        "processing": "योजना की जानकारी खोजकर जवाब की जाँच हो रही है…",
        "preparing_audio": "जवाब का ऑडियो तैयार हो रहा है…",
        "transcribing": "आपकी रिकॉर्डिंग को लिखा जा रहा है…",
        "transcription_failed": "आवाज़ समझ नहीं आई। कृपया दोबारा रिकॉर्ड करें या सवाल लिखें।",
        "voice_unavailable": "आवाज़ पहचान अभी उपलब्ध नहीं है। आप अपना सवाल लिख सकते हैं।",
        "chat_placeholder": "पात्रता, लाभ, ज़रूरी दस्तावेज़ या आवेदन के बारे में पूछें…",
        "about": "इस सेवा के बारे में",
        "disclaimer": "योजना सहायक एक स्वतंत्र शैक्षिक जानकारी सेवा है, सरकारी वेबसाइट या सेवा नहीं। योजनाओं के नियम और पात्रता बदल सकते हैं। आवेदन से पहले जुड़े आधिकारिक स्रोत या संबंधित विभाग से जानकारी की पुष्टि करें।",
        "fallback": "उपलब्ध आधिकारिक जानकारी से इस जवाब की पुष्टि नहीं हो सकी।",
        "error": "सवाल पर काम करते समय समस्या हुई। कृपया फिर कोशिश करें।",
    },
}


def tr(key: str) -> str:
    lang = "hi" if st.session_state.get("question_language") == "हिन्दी" else "en"
    return UI_TEXT[lang][key]


def add_question(question: str, lang: str, source: str = "text") -> None:
    """Run the answer pipeline and retain its answer, evidence, checks and audio."""
    question = (question or "").strip()
    if not question:
        st.warning(tr("empty_input"))
        return

    st.session_state.messages.append({"role": "user", "content": question, "input_source": source})
    try:
        with st.spinner(tr("processing")):
            result = answer_question(question, lang=lang, k=4)

        status = result.get("status", "refused")
        answer_text = result.get("spoken_text") or (
            tr("fallback")
        )
        audio_bytes = None
        voice_error = None
        if st.session_state.speak_answers and status == "verified" and answer_text:
            try:
                with st.spinner(tr("preparing_audio")):
                    audio_bytes = speak(answer_text, lang=result.get("lang", lang))
            except Exception as exc:
                voice_error = str(exc)

        st.session_state.messages.append({
            "role": "assistant", "content": answer_text, "status": status,
            "chunks": result.get("chunks", []),
            "verification": result.get("verification", {}),
            "audio": audio_bytes, "latency": result.get("latency", {}),
            "voice_error": voice_error, "input_source": source,
        })
    except Exception as exc:
        st.session_state.messages.append({
            "role": "assistant",
            "content": tr("error"),
            "status": "refused", "chunks": [], "verification": {}, "audio": None,
            "latency": {}, "voice_error": str(exc), "input_source": source,
        })


def latest_assistant_message():
    return next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)


def status_text(status: str) -> tuple[str, str]:
    return {
        "verified": (tr("verified"), "verified"),
        "partial": (tr("partial"), "partial"),
        "refused": (tr("refused"), "refused"),
    }.get(status, (tr("refused"), "refused"))


def render_conversation() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "user" and message.get("input_source") == "voice":
                st.caption(tr("asked_voice"))
            elif message["role"] == "assistant":
                label, _ = status_text(message.get("status", "refused"))
                st.caption(label)
                if message.get("audio"):
                    st.audio(message["audio"], format="audio/wav")
                elif message.get("voice_error") and message.get("status") == "verified":
                    st.caption(tr("audio_unavailable"))


def render_evidence(message) -> None:
    if message is None:
        st.markdown(f'<div class="ys-panel-title">{tr("evidence_title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ys-muted">{tr("evidence_intro")}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="ys-info">{tr("evidence_empty")}</div>', unsafe_allow_html=True)
        return

    status = message.get("status", "refused")
    label, css_status = status_text(status)
    st.markdown(f'<div class="ys-panel-title">{tr("evidence_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ys-status {css_status}">{label}</div>', unsafe_allow_html=True)

    verification = message.get("verification") or {}
    score = verification.get("groundedness")
    if score is not None:
        st.metric(tr("groundedness"), f"{score:.2f}", help=tr("groundedness_help"))

    sentences = verification.get("sentences", [])
    if sentences:
        st.markdown(f"**{tr('sentence_checks')}**")
        for sentence in sentences:
            sentence_label = sentence.get("label", "Unknown").lower()
            slug = sentence_label if sentence_label in {"supported", "unsupported", "contradicted"} else "unknown"
            safe_label = html.escape(tr(slug).upper())
            safe_text = html.escape(str(sentence.get("text", "")))
            st.markdown(
                f'<div class="ys-check"><div class="ys-check-label {slug}">{safe_label}</div>{safe_text}</div>',
                unsafe_allow_html=True,
            )
    elif status == "refused":
        st.caption(tr("no_sentence"))

    chunks = message.get("chunks", [])
    st.markdown(f"**{tr('retrieved_info')}**")
    if not chunks:
        st.caption(tr("no_passages"))
    else:
        for rank, chunk in enumerate(chunks, start=1):
            name = chunk.get("name_en") or chunk.get("scheme_id") or "Government scheme"
            section = (chunk.get("section") or "Overview").replace("_", " ").title()
            st.markdown(f"**{rank}. {name} · {section}**")
            passage = html.escape(str(chunk.get("text", "")))
            st.markdown(f'<div class="ys-evidence">{passage}</div>', unsafe_allow_html=True)
            url = chunk.get("source_url")
            if url:
                st.markdown(f"[{tr('open_source')}]({url})")

    if message.get("latency"):
        with st.expander(tr("technical_details")):
            for stage, seconds in message["latency"].items():
                st.write(f"**{stage.replace('_', ' ').title()}:** {seconds:.2f} seconds")


# Header and appearance controls.
head_left, head_right = st.columns([2, 3])
logo_mode = "dark" if st.session_state.dark_mode else "light"
logo_path = BASE_DIR / "assets" / f"yojana-sahayak-logo-{logo_mode}.svg"
logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
with head_left:
    st.markdown(
        f'<div class="ys-topbar"><img class="ys-brand-logo" src="data:image/svg+xml;base64,{logo_data}" alt="Yojana Sahayak — योजना सहायक"></div>',
        unsafe_allow_html=True,
    )
with head_right:
    controls = st.columns([1.45, 1.55, 1.45])
    with controls[0]:
        language = st.segmented_control(
            tr("language"),
            options=["English", "हिन्दी"],
            default="English",
            key="question_language",
            label_visibility="collapsed",
            width="stretch",
        )
    with controls[1]:
        st.toggle(tr("dark_mode"), key="dark_mode")
    with controls[2]:
        if st.button(tr("new_chat"), use_container_width=True, disabled=not st.session_state.messages):
            st.session_state.messages = []
            st.rerun()

selected_lang = "en" if language == "English" else "hi"

st.markdown(
    f"""<section class="ys-hero"><div class="ys-eyebrow">{tr("hero_eyebrow")}</div>
    <h1>{tr("hero_title")}</h1>
    <p>{tr("hero_description")}</p></section>""",
    unsafe_allow_html=True,
)

prefs_left, prefs_right = st.columns([2, 3])
with prefs_left:
    st.toggle(tr("read_aloud"), key="speak_answers")
with prefs_right:
    st.caption(tr("informational_aid"))

if not st.session_state.messages:
    st.markdown(f"### {tr('popular')}")
    prompt_cols = st.columns(2)
    quick_prompts = [
        tr("prompt_farmer"),
        tr("prompt_ujjwala"),
    ]
    for col, prompt in zip(prompt_cols, quick_prompts):
        with col:
            if st.button(prompt, use_container_width=True):
                add_question(prompt, selected_lang)
                st.rerun()

# The chat stays central; the latest answer's verification and sources stay beside it.
chat_col, evidence_col = st.columns([1.8, 1], gap="large")
with chat_col:
    st.markdown(f'<div class="ys-panel-title">{tr("conversation")}</div>', unsafe_allow_html=True)
    if st.session_state.messages:
        render_conversation()
    else:
        st.markdown(f'<div class="ys-info">{tr("empty_conversation")}</div>', unsafe_allow_html=True)
    prompt = st.chat_input(
        tr("chat_placeholder"),
        accept_audio=True,
        audio_sample_rate=16000,
        key="scheme_chat_input",
        width="stretch",
    )
    if prompt is not None:
        if prompt.audio is not None:
            try:
                with st.spinner(tr("transcribing")):
                    transcription = transcribe(prompt.audio.getvalue())
                recognized = (transcription.get("text") or "").strip()
                if recognized:
                    add_question(
                        recognized,
                        transcription.get("lang", selected_lang),
                        source="voice",
                    )
                else:
                    st.warning(tr("transcription_failed"))
            except Exception:
                st.error(tr("voice_unavailable"))
        elif prompt.text.strip():
            add_question(prompt.text, selected_lang)
        st.rerun()

with evidence_col:
    with st.container(border=True):
        render_evidence(latest_assistant_message())

st.markdown(
    f"""<div class="ys-footer"><strong>{tr("about")}:</strong> {tr("disclaimer")}</div>""",
    unsafe_allow_html=True,
)
