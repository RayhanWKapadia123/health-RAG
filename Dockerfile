FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper/ ./scraper/
COPY mongo-init/ ./mongo-init/
COPY src/ ./src/

WORKDIR /app/scraper

ENTRYPOINT ["python", "scrape.py"]
