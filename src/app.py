import os
import streamlit as st
import pandas as pd
import anthropic

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


def render_county_card(row: pd.Series):
    tier = int(row["health_tier"])
    color = TIER_COLORS[tier]
    st.markdown(
        f"<div style='padding:12px;border-left:4px solid {color};background:#f9f9f9;border-radius:4px'>"
        f"<strong>{row['county']} County</strong><br>"
        f"<span style='background:{color};color:white;padding:2px 8px;border-radius:3px;font-size:0.8em'>"
        f"{TIER_LABELS[tier]}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    c1.metric("Uninsured", f"{row['uninsured_percent']}%")
    c2.metric("Diabetes", f"{row['diabetes_percent']}%")


def main():
    st.set_page_config(
        page_title="Indiana Healthcare Intelligence",
        page_icon="🏥",
        layout="centered",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("Indiana Healthcare Intelligence")
    st.caption("Ask questions about county-level healthcare disparities across Indiana")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        api_key = st.sidebar.text_input("Anthropic API Key", type="password")
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar to enable chat.")

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
        for suggestion in suggestions:
            if st.button(suggestion, key=suggestion):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                if api_key:
                    reply = chat(suggestion, df, api_key)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                else:
                    st.error("Add your API key in the sidebar first.")
                st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask about Indiana healthcare..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if api_key:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = chat(prompt, df, api_key)
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        else:
            st.error("Add your API key in the sidebar first.")

    if st.session_state.messages:
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
