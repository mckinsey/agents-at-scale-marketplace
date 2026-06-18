FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml ./
COPY src/ ./src/

RUN uv sync --no-dev

EXPOSE 8352

CMD ["uv", "run", "python", "-m", "telegram_channel"]
