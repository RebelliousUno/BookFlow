FROM ghcr.io/astral-sh/uv:0.5.29 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app

ENV UV_NO_DEV=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev \
    && adk telemetry disable

COPY goodreads_agent/ ./goodreads_agent/

CMD ["adk", "run", "--in_memory", "goodreads_agent", "go"]
