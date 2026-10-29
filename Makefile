# Run `make help`. Uses the virtualenv in .venv if present.
PY := $(shell [ -x $(CURDIR)/.venv/bin/python ] && echo $(CURDIR)/.venv/bin/python || echo python3)
export PATH := $(CURDIR)/.venv/bin:$(PATH)

.PHONY: help install test test-server test-eval check-dataset client run dev docker docker-run eval
help:
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

install: ## create .venv and install Python + client dependencies (ESLint: npm i -g eslint)
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt
	cd client && npm ci

test: test-server test-eval check-dataset ## run every offline test
test-server: ## server tests (add ARGS="-m integration" for the real-binary tests only)
	cd server && $(PY) -m pytest -q $(ARGS)
test-eval: ## evaluation tests
	cd evaluation && $(PY) -m pytest -q
check-dataset: ## generated dataset files match dataset/src
	cd evaluation && $(PY) build_dataset.py --check

client: ## type-check and build the UI into client/dist
	cd client && npx tsc -b && npx vite build
run: client ## API + built UI on http://localhost:8000
	cd server && $(PY) -m uvicorn main:app --port 8000
dev: ## API with reload on :8000; start the UI separately with `cd client && npm run dev`
	cd server && $(PY) -m uvicorn main:app --reload --port 8000

docker: ## build the image
	docker build -t code-review .
docker-run: ## run it on http://localhost:8000 (reads GEMINI_API_KEY from .env)
	docker run --rm -p 8000:8000 --env-file .env code-review

eval: ## resume the evaluation run (stops cleanly at the daily API quota)
	cd evaluation && $(PY) run_eval.py --system all --min-interval 5 --resume && $(PY) compute_metrics.py
