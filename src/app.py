import os
import sys
import streamlit as st
import pandas as pd
import anthropic
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

TIER_COLORS = {
    1: "#b91c1c",
    2: "#f97316",
    3: "#eab308",
    4: "#16a34a",
}

TIER_LABELS = {
    1: "Tier 1 — Critical Need",
    2: "Tier 2 — High Need",
    3: "Tier 3 — Moderate Need",
    4: "Tier 4 — Lower Need",
}

SAMPLE_DATA = pd.DataFrame([
    {"county": "LaGrange",  "uninsured_percent": 28.2, "diabetes_percent": 14.1, "health_tier": 1},
    {"county": "Daviess",   "uninsured_percent": 18.6, "diabetes_percent": 13.8, "health_tier": 1},
    {"county": "Crawford",  "uninsured_percent": 12.1, "diabetes_percent": 13.2, "health_tier": 1},
    {"county": "Jay",       "uninsured_percent": 12.0, "diabetes_percent": 13.5, "health_tier": 1},
    {"county": "Elkhart",   "uninsured_percent": 15.2, "diabetes_percent": 12.9, "health_tier": 2},
    {"county": "Noble",     "uninsured_percent": 14.6, "diabetes_percent": 12.1, "health_tier": 2},
    {"county": "Marshall",  "uninsured_percent": 14.5, "diabetes_percent": 11.8, "health_tier": 2},
    {"county": "Marion",    "uninsured_percent": 13.2, "diabetes_percent": 11.5, "health_tier": 2},
    {"county": "Wayne",     "uninsured_percent": 12.0, "diabetes_percent": 12.4, "health_tier": 2},
    {"county": "Kosciusko", "uninsured_percent": 12.8, "diabetes_percent": 11.9, "health_tier": 2},
    {"county": "Cass",      "uninsured_percent": 13.0, "diabetes_percent": 12.6, "health_tier": 2},
    {"county": "Clinton",   "uninsured_percent": 12.9, "diabetes_percent": 12.3, "health_tier": 2},
    {"county": "Johnson",   "uninsured_percent":  6.9, "diabetes_percent":  9.4, "health_tier": 3},
    {"county": "Monroe",    "uninsured_percent":  8.1, "diabetes_percent": 10.2, "health_tier": 3},
    {"county": "Allen",     "uninsured_percent":  9.3, "diabetes_percent": 10.8, "health_tier": 3},
    {"county": "Hamilton",  "uninsured_percent":  5.1, "diabetes_percent":  8.2, "health_tier": 4},
    {"county": "Boone",     "uninsured_percent":  5.8, "diabetes_percent":  8.9, "health_tier": 4},
    {"county": "Hendricks", "uninsured_percent":  6.2, "diabetes_percent":  9.1, "health_tier": 4},
])

_scraper_path = Path(__file__).parent.parent / "scraper"
if _scraper_path.exists() and str(_scraper_path) not in sys.path:
    sys.path.insert(0, str(_scraper_path))


def load_data(csv_path: str | None = None) -> pd.DataFrame:
    if csv_path:
        df = pd.read_csv(csv_path)
    else:
        df = SAMPLE_DATA.copy()
    df["tier_label"] = df["health_tier"].map(TIER_LABELS)
    df["tier_color"] = df["health_tier"].map(TIER_COLORS)
    return df


def build_data_context(df: pd.DataFrame) -> str:
    lines = ["Indiana county healthcare data (2024):\n"]
    for _, row in df.iterrows():
        lines.append(
            f"- {row['county']} County: "
            f"uninsured {row['uninsured_percent']}%, "
            f"diabetes {row['diabetes_percent']}%, "
            f"{TIER_LABELS[int(row['health_tier'])]}"
        )
    return "\n".join(lines)


