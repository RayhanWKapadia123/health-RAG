# health-RAG

A retrieval-augmented generation (RAG) tool for health websites. It scrapes pages, splits them into chunks, embeds the chunks with OpenAI, stores them in MongoDB, and answers questions through a REST API.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key
```

| Variable         | Description                               |
| ---------------- | ----------------------------------------- |
| `OPENAI_API_KEY` | Used to create embeddings and generate answers |

## Quick Start

```bash
# 1. Start MongoDB and the API
docker-compose up -d mongodb api

# 2. Set up the database (first time only)
docker-compose run --rm setup

# 3. Scrape a site
docker-compose run --rm scraper https://www.in.gov/health/

# 4. Ask a question via the API
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the Indiana Department of Health?"}'
```

## API

The API runs at `http://localhost:8000`.

Interactive docs are available at `http://localhost:8000/docs`.

### POST /ask

Ask a question against the scraped data.

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

## Scraping

Add more pages to the database at any time:

```bash
docker-compose run --rm scraper <url>
```

## Inspecting Stored Data

Connect to the MongoDB container:

```bash
docker exec -it health-rag-mongodb mongosh \
  "mongodb://admin:password@localhost:27017/health_rag?authSource=admin"
```

Useful queries:

```javascript
// Count chunks
db.documents.countDocuments()

// View the first chunk (without the embedding vector)
db.documents.findOne({}, { embedding: 0 })

// View all chunks from a specific URL
db.documents.find({ url: "https://www.in.gov/health/" }, { embedding: 0 }).pretty()

// List all scraped URLs
db.documents.distinct("url")

// View all chunks
db.documents.find({}, { embedding: 0 }).pretty()
```

> **Note:** `admin:password` is the local development default. Change it in `docker-compose.yml` before deploying anywhere.
