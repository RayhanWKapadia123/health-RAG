# health-RAG

A retrieval-augmented generation (RAG) tool for health websites. It scrapes pages, splits them into chunks, embeds the chunks with OpenAI, stores them in MongoDB, and answers questions through a REST API and Streamlit UI.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)
- `make`

## Project Structure

```
health-RAG/
├── backend/          # Scraper, API, query engine
├── frontend/         # Streamlit UI
├── docker-compose.yml
├── Makefile
└── .env
```

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key
```

## Quick Start

```bash
make build                                  # Build all images
make setup                                  # Initialize the database (first time only)
make scrape url=https://www.in.gov/health/  # Scrape a site
make up                                     # Start API and Streamlit
```

Then open **http://localhost:8501** in your browser.

## Makefile Commands

| Command                      | Description                              |
| ---------------------------- | ---------------------------------------- |
| `make build`                 | Build all Docker images                  |
| `make up`                    | Start MongoDB, API, and Streamlit        |
| `make down`                  | Stop all containers                      |
| `make setup`                 | Initialize the database (run once)       |
| `make scrape url=<url>`      | Scrape a URL and store chunks            |
| `make query q="<question>"`  | Ask a question via the CLI               |
| `make logs`                  | Tail logs for the API and Streamlit      |
| `make clean`                 | Stop containers and delete all data      |

## API

The API runs at `http://localhost:8000`.

Interactive docs are available at `http://localhost:8000/docs`.

### POST /ask

**Request:**
```json
{
  "question": "What are the side effects of ibuprofen?",
  "top_k": 5
}
```

| Field      | Type    | Required | Description                              |
| ---------- | ------- | -------- | ---------------------------------------- |
| `question` | string  | yes      | The question to ask                      |
| `top_k`    | integer | no       | Number of chunks to retrieve (default 5) |

**Response:**
```json
{
  "question": "What are the side effects of ibuprofen?",
  "answer": "Common side effects include nausea, stomach pain...",
  "sources": [
    { "url": "https://www.in.gov/health/", "title": "Indiana Department of Health" }
  ]
}
```

### GET /health

Returns `{"status": "ok"}` — used to verify the API is running.

## Inspecting Stored Data

```bash
docker exec -it health-rag-mongodb mongosh \
  "mongodb://admin:password@localhost:27017/health_rag?authSource=admin"
```

```javascript
db.documents.countDocuments()
db.documents.distinct("url")
db.documents.find({}, { embedding: 0 }).pretty()
db.documents.find({ url: "https://www.in.gov/health/" }, { embedding: 0 }).pretty()
```

> **Note:** `admin:password` is the local development default. Change it in `docker-compose.yml` before deploying anywhere.
