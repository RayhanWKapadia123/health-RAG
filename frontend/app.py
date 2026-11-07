import io
import os

import httpx
from audiorecorder import audiorecorder
from openai import OpenAI
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

API_URL = os.environ.get("API_URL", "http://localhost:8000")
_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

STYLE = """
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] {
    background: #0f1117;
    color: #e8eaf0;
}
[data-testid="stSidebar"] {
    background: #161b27;
    border-right: 1px solid #1f2937;
}
[data-testid="stSidebar"] * { color: #c9cdd8 !important; }

/* ── Header ── */
.rag-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 28px 0 6px;
    border-bottom: 1px solid #1f2937;
    margin-bottom: 24px;
}
.rag-header .logo {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #2563eb, #0ea5e9);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; line-height: 1;
}
.rag-header h1 {
    margin: 0; font-size: 1.5rem; font-weight: 700;
    color: #f1f5f9; letter-spacing: -0.3px;
}
.rag-header p {
    margin: 2px 0 0; font-size: 0.82rem; color: #64748b;
}

/* ── Suggestion cards ── */
.suggestion-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 32px 0 8px;
}
.suggestion-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    margin-bottom: 10px;
}

/* ── Follow-up chips ── */
.followup-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    margin: 20px 0 8px;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: #1e2535 !important;
    color: #94a3b8 !important;
    border: 1px solid #2a3347 !important;
    border-radius: 10px !important;
    font-size: 0.83rem !important;
    padding: 10px 14px !important;
    transition: all 0.15s ease !important;
    text-align: left !important;
    width: 100% !important;
}
[data-testid="stButton"] > button:hover {
    background: #253047 !important;
    border-color: #3b82f6 !important;
    color: #e2e8f0 !important;
}

/* Clear chat button — distinct style */
[data-testid="stButton"][key="clear_chat"] > button,
.clear-btn button {
    background: transparent !important;
    border-color: #374151 !important;
    color: #6b7280 !important;
    font-size: 0.78rem !important;
    padding: 6px 12px !important;
    border-radius: 6px !important;
    width: auto !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
}
[data-testid="stChatMessage"][data-testid*="user"] [data-testid="stMarkdownContainer"] p {
    background: #1e3a5f;
    border-radius: 14px 14px 4px 14px;
    padding: 10px 14px;
    display: inline-block;
    color: #e2e8f0;
}

/* ── Source expander ── */
[data-testid="stExpander"] {
    background: #161b27 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    color: #64748b !important;
    font-size: 0.8rem !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: #1a2035 !important;
    border: 1px solid #2a3347 !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.9rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
}

/* ── Sidebar history ── */
.sidebar-heading {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #475569;
    padding: 16px 0 8px;
}
.sidebar-empty {
    font-size: 0.82rem;
    color: #4b5563;
    padding: 8px 0;
}

/* ── Status badge ── */
.status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    background: #22c55e;
    border-radius: 50%;
    margin-right: 5px;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #3b82f6 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a3347; border-radius: 3px; }

/* ── Audiorecorder ── */
.stAudio, [data-testid="stAudio"] { display: none !important; }
</style>
"""


