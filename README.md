# Health RAG

A retrieval-augmented generation (RAG) chatbot for Indiana public health data. Documents from `health_data_zip` are chunked, embedded with OpenAI, and stored in MongoDB Atlas Local. A FastAPI backend handles vector search and answer generation; a Streamlit frontend provides the chat UI.

---

## Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (includes Docker Compose)
- [Make](https://www.gnu.org/software/make/) — pre-installed on macOS/Linux
- An [OpenAI API key](https://platform.openai.com/api-keys)

---

## Step 1 — Configure environment

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
MONGO_URI=mongodb://admin:password@localhost:27017/?authSource=admin
```

---

## Step 2 — Build the Docker images

```bash
make build
```

This builds the backend and frontend images. Only needed once, or after changing dependencies.

---

## Step 3 — Start the database

```bash
docker-compose up -d mongodb
```

Wait a few seconds for MongoDB to become healthy before continuing.

---

## Step 4 — Initialize the database

```bash
make setup
```

Creates the collection, standard indexes, and the vector search index. **Run this once** — re-running it is safe but skips anything already created.

---

## Step 5 — Ingest the health documents

```bash
make ingest
```

Reads all `.md` files from `health_data_zip/`, chunks and embeds them with OpenAI, and stores them in MongoDB. This takes a few minutes depending on the number of files (~695 documents).

---

## Step 6 — Start the API and UI

```bash
make up
```

Starts MongoDB (if not already running), the FastAPI backend, and the Streamlit frontend.

| Service   | URL                          |
|-----------|------------------------------|
| Chat UI   | http://localhost:8501        |
| API       | http://localhost:8000        |
| API docs  | http://localhost:8000/docs   |

Open **http://localhost:8501** in your browser and start asking questions.

---

## All make commands

| Command                     | Description                                        |
|-----------------------------|----------------------------------------------------|
| `make build`                | Build all Docker images                            |
| `make up`                   | Start MongoDB, API, and Streamlit                  |
| `make down`                 | Stop all containers                                |
| `make setup`                | Initialize the database and vector index (once)    |
| `make ingest`               | Load all health_data_zip documents into MongoDB    |
| `make scrape url=<url>`     | Scrape a URL and store it as additional context    |
| `make query q="<question>"` | Ask a question from the command line               |
| `make logs`                 | Tail logs for the API and Streamlit                |
| `make clean`                | Stop containers and delete all stored data         |

---

## Chrome Extension

A lightweight chat popup that talks to your local API — no extra setup required beyond the Docker stack already running.

### Load the extension

1. Run `make build && make up` to ensure the backend is running with CORS enabled.
2. Open `chrome://extensions` in Chrome.
3. Enable **Developer mode** (toggle in the top-right corner).
4. Click **Load unpacked** and select the `extension/` folder in this project.
5. Click the extension icon in the Chrome toolbar to open the chat popup.

> The Docker stack must be running locally for the extension to work. The popup shows a **Connected** / **API offline** status badge so you always know the state.

---

## Inspecting the database

```bash
docker exec -it health-rag-mongodb mongosh \
  "mongodb://admin:password@localhost:27017/health_rag?authSource=admin"
```

Useful queries inside the shell:

```javascript
db.documents.countDocuments()
db.documents.distinct("metadata.source")
db.documents.find({}, { embedding: 0 }).limit(5).pretty()
```

---

## Troubleshooting

**"No relevant data found"** — The vector index hasn't been created or documents haven't been ingested. Run `make setup` then `make ingest`.

**"Could not connect to the API"** — The backend isn't running. Run `make up` and wait a few seconds for it to start.

**Ingest fails with an embedding error** — Check that `OPENAI_API_KEY` is set correctly in `.env`.
