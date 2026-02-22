.PHONY: install run test lint

install:
	pip install -e ".[dev]"

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