def chat(user_message: str, df: pd.DataFrame, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    data_context = build_data_context(df)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]
    history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=(
            "You are an Indiana healthcare data analyst. "
            "Answer questions about Indiana county-level healthcare using only the data below. "
            "Cite specific counties and numbers in every answer. "
            "If asked about a county not in the data, say so.\n\n"
            + data_context
        ),
        messages=history,
    )
    return response.content[0].text


def generate_followups(question: str, answer: str, provider: str, api_key: str) -> list[str]:
    system_prompt = (
        "You generate follow-up questions for a healthcare data chatbot about Indiana counties. "
        "Given a question and answer, return exactly 3-4 short follow-up questions the user might ask next. "
        "If the answer mentions specific counties, organizations, or health programs, include questions about "
        "contact information, phone numbers, or names of relevant people or agencies when appropriate. "
        "Return only the questions, one per line, no numbering, no bullets, no extra text."
    )
    user_content = f"Question: {question}\n\nAnswer: {answer}"

    if provider == "Anthropic (Claude)":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-5-5",
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()
    else:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content.strip()

    return [q.strip() for q in raw.splitlines() if q.strip()][:4]


def render_history_sidebar(placeholder):
    # TODO: replace st.session_state.messages with MongoDB query here
    # e.g. messages = db["health_rag"]["conversations"].find({"session_id": session_id})
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


def handle_response(prompt: str, df: pd.DataFrame, provider: str, api_key: str):
    """Get answer, store messages, generate and store follow-ups."""
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = chat(prompt, df, api_key)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.spinner("Generating follow-up questions..."):
        followups = generate_followups(prompt, reply, provider, api_key)
    st.session_state.followups = followups


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

    st.title("Indiana Healthcare Intelligence")
    st.caption("Ask questions about county-level healthcare disparities across Indiana")

    st.sidebar.markdown("### Settings")
    provider = st.sidebar.radio(
        "AI Provider",
        ["Anthropic (Claude)", "OpenAI + RAG (MongoDB)"],
        index=0,
    )

    api_key = ""
    if provider == "Anthropic (Claude)":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            api_key = st.sidebar.text_input("Anthropic API Key", type="password")
        if not api_key:
            st.warning("Enter your Anthropic API key in the sidebar to enable chat.")
    else:
        if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("MONGO_URI"):
            st.warning("OPENAI_API_KEY and MONGO_URI must be set in .env for the RAG pipeline.")

    history_placeholder = st.sidebar.empty()
    render_history_sidebar(history_placeholder)

    df = load_data()

    # Render message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested questions shown before first message
    if not st.session_state.messages:
        st.markdown("**Try asking:**")
        suggestions = [
            "Which counties have the highest uninsured rates?",
            "Which counties are Tier 1 Critical Need?",
            "Compare LaGrange and Hamilton County",
            "Where should a new community clinic be opened?",
        ]
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            if cols[i % 2].button(suggestion, use_container_width=True, key=f"sug_{i}"):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                with st.chat_message("user"):
                    st.markdown(suggestion)
                if api_key:
                    handle_response(suggestion, df, provider, api_key)
                else:
                    st.error("Add your API key in the sidebar first.")
                render_history_sidebar(history_placeholder)
                st.rerun()

    # Follow-up question buttons shown after last answer
    if st.session_state.followups and st.session_state.messages:
        st.markdown("**You might also want to ask:**")
        for i, followup in enumerate(st.session_state.followups):
            if st.button(followup, key=f"followup_{i}", use_container_width=True):
                st.session_state.followups = []
                st.session_state.messages.append({"role": "user", "content": followup})
                with st.chat_message("user"):
                    st.markdown(followup)
                if api_key:
                    handle_response(followup, df, provider, api_key)
                render_history_sidebar(history_placeholder)
                st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask about Indiana healthcare..."):
        st.session_state.followups = []
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if api_key:
            handle_response(prompt, df, provider, api_key)
        else:
            st.error("Add your API key in the sidebar first.")
        render_history_sidebar(history_placeholder)

    if st.session_state.messages:
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.session_state.followups = []
            st.rerun()


if __name__ == "__main__":
    main()