def ask_api(question: str, history: list[dict]) -> dict:
    response = httpx.post(
        f"{API_URL}/ask",
        json={
            "question": question,
            "history": [
                {"role": m["role"], "content": m["content"]}
                for m in history
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def transcribe_audio(audio) -> str:
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    buf.name = "audio.wav"
    result = _openai.audio.transcriptions.create(model="whisper-1", file=buf)
    return result.text.strip()


def generate_followups(question: str, answer: str) -> list[str]:
    response = _openai.chat.completions.create(
        model="gpt-5.6-terra",
        max_completion_tokens=256,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate follow-up questions for a healthcare data chatbot about Indiana counties. "
                    "Given a question and answer, return exactly 3-4 short follow-up questions the user might ask next. "
                    "If the answer mentions specific counties, organizations, or health programs, include questions about "
                    "contact information, phone numbers, or names of relevant people or agencies when appropriate. "
                    "Return only the questions, one per line, no numbering, no bullets, no extra text."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer}"},
        ],
    )
    raw = response.choices[0].message.content.strip()
    return [q.strip() for q in raw.splitlines() if q.strip()][:4]


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-heading">Indiana Health RAG</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<span class="status-dot"></span><span style="font-size:0.78rem;color:#4b5563;">Connected</span>',
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown('<div class="sidebar-heading">Conversation History</div>', unsafe_allow_html=True)

        messages = st.session_state.messages
        pairs = []
        i = 0
        while i < len(messages) - 1:
            if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
                pairs.append((messages[i]["content"], messages[i + 1]["content"]))
                i += 2
            else:
                i += 1

        if pairs:
            for idx, (question, answer) in enumerate(reversed(pairs)):
                label = question if len(question) <= 48 else question[:45] + "..."
                with st.expander(label, expanded=False):
                    st.markdown(f"**You:** {question}")
                    st.markdown(f"**Assistant:** {answer}")
        else:
            st.markdown(
                '<div class="sidebar-empty">No history yet.</div>',
                unsafe_allow_html=True,
            )

        if pairs:
            st.divider()
            if st.button("Clear conversation", key="clear_chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.followups = []
                st.rerun()


def handle_response(prompt: str):
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = ask_api(prompt, st.session_state.messages[:-1])
                reply = result["answer"]
                sources = result.get("sources", [])
            except httpx.HTTPStatusError as e:
                reply = "No relevant data found. Try ingesting documents first." if e.response.status_code == 404 else f"API error: {e}"
                sources = []
            except httpx.ConnectError:
                reply = f"Could not connect to the API at {API_URL}. Is it running?"
                sources = []

        st.markdown(reply)
        if sources:
            with st.expander(f"Sources ({len(sources)})"):
                for s in sources:
                    st.markdown(f"- [{s['title']}]({s['url']})")

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "sources": sources,
    })

    with st.spinner("Generating follow-up questions..."):
        st.session_state.followups = generate_followups(prompt, reply)


def main():
    st.set_page_config(
        page_title="Indiana Health RAG",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(STYLE, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "followups" not in st.session_state:
        st.session_state.followups = []
    if "last_audio_id" not in st.session_state:
        st.session_state.last_audio_id = None

    render_sidebar()

    # Constrain main content width
    _, main_col, _ = st.columns([1, 5, 1])

    with main_col:
        st.markdown(
            """
            <div class="rag-header">
                <div class="logo">🏥</div>
                <div>
                    <h1>Indiana Healthcare Intelligence</h1>
                    <p>Ask questions about public health programs, services, and data across Indiana</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander(f"Sources ({len(msg['sources'])})"):
                        for s in msg["sources"]:
                            st.markdown(f"- [{s['title']}]({s['url']})")

        # Empty state suggestions
        if not st.session_state.messages:
            st.markdown('<div class="suggestion-label">Try asking</div>', unsafe_allow_html=True)
            suggestions = [
                "What services does the Indiana Department of Health provide?",
                "What health programs are available in Indiana?",
                "How do I report a public health concern in Indiana?",
                "What resources exist for maternal health in Indiana?",
            ]
            cols = st.columns(2)
            for i, suggestion in enumerate(suggestions):
                if cols[i % 2].button(suggestion, use_container_width=True, key=f"sug_{i}"):
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    with st.chat_message("user"):
                        st.markdown(suggestion)
                    handle_response(suggestion)
                    st.rerun()

        # Follow-up chips
        if st.session_state.followups and st.session_state.messages:
            st.markdown('<div class="followup-label">You might also ask</div>', unsafe_allow_html=True)
            for i, followup in enumerate(st.session_state.followups):
                if st.button(followup, key=f"followup_{i}", use_container_width=True):
                    st.session_state.followups = []
                    st.session_state.messages.append({"role": "user", "content": followup})
                    with st.chat_message("user"):
                        st.markdown(followup)
                    handle_response(followup)
                    st.rerun()

        # Input row: text + mic
        input_col, mic_col = st.columns([11, 1])
        with input_col:
            prompt = st.chat_input("Ask about Indiana healthcare...")
        with mic_col:
            audio = audiorecorder("🎙", "⏹", key="mic")

        # Mic transcription
        if audio and len(audio) > 0:
            audio_id = len(audio)
            if audio_id != st.session_state.last_audio_id:
                st.session_state.last_audio_id = audio_id
                with st.spinner("Transcribing..."):
                    prompt = transcribe_audio(audio)

        if prompt:
            st.session_state.followups = []
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            handle_response(prompt)
            st.rerun()


if __name__ == "__main__":
    main()
