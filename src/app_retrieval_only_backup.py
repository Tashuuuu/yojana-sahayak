import sys
from pathlib import Path

import streamlit as st

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.retrieve import retrieve


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Yojana Sahayak",
    page_icon="🇮🇳",
    layout="wide"
)


# --------------------------------------------------
# CUSTOM STYLING
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
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Your assistant for understanding Indian government schemes'
    '</div>',
    unsafe_allow_html=True
)

st.divider()

st.markdown("""
<div class="info-box">
    <b>Welcome!</b> Ask a question about government schemes.
    Yojana Sahayak will search its knowledge base and show
    the most relevant information with source references.
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("About")

    st.write(
        "Yojana Sahayak helps users discover information "
        "about government welfare schemes."
    )

    st.divider()

    st.subheader("Current capabilities")

    st.write("✅ Multilingual semantic retrieval")
    st.write("✅ FAISS similarity search")
    st.write("✅ Top 4 relevant passages")
    st.write("⏳ AI-generated answers")
    st.write("⏳ Answer verification")
    st.write("⏳ Voice interaction")

    st.divider()

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------
# DISPLAY PREVIOUS MESSAGES
# --------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if message["role"] == "assistant":
            for rank, result in enumerate(
                message.get("results", []), start=1
            ):
                with st.expander(
                    f"Source {rank}: {result['name_en']} "
                    f"— {result['section']}"
                ):
                    st.write(result["text"])

                    st.caption(
                        f"Similarity score: "
                        f"{result['similarity_score']:.4f}"
                    )

                    st.markdown(
                        f"[View source]({result['source_url']})"
                    )


# --------------------------------------------------
# CHAT INPUT AND RETRIEVAL
# --------------------------------------------------

question = st.chat_input(
    "Ask something about a government scheme..."
)

if question:

    # Display user question
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    # Retrieve relevant information
    with st.chat_message("assistant"):

        with st.spinner("Searching the scheme database..."):

            try:
                results = retrieve(question, top_k=4)

                if results:

                    st.markdown(
                        "**I found the following relevant information "
                        "in the scheme database:**"
                    )

                    st.info(
                        "These are retrieved source passages, "
                        "not yet AI-generated answers."
                    )

                    for rank, result in enumerate(results, start=1):

                        with st.expander(
                            f"Source {rank}: {result['name_en']} "
                            f"— {result['section']}",
                            expanded=(rank == 1)
                        ):

                            st.write(result["text"])

                            st.caption(
                                f"Similarity score: "
                                f"{result['similarity_score']:.4f}"
                            )

                            st.markdown(
                                f"[View official source]"
                                f"({result['source_url']})"
                            )

                    response = (
                        "I found relevant information in the "
                        "scheme database. Please review the "
                        "retrieved passages above."
                    )

                else:

                    response = (
                        "I couldn't find relevant information "
                        "for this question in the current database."
                    )

                    st.warning(response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "results": results
                })

            except Exception as error:

                st.error(
                    f"Something went wrong while retrieving "
                    f"information: {error}"
                )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Yojana Sahayak | MSc AIML Project | "
    "Retrieval-powered prototype"
)
