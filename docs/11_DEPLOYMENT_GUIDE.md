# 11 Deployment Guide (Low-Level Design)

## Docker Multi-Stage Build (`docker/Dockerfile.prod`)

To deploy to Render/Koyeb, we need a small container. We use a multi-stage build pattern.

### Stage 1: Builder
Uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`.
We copy `pyproject.toml` and `uv.lock`. We run `uv sync --frozen --no-dev`. 
This guarantees deterministic dependency resolution. It places all packages into a `.venv`.

### Stage 2: Runtime
Uses a vanilla `python:3.12-slim-bookworm` image (no `uv` required).
We copy the `.venv` folder from Stage 1 into Stage 2.
We set `ENV PATH="/app/.venv/bin:$PATH"`. This makes Python use the virtual environment packages globally inside the container.

### Render Execution
Render spins up the container and runs the `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
Render automatically sets the `PORT` environment variable and maps traffic. We use 0.0.0.0 to bind to all interfaces, allowing Render's load balancers to forward traffic into the Docker container.
