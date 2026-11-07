.PHONY: build up down setup scrape ingest query logs clean

build:
	docker-compose build

up:
	docker-compose up -d mongodb api streamlit

down:
	docker-compose down

setup:
	docker-compose run --rm setup

scrape:
	@if [ -z "$(url)" ]; then echo "Usage: make scrape url=https://example.com"; exit 1; fi
	docker-compose run --rm scraper $(url)

ingest:
	docker-compose run --rm ingest

query:
	@if [ -z "$(q)" ]; then echo "Usage: make query q=\"your question\""; exit 1; fi
	docker-compose run --rm query "$(q)"

logs:
	docker-compose logs -f api streamlit

clean:
	docker-compose down -v
