.PHONY: dev test lint fmt

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -q

lint:
	python -m compileall app

fmt:
	python -m compileall app
