FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY --chown=1000:1000 pyproject.toml ./
COPY --chown=1000:1000 src ./src

RUN uv sync --no-dev

USER 1000

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["python", "-m", "file_api"]
