# health-RAG
Usage:
  # Add an .env file and add your keys:
    OPENAI_API_KEY=SOME_KEY
    MONGO_URI=SOME_URI

  # 1. Start MongoDB
  docker-compose up -d mongodb

  # 2. Set up the database
  docker-compose run --rm setup

  # 3. Scrape a site
  docker-compose run --rm scraper https://www.in.gov/health/

  # 4. Ask a question
  docker-compose run --rm query "What is the Indiana department of health?"

# Ask a question
docker-compose run --rm query "What are the side effects of ibuprofen?"