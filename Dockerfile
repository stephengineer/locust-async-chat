FROM python:3.14-slim AS base

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency and metadata files for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only (no dev group)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ src/

# Install the project itself
RUN uv sync --frozen --no-dev

# Locust web UI port
EXPOSE 8089
# Webhook callback port
EXPOSE 44379

# Run locust via uv so the virtualenv is activated
ENTRYPOINT ["uv", "run", "--no-dev", "locust", "-f", "src/locust_async_chat/locustfile.py"]
