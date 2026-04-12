.PHONY: install dev test lint format run clean docker

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

run:
	python -m src.cli demo

streamlit:
	streamlit run src/viz/app.py

docker:
	docker build -t combinatorial-auction .
	docker run -p 8501:8501 combinatorial-auction

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache *.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
