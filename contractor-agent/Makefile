.PHONY: install start build clean

install:
	uv sync

start:
	uv run uvicorn main:app --reload --port 8001

build:
	uv sync

clean:
	rm -rf .venv __pycache__ .pytest_cache
