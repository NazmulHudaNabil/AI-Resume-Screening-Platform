# 09 Environment Variables (Low-Level Design)

## `BaseSettings` (`app/core/config.py`)

We use Pydantic `BaseSettings` to manage configuration. This ensures that if an environment variable is missing, the application crashes on startup with a clear error, rather than failing randomly in production.

- `DATABASE_URL`: Passed to `sqlalchemy.ext.asyncio.create_async_engine()`. Must use an async driver (e.g., `postgresql+asyncpg://`).
- `QDRANT_URL` / `QDRANT_API_KEY`: Injected into the `QdrantClient` constructor.
- `REDIS_URL`: Passed to `redis.asyncio.from_url()`.
- `GROQ_API_KEY` / `GEMINI_API_KEY`: Used in HTTP Authorization headers for external API calls.
- `JWT_SECRET`: Used as the salt in `jwt.encode()`. Must be exactly matched across multiple instances if horizontally scaled.
