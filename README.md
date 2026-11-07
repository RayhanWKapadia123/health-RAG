# Indiana health-RAG

Indiana Healthcare Intelligence — a RAG-based chatbot.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage:
### 1. Add an .env file and add your keys:
    ```
    export ANTHROPIC_API_KEY=sk-ant-...
    export OPENAI_API_KEY=SOME_KEY
    MONGO_URI=SOME_URI
    ```
    
### 2. Start MongoDB
```
docker-compose up -d mongodb
```

### 3. Set up the database
```
docker-compose run --rm setup
```

### 4. Scrape a site
```
docker-compose run --rm scraper https://www.in.gov/health/
```

### 5. Ask a question
```
docker-compose run --rm query "What is the Indiana department of health?"
```

## Run Streamlit in browser

```bash
streamlit run src/app.py
```

## Run Streamlit in Docker

```bash
docker build -t health-rag .
docker run -p 8501:8501 --env-file .env health-rag
```

Then open http://localhost:8501 in your browser.