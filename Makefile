# Commandes du projet : make test, make up, make demo...
.PHONY: install test up down mcp worker gui lint

install:
	pip install -r requirements.txt

test:
	pytest -q

lint:
	ruff check src app tests

mcp:            ## serveur MCP seul (dev sans Docker)
	PYTHONPATH=src python -m bondalorians.mcp_server.server

worker:         ## worker seul (dev sans Docker)
	PYTHONPATH=src python -m bondalorians.worker.main

gui:            ## GUI seule (dev sans Docker)
	streamlit run app/Home.py

up:             ## toute la pile : GUI + MCP + worker
	docker compose up --build -d
	docker compose logs -f --tail=20

down:
	docker compose down
