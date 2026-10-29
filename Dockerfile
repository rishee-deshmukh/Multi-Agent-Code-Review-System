# One image: the FastAPI backend, the static analysers it shells out to, and the built React UI,
# all served from one origin on one port. Nothing secret is baked in; pass GEMINI_API_KEY at run time.
ARG NODE_VERSION=22
ARG PYTHON_VERSION=3.12
ARG ESLINT_VERSION=10.13.0

# --- build the UI ---
FROM node:${NODE_VERSION}-slim AS client
WORKDIR /client
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

# --- ESLint, installed on the same Node it will run on ---
FROM node:${NODE_VERSION}-slim AS eslint
ARG ESLINT_VERSION
RUN npm install -g eslint@${ESLINT_VERSION}

# --- runtime ---
FROM python:${PYTHON_VERSION}-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    SEMGREP_SEND_METRICS=off \
    SEMGREP_ENABLE_VERSION_CHECK=0 \
    STATIC_DIR=/app/static \
    HOME=/home/app

COPY --from=eslint /usr/local/bin/node /usr/local/bin/node
COPY --from=eslint /usr/local/lib/node_modules/eslint /usr/local/lib/node_modules/eslint
RUN ln -s ../lib/node_modules/eslint/bin/eslint.js /usr/local/bin/eslint

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY server/ ./server/
COPY --from=client /client/dist ./static

# semgrep and eslint write caches under $HOME, so the unprivileged user needs a real one
RUN useradd --create-home --home-dir /home/app --uid 10001 app
USER app
WORKDIR /app/server

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)"
# $PORT is set by Render, Heroku-style hosts and Cloud Run
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
