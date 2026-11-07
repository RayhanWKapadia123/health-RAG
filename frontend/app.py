import os

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")


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


def main():
    st.set_page_config(
        page_title="Indiana Healthcare Intelligence",
        page_icon="🏥",
        layout="centered",
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("Indiana Healthcare Intelligence")
    st.caption("Ask questions about Indiana health data")

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
        for suggestion in suggestions:
            if st.button(suggestion, key=suggestion):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                with st.spinner("Thinking..."):
                    try:
                        result = ask_api(suggestion, st.session_state.messages[:-1])
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": result.get("sources", []),
                        })
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            st.error("No relevant data found. Try scraping more pages first.")
                        else:
                            st.error(f"API error: {e}")
                    except httpx.ConnectError:
                        st.error(f"Could not connect to the API at {API_URL}. Is it running?")
                st.rerun()

    if prompt := st.chat_input("Ask about Indiana healthcare..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = ask_api(prompt, st.session_state.messages[:-1])
                    st.markdown(result["answer"])
                    if result.get("sources"):
                        with st.expander("Sources"):
                            for s in result["sources"]:
                                st.markdown(f"- [{s['title']}]({s['url']})")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result.get("sources", []),
                    })
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        msg = "No relevant data found. Try scraping more pages first."
                    else:
                        msg = f"API error: {e}"
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                except httpx.ConnectError:
                    msg = f"Could not connect to the API at {API_URL}. Is it running?"
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})

    if st.session_state.messages:
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
