FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN groupadd -r evaluator && useradd -r --uid 1001 -g evaluator evaluator

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev --extra all && \
    mkdir -p /home/evaluator/.cache/uv && \
    chown -R evaluator:evaluator /app && \
    chown -R evaluator:evaluator /home/evaluator/.cache

USER evaluator

ENV HOME=/home/evaluator
ENV XDG_CACHE_HOME=/home/evaluator/.cache

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "evaluator"]
