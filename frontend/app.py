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


def render_history_sidebar(placeholder):
    messages = st.session_state.messages
    pairs = []
    i = 0
    while i < len(messages) - 1:
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            pairs.append((messages[i]["content"], messages[i + 1]["content"]))
            i += 2
        else:
            i += 1

    with placeholder.container():
        st.markdown("### Conversation History")
        if pairs:
            for idx, (question, answer) in enumerate(reversed(pairs)):
                label = question if len(question) <= 50 else question[:47] + "..."
                with st.expander(f"Q{len(pairs) - idx}: {label}"):
                    st.markdown(f"**You:** {question}")
                    st.markdown(f"**Assistant:** {answer}")
        else:
            st.caption("No history yet. Ask a question to get started.")


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
            with st.expander("Sources"):
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
        page_title="Indiana Healthcare Intelligence",
        page_icon="🏥",
        layout="centered",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "followups" not in st.session_state:
        st.session_state.followups = []
    if "last_audio_id" not in st.session_state:
        st.session_state.last_audio_id = None

    st.title("Indiana Healthcare Intelligence")
    st.caption("Ask questions about county-level healthcare disparities across Indiana")

    history_placeholder = st.sidebar.empty()
    render_history_sidebar(history_placeholder)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"- [{s['title']}]({s['url']})")

    if not st.session_state.messages:
        st.markdown("**Try asking:**")
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
                render_history_sidebar(history_placeholder)
                st.rerun()

    if st.session_state.followups and st.session_state.messages:
        st.markdown("**Based on the response, you might also want to ask:**")
        for i, followup in enumerate(st.session_state.followups):
            if st.button(followup, key=f"followup_{i}", use_container_width=True):
                st.session_state.followups = []
                st.session_state.messages.append({"role": "user", "content": followup})
                with st.chat_message("user"):
                    st.markdown(followup)
                handle_response(followup)
                render_history_sidebar(history_placeholder)
                st.rerun()

    # Text input and mic button side by side
    input_col, mic_col = st.columns([11, 1])

    with input_col:
        prompt = st.chat_input("Ask about Indiana healthcare...")

    with mic_col:
        audio = audiorecorder("🎙", "⏹", key="mic")

    # Handle mic input — only fire once per new recording
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
        render_history_sidebar(history_placeholder)

    if st.session_state.messages:
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.session_state.followups = []
            st.rerun()


if __name__ == "__main__":
    main()
