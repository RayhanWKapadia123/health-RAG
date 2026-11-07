# health-RAG

Indiana Healthcare Intelligence — a RAG-based chatbot for exploring county-level healthcare disparities across Indiana's 92 counties.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run src/app.py
```

## API Key

Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or enter it in the sidebar when the app launches.
