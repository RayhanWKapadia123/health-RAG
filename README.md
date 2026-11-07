# Indiana health-RAG

Indiana Healthcare Intelligence — a RAG-based chatbot for exploring county-level healthcare disparities across Indiana's 92 counties. Ask questions in plain English and get answers grounded in real public health data.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
MONGO_URI=mongodb://admin:password@localhost:27017/?authSource=admin
```

## Usage

### 1. Start MongoDB
```bash
docker-compose up -d mongodb
```

### 2. Set up the database
```bash
docker-compose run --rm setup
```

### 3. Scrape a site
```bash
docker-compose run --rm scraper https://www.in.gov/health/
```

### 4. Ask a question (CLI)
```bash
docker-compose run --rm query "What is the Indiana department of health?"
```

### 5. Run the Streamlit app

**Locally:**
```bash
streamlit run src/app.py
```

**Via Docker Compose:**
```bash
docker-compose up streamlit
```

Then open http://localhost:8501 in your browser.
